import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .simulation import World

TICK_RATE_HZ = 30
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

app = FastAPI(title="Alive")
app.mount("/static", StaticFiles(directory=FRONTEND_DIR / "static"), name="static")

world = World()
connections: set[WebSocket] = set()


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    await websocket.send_text(json.dumps(world.to_dict()))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if message.get("type") == "move_to":
                x, y = message.get("x"), message.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    world.set_target(x, y)
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(websocket)


async def simulation_loop():
    dt = 1 / TICK_RATE_HZ
    while True:
        await asyncio.sleep(dt)
        world.step(dt)
        if not connections:
            continue
        payload = json.dumps(world.to_dict())
        stale = []
        for ws in connections:
            try:
                await ws.send_text(payload)
            except Exception:
                stale.append(ws)
        for ws in stale:
            connections.discard(ws)


@app.on_event("startup")
async def start_simulation():
    asyncio.create_task(simulation_loop())
