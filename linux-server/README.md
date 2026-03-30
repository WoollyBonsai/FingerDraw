# FingerDraw Linux Server

This server handles screen capturing via PipeWire and GStreamer, encodes it with hardware acceleration (VA-API), and emulates a touchscreen on Linux using uinput.

The project was developed and tested on Fedora 41/42.

## Installation

### 1. System Packages

You need GStreamer 1.0, its plugins, and the Python bindings. 

#### Fedora
```bash
sudo dnf install gstreamer1 gstreamer1-plugins-base gstreamer1-plugins-good \
                 gstreamer1-plugins-bad-free gstreamer1-plugins-ugly-free \
                 gstreamer1-vaapi pipewire-gstreamer python3-gstreamer1
```

#### Ubuntu / Debian / Linux Mint
```bash
sudo apt install gstreamer1.0-plugins-base gstreamer1.0-plugins-good \
                 gstreamer1.0-plugins-bad gstreamer1.0-plugins-ugly \
                 gstreamer1.0-vaapi gstreamer1.0-pipewire python3-gst-1.0
```

#### Arch Linux
```bash
sudo pacman -S gst-plugins-base gst-plugins-good gst-plugins-bad \
               gst-plugins-ugly gst-plugin-va gst-plugin-pipewire python-gobject
```

### 2. Permissions
The script needs access to `/dev/uinput` to emulate touch events.
```bash
sudo usermod -aG input $USER
# You might need to run this if you don't want to reboot:
sudo chmod 666 /dev/uinput
```

### 3. Python Setup
Install the requirements:
```bash
pip install -r requirements.txt
```

## Usage

1. Run the server: `python main.py`
2. Open the Android app and enter your PC's IP.
3. Once the app connects, it sends a UDP packet. The server uses this to auto-detect your Android IP and starts the stream immediately.
4. Use the "Restart Stream" button on the Android toolbar if the video freezes or lags.

## Network & Firewall
Ensure these ports are open if you have a firewall (like firewalld or ufw) enabled:
- **8000 (TCP)**: Socket.IO control signals.
- **9999 (UDP)**: Touch data.
- **5000 (UDP)**: Video stream.

## Changing Encoders
If you don't have an AMD/Intel iGPU supported by VA-API, you can swap the encoder in the `launch_pipeline` function in `main.py`. You don't need to change any Android code.

**Standard Software (CPU) - Works everywhere:**
```python
"x264enc tune=zerolatency bitrate=2000 speed-preset=ultrafast !"
```

**NVIDIA (NVENC):**
```python
"nvh264enc bitrate=2000 preset=low-latency-hq !"
```

**Intel/AMD (VA-API) - Current Default:**
```python
"vah264enc bitrate=2000 rate-control=cbr target-usage=7 !"
```

**ARM / Raspberry Pi:**
```python
"v4l2h264enc !"
```

## How it works
- **Capture**: Uses `pipewiresrc` to grab the desktop from the Wayland portal.
- **Input**: Listens on a UDP socket for raw touch coordinates, then uses `evdev` to inject them into the Linux kernel as a virtual touchscreen.
- **Sync**: Socket.IO is used for initial handshake and resolution sync.
