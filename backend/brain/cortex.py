"""Spatial Pooler -> Temporal Memory pipeline over the sensory stream.

Outputs:
- anomaly score: how surprised the temporal memory was by the current input
  given its predictions - our first, primitive awareness signal.
- room belief: an SDR classifier (htm.core Predictor) reads the TM's active
  cells and gives a probability per room - "where am I, judging only by what
  I see?" The classifier is a readout, not a control signal: the brain still
  never receives coordinates, only a room label to associate with its own
  internal state during learning.
"""

import json
import os
import time
from pathlib import Path

from htm.bindings.algorithms import Predictor, SpatialPooler, TemporalMemory
from htm.bindings.sdr import SDR

from .encoders import SensoryEncoder

COLUMNS = 1024
CELLS_PER_COLUMN = 8
ANOMALY_EMA_ALPHA = 0.02  # smoothing for the running average
PREDICTOR_ALPHA = 0.08
SAVE_INTERVAL_SECONDS = 60

STATE_DIR = Path(
    os.environ.get("BRAIN_STATE_DIR", Path(__file__).resolve().parent.parent.parent / "brain_state")
)


class Cortex:
    def __init__(self, num_rooms=0):
        self.encoder = SensoryEncoder()
        self.num_rooms = num_rooms

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

        self.classifier = Predictor(steps=[0], alpha=PREDICTOR_ALPHA) if num_rooms > 0 else None
        self.classifier_samples = 0
        self.room_belief = [0.0] * num_rooms

        self.anomaly = 1.0
        self.anomaly_avg = 1.0
        self.ticks = 0
        self._last_save = time.monotonic()
        self._load_state()

    def step(self, creature, room=-1, learn=True):
        senses = creature.senses_dict()
        encoded = self.encoder.encode(senses)

        active_columns = SDR(self.sp.getColumnDimensions())
        self.sp.compute(encoded, learn, active_columns)
        self.tm.compute(active_columns, learn)

        self.anomaly = float(self.tm.anomaly)
        self.anomaly_avg += ANOMALY_EMA_ALPHA * (self.anomaly - self.anomaly_avg)
        self.ticks += 1

        if self.classifier is not None:
            self._update_room_belief(room, learn)

        if learn and time.monotonic() - self._last_save > SAVE_INTERVAL_SECONDS:
            self.save_state()
        return self.anomaly

    def _update_room_belief(self, room, learn):
        """Location readout: classify the TM's active cells into a room label.
        Best-effort - a classifier hiccup must never take the sim down."""
        active_cells = self.tm.getActiveCells()
        try:
            if learn and 0 <= room < self.num_rooms:
                self.classifier.learn(self.ticks, active_cells, room)
                self.classifier_samples += 1
            if self.classifier_samples > 0:
                pdf = list(self.classifier.infer(active_cells)[0])
                pdf = pdf[: self.num_rooms]
                pdf += [0.0] * (self.num_rooms - len(pdf))
                self.room_belief = pdf
        except Exception:
            pass

    def state_dict(self):
        return {
            "available": True,
            "anomaly": round(self.anomaly, 4),
            "anomaly_avg": round(self.anomaly_avg, 4),
            "ticks": self.ticks,
            "room_belief": [round(p, 4) for p in self.room_belief],
        }

    def save_state(self):
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            self.sp.saveToFile(str(STATE_DIR / "sp.bin"))
            self.tm.saveToFile(str(STATE_DIR / "tm.bin"))
            if self.classifier is not None:
                self.classifier.saveToFile(str(STATE_DIR / "predictor.bin"))
            # Predictor.learn requires a monotonically increasing recordNum,
            # so ticks must survive restarts alongside it.
            meta = {
                "ticks": self.ticks,
                "num_rooms": self.num_rooms,
                "classifier_samples": self.classifier_samples,
            }
            (STATE_DIR / "meta.json").write_text(json.dumps(meta))
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

        meta_path = STATE_DIR / "meta.json"
        predictor_path = STATE_DIR / "predictor.bin"
        if self.classifier is None or not (meta_path.exists() and predictor_path.exists()):
            return
        try:
            meta = json.loads(meta_path.read_text())
            if meta.get("num_rooms") != self.num_rooms:
                return  # different floor plan; the saved room labels are meaningless
            self.classifier.loadFromFile(str(predictor_path))
            self.ticks = int(meta.get("ticks", 0))
            self.classifier_samples = int(meta.get("classifier_samples", 0))
        except Exception:
            pass
