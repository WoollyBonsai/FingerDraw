import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
from notebook_core.api import router as notebook_router

video_queues = []
api_loop = None

# Collaboration State
# Map of note_id -> set of active SIDs
note_sessions = {}
# Map of SID -> note_id (to easily clean up on disconnect)
sid_to_note = {}

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
    fastapi_app.include_router(notebook_router)

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

    # --- Notebook Collaboration Events ---
    @sio.event
    async def notebook_join(sid, note_id):
        await sio.enter_room(sid, note_id)
        if note_id not in note_sessions:
            note_sessions[note_id] = set()
        note_sessions[note_id].add(sid)
        sid_to_note[sid] = note_id
        
        # Broadcast updated user counts
        await broadcast_active_users()

    @sio.event
    async def notebook_leave(sid, note_id):
        await sio.leave_room(sid, note_id)
        if sid in sid_to_note:
            n_id = sid_to_note[sid]
            if n_id in note_sessions:
                note_sessions[n_id].discard(sid)
                if len(note_sessions[n_id]) == 0:
                    del note_sessions[n_id]
            del sid_to_note[sid]
        await broadcast_active_users()

    @sio.event
    async def notebook_action(sid, data):
        # data: { note_id: str, action: str, payload: dict }
        note_id = data.get('note_id')
        if note_id:
            # Broadcast to everyone in the room except the sender
            await sio.emit('notebook_action', data, room=note_id, skip_sid=sid)
            
    @sio.event
    async def get_active_users(sid):
        counts = {nid: len(users) for nid, users in note_sessions.items()}
        await sio.emit('active_users_update', counts, to=sid)

def handle_client_disconnect(sid):
    if sid in sid_to_note:
        note_id = sid_to_note[sid]
        if note_id in note_sessions:
            note_sessions[note_id].discard(sid)
            if len(note_sessions[note_id]) == 0:
                del note_sessions[note_id]
        del sid_to_note[sid]
        # We can't await easily in a non-async context, so we use the loop
        if api_loop and not api_loop.is_closed():
            api_loop.create_task(broadcast_active_users())

async def broadcast_active_users():
    counts = {nid: len(users) for nid, users in note_sessions.items()}
    from main import sio
    await sio.emit('active_users_update', counts)
