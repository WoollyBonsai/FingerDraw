import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import socket
import struct
import sys
import time
from threading import Thread

Gst.init(None)

class VideoReceiver:
    def __init__(self, port=5000):
        self.port = port
        self.pipeline = None
        self.loop = GLib.MainLoop()

    def start(self):
        # Pipeline for receiving RTP H264 stream
        # Using avdec_h264 for software decoding (available on most systems)
        # Using autovideosink for display
        pipeline_str = (
            f"udpsrc port={self.port} ! "
            "application/x-rtp,media=video,clock-rate=90000,encoding-name=H264,payload=96 ! "
            "rtpjitterbuffer latency=0 mode=0 ! "
            "rtph264depay ! h264parse ! avdec_h264 ! "
            "videoconvert ! autovideosink sync=false"
        )
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            print(f"Failed to create pipeline: {e}")
            return

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self.on_error)
        bus.connect("message::eos", self.on_eos)

        self.pipeline.set_state(Gst.State.PLAYING)
        print(f"Video Receiver started on port {self.port}...")
        
        self.thread = Thread(target=self.loop.run)
        self.thread.start()

    def on_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"GStreamer Error: {err.message}")
        self.stop()

    def on_eos(self, bus, msg):
        print("End of stream")
        self.stop()

    def stop(self):
        if self.pipeline:
            self.pipeline.set_state(Gst.State.NULL)
        if self.loop.is_running():
            self.loop.quit()

class InputSender:
    def __init__(self, server_ip="127.0.0.1", port=5001):
        self.server_ip = server_ip
        self.port = port
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send_event(self, event_type, x, y, pressure):
        """
        Sends an input event via UDP.
        Format: B (type), f (x), f (y), f (pressure)
        """
        data = struct.pack("!Bfff", event_type, x, y, pressure)
        self.sock.sendto(data, (self.server_ip, self.port))

    def close(self):
        self.sock.close()

if __name__ == "__main__":
    server_ip = "127.0.0.1"
    video_port = 5000
    input_port = 5001

    if len(sys.argv) > 1:
        server_ip = sys.argv[1]

    print(f"--- FingerDraw Test Receiver ---")
    print(f"Server IP: {server_ip}")
    print(f"Video Port: {video_port}")
    print(f"Input Port: {input_port}")
    print(f"--------------------------------")

    receiver = VideoReceiver(port=video_port)
    receiver.start()

    sender = InputSender(server_ip=server_ip, port=input_port)

    print("\nControls:")
    print("  This script currently only displays the video.")
    print("  Input sending is implemented in the InputSender class but not yet hooked to UI events.")
    print("  Press Ctrl+C to stop.")

    try:
        while True:
            # For now, we just keep it alive. 
            # In a real app, this would be hooked to touch events.
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down receiver...")
        receiver.stop()
        sender.close()
        print("Stopped.")
