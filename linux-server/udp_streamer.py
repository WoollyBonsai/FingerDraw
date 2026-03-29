import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst, GLib
import dbus
import dbus.mainloop.glib
from threading import Thread
import time
import random

# Core initialization
Gst.init(None)

class WaylandUdpServer:
    def __init__(self, target_ip, port=5000):
        self.target_ip = target_ip
        self.port = port
        self.pipeline = None
        self.loop = None
        self.thread = None

    def stop(self):
        if self.pipeline:
            print("\nStopping stream...")
            self.pipeline.set_state(Gst.State.NULL)
        if self.loop:
            self.loop.quit()

    def start(self):
        """Starts the server logic in a dedicated thread."""
        self.thread = Thread(target=self._run_server_thread)
        self.thread.daemon = True
        self.thread.start()

    def _run_server_thread(self):
        """This thread behaves exactly like the standalone stream_screen.py script."""
        # Setup DBus for this thread
        dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
        self.bus = dbus.SessionBus()
        self.loop = GLib.MainLoop()
        
        self.proxy = self.bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
        self.iface = dbus.Interface(self.proxy, "org.freedesktop.portal.ScreenCast")

        # Unique tokens to prevent Wayland session conflicts
        token = int(time.time())
        self.session_token = f"fd_session_{token}"
        self.request_token = f"fd_req_{token}"

        options = {
            "session_handle_token": self.session_token, 
            "handle_token": self.request_token
        }
        
        request_path = self.iface.CreateSession(options)
        self.bus.add_signal_receiver(self.on_create_session, "Response", 
                                   "org.freedesktop.portal.Request", path=request_path)
        
        print(f"Requesting ScreenCast Portal Authorization (Token: {self.session_token})...")
        # Start the loop - it will block here and handle all signals
        self.loop.run()

    def on_create_session(self, response, results):
        if response != 0: 
            print(f"Portal Session failed: {response}")
            return
        
        self.session_handle = results['session_handle']
        print(f"Session created: {self.session_handle}")
        
        select_token = f"fd_sel_{int(time.time())}"
        options = {"handle_token": select_token, "types": dbus.UInt32(1), "multiple": False}
        
        # Note: We don't filter by path here to be safer with signal delivery
        self.bus.add_signal_receiver(self.on_select_sources, "Response",
                                   "org.freedesktop.portal.Request")
        
        self.iface.SelectSources(self.session_handle, options)

    def on_select_sources(self, response, results):
        # We check response since we aren't filtering by path anymore
        if response != 0: return
        
        start_token = f"fd_start_{int(time.time())}"
        options = {"handle_token": start_token}
        
        self.bus.add_signal_receiver(self.on_start, "Response",
                                   "org.freedesktop.portal.Request")
        
        print("Waiting for Screen selection...")
        self.iface.Start(self.session_handle, "", options)

    def on_start(self, response, results):
        if response != 0: return
        
        node_id = results['streams'][0][0]
        fd_obj = self.iface.OpenPipeWireRemote(self.session_handle, {})
        fd = fd_obj.take() 
        print(f"PipeWire Remote Ready. Node: {node_id}")
        self.launch_pipeline(fd, node_id)

    def launch_pipeline(self, fd, node_id):
        # Using the EXACT pipeline that worked in stream_screen.py
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
        
        print(f"Stream starting to {self.target_ip}:{self.port}...")
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
            self.pipeline.set_state(Gst.State.PLAYING)
            print("--- STREAM ACTIVE ---")
        except Exception as e:
            print(f"GStreamer Launch Error: {e}")
