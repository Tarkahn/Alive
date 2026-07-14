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

## Next

### Phase C — Localization: "knows where it is by looking"

1. **Sensorimotor prediction**: condition Temporal Memory predictions on the
   motor efference copy (already in the encoded input) — "if I turn left
   here, I should see the doorway."
2. **Location readout** (measurement, not control): the BSP generator already
   stores room rectangles in `World.rooms`. Train an SDR classifier
   (htm.core `Predictor`) from TM active cells → room label. UI panel with
   per-room belief bars.
3. **Kidnapped-creature test**: teleport the creature to a random room,
   brain intact; watch the room-belief converge to the truth as it looks
   around and moves. This is the demoable milestone for "knows where it is
   simply by looking around."

### Phase D — Acting on the world & survival

4. Pushable objects (body pushing), then pinchers as articulated actuators.
5. Food and an energy drive; hunger as interoception fed into the same
   encoder stack (self-awareness includes sensing one's own body state).
6. Predators with scripted hunting; evasion becomes a survival pressure.
7. Curiosity-driven exploration: use the anomaly signal as intrinsic reward
   for the wander controller (seek the unfamiliar).

### Later — Thousand Brains

Evaluate swapping/augmenting the htm.core cortex with `tbp.monty`
(Numenta's Thousand Brains Project) — its sensor-module/motor-system
abstractions map directly onto our senses-in / motor-commands-out
interfaces.
