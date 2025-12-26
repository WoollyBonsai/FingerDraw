# FingerDraw Feature Goals

This document outlines the features for the FingerDraw application, which turns an Android device into a graphics tablet for a PC.

## Core Features

- [X] **Client-Server Architecture:**
    - [X] Android application as the client.
    - [X] Windows/Linux application as the server.
- [X] **Wireless Communication:** All communication over Wi-Fi for low latency.
- [X] **Screen Sharing:**
    - [X] Real-time screen mirroring from the server (PC) to the client (Android).
- [X] **Input Transfer:**
    - [X] Transmit touch/stylus data from the Android client to the PC.
    - [X] Simulate mouse movements and clicks on the PC based on the received data.
- [X] **Automatic Scaling:**
    - [X] Calibrate input scale automatically when the user zooms on the Android client.
- [X] **Connection:**
    - [X] The server displays its IP address.
    - [X] The client (Android app) has a field to enter the server's IP address for connection.
    - [X] Implement IP address persistence on Android client.

## Future/Optional Features

- [ ] Pressure sensitivity support. (Deferred)
- [X] Customizable buttons on the Android app (e.g., for undo, redo, specific key presses).
- [X] Linux support for the server.
- [X] Pen/Stylus button support.
- [ ] Encrypted data transfer. (Deferred due to build issues)
- [X] Settings screen:
    - [X] Theme selection (Light/Dark/System)
    - [X] Stylus button mapping
    - [X] Screen stream quality
