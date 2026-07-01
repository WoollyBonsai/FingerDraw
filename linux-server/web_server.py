import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os

video_queues = []
api_loop = None

def broadcast_jpeg(frame_bytes):
    if api_loop and not api_loop.is_closed():
        api_loop.call_soon_threadsafe(_push_to_queues, frame_bytes)

def _push_to_queues(frame_bytes):
    for q in video_queues:
        try:
            q.put_nowait(frame_bytes)
        except asyncio.QueueFull:
            pass

def setup_web_routes(fastapi_app, sio, handle_input_command_fn):
    os.makedirs('web', exist_ok=True)
    fastapi_app.mount("/static", StaticFiles(directory="web"), name="static")

    @fastapi_app.on_event("startup")
    async def startup_event():
        global api_loop
        api_loop = asyncio.get_running_loop()

    @fastapi_app.get("/")
    async def index():
        with open("web/index.html", "r") as f:
            return HTMLResponse(f.read())

    @fastapi_app.websocket("/ws/video")
    async def video_endpoint(websocket: WebSocket):
        await websocket.accept()
        q = asyncio.Queue(maxsize=2)
        video_queues.append(q)
        try:
            while True:
                frame = await q.get()
                await websocket.send_bytes(frame)
        except WebSocketDisconnect:
            pass
        except Exception as e:
            print(f"WebSocket error: {e}")
        finally:
            if q in video_queues:
                video_queues.remove(q)

    @sio.event
    async def input_command(sid, cmd_str):
        handle_input_command_fn(cmd_str)
