# Roadmap

The project goal: experiment with machine learning for **perception and
consciousness** using the Numenta/HTM lineage. The creature should learn to
navigate its rooms, know where it is "by looking around," and eventually act
on its world — with awareness of itself and its surroundings from the very
beginning.

## Done

- **Phase A — Embodiment**: floor plan (deterministic via `WORLD_SEED`),
  collision physics, motor interface `(forward_speed, turn_rate)`, senses
  (9 raycast vision, touch, proprioception), sensor overlay UI, click-to-move
  and autonomous wander controllers.
- **Phase B — First brain (prediction & surprise)**: htm.core encoders →
  Spatial Pooler → Temporal Memory over the sensory stream; live surprise
  (anomaly) meter and sparkline; brain state persistence.
- **Phase C — Localization: "knows where it is by looking"**:
  sensorimotor prediction (TM conditioned on the motor efference copy in the
  encoded input); location readout via an SDR classifier (htm.core
  `Predictor`) from TM active cells → room label, trained online against
  `World.rooms` ground truth; per-room belief bars in the UI (● marks the
  true room); **kidnap button** — teleport to a random room, brain intact,
  and watch the belief re-converge as the creature looks around. Room labels
  are drawn on the canvas; classifier state persists with the rest of the
  brain (and is discarded if the floor plan changed).

## Next

### Phase D — Acting on the world & survival

1. Pushable objects (body pushing), then pinchers as articulated actuators.
2. Food and an energy drive; hunger as interoception fed into the same
   encoder stack (self-awareness includes sensing one's own body state).
3. Predators with scripted hunting; evasion becomes a survival pressure.
4. Curiosity-driven exploration: use the anomaly signal as intrinsic reward
   for the wander controller (seek the unfamiliar).

### Later — Thousand Brains

Evaluate swapping/augmenting the htm.core cortex with `tbp.monty`
(Numenta's Thousand Brains Project) — its sensor-module/motor-system
abstractions map directly onto our senses-in / motor-commands-out
interfaces.
