
import asyncio
import base64
import io
import socket
from threading import Thread

import mss
import uvicorn
from fastapi import FastAPI
from pynput.mouse import Button, Controller as MouseController
from pynput.keyboard import Key, Controller as KeyboardController
from PIL import Image
from socketio import ASGIApp, AsyncServer

# --- Basic Server Setup ---
sio = AsyncServer(async_mode="asgi", cors_allowed_origins="*")
app = FastAPI()
app = ASGIApp(sio, app)

mouse = MouseController()
keyboard = KeyboardController()

# --- Utility ---
def get_ip_address():
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

# --- Socket.IO Event Handlers ---
@sio.event
async def connect(sid, environ):
    print(f"Client connected: {sid}")

@sio.event
async def disconnect(sid):
    print(f"Client disconnected: {sid}")

@sio.event
async def start_stream(sid, data):
    print(f"Starting screen stream for client: {sid}")
    asyncio.create_task(stream_screen(sid))

@sio.event
async def stop_stream(sid, data):
    print(f"Stopping screen stream for client: {sid}")

@sio.event
async def mouse_move(sid, x, y):
    try:
        mouse.position = (x, y)
    except Exception as e:
        print(f"Error processing mouse_move event: {e}")

@sio.event
async def mouse_down(sid, x, y):
    try:
        mouse.position = (x, y)
        mouse.press(Button.left)
    except Exception as e:
        print(f"Error processing mouse_down event: {e}")

@sio.event
async def mouse_up(sid):
    try:
        mouse.release(Button.left)
    except Exception as e:
        print(f"Error processing mouse_up event: {e}")

@sio.event
async def right_click(sid):
    try:
        mouse.click(Button.right)
    except Exception as e:
        print(f"Error processing right_click event: {e}")

@sio.event
async def stylus_secondary_button(sid):
    try:
        mouse.click(Button.right)
        print("Stylus secondary button pressed: Right Click simulated.")
    except Exception as e:
        print(f"Error processing stylus_secondary_button event: {e}")

@sio.event
async def undo(sid):
    try:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('z')
            keyboard.release('z')
    except Exception as e:
        print(f"Error processing undo event: {e}")

@sio.event
async def redo(sid):
    try:
        with keyboard.pressed(Key.ctrl):
            keyboard.press('y')
            keyboard.release('y')
    except Exception as e:
        print(f"Error processing redo event: {e}")

# --- Screen Streaming Logic ---
async def stream_screen(sid):
    with mss.mss() as sct:
        while True:
            try:
                # Check if the client is still connected before proceeding
                if not sio.sid_is_connected(sid):
                    print(f"Client {sid} is no longer connected. Stopping stream.")
                    break

                # Get information of monitor 1
                monitor_number = 1
                mon = sct.monitors[monitor_number]

                # The screen part to capture
                monitor = {
                    "top": mon["top"],
                    "left": mon["left"],
                    "width": mon["width"],
                    "height": mon["height"],
                    "mon": monitor_number,
                }
                sct_img = sct.grab(monitor)
                img = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
                
                buffered = io.BytesIO()
                img.save(buffered, format="JPEG", quality=50) # quality can be adjusted
                img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

                await sio.emit("screen_frame", {"image": img_str}, to=sid)
                await asyncio.sleep(1/30) # 30fps

            except Exception as e:
                print(f"Error during screen streaming for {sid}: {e}")
                break

# --- Main Application ---
if __name__ == "__main__":
    ip_address = get_ip_address()
    print("--- FingerDraw Server ---")
    print(f"Connect your Android client to: {ip_address}:8000")
    print("-------------------------")
    uvicorn.run(app, host="0.0.0.0", port=8000)
