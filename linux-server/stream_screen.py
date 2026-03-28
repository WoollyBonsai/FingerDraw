import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import argparse
import sys
import dbus
import dbus.mainloop.glib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)

class ScreenStreamer:
    def __init__(self, target_ip, port=5000):
        self.bus = dbus.SessionBus()
        self.target_ip = target_ip
        self.port = port
        self.pipeline = None
        self.loop = GLib.MainLoop()
        
        self.proxy = self.bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
        self.iface = dbus.Interface(self.proxy, "org.freedesktop.portal.ScreenCast")

    def start(self):
        options = {"session_handle_token": "session_screen", "handle_token": "handle_screen"}
        request_path = self.iface.CreateSession(options)
        self.bus.add_signal_receiver(self.on_create_session, "Response", 
                                   "org.freedesktop.portal.Request", path=request_path)
        print("Awaiting Portal Authorization...")
        self.loop.run()

    def on_create_session(self, response, results):
        if response != 0: 
            print(f"Session failed: {response}")
            self.loop.quit()
            return
        self.session_handle = results['session_handle']
        options = {"handle_token": "handle_screen_2", "types": dbus.UInt32(1), "multiple": False}
        request_path = self.iface.SelectSources(self.session_handle, options)
        self.bus.add_signal_receiver(self.on_select_sources, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_select_sources(self, response, results):
        if response != 0: 
            print("Selection cancelled")
            self.loop.quit()
            return
        options = {"handle_token": "handle_screen_3"}
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
        # Force baseline profile for maximum Android compatibility
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

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Stream live screen over UDP/RTP")
    parser.add_argument("ip", help="Target Android IP address")
    parser.add_argument("--port", type=int, default=5000, help="Target port (default: 5000)")
    
    args = parser.parse_args()
    streamer = ScreenStreamer(args.ip, args.port)
    streamer.start()
