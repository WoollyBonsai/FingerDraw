import asyncio
import socket
from threading import Thread
from urllib.parse import parse_qs

import uvicorn
import uinput
from fastapi import FastAPI
from pynput.keyboard import Key, Controller as KeyboardController
from socketio import ASGIApp, AsyncServer

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
gi.require_version('GstRtspServer', '1.0')
from gi.repository import GstRtspServer
gi.require_version("Gdk", "3.0")
from gi.repository import Gdk

from jeepney import DBusAddress, new_method_call
from jeepney.io.asyncio import open_dbus_router
from jeepney.low_level import Variant

# Initialize GStreamer
Gst.init(None)

# Global variables
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

def get_screen_resolution_wayland():
    """
    Gets the screen resolution on a Wayland system using Gdk.
    Returns a tuple (width, height) or None if unable to determine.
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
            else:
                print("No primary monitor found.")
        else:
            print("Could not get default Gdk display.")
    except Exception as e:
        print(f"An error occurred while getting screen resolution: {e}")
    return None

async def get_pipewire_node_id():
    """
    Uses jeepney to request a screen cast session and returns the PipeWire node ID.
    """
    try:
        portal_addr = DBusAddress(
            '/org/freedesktop/portal/desktop',
            bus_name='org.freedesktop.portal.Desktop',
            interface='org.freedesktop.portal.ScreenCast'
        )

        async with open_dbus_router(bus='SESSION') as router:
            # Create a session
            create_session_msg = new_method_call(
                portal_addr, 'CreateSession', 'a{sv}', ({},)
            )
            reply = await router.send_and_get_reply(create_session_msg)
            
            # The reply contains the object path for the new session
            session_handle = reply.body[0] 

            # FIX: Create a NEW DBusAddress for the session instead of using .replace()
            session_addr = DBusAddress(
                session_handle, # Use the new path here
                bus_name='org.freedesktop.portal.Desktop',
                interface='org.freedesktop.portal.ScreenCast'
            )

            # Select sources
            select_sources_msg = new_method_call(
                session_addr, 'SelectSources', 'a{sv}',
                ({'multiple': Variant('b', False), 'types': Variant('u', 1)},)
            )
            await router.send_and_get_reply(select_sources_msg)

            # Start the stream
            start_msg = new_method_call(
                session_addr, 'Start', 's', ('',)
            )
            reply = await router.send_and_get_reply(start_msg)
            streams = reply.body[1]
            node_id = streams['streams'][0][1]

            print(f"PipeWire node ID: {node_id}")
            return node_id
    except Exception as e:
        print(f"Error getting PipeWire node ID: {e}")
        return None

def get_gstreamer_pipeline(node_id):
    pipeline_str = (
        f"pipewiresrc path={node_id} ! "
        "videoconvert ! "
        "video/x-raw,format=NV12 ! "
        "vaapih264enc rate-control=cbr bitrate=8000 ! "
        "rtph264pay name=pay0 pt=96"
    )
    return pipeline_str

class GstServer(GstRtspServer.RTSPServer):
    def __init__(self, **properties):
        super().__init__(**properties)
        self.factory = GstRtspServer.RTSPMediaFactory()
        self.factory.set_launch_string(get_gstreamer_pipeline(None))
        self.factory.set_shared(True)
        self.get_mount_points().add_factory("/test", self.factory)
        self.attach(None)

# --- Socket.IO Setup ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
app = ASGIApp(sio, app)

# --- Uinput Setup ---
device = uinput.Device([
    uinput.ABS_X + (0, SCREEN_WIDTH, 0, 0),
    uinput.ABS_Y + (0, SCREEN_HEIGHT, 0, 0),
    uinput.ABS_PRESSURE + (0, 255, 0, 0),
    uinput.BTN_TOUCH,
    uinput.BTN_TOOL_PEN,
])

keyboard = KeyboardController()

gst_server = None

@sio.event
async def connect(sid, environ):
    global gst_server
    client_ip = environ['asgi.scope']['client'][0]
    query_string = environ.get('query_string', b'').decode()
    query_params = parse_qs(query_string)
    quality = query_params.get('quality', ['Medium'])[0]
    
    print(f"Client connected: {sid}, IP: {client_ip}, Quality: {quality}")

    await sio.emit('screen_resolution', {'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT}, to=sid)

    node_id = await get_pipewire_node_id()
    if not node_id:
        print("Failed to get PipeWire node ID. Cannot start stream.")
        return
    
    if gst_server:
        # We don't need to do anything here as the server is already running
        pass
    else:
        gst_server = GstServer()

    # Update the pipeline with the correct node_id
    gst_server.factory.set_launch_string(get_gstreamer_pipeline(node_id))
    print(f"RTSP stream available at: rtsp://{get_ip_address()}:8554/test")

@sio.event
async def disconnect(sid):
    global gst_server
    print(f"Client disconnected: {sid}")
    # No need to do anything here as the RTSP server keeps running
    pass

@sio.event
async def mouse_move(sid, x, y, pressure):
    try:
        real_x = int(x * SCREEN_WIDTH)
        real_y = int(y * SCREEN_HEIGHT)
        device.emit(uinput.ABS_X, real_x)
        device.emit(uinput.ABS_Y, real_y)
        device.emit(uinput.ABS_PRESSURE, int(pressure * 255))
    except Exception as e:
        print(f"Error processing mouse_move event: {e}")

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
        print(f"Error processing mouse_down event: {e}")

@sio.event
async def mouse_up(sid):
    try:
        device.emit(uinput.BTN_TOUCH, 0)
    except Exception as e:
        print(f"Error processing mouse_up event: {e}")

@sio.event
async def right_click(sid):
    try:
        keyboard.press(Key.ctrl)
        keyboard.press(Key.shift)
        keyboard.press(Key.f10)
        keyboard.release(Key.f10)
        keyboard.release(Key.shift)
        keyboard.release(Key.ctrl)
    except Exception as e:
        print(f"Error processing right_click event: {e}")

@sio.event
async def middle_click(sid):
    try:
        keyboard.press(Key.shift)
        keyboard.press(Key.f10)
        keyboard.release(Key.f10)
        keyboard.release(Key.shift)
    except Exception as e:
        print(f"Error processing middle_click event: {e}")

@sio.event
async def undo(sid):
    try:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('z')
            keyboard.release('z')
    except Exception as e:
        print(f"Error processing undo event: {e}")

@sio.event
async def redo(sid):
    try:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('y')
            keyboard.release('y')
    except Exception as e:
        print(f"Error processing redo event: {e}")

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

    resolution = get_screen_resolution_wayland()
    if resolution:
        SCREEN_WIDTH, SCREEN_HEIGHT = resolution
        print(f"Detected screen resolution: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")
    else:
        print(f"Could not detect screen resolution, using defaults: {SCREEN_WIDTH}x{SCREEN_HEIGHT}")

    socketio_thread = Thread(target=run_socketio_server)
    socketio_thread.daemon = True
    socketio_thread.start()

    loop = GLib.MainLoop()
    try:
        loop.run()
    except KeyboardInterrupt:
        print("Shutting down server.")
        if gst_server:
            gst_server.factory.set_launch_string("videotestsrc ! rtph264pay name=pay0 pt=96") # Stop the stream
            gst_server.get_mount_points().remove_factory("/test")
        loop.quit()