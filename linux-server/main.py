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
import asyncio
from threading import Thread
from fastapi import FastAPI
from pynput.keyboard import Key, Controller as KeyboardController
from socketio import ASGIApp, AsyncServer
import evdev
from evdev import UInput, ecodes as e, AbsInfo

parser = argparse.ArgumentParser(description="FingerDraw Linux Server")
parser.add_argument("--api-port", type=int, default=8000, help="Socket.IO/API Port (default: 8000)")
parser.add_argument("--udp-input-port", type=int, default=9999, help="UDP Input Port (default: 9999)")
parser.add_argument("--video-port", type=int, default=5000, help="UDP Video Stream Port (default: 5000)")
args = parser.parse_args()

# Core initialization
dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)

# Global variables
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
keyboard = KeyboardController()
ui = None # Initialized in main
is_pressed = False
UDP_INPUT_PORT = args.udp_input_port
API_PORT = args.api_port
VIDEO_PORT = args.video_port
detected_android_ip = None

# --- Socket.IO Setup ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
fastapi_app = FastAPI()
app = ASGIApp(sio, fastapi_app)

class FingerDrawServer:
    def __init__(self, target_ip=None, port=VIDEO_PORT):
        self.bus = dbus.SessionBus()
        self.target_ip = target_ip
        self.port = port
        self.pipeline = None
        self.loop = None
        self.gst_thread = None
        
        self.proxy = self.bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
        self.iface = dbus.Interface(self.proxy, "org.freedesktop.portal.ScreenCast")

    def start(self, target_ip):
        print(f"--- STARTING STREAM FOR {target_ip} ---")
        self.target_ip = target_ip
        
        # STOP PREVIOUS PIPELINE IF RUNNING
        self.stop()
        
        self.loop = GLib.MainLoop()
        self.gst_thread = Thread(target=self._run_gst_loop)
        self.gst_thread.start()

    def _run_gst_loop(self):
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

    def stop(self):
        if self.pipeline:
            print("Cleaning up GStreamer pipeline...")
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            print("--- STREAM STOPPED ---")
        if self.loop:
            self.loop.quit()
            self.loop = None

    def on_create_session(self, response, results):
        if response != 0: 
            print(f"Session failed: {response}")
            if self.loop: self.loop.quit()
            return
        self.session_handle = results['session_handle']
        options = {"handle_token": "fd_handle_2", "types": dbus.UInt32(1), "multiple": False}
        request_path = self.iface.SelectSources(self.session_handle, options)
        self.bus.add_signal_receiver(self.on_select_sources, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_select_sources(self, response, results):
        if response != 0: 
            print("Selection cancelled")
            if self.loop: self.loop.quit()
            return
        options = {"handle_token": "fd_handle_3"}
        request_path = self.iface.Start(self.session_handle, "", options)
        self.bus.add_signal_receiver(self.on_start, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_start(self, response, results):
        if response != 0: 
            print("Start failed")
            if self.loop: self.loop.quit()
            return
        node_id = results['streams'][0][0]
        fd_obj = self.iface.OpenPipeWireRemote(self.session_handle, {})
        fd = fd_obj.take() 
        self.launch_pipeline(fd, node_id)

    def launch_pipeline(self, fd, node_id):
        # Optimized for low latency and lower bandwidth
        # target-usage=4 is a better balance for quality vs speed
        pipeline_str = f"""
            pipewiresrc fd={fd} path={node_id} do-timestamp=true !
            queue leaky=downstream max-size-buffers=1 !
            videoconvert !
            videorate !
            videoscale !
            video/x-raw,width=1280,height=720,framerate=40/1,format=I420 !
            videoconvert !
            video/x-raw,format=NV12 !
            vah264enc bitrate=1500 rate-control=cbr target-usage=4 ! 
            rtph264pay config-interval=1 !
            udpsink host={self.target_ip} port={self.port} sync=false
        """
        
        print(f"Streaming screen to {self.target_ip}:{self.port} via VA-API...")
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.pipeline.set_state(Gst.State.PLAYING)
            print("--- STREAM ACTIVE ---")
        except Exception as e:
            print(f"Failed to create pipeline: {e}")
            if self.loop: self.loop.quit()

# Global server instance
fd_server = FingerDrawServer()

# --- UDP Input Listener ---
def run_udp_input_listener():
    global is_pressed, detected_android_ip
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", UDP_INPUT_PORT))
    print(f"UDP Input Listener started on port {UDP_INPUT_PORT}")
    
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            
            # Auto-detect IP from the sender of UDP packets
            if detected_android_ip != addr[0]:
                detected_android_ip = addr[0]
                print(f"--- AUTO-DETECTED ANDROID IP: {detected_android_ip} ---")

            msg = data.decode('utf-8')
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
            elif cmd == 'ALT':
                state = int(parts[1])
                if state == 1:
                    keyboard.press(Key.alt)
                else:
                    keyboard.release(Key.alt)
            elif cmd == 'META':
                keyboard.tap(Key.cmd)
            elif cmd == 'TAB':
                keyboard.tap(Key.tab)
            else:
                # Debug message
                pass
        except Exception as ex:
            print(f"UDP Input Error: {ex}")

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    global detected_android_ip
    print(f"Socket.IO Handshake initiated (SID: {sid})")
    
    # Wait up to 3 seconds for the UDP listener to catch a packet if it hasn't yet
    timeout = 30 
    while not detected_android_ip and timeout > 0:
        await asyncio.sleep(0.1)
        timeout -= 1

    target_ip = detected_android_ip if detected_android_ip else "127.0.0.1"
    
    if target_ip == "127.0.0.1":
        print("!! WARNING: No UDP packets detected. !!")
    
    print(f"Resolved Android IP for GStreamer: {target_ip}")
    
    fd_server.start(target_ip)
    await sio.emit('screen_resolution', {'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT}, to=sid)

@sio.event
async def restart_stream(sid):
    global detected_android_ip
    target_ip = detected_android_ip if detected_android_ip else "127.0.0.1"
    print(f"Restart stream requested for {target_ip}")
    fd_server.start(target_ip)

@sio.event
async def disconnect_request(sid):
    print(f"Disconnect requested by sid: {sid}")
    fd_server.stop()
    await sio.emit('disconnect_ack', to=sid)

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")
    fd_server.stop()

def run_api():
    uvicorn.run(app, host="0.0.0.0", port=API_PORT)

import subprocess

def get_local_ips():
    try:
        output = subprocess.check_output(['hostname', '-I']).decode('utf-8').strip()
        ips = [ip for ip in output.split() if not ip.startswith('127.')]
        return ips
    except Exception:
        return []

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

    print(f"--- FingerDraw Server v2.1 ---")
    local_ips = get_local_ips()
    if local_ips:
        print(f"Available IP Addresses: {', '.join(local_ips)}")
    else:
        print("Could not determine local IP addresses.")
    print(f"Waiting for Android connection on port {API_PORT}...")
    print(f"UDP Input Port: {UDP_INPUT_PORT}")
    print(f"UDP Video Port: {VIDEO_PORT}")
    print(f"---------------------------------------------")

    # Main thread keeps running to allow KeyboardInterrupt
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down server...")
        fd_server.stop()
        sys.exit(0)
