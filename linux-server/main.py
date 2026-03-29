import argparse
import asyncio
import socket
import time
from threading import Thread
from urllib.parse import parse_qs

import uvicorn
import uinput
from fastapi import FastAPI
from pynput.keyboard import Key, Controller as KeyboardController
from socketio import ASGIApp, AsyncServer

from udp_streamer import WaylandUdpServer

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk

# Initialize GStreamer
Gst.init(None)

# Global variables
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
udp_server = None

def get_screen_resolution_wayland():
    """
    Gets the screen resolution on a Wayland system using Gdk.
    """
    try:
        display = Gdk.Display.get_default()
        if display:
            monitor = display.get_primary_monitor()
            if not monitor:
                monitor = display.get_monitor(0)
            
            if monitor:
                geometry = monitor.get_geometry()
                return geometry.width, geometry.height
    except Exception as e:
        print(f"An error occurred while getting screen resolution: {e}")
    return None

# --- Socket.IO Setup ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
app = ASGIApp(sio, app)

# --- Uinput Setup ---
# Creating a high-resolution input device
device = uinput.Device([
    uinput.ABS_X + (0, SCREEN_WIDTH, 0, 0),
    uinput.ABS_Y + (0, SCREEN_HEIGHT, 0, 0),
    uinput.ABS_PRESSURE + (0, 255, 0, 0),
    uinput.BTN_TOUCH,
    uinput.BTN_TOOL_PEN,
])

keyboard = KeyboardController()

@sio.event
async def connect(sid, environ):
    global udp_server
    client_ip = environ['asgi.scope']['client'][0]
    print(f"Client connected: {sid}, IP: {client_ip}")

    # Send resolution to client for mapping (optional)
    await sio.emit('screen_resolution', {'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT}, to=sid)

    if udp_server is None:
        print(f"Starting UDP stream to {client_ip}:5000")
        udp_server = WaylandUdpServer(target_ip=client_ip, port=5000)
        udp_server.start()
        udp_server.run_loop()

@sio.event
async def disconnect(sid):
    global udp_server
    print(f"Client disconnected: {sid}")
    # Note: In a multi-user scenario, we'd count sessions. 
    # For FingerDraw, one client at a time is the standard.

@sio.event
async def mouse_move(sid, x, y, pressure):
    try:
        # Map normalized 0.0-1.0 to screen pixels
        real_x = int(x * SCREEN_WIDTH)
        real_y = int(y * SCREEN_HEIGHT)
        device.emit(uinput.ABS_X, real_x)
        device.emit(uinput.ABS_Y, real_y)
        device.emit(uinput.ABS_PRESSURE, int(pressure * 255))
    except Exception as e:
        print(f"Error in mouse_move: {e}")

@sio.event
async def mouse_down(sid, x, y, pressure):
    try:
        real_x = int(x * SCREEN_WIDTH)
        real_y = int(y * SCREEN_HEIGHT)
        device.emit(uinput.ABS_X, real_x)
        device.emit(uinput.ABS_Y, real_y)
        device.emit(uinput.ABS_PRESSURE, int(pressure * 255))
        device.emit(uinput.BTN_TOUCH, 1)
    except Exception as e:
        print(f"Error in mouse_down: {e}")

@sio.event
async def mouse_up(sid):
    try:
        device.emit(uinput.BTN_TOUCH, 0)
    except Exception as e:
        print(f"Error in mouse_up: {e}")

# Shortcuts
@sio.event
async def undo(sid):
    with keyboard.pressed(Key.ctrl):
        keyboard.press('z')
        keyboard.release('z')

@sio.event
async def redo(sid):
    with keyboard.pressed(Key.ctrl):
        keyboard.press('y')
        keyboard.release('y')

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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="FingerDraw Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()

    resolution = get_screen_resolution_wayland()
    if resolution:
        SCREEN_WIDTH, SCREEN_HEIGHT = resolution
        print(f"Detected screen resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    print(f"--- FingerDraw Server Running ---")
    print(f"IP: {get_ip_address()}")
    print(f"Port: {args.port}")
    print(f"---------------------------------")

    uvicorn.run(app, host=args.host, port=args.port)
