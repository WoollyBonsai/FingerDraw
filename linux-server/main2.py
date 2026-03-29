import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import argparse
import sys
import dbus
import dbus.mainloop.glib
import uvicorn
import uinput
import socket
import time
from threading import Thread
from fastapi import FastAPI
from pynput.keyboard import Key, Controller as KeyboardController
from socketio import ASGIApp, AsyncServer

# Core initialization
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)

# Global variables
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
keyboard = KeyboardController()
device = None # Initialized in main

# --- Socket.IO Setup ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
app = ASGIApp(sio, app)

class FingerDrawServer:
    def __init__(self, target_ip, port=5000):
        self.bus = dbus.SessionBus()
        self.target_ip = target_ip
        self.port = port
        self.pipeline = None
        self.loop = GLib.MainLoop()
        
        self.proxy = self.bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
        self.iface = dbus.Interface(self.proxy, "org.freedesktop.portal.ScreenCast")

    def start(self):
        options = {"session_handle_token": "fd_session", "handle_token": "fd_handle"}
        request_path = self.iface.CreateSession(options)
        self.bus.add_signal_receiver(self.on_create_session, "Response", 
                                   "org.freedesktop.portal.Request", path=request_path)
        print("Awaiting Portal Authorization (Check your desktop prompts)...")
        self.loop.run()

    def on_create_session(self, response, results):
        if response != 0: 
            print(f"Session failed: {response}")
            self.loop.quit()
            return
        self.session_handle = results['session_handle']
        options = {"handle_token": "fd_handle_2", "types": dbus.UInt32(1), "multiple": False}
        request_path = self.iface.SelectSources(self.session_handle, options)
        self.bus.add_signal_receiver(self.on_select_sources, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_select_sources(self, response, results):
        if response != 0: 
            print("Selection cancelled")
            self.loop.quit()
            return
        options = {"handle_token": "fd_handle_3"}
        request_path = self.iface.Start(self.session_handle, "", options)
        self.bus.add_signal_receiver(self.on_start, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_start(self, response, results):
        if response != 0: 
            print("Start failed")
            self.loop.quit()
            return
        node_id = results['streams'][0][0]
        fd_obj = self.iface.OpenPipeWireRemote(self.session_handle, {})
        fd = fd_obj.take() 
        self.launch_pipeline(fd, node_id)

    def launch_pipeline(self, fd, node_id):
        pipeline_str = f"""
            pipewiresrc fd={fd} path={node_id} do-timestamp=true !
            queue leaky=downstream max-size-buffers=1 !
            videoconvert !
            videoscale !
            video/x-raw,width=1280,height=720 !
            videoconvert !
            x264enc tune=zerolatency bitrate=3000 speed-preset=ultrafast ! 
            video/x-h264,profile=baseline !
            rtph264pay config-interval=1 !
            udpsink host={self.target_ip} port={self.port} sync=false
        """
        
        print(f"Streaming screen to {self.target_ip}:{self.port}...")
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.pipeline.set_state(Gst.State.PLAYING)
            print("--- STREAM ACTIVE ---")
            
            bus = self.pipeline.get_bus()
            bus.add_signal_watch()
            bus.connect("message::error", self.on_error)
        except Exception as e:
            print(f"Failed to create pipeline: {e}")
            self.loop.quit()

    def on_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"GStreamer Error: {err.message}")
        self.loop.quit()

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    print(f"Android connected: {sid}")
    await sio.emit('screen_resolution', {'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT}, to=sid)

@sio.event
async def mouse_move(sid, x, y, pressure):
    if device:
        device.emit(uinput.ABS_X, int(x * SCREEN_WIDTH))
        device.emit(uinput.ABS_Y, int(y * SCREEN_HEIGHT))
        device.emit(uinput.ABS_PRESSURE, int(pressure * 255))

@sio.event
async def mouse_down(sid, x, y, pressure):
    if device:
        device.emit(uinput.ABS_X, int(x * SCREEN_WIDTH))
        device.emit(uinput.ABS_Y, int(y * SCREEN_HEIGHT))
        device.emit(uinput.ABS_PRESSURE, int(pressure * 255))
        device.emit(uinput.BTN_TOUCH, 1)

@sio.event
async def mouse_up(sid):
    if device:
        device.emit(uinput.BTN_TOUCH, 0)

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

def get_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
    except:
        return "127.0.0.1"
    finally:
        s.close()

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("ip", help="Android Device IP")
    args = parser.parse_args()

    # Initialize uinput
    device = uinput.Device([
        uinput.ABS_X + (0, SCREEN_WIDTH, 0, 0),
        uinput.ABS_Y + (0, SCREEN_HEIGHT, 0, 0),
        uinput.ABS_PRESSURE + (0, 255, 0, 0),
        uinput.BTN_TOUCH,
        uinput.BTN_TOOL_PEN,
    ])

    # Start Socket.IO in background
    api_thread = Thread(target=run_api)
    api_thread.daemon = True
    api_thread.start()

    print(f"--- FingerDraw Server v2 ---")
    print(f"PC IP: {get_ip()}")
    print(f"Android Target: {args.ip}")
    print(f"Socket.IO Port: 8000")
    print(f"-----------------------------")

    # Start GStreamer / Portal logic in main thread
    server = FingerDrawServer(args.ip)
    server.start()
