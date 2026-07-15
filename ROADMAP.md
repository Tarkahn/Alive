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
- **Phase D (first half) — Acting on the world**: pushable boxes — the
  creature shoves them with its body, they jam against walls and each other,
  they occlude vision (the creature sees surfaces, not categories), and
  pushing registers as touch. Food and an energy drive: energy drains with
  time and movement, food restores it (pellets respawn elsewhere), hunger
  weakens top speed, and energy feeds the encoder stack as **interoception**
  — self-awareness includes sensing one's own body state. Energy meter in
  the panel. Brain state from an older sensory layout is detected and
  discarded rather than crashing.

## Next

### Phase D (second half) — Survival

1. Pinchers as articulated actuators (grasping, not just shoving).
2. Predators with scripted hunting; evasion becomes a survival pressure.
3. Curiosity-driven exploration: use the anomaly signal as intrinsic reward
   for the wander controller (seek the unfamiliar).

### Later — Thousand Brains

Evaluate swapping/augmenting the htm.core cortex with `tbp.monty`
(Numenta's Thousand Brains Project) — its sensor-module/motor-system
abstractions map directly onto our senses-in / motor-commands-out
interfaces.
