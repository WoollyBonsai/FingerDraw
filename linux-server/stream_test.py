import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import argparse
import sys
import socket

Gst.init(None)

def get_local_ip():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

def stream_file(file_path, target_ip, port):
    # Pipeline to stream a file over UDP/RTP with RE-ENCODING for maximum compatibility
    # We use x264enc (CPU) as requested/implied for stability
    # tune=zerolatency is critical for real-time applications
    pipeline_str = f"""
        filesrc location={file_path} ! 
        qtdemux ! 
        h264parse ! 
        avdec_h264 ! 
        videoconvert ! 
        videoscale ! 
        capsfilter caps="video/x-raw,width=1280,height=720" !
        x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast ! 
        rtph264pay config-interval=1 ! 
        udpsink host={target_ip} port={port} sync=true
    """
    
    print(f"--- FingerDraw Streamer ---")
    print(f"File: {file_path}")
    print(f"Target: {target_ip}:{port}")
    print(f"----------------------------")
    print(f"Pipeline: {pipeline_str}")
    
    try:
        pipeline = Gst.parse_launch(pipeline_str)
        pipeline.set_state(Gst.State.PLAYING)
        
        loop = GLib.MainLoop()
        
        bus = pipeline.get_bus()
        bus.add_signal_watch()
        
        def on_message(bus, msg):
            if msg.type == Gst.MessageType.EOS:
                print("End of stream. Restarting...")
                pipeline.set_state(Gst.State.READY)
                pipeline.set_state(Gst.State.PLAYING)
            elif msg.type == Gst.MessageType.ERROR:
                err, debug = msg.parse_error()
                print(f"Error: {err.message}")
                loop.quit()
        
        bus.connect("message", on_message)
        loop.run()
        
    except Exception as e:
        print(f"Failed to start stream: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream a video file over UDP/RTP (re-encoded)")
    parser.add_argument("file", help="Path to the video file")
    parser.add_argument("ip", help="Target IP address (the Android device IP)")
    parser.add_argument("--port", type=int, default=5000, help="Target port (default: 5000)")
    
    args = parser.parse_args()
    stream_file(args.file, args.ip, args.port)
