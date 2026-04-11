import os
import sys
import socket
import asyncio
from threading import Thread
from fastapi import FastAPI
from socketio import ASGIApp, AsyncServer
import uvicorn

# --- 1. GSTREAMER ENVIRONMENT SETUP ---
# No global environment variables needed; we inject them into the process here.
gst_root = r"C:\Program Files\gstreamer\1.0\msvc_x86_64"
bin_path = os.path.join(gst_root, "bin")
gi_path = os.path.join(gst_root, "lib", "site-packages")

os.environ['PATH'] = bin_path + os.pathsep + os.environ.get('PATH', '')
os.add_dll_directory(bin_path)
sys.path.insert(0, gi_path)
os.environ['GI_TYPELIB_PATH'] = os.path.join(gst_root, "lib", "girepository-1.0")
os.environ['GST_PLUGIN_PATH'] = os.path.join(gst_root, "lib", "gstreamer-1.0")

try:
    import gi
    gi.require_version('Gst', '1.0')
    from gi.repository import Gst
    Gst.init(None)
    print("SUCCESS: GStreamer 1.0 Engine Loaded")
except Exception as e:
    print(f"FATAL: GStreamer linking failed. Check path: {e}")
    sys.exit(1)

# --- 2. CONFIGURATION & NETWORKING ---
UDP_WORKER_PORT = 9999  # Local C++ Worker Port
STREAM_PORT = 5000      # Video Port (UDP to Android)
API_PORT = 8000         # Web/Socket.IO Port

# Primary screen metrics for Android normalization
import ctypes
user32 = ctypes.windll.user32
SCREEN_WIDTH = user32.GetSystemMetrics(0)
SCREEN_HEIGHT = user32.GetSystemMetrics(1)

# Socket for relaying data to C++ Worker
relay_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

# --- 3. STREAMING ENGINE ---
class FingerDrawStreamer:
    def __init__(self):
        self.pipeline = None

    def start(self, target_ip):
        self.stop()
        
        # Pipeline: DXGI Capture -> GPU Convert -> Download to RAM -> x264 Software Enc -> UDP Sink
        # This setup avoids "no element d3d11h264enc" by using x264enc (CPU)
        pipeline_str = (
            f"d3d11screencapturesrc capture-api=dxgi do-timestamp=true ! "
            f"queue leaky=downstream max-size-buffers=1 ! "
            f"d3d11convert ! "
            f"video/x-raw(memory:D3D11Memory),width=2560,height=1440,framerate=40/1 ! "
            f"d3d11download ! "
            f"video/x-raw,format=I420 ! "
            f"x264enc bitrate=8000 tune=zerolatency speed-preset=ultrafast ! "
            f"rtph264pay config-interval=1 ! "
            f"udpsink host={target_ip} port={STREAM_PORT} sync=false"
        )
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.pipeline.set_state(Gst.State.PLAYING)
            print(f"VIDEO STREAM ACTIVE -> {target_ip}:{STREAM_PORT}")
        except Exception as e:
            print(f"GStreamer Pipeline Error: {e}")

    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
            self.pipeline = None
            print("Video Stream Stopped.")

fd_engine = FingerDrawStreamer()

# --- 4. FASTAPI & SOCKET.IO GATEWAY ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
fastapi_app = FastAPI()
app = ASGIApp(sio, fastapi_app)

@sio.event
async def connect(sid, environ):
    # Retrieve true Android IP from ASGI scope or headers
    scope = environ.get('asgi.scope', {})
    client = scope.get('client')
    
    if client:
        client_ip = client[0]
    else:
        client_ip = environ.get('HTTP_X_FORWARDED_FOR', environ.get('REMOTE_ADDR', '127.0.0.1'))
    
    if ',' in client_ip:
        client_ip = client_ip.split(',')[0].strip()

    print(f"HANDSHAKE: Android device connected from {client_ip}")
    
    # Start the video stream to the phone
    fd_engine.start(client_ip)
    
    # Send resolution to Android for coordinate scaling
    await sio.emit('screen_resolution', {'width': SCREEN_WIDTH, 'height': SCREEN_HEIGHT}, to=sid)

@sio.on("input_data")
async def handle_input(sid, data):
    """
    Relays Android touch data ("D:x,y,p", "M:x,y,p", "U") to C++ Worker.
    """
    try:
        relay_sock.sendto(data.encode('utf-8'), ("127.0.0.1", UDP_WORKER_PORT))
    except Exception as e:
        print(f"Relay Error: {e}")

@sio.event
async def disconnect(sid):
    print("Client Disconnected.")
    fd_engine.stop()

# --- 5. EXECUTION ---
if __name__ == "__main__":
    print(f"--- FINGERDRAW PYTHON GATEWAY ---")
    print(f"API/Socket.IO: {API_PORT} | Stream Port: {STREAM_PORT}")
    print(f"Targeting C++ Worker on: 127.0.0.1:{UDP_WORKER_PORT}")
    
    # Run Uvicorn Server
    uvicorn.run(app, host="0.0.0.0", port=API_PORT, log_level="info")