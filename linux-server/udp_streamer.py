import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GLib, GstPbutils, GObject
import sys
import dbus
import dbus.mainloop.glib
from threading import Thread

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)

class WaylandUdpServer:
    def __init__(self, target_ip="127.0.0.1", port=5000):
        self.bus = dbus.SessionBus()
        self.target_ip = target_ip
        self.port = port
        self.pipeline = None
        self.loop = GLib.MainLoop()
        
        self.proxy = self.bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
        self.iface = dbus.Interface(self.proxy, "org.freedesktop.portal.ScreenCast")

    def stop(self):
        """Properly shuts down the pipeline with EOS."""
        if self.pipeline:
            print("\nSending EOS to pipeline...")
            self.pipeline.send_event(Gst.Event.new_eos())
            bus = self.pipeline.get_bus()
            bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
            self.pipeline.set_state(Gst.State.NULL)
            print("Pipeline stopped.")
        if self.loop.is_running():
            self.loop.quit()

    def start(self):
        options = {"session_handle_token": "session_udp", "handle_token": "handle_udp"}
        request_path = self.iface.CreateSession(options)
        self.bus.add_signal_receiver(self.on_create_session, "Response", 
                                   "org.freedesktop.portal.Request", path=request_path)
        print("Awaiting Portal Authorization for UDP Streaming...")

    def run_loop(self):
        """Runs the GLib main loop in a separate thread."""
        self.loop_thread = Thread(target=self.loop.run)
        self.loop_thread.start()

    def on_create_session(self, response, results):
        if response != 0: 
            print(f"Session failed: {response}")
            self.stop()
            return
        self.session_handle = results['session_handle']
        options = {"handle_token": "handle_udp_2", "types": dbus.UInt32(1), "multiple": False}
        request_path = self.iface.SelectSources(self.session_handle, options)
        self.bus.add_signal_receiver(self.on_select_sources, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_select_sources(self, response, results):
        if response != 0: 
            print("Selection cancelled")
            self.stop()
            return
        options = {"handle_token": "handle_udp_3"}
        request_path = self.iface.Start(self.session_handle, "", options)
        self.bus.add_signal_receiver(self.on_start, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_start(self, response, results):
        if response != 0: 
            print("Start failed")
            self.stop()
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
            videorate !
            capsfilter caps="video/x-raw,framerate=60/1" !
            videoscale !
            capsfilter caps="video/x-raw,width=1920,height=1080" !
            nvh264enc bitrate=15000 ! 
            h264parse !
            mpegtsmux alignment=7 !
            udpsink host={self.target_ip} port={self.port} sync=false
        """
        
        try:
            self.pipeline = Gst.parse_launch(pipeline_str)
        except Exception as e:
            print(f"Failed to create pipeline: {e}")
            self.stop()
            return

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self.on_pipeline_error)
        
        print(f"UDP Streaming (MPEG-TS) to {self.target_ip}:{self.port} started...")
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_element_added(self, bin, element):
        if "enc" in element.get_name().lower():
            prop_name = "bitrate"
            if element.get_property(prop_name) is not None:
                val = 15000 
                element.set_property(prop_name, val)
                print(f"Quality Set: {element.get_name()} @ {val} kbit/s")

    def on_pipeline_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"PIPELINE ERROR: {err.message}")
        self.stop()
