import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .simulation import World

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Alive")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

world = World()


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    await websocket.send_text(json.dumps(world.to_dict()))
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
