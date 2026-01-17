import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0') # Fix the version warning
from gi.repository import Gst, GLib, GstPbutils
import sys
import dbus
import dbus.mainloop.glib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
Gst.init(None)

class WaylandScreenServer:
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
            # Wait for EOS to propagate before stopping
            bus = self.pipeline.get_bus()
            bus.timed_pop_filtered(Gst.CLOCK_TIME_NONE, Gst.MessageType.EOS | Gst.MessageType.ERROR)
            self.pipeline.set_state(Gst.State.NULL)
        self.loop.quit()

    def start(self):
        options = {"session_handle_token": "session_1", "handle_token": "handle_1"}
        request_path = self.iface.CreateSession(options)
        self.bus.add_signal_receiver(self.on_create_session, "Response", 
                                   "org.freedesktop.portal.Request", path=request_path)
        print("Awaiting Portal Authorization...")
        try:
            self.loop.run()
        except KeyboardInterrupt:
            self.stop()

    def on_create_session(self, response, results):
        if response != 0: sys.exit(f"Session failed: {response}")
        self.session_handle = results['session_handle']
        options = {"handle_token": "handle_2", "types": dbus.UInt32(1), "multiple": False}
        request_path = self.iface.SelectSources(self.session_handle, options)
        self.bus.add_signal_receiver(self.on_select_sources, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_select_sources(self, response, results):
        if response != 0: sys.exit("Selection cancelled")
        options = {"handle_token": "handle_3"}
        request_path = self.iface.Start(self.session_handle, "", options)
        self.bus.add_signal_receiver(self.on_start, "Response",
                                   "org.freedesktop.portal.Request", path=request_path)

    def on_start(self, response, results):
        if response != 0: sys.exit("Start failed")
        node_id = results['streams'][0][0]
        fd_obj = self.iface.OpenPipeWireRemote(self.session_handle, {})
        fd = fd_obj.take() 
        self.launch_pipeline(fd, node_id)

    def launch_pipeline(self, fd, node_id):
        # 1. Define Profiles
        container_caps = Gst.Caps.from_string("video/x-matroska")
        container_profile = GstPbutils.EncodingContainerProfile.new(
            "mkv_profile", None, container_caps, None
        )

        video_caps = Gst.Caps.from_string("video/x-h264,profile=high")
        video_profile = GstPbutils.EncodingVideoProfile.new(video_caps, None, None, 0)
        
        # Enforce 1080p60 at the profile level
        restriction = Gst.Caps.from_string("video/x-raw,width=1920,height=1080,framerate=60/1")
        video_profile.set_restriction(restriction)
        container_profile.add_profile(video_profile)

        # 2. Pipeline with Explicit Capsfilters
        pipeline_str = f"""
            pipewiresrc fd={fd} path={node_id} do-timestamp=true !
            queue leaky=downstream max-size-buffers=1 !
            videoconvert !
            videorate !
            capsfilter caps="video/x-raw,framerate=60/1" !
            videoscale !
            capsfilter caps="video/x-raw,width=1920,height=1080" name=last_link
            
            encodebin name=ebin !
            filesink location=output_test.mkv
        """
        self.pipeline = Gst.parse_launch(pipeline_str)

        # 3. Element Setup
        ebin = self.pipeline.get_by_name("ebin")
        ebin.set_property("profile", container_profile)
        
        # Connect to dynamic element addition to set bitrate
        ebin.connect("element-added", self.on_element_added)

        # 4. Manual Link using Modern Pad Request
        last_link = self.pipeline.get_by_name("last_link")
        ebin_sink_pad = ebin.request_pad_simple("video_%u")
        last_src_pad = last_link.get_static_pad("src")
        
        if last_src_pad.link(ebin_sink_pad) != Gst.PadLinkReturn.OK:
            print("Link Error: Capsfilter -> encodebin")
            self.stop()
            return

        bus = self.pipeline.get_bus()
        bus.add_signal_watch()
        bus.connect("message::error", self.on_pipeline_error)
        
        print(f"Hardware-agnostic 1080p60 recording started...")
        self.pipeline.set_state(Gst.State.PLAYING)

    def on_element_added(self, bin, element):
        """Forces 15Mbps bitrate on the selected hardware encoder."""
        # Detect if the added element is an encoder
        if "enc" in element.get_name().lower():
            # Standard hardware encoders use 'bitrate' property in kbit/sec
            # nvh264enc and x264enc use bit/sec; vah264enc uses kbit/sec.
            # We target ~15Mbps for high-fidelity tablet streaming.
            prop_name = "bitrate"
            if element.get_property("bitrate") is not None:
                # 15000 kbit/s is standard for VA-API (AMD)
                val = 15000 if "va" in element.get_name().lower() else 15000000
                element.set_property(prop_name, val)
                print(f"Quality Set: {element.get_name()} @ {val}")

    def on_pipeline_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"PIPELINE ERROR: {err.message}")
        self.stop()
        
    def on_element_message(self, bus, msg):
        """Prints which hardware encoder was selected by encodebin."""
        if msg.has_name("encoder-selection"):
            structure = msg.get_structure()
            encoder = structure.get_value("factory-name")
            print(f"Selected Encoder: {encoder}")

    def on_pipeline_error(self, bus, msg):
        err, debug = msg.parse_error()
        print(f"PIPELINE ERROR: {err.message}")
        self.stop()

    def on_state_changed(self, bus, msg):
        old, new, pending = msg.parse_state_changed()
        if msg.src == self.pipeline:
            print(f"Pipeline state: {new.value_name}")

if __name__ == "__main__":
    server = WaylandScreenServer()
    server.start()