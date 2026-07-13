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
