# Alive

An experiment in machine perception and (primitive) consciousness. A small
creature lives in a 2D house of rooms and doorways. It has senses (vision
rays, touch, proprioception) and actuators (walking, turning), and an
HTM brain — Hierarchical Temporal Memory, the Numenta/NuPIC lineage of
neuroscience-based learning algorithms — that continuously predicts its own
sensory stream. The long-term goal: a creature that learns to navigate,
knows where it is just by looking around, and acts on its world to survive.

See `ROADMAP.md` for where this is headed.

## How it works

- **World** (`backend/simulation.py`): BSP-generated floor plan (fixed by
  `WORLD_SEED`, default 42, so the map survives restarts — you can't learn a
  map that changes under you). Creature physics, collision, raycast vision.
- **Brain** (`backend/brain/`): sensory encoders → SDRs → Spatial Pooler →
  Temporal Memory (htm.core). Output: an anomaly score per tick — how
  *surprised* the creature is by what it senses. Familiar places become
  boring; new rooms spike surprise. Brain state is saved to `brain_state/`
  periodically so learning survives restarts.
- **Server** (`backend/main.py`): FastAPI; steps the world and brain at 30Hz,
  streams state over a WebSocket.
- **UI** (`frontend/`): canvas renderer with a sensor overlay (vision rays,
  touch flash), a brain panel (surprise meter + history sparkline), and
  controls. Click the floor: the creature walks there (straight-line — it has
  no pathfinding yet; walls stop it honestly). Toggle **autonomous wander**
  to let it roam and learn on its own.

Design rules: the brain only ever receives senses plus a copy of its own
motor commands — never world coordinates. And every controller (player click,
wander, future brains) drives the creature through the same motor interface:
`(forward_speed, turn_rate)`.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open http://localhost:8000. The app runs fine without the brain
(the panel shows "offline") — to enable it, install htm.core:

### Installing htm.core (the brain)

htm.core builds from source and needs `cmake`, a C++17 compiler, and `make`.

```bash
git clone https://github.com/htm-community/htm.core.git
cd htm.core
python htm_install.py
```

If your network blocks GitHub archive downloads (CMake fetches third-party
tarballs at configure time), pre-populate `build/Thirdparty/` as described in
htm.core's `AirGapBuild.md` — cloning each dependency repo at the pinned
version into `build/Thirdparty/<name>/` works.

## Deploying to Render

This repo includes a `render.yaml` blueprint, so Render can pick up the
build/start commands automatically:

1. Log into [Render](https://dashboard.render.com) and click **New +** →
   **Blueprint**.
2. Connect the `tarkahn/alive` GitHub repo. Render will detect
   `render.yaml` and configure the service for you.
3. Click **Apply** to deploy.

The free plan spins the service down after periods of inactivity, so the
first request after a while can take ~30s to wake it back up. The free tier
does not build htm.core, so the deployed site runs in no-brain mode —
learning experiments are meant to run locally.

## Project layout

```
backend/
  main.py           FastAPI app, WebSocket endpoint, 30Hz sim loop
  simulation.py     World gen, creature physics, senses, controllers
  brain/
    encoders.py     senses -> SDR encoders
    cortex.py       Spatial Pooler -> Temporal Memory, anomaly out
frontend/
  index.html
  static/
    main.js         WebSocket client, canvas rendering, panels
    style.css
ROADMAP.md          where this project is going
```
