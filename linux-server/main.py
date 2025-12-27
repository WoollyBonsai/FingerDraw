import asyncio
import socket
from threading import Thread
import subprocess

import uvicorn
from fastapi import FastAPI
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from socketio import ASGIApp, AsyncServer

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GObject
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk

# Initialize GStreamer
Gst.init(None)
GObject.threads_init()

# Global variables for screen resolution
SCREEN_WIDTH = 1920 # Default or fallback
SCREEN_HEIGHT = 1080 # Default or fallback

def get_screen_resolution_wayland():
    """
    Gets the screen resolution on a Wayland system using Gdk.
    Returns a tuple (width, height) or None if unable to determine.
    """
    try:
        display = Gdk.Display.get_default()
        if display:
            # Get the primary monitor
            monitor = display.get_primary_monitor()
            if not monitor:
                # Fallback to the first monitor if no primary is found
                monitor = display.get_monitor(0)
            
            if monitor:
                geometry = monitor.get_geometry()
                return geometry.width, geometry.height
            else:
                print("No primary monitor found.")
        else:
            print("Could not get default Gdk display.")
    except Exception as e:
        print(f"An error occurred while getting screen resolution: {e}")
    return None

def start_tablet_stream(client_ip):
    # Pipeline for AMD Radeon 780M (VA-API)
    # - pipewiresrc: Captures Wayland without the screenshot 'flash'
    # - vaapih264enc: Uses your AMD GPU
    pipeline_str = (
        "pipewiresrc ! "
        "videoconvert ! "
        "video/x-raw,format=NV12 ! "
        "vaapih264enc rate-control=cbr bitrate=8000 ! "
        "h264parse ! "
        "rtph264pay pt=96 ! "
        f"udpsink host={client_ip} port=5000 sync=false"
    )
    print(f"Starting GStreamer pipeline: {pipeline_str}")
    
    # Use subprocess.Popen to run the gst-launch-1.0 command
    # This detaches the GStreamer pipeline from the Python script's GObject loop,
    # which is important since we are now running uvicorn in the main thread (or a separate thread).
    cmd = ["gst-launch-1.0"] + pipeline_str.split()
    return subprocess.Popen(cmd)

# --- Socket.IO Setup ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
app = ASGIApp(sio, app)

mouse = MouseController()
keyboard = KeyboardController()

gst_process = None

@sio.event
async def connect(sid, environ):
    global gst_process
    client_ip = environ['asgi.scope']['client'][0]
    print(f"Client connected: {sid}, IP: {client_ip}")
    if gst_process:
        gst_process.terminate()
    gst_process = start_tablet_stream(client_ip)

@sio.event
async def disconnect(sid):
    global gst_process
    print(f"Client disconnected: {sid}")
    if gst_process:
        gst_process.terminate()
        gst_process = None

# Note: start_stream and stop_stream are no longer needed as the client will connect to RTSP directly

@sio.event
async def mouse_move(sid, x, y):
    try:
        real_x = x * SCREEN_WIDTH
        real_y = y * SCREEN_HEIGHT
        mouse.position = (real_x, real_y)
    except Exception as e:
        print(f"Error processing mouse_move event: {e}")

@sio.event
async def mouse_down(sid, x, y):
    try:
        real_x = x * SCREEN_WIDTH
        real_y = y * SCREEN_HEIGHT
        mouse.position = (real_x, real_y)
        mouse.press(Button.left)
    except Exception as e:
        print(f"Error processing mouse_down event: {e}")

@sio.event
async def mouse_up(sid):
    try:
        mouse.release(Button.left)
    except Exception as e:
        print(f"Error processing mouse_up event: {e}")

@sio.event
async def right_click(sid):
    try:
        mouse.click(Button.right)
    except Exception as e:
        print(f"Error processing right_click event: {e}")

# ... other input event handlers (undo, redo, etc.) ...

def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def run_socketio_server():
    uvicorn.run(app, host="0.0.0.0", port=8000)

# --- Main Application ---
if __name__ == "__main__":
    ip_address = get_ip_address()
    print("--- FingerDraw Server ---")
    print(f"Socket.IO server running at: {ip_address}:8000")
    print("-------------------------")

    # Get screen resolution
    resolution = get_screen_resolution_wayland()
    if resolution:
        SCREEN_WIDTH, SCREEN_HEIGHT = resolution
        print(f"Detected screen resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    else:
        print(f"Could not detect screen resolution, using defaults: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    # Start the FastAPI/Socket.IO server in a separate thread
    socketio_thread = Thread(target=run_socketio_server)
    socketio_thread.daemon = True
    socketio_thread.start()

    # Keep the main thread alive to allow the Socket.IO thread to run
    try:
        while True:
            import time
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down server.")
        if gst_process:
            gst_process.terminate()
            gst_process.wait()