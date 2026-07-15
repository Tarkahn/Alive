"""Turn the creature's sensory snapshot into one concatenated SDR.

Channels:
- each vision ray's normalized distance  -> RDSE
- heading                                -> periodic scalar encoder
- touch                                  -> scalar encoder (2 buckets)
- motor efference copy (speed, turn)     -> RDSE each
- interoception: energy (hunger)         -> RDSE
"""

import math

from htm.bindings.encoders import RDSE, RDSE_Parameters, ScalarEncoder, ScalarEncoderParameters
from htm.bindings.sdr import SDR

from ..simulation import MAX_SPEED, MAX_TURN_RATE, NUM_VISION_RAYS

# RDSE sizes: htm.core's hash-collision-resistance check is strict (and
# varies by seed); 500/25 passes reliably across seeds, smaller sizes don't.
RAY_SIZE = 500
RAY_ACTIVE = 25
HEADING_SIZE = 144
HEADING_ACTIVE = 13
TOUCH_SIZE = 20
TOUCH_ACTIVE = 10
MOTOR_SIZE = 500
MOTOR_ACTIVE = 25
ENERGY_SIZE = 500
ENERGY_ACTIVE = 25


def _rdse(size, active, resolution, seed):
    params = RDSE_Parameters()
    params.size = size
    params.activeBits = active
    params.resolution = resolution
    params.seed = seed
    return RDSE(params)


class SensoryEncoder:
    def __init__(self):
        self.ray_encoders = [
            _rdse(RAY_SIZE, RAY_ACTIVE, resolution=0.05, seed=100 + i)
            for i in range(NUM_VISION_RAYS)
        ]

        heading_params = ScalarEncoderParameters()
        heading_params.minimum = -math.pi
        heading_params.maximum = math.pi
        heading_params.periodic = True
        heading_params.size = HEADING_SIZE
        heading_params.activeBits = HEADING_ACTIVE
        self.heading_encoder = ScalarEncoder(heading_params)

        touch_params = ScalarEncoderParameters()
        touch_params.minimum = 0
        touch_params.maximum = 1
        touch_params.size = TOUCH_SIZE
        touch_params.activeBits = TOUCH_ACTIVE
        self.touch_encoder = ScalarEncoder(touch_params)

        self.speed_encoder = _rdse(MOTOR_SIZE, MOTOR_ACTIVE, resolution=MAX_SPEED / 20, seed=200)
        self.turn_encoder = _rdse(MOTOR_SIZE, MOTOR_ACTIVE, resolution=MAX_TURN_RATE / 10, seed=201)
        self.energy_encoder = _rdse(ENERGY_SIZE, ENERGY_ACTIVE, resolution=0.05, seed=202)

        self.size = (
            RAY_SIZE * NUM_VISION_RAYS + HEADING_SIZE + TOUCH_SIZE + MOTOR_SIZE * 2 + ENERGY_SIZE
        )

    def encode(self, senses):
        parts = []
        for encoder, ray in zip(self.ray_encoders, senses["vision"]):
            parts.append(encoder.encode(ray["normalized"]))

        proprio = senses["proprioception"]
        heading = math.atan2(proprio["heading_sin"], proprio["heading_cos"])
        parts.append(self.heading_encoder.encode(heading))
        parts.append(self.touch_encoder.encode(1 if senses["touch"] else 0))
        parts.append(self.speed_encoder.encode(proprio["speed"]))
        parts.append(self.turn_encoder.encode(proprio["turn_rate"]))
        parts.append(self.energy_encoder.encode(senses["interoception"]["energy"]))

        combined = SDR(self.size)
        combined.concatenate(parts)
        return combined
