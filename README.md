# FingerDraw

FingerDraw is a low-latency tool that turns your Android device into a wireless drawing tablet for your PC. It uses GStreamer for high-performance screen mirroring and uinput/evdev for precise touch and pressure emulation.

The project was developed and tested on Fedora Linux 41/42.

## Components

- **`android-client/`**: Native Android app (Kotlin/GStreamer) for capturing touch input and displaying the low-latency stream.
- **`linux-server/`**: Python server for Linux that captures the desktop via PipeWire/Wayland and emulates a touchscreen.
- **`windows-server/`**: Legacy/WIP Python server for Windows.

## Quick Start (Linux)

### 1. Start the Server
Navigate to the `linux-server` directory, install the requirements, and run:
```bash
cd linux-server
python main.py
```
*See `linux-server/README.md` for detailed system dependencies (GStreamer, VA-API).*

### 2. Connect the Android Client
- Install the APK on your device.
- Open the app and enter the IP address of your PC.
- Once connected, the server will auto-detect the device and start the stream.

## Features
- **Low Latency**: Optimized GStreamer pipeline with hardware-accelerated encoding (VA-API).
- **Auto-IP Detection**: No need to manually configure IPs on the server side.
- **Touch & Pressure**: Emulates a real touchscreen device on Linux, supporting pressure-sensitive styluses.
- **Dynamic Controls**: Zoom, pan, and stream restart functionality directly on the Android toolbar.

## Requirements
- **PC**: Linux with PipeWire (Wayland recommended) and a hardware-accelerated H.264 encoder (Intel/AMD/NVIDIA).
- **Network**: 5GHz Wi-Fi or Ethernet is highly recommended for stable, low-latency performance. ( Tested on 2.4GHz and it works fine there too. Just jitters in stream ( not input just stream ) when shortage of bandwidth by high usage by user. )
