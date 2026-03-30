import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import argparse
import sys
import dbus
import dbus.mainloop.glib
import uvicorn
import socket
import time
from threading import Thread
from fastapi import FastAPI
from pynput.keyboard import Key, Controller as KeyboardController
from socketio import ASGIApp, AsyncServer
import evdev
from evdev import UInput, ecodes as e, AbsInfo

# Core initialization
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)

# Global variables
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
keyboard = KeyboardController()
ui = None # Initialized in main
is_pressed = False

# HARDCODED IPs for testing
ANDROID_IP = "172.16.150.107"
SERVER_IP = "172.16.35.250"
UDP_INPUT_PORT = 9999

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
        token = int(time.time())
        options = {
            "session_handle_token": f"fd_session_{token}", 
            "handle_token": f"fd_handle_{token}"
        }
        request_path = self.iface.CreateSession(options)
        self.bus.add_signal_receiver(self.on_create_session, "Response", 
                                   "org.freedesktop.portal.Request", path=request_path)
        print(f"Awaiting Portal Authorization for {self.target_ip}...")
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
        except Exception as e:
            print(f"Failed to create pipeline: {e}")
            self.loop.quit()

# --- UDP Input Listener (Logic mirrored from working server.py) ---
def run_udp_input_listener():
    global is_pressed
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_INPUT_PORT))
    print(f"UDP Input Listener started on port {UDP_INPUT_PORT}")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            msg = data.decode('utf-8')
            # print(f"UDP: {msg}") 
            parts = msg.split(':')
            if not parts: continue
            
            cmd = parts[0]
            if cmd in ['D', 'M']:
                try:
                    params = parts[1].split(',')
                    x_norm, y_norm, p_norm = float(params[0]), float(params[1]), float(params[2])
                    
                    if not is_pressed:
                        ui.write(e.EV_KEY, e.BTN_TOUCH, 1)
                        is_pressed = True
                    
                    ui.write(e.EV_ABS, e.ABS_X, int(x_norm * SCREEN_WIDTH))
                    ui.write(e.EV_ABS, e.ABS_Y, int(y_norm * SCREEN_HEIGHT))
                    ui.write(e.EV_ABS, e.ABS_PRESSURE, int(p_norm * 255))
                    ui.syn()
                except: pass
            elif cmd == 'U':
                ui.write(e.EV_KEY, e.BTN_TOUCH, 0)
                ui.syn()
                is_pressed = False
        except Exception as ex:
            print(f"UDP Input Error: {ex}")

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    print(f"Android connected via Socket.IO: {sid}")
    await sio.emit('screen_resolution', {'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT}, to=sid)

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    capabilities = {
        e.EV_KEY: [e.BTN_TOUCH],
        e.EV_ABS: [
            (e.ABS_X, AbsInfo(value=0, min=0, max=SCREEN_WIDTH, fuzz=0, flat=0, resolution=0)),
            (e.ABS_Y, AbsInfo(value=0, min=0, max=SCREEN_HEIGHT, fuzz=0, flat=0, resolution=0)),
            (e.ABS_PRESSURE, AbsInfo(value=0, min=0, max=255, fuzz=0, flat=0, resolution=0)),
        ]
    }

    try:
        # User requested to omit props attribute in function call
        ui = UInput(capabilities, name='FingerDraw-Touchscreen', version=0x1)
        print("UInput device created successfully via evdev.")
    except Exception as ex:
        print(f"Error creating uinput device: {ex}")
        sys.exit(1)

    udp_thread = Thread(target=run_udp_input_listener)
    udp_thread.daemon = True
    udp_thread.start()

    api_thread = Thread(target=run_api)
    api_thread.daemon = True
    api_thread.start()

    print(f"--- FingerDraw Server v2 (UDP Mode) ---")
    print(f"Server IP: {SERVER_IP}")
    print(f"Android IP: {ANDROID_IP}")
    print(f"UDP Input Port: {UDP_INPUT_PORT}")
    print(f"---------------------------------------------")

    server = FingerDrawServer(ANDROID_IP)
    server.start()
