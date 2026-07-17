"""Spatial Pooler -> Temporal Memory pipeline over the sensory stream.

Outputs:
- anomaly score: how surprised the temporal memory was by the current input
  given its predictions - our first, primitive awareness signal.
- room belief: an SDR classifier (htm.core Predictor) reads the TM's active
  cells and gives a probability per room - "where am I, judging only by what
  I see?" The classifier is a readout, not a control signal: the brain still
  never receives coordinates, only a room label to associate with its own
  internal state during learning.
- danger: a second classifier trained with a future-step horizon on the pain
  sense - "given what I perceive right now, will it hurt soon?" When this
  rises before a predator makes contact, the creature has learned to
  anticipate harm rather than merely react to it.
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
DANGER_STEPS = [15, 30, 45]  # horizons: predict pain 0.5-1.5s ahead (at 30Hz)
DANGER_PAIN_THRESHOLD = 0.1  # the pain level that counts as "it hurts"
SAVE_INTERVAL_SECONDS = 60

STATE_DIR = Path(
    os.environ.get("BRAIN_STATE_DIR", Path(__file__).resolve().parent.parent.parent / "brain_state")
)


class Cortex:
    def __init__(self, num_rooms=0):
        self.encoder = SensoryEncoder()
        self.num_rooms = num_rooms

        self.sp = self._build_sp()
        self.tm = self._build_tm()

        self.classifier = Predictor(steps=[0], alpha=PREDICTOR_ALPHA) if num_rooms > 0 else None
        self.classifier_samples = 0
        self.room_belief = [0.0] * num_rooms

        self.danger_classifier = Predictor(steps=DANGER_STEPS, alpha=PREDICTOR_ALPHA)
        self.danger_samples = 0
        self.danger = 0.0

        self.anomaly = 1.0
        self.anomaly_avg = 1.0
        self.ticks = 0
        self._last_save = time.monotonic()
        self._load_state()

    def _build_sp(self):
        return SpatialPooler(
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

    def _build_tm(self):
        return TemporalMemory(
            columnDimensions=[COLUMNS],
            cellsPerColumn=CELLS_PER_COLUMN,
            seed=1960,
        )

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
        self._update_danger(senses["interoception"]["pain"], learn)

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

    def _update_danger(self, pain, learn):
        """Danger readout: predict whether the pain sense will be firing
        0.5-1.5s from now, given the TM's current active cells. The
        classifier's step horizons do the temporal credit assignment: they
        associate what the brain perceived *before* each bite with the pain
        that followed. Danger is the worst case across horizons. Best-effort,
        like the room readout."""
        active_cells = self.tm.getActiveCells()
        label = 1 if pain > DANGER_PAIN_THRESHOLD else 0
        try:
            if learn:
                self.danger_classifier.learn(self.ticks, active_cells, label)
                self.danger_samples += 1
            if self.danger_samples > max(DANGER_STEPS):
                predictions = self.danger_classifier.infer(active_cells)
                self.danger = max(
                    (float(pdf[1]) for pdf in predictions.values() if len(pdf) > 1),
                    default=0.0,
                )
        except Exception:
            pass

    def state_dict(self):
        return {
            "available": True,
            "anomaly": round(self.anomaly, 4),
            "anomaly_avg": round(self.anomaly_avg, 4),
            "ticks": self.ticks,
            "room_belief": [round(p, 4) for p in self.room_belief],
            "danger": round(self.danger, 4),
        }

    def save_state(self):
        try:
            STATE_DIR.mkdir(parents=True, exist_ok=True)
            self.sp.saveToFile(str(STATE_DIR / "sp.bin"))
            self.tm.saveToFile(str(STATE_DIR / "tm.bin"))
            if self.classifier is not None:
                self.classifier.saveToFile(str(STATE_DIR / "predictor.bin"))
            self.danger_classifier.saveToFile(str(STATE_DIR / "danger.bin"))
            # Predictor.learn requires a monotonically increasing recordNum,
            # so ticks must survive restarts alongside it.
            meta = {
                "ticks": self.ticks,
                "num_rooms": self.num_rooms,
                "classifier_samples": self.classifier_samples,
                "danger_samples": self.danger_samples,
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
                if self.sp.getNumInputs() != self.encoder.size:
                    raise ValueError("saved brain was trained on a different sensory layout")
            except Exception:
                # Stale or incompatible state (e.g. the encoder grew a new
                # sense since the save): start fresh rather than crash later.
                self.sp = self._build_sp()
                self.tm = self._build_tm()

        meta_path = STATE_DIR / "meta.json"
        if not meta_path.exists():
            return
        try:
            meta = json.loads(meta_path.read_text())
        except Exception:
            return
        # Restoring ticks keeps Predictor recordNums monotonically increasing
        # across restarts for both classifiers.
        self.ticks = int(meta.get("ticks", 0))

        predictor_path = STATE_DIR / "predictor.bin"
        if (
            self.classifier is not None
            and predictor_path.exists()
            and meta.get("num_rooms") == self.num_rooms  # else labels are meaningless
        ):
            try:
                self.classifier.loadFromFile(str(predictor_path))
                self.classifier_samples = int(meta.get("classifier_samples", 0))
            except Exception:
                pass

        danger_path = STATE_DIR / "danger.bin"
        if danger_path.exists():
            try:
                self.danger_classifier.loadFromFile(str(danger_path))
                self.danger_samples = int(meta.get("danger_samples", 0))
            except Exception:
                pass
