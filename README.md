# Alive

A 2D world of creatures, built as a sandbox for experimenting with machine
learning algorithms (genetic algorithms, neuroevolution, reinforcement
learning, etc.).

Right now the creatures just wander the world randomly — this is the
foundation to build ML-driven behavior on top of.

## Stack

- **Backend**: Python (FastAPI), runs the simulation loop and streams world
  state to clients over a WebSocket.
- **Frontend**: plain HTML/JS + Canvas, renders whatever state the backend
  sends.

## Running locally

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn backend.main:app --reload
```

Then open http://localhost:8000 in your browser.

## Deploying to Render

This repo includes a `render.yaml` blueprint, so Render can pick up the
build/start commands automatically:

1. Log into [Render](https://dashboard.render.com) and click **New +** →
   **Blueprint**.
2. Connect the `tarkahn/alive` GitHub repo. Render will detect
   `render.yaml` and configure the service for you.
3. Click **Apply** to deploy. Render assigns a public `https://...onrender.com`
   URL — that's reachable from your iPhone (or anywhere), no LAN required.

The free plan spins the service down after periods of inactivity, so the
first request after a while can take ~30s to wake it back up.

## Project layout

```
backend/
  main.py         FastAPI app, WebSocket endpoint, simulation loop
  simulation.py   World and Creature classes
frontend/
  index.html
  static/
    main.js       WebSocket client + canvas rendering
    style.css
```
