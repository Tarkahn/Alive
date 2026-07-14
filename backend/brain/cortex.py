"""Spatial Pooler -> Temporal Memory pipeline over the sensory stream.

The output is the anomaly score: how surprised the temporal memory was by the
current input given its predictions - our first, primitive awareness signal.
"""

import os
import time
from pathlib import Path

from htm.bindings.algorithms import SpatialPooler, TemporalMemory
from htm.bindings.sdr import SDR

from .encoders import SensoryEncoder

COLUMNS = 1024
CELLS_PER_COLUMN = 8
ANOMALY_EMA_ALPHA = 0.02  # smoothing for the running average
SAVE_INTERVAL_SECONDS = 60

STATE_DIR = Path(
    os.environ.get("BRAIN_STATE_DIR", Path(__file__).resolve().parent.parent.parent / "brain_state")
)


class Cortex:
    def __init__(self):
        self.encoder = SensoryEncoder()

        self.sp = SpatialPooler(
            inputDimensions=[self.encoder.size],
            columnDimensions=[COLUMNS],
            potentialPct=0.85,
            globalInhibition=True,
            localAreaDensity=0.04,
            synPermInactiveDec=0.006,
            synPermActiveInc=0.04,
            synPermConnected=0.14,
            boostStrength=3.0,
            wrapAround=True,
            seed=1956,
        )
        self.tm = TemporalMemory(
            columnDimensions=[COLUMNS],
            cellsPerColumn=CELLS_PER_COLUMN,
            seed=1960,
        )

        self.anomaly = 1.0
        self.anomaly_avg = 1.0
        self.ticks = 0
        self._last_save = time.monotonic()
        self._load_state()

    def step(self, creature, learn=True):
        senses = creature.senses_dict()
        encoded = self.encoder.encode(senses)

        active_columns = SDR(self.sp.getColumnDimensions())
        self.sp.compute(encoded, learn, active_columns)
        self.tm.compute(active_columns, learn)

        self.anomaly = float(self.tm.anomaly)
        self.anomaly_avg += ANOMALY_EMA_ALPHA * (self.anomaly - self.anomaly_avg)
        self.ticks += 1

        if learn and time.monotonic() - self._last_save > SAVE_INTERVAL_SECONDS:
            self.save_state()
        return self.anomaly

    def state_dict(self):
        return {
            "available": True,
            "anomaly": round(self.anomaly, 4),
            "anomaly_avg": round(self.anomaly_avg, 4),
            "ticks": self.ticks,
        }

    def save_state(self):
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            self.sp.saveToFile(str(STATE_DIR / "sp.bin"))
            self.tm.saveToFile(str(STATE_DIR / "tm.bin"))
            self._last_save = time.monotonic()
        except Exception:
            pass  # persistence is best-effort; never take the sim down

    def _load_state(self):
        sp_path = STATE_DIR / "sp.bin"
        tm_path = STATE_DIR / "tm.bin"
        if sp_path.exists() and tm_path.exists():
            try:
                self.sp.loadFromFile(str(sp_path))
                self.tm.loadFromFile(str(tm_path))
            except Exception:
                pass  # stale/incompatible state; start fresh
