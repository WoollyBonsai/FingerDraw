# FingerDraw Linux Server

This is the Linux server for the FingerDraw application.

## Dependencies

This server requires some system dependencies to be installed. A setup script is provided for Fedora-based distributions.

```bash
./setup.sh
```

## Installation

1.  **Create a virtual environment:**
    ```bash
    python3 -m venv venv
    source venv/bin/activate
    ```

2.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **A note on Wayland and X11:**
    The `pynput` library, used for controlling the mouse, may require you to be running on an X11 session. If you are on Wayland and experience issues, please switch to an X11 session. On Fedora, you can do this by clicking the gear icon on the login screen and selecting "GNOME on Xorg". Some distributions might require installing `python3-xlib`.

    Additionally, for screen capturing to work correctly on Wayland, you may need to configure pipewire. `mss` which is used for screen capture has experimental support for wayland. 

## Running the server

1.  **Activate the virtual environment:**
    ```bash
    source venv/bin/activate
    ```

2.  **Run the server:**
    ```bash
    python main.py
    ```

The server will print its IP address. Enter this address in the Android client to connect.
