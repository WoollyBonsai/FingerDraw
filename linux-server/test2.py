import time
import socket
import struct
import uinput
from threading import Thread
from udp_streamer import WaylandUdpServer

# Screen resolution (should ideally be detected, but hardcoding for now as in main.py)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080

class InputReceiver:
    def __init__(self, port=5001):
        self.port = port
        self.running = False
        self.device = uinput.Device([
            uinput.ABS_X + (0, SCREEN_WIDTH, 0, 0),
            uinput.ABS_Y + (0, SCREEN_HEIGHT, 0, 0),
            uinput.ABS_PRESSURE + (0, 255, 0, 0),
            uinput.BTN_TOUCH,
            uinput.BTN_TOOL_PEN,
        ])
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.settimeout(1.0)

    def start(self):
        self.running = True
        self.thread = Thread(target=self._run)
        self.thread.start()
        print(f"Input Receiver listening on UDP port {self.port}...")

    def stop(self):
        self.running = False
        self.thread.join()
        self.sock.close()

    def _run(self):
        while self.running:
            try:
                data, addr = self.sock.recvfrom(1024)
                if len(data) >= 13:
                    # Format: B (type), f (x), f (y), f (pressure)
                    event_type, x, y, pressure = struct.unpack("!Bfff", data[:13])
                    
                    real_x = int(x * SCREEN_WIDTH)
                    real_y = int(y * SCREEN_HEIGHT)
                    real_pressure = int(pressure * 255)

                    if event_type == 0: # Move
                        self.device.emit(uinput.ABS_X, real_x)
                        self.device.emit(uinput.ABS_Y, real_y)
                        self.device.emit(uinput.ABS_PRESSURE, real_pressure)
                    elif event_type == 1: # Down
                        self.device.emit(uinput.ABS_X, real_x)
                        self.device.emit(uinput.ABS_Y, real_y)
                        self.device.emit(uinput.ABS_PRESSURE, real_pressure)
                        self.device.emit(uinput.BTN_TOUCH, 1)
                    elif event_type == 2: # Up
                        self.device.emit(uinput.BTN_TOUCH, 0)
            except socket.timeout:
                continue
            except Exception as e:
                print(f"Error in input receiver: {e}")

if __name__ == "__main__":
    target_ip = "172.16.252.31"
    port = 5000
    input_port = 5001
    
    print(f"--- FingerDraw Test Server ---")
    print(f"Target IP (Video): {target_ip}")
    print(f"Video Port: {port}")
    print(f"Input Port (Local): {input_port}")
    print(f"--------------------------------")

    # Initialize the Wayland UDP Server (Screen Streamer)
    udp_server = WaylandUdpServer(target_ip=target_ip, port=port)
    
    # Initialize the Input Receiver
    input_receiver = InputReceiver(port=input_port)
    
    # Start the portal request process
    udp_server.start()
    
    # Start the GLib main loop in a background thread
    udp_server.run_loop()

    # Start the input receiver
    input_receiver.start()
    
    print("\nAwaiting portal authorization... Once authorized, the stream will begin.")
    print("Press Ctrl+C to stop.")

    try:
        # Keep the main thread alive while the stream runs
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        input_receiver.stop()
        udp_server.stop()
        print("Stopped.")
