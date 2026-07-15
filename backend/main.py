import asyncio
import json
from pathlib import Path

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import brain
from .simulation import World

TICK_RATE_HZ = 30
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"


class NoCacheStaticFiles(StaticFiles):
    """Browsers must revalidate static assets on every load - a stale cached
    main.js next to a fresh index.html silently breaks the UI."""

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache"
        return response


app = FastAPI(title="Alive")
app.mount("/static", NoCacheStaticFiles(directory=FRONTEND_DIR / "static"), name="static")

world = World()
cortex = brain.build(world) if brain.available else None
connections: set[WebSocket] = set()


@app.get("/")
async def index():
    return FileResponse(FRONTEND_DIR / "index.html", headers={"Cache-Control": "no-cache"})


@app.websocket("/ws")
async def ws_endpoint(websocket: WebSocket):
    await websocket.accept()
    connections.add(websocket)
    await websocket.send_text(json.dumps(_payload()))
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                continue
            kind = message.get("type")
            if kind == "move_to":
                x, y = message.get("x"), message.get("y")
                if isinstance(x, (int, float)) and isinstance(y, (int, float)):
                    world.set_target(x, y)
            elif kind == "set_mode":
                world.set_mode(message.get("mode"))
    except WebSocketDisconnect:
        pass
    finally:
        connections.discard(websocket)


def _payload():
    data = world.to_dict()
    data["brain"] = cortex.state_dict() if cortex else {"available": False}
    return data


async def simulation_loop():
    dt = 1 / TICK_RATE_HZ
    while True:
        await asyncio.sleep(dt)
        world.step(dt)
        if cortex:
            cortex.step(world.creatures[0])
        if not connections:
            continue
        payload = json.dumps(_payload())
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
