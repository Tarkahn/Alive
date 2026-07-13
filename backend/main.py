import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .simulation import World

TICK_RATE_HZ = 20
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
    try:
        while True:
            # Keep the connection open; the sim loop pushes state, not the client.
            await websocket.receive_text()
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
