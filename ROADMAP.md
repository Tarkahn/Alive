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
- **Phase D (second half) — Survival pressure**: predators — a scripted
  hunter always seeking the creature's position, same walls-stop-it-honestly
  collision as everything else (no pathfinding, no stealth), visible to
  vision rays so the brain has something to associate with danger. A bite
  drains energy and starts a cooldown, so evasion (actually running) matters
  instead of being chain-bitten. Curiosity-driven exploration: the wander
  controller now takes the brain's smoothed anomaly as an intrinsic-reward
  signal — bored (familiar, low-anomaly) states re-roll direction far more
  often to go find somewhere unfamiliar, novel (high-anomaly) states let the
  current heading run longer to investigate. Falls back to plain random-walk
  babbling when no brain is present, so `World.step` stays brain-agnostic.

- **Phase E — Feeling danger**: nociception — a bite fires a pain sense
  that lingers ~2s, encoded into the SDR stack like everything else.
  Hearing — an omnidirectional sense of predator-footstep loudness that
  carries through walls, because a pursuer approaches from behind where
  vision can't see. Predator satiation — after a bite it retreats home
  until hunger returns, giving experience the episodic rhythm (quiet →
  approach → bite → retreat) that makes danger learnable at all; it also
  takes short random detours when stuck against a wall. **Danger readout**:
  a second SDR classifier predicts pain 0.5–1.5s ahead from the TM's active
  cells. Verified: after ~17 sim-minutes the danger signal discriminates
  audible threat from safety at ~11x (0.25 vs 0.02) — the creature has
  learned to fear the sound of approaching footsteps, anticipating harm
  rather than merely reacting to it. UI: pain flash, hearing meter, danger
  meter.

## Next

### Phase D/E (remaining) — Grasping

1. Pinchers as articulated actuators (grasping, not just shoving) — parked
   until there's something worth grasping beyond what pushing already
   covers.

### Later — Thousand Brains

Evaluate swapping/augmenting the htm.core cortex with `tbp.monty`
(Numenta's Thousand Brains Project) — its sensor-module/motor-system
abstractions map directly onto our senses-in / motor-commands-out
interfaces.
