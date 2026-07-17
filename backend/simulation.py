import math
import os
import random
import uuid

COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22"]

WALL_THICKNESS = 8
DOOR_WIDTH = 48
MIN_ROOM_SIZE = 90

DEFAULT_WORLD_SEED = 42

BODY_LENGTH = 20
BODY_WIDTH = 12
HEAD_RADIUS = 5
LEG_LENGTH = 9
LEG_SWING = 4
LEG_CYCLE_RATE = 10  # radians/sec of gait phase while moving

MAX_SPEED = 55  # pixels/sec
MAX_TURN_RATE = 3.5  # radians/sec
COLLISION_RADIUS = 14  # keeps the head clear of walls when walking head-first
STOP_DISTANCE = 5

NUM_VISION_RAYS = 9
VISION_ARC = math.radians(120)
VISION_RANGE = 250.0

BOX_SIZE = 22
NUM_BOXES = 3

NUM_FOOD = 3
FOOD_RADIUS = 5
FOOD_ENERGY = 0.35
ENERGY_DRAIN_IDLE = 1 / 240  # empty in ~4 sim-minutes at rest
ENERGY_DRAIN_MOVING = 1 / 90  # additional drain at full speed
LOW_ENERGY = 0.25  # below this, hunger weakens the body
WEAK_SPEED_FLOOR = 0.3  # fraction of strength left at zero energy

NUM_PREDATORS = 1
PREDATOR_RADIUS = 9
PREDATOR_MAX_SPEED = MAX_SPEED * 0.75  # slower than the creature's top speed - outrunnable if it commits
PREDATOR_TURN_RATE = MAX_TURN_RATE * 0.6
BITE_ENERGY_LOSS = 0.25
SATIATED_SECONDS = 20.0  # after a bite the predator is sated: goes home, no hunting
PAIN_DECAY_PER_SEC = 0.5  # a bite's pain lingers for ~2 seconds
HEARING_RANGE = 200.0  # how far away predator footsteps are audible (through walls)

# (along-body sign, side sign, gait phase offset) - diagonal pairs move together,
# like a quadruped trot.
LEG_LAYOUT = [
    (1, 1, 0),
    (1, -1, math.pi),
    (-1, 1, math.pi),
    (-1, -1, 0),
]


def _split_wall(axis, split_pos, rect, rng):
    """Wall rects along a split line, with a doorway-sized gap cut into it."""
    walls = []
    if axis == "vertical":
        wall_x = split_pos - WALL_THICKNESS / 2
        y0, y1 = rect["y"], rect["y"] + rect["h"]
        span = y1 - y0
        door_w = min(DOOR_WIDTH, span * 0.4)
        door_start = rng.uniform(y0 + span * 0.2, y1 - span * 0.2 - door_w)
        door_end = door_start + door_w
        if door_start - y0 > 1:
            walls.append({"x": wall_x, "y": y0, "w": WALL_THICKNESS, "h": door_start - y0})
        if y1 - door_end > 1:
            walls.append({"x": wall_x, "y": door_end, "w": WALL_THICKNESS, "h": y1 - door_end})
    else:
        wall_y = split_pos - WALL_THICKNESS / 2
        x0, x1 = rect["x"], rect["x"] + rect["w"]
        span = x1 - x0
        door_w = min(DOOR_WIDTH, span * 0.4)
        door_start = rng.uniform(x0 + span * 0.2, x1 - span * 0.2 - door_w)
        door_end = door_start + door_w
        if door_start - x0 > 1:
            walls.append({"x": x0, "y": wall_y, "w": door_start - x0, "h": WALL_THICKNESS})
        if x1 - door_end > 1:
            walls.append({"x": door_end, "y": wall_y, "w": x1 - door_end, "h": WALL_THICKNESS})
    return walls


def _bsp(rect, depth, walls, rooms, rng):
    can_split_v = rect["w"] >= MIN_ROOM_SIZE * 2 + WALL_THICKNESS
    can_split_h = rect["h"] >= MIN_ROOM_SIZE * 2 + WALL_THICKNESS

    if depth <= 0 or (not can_split_v and not can_split_h):
        rooms.append(dict(rect))
        return

    if can_split_v and can_split_h:
        axis = rng.choice(["vertical", "horizontal"])
    else:
        axis = "vertical" if can_split_v else "horizontal"

    if axis == "vertical":
        split_x = rect["x"] + rng.uniform(rect["w"] * 0.35, rect["w"] * 0.65)
        walls.extend(_split_wall("vertical", split_x, rect, rng))
        left = {"x": rect["x"], "y": rect["y"], "w": split_x - rect["x"], "h": rect["h"]}
        right = {"x": split_x, "y": rect["y"], "w": rect["x"] + rect["w"] - split_x, "h": rect["h"]}
        _bsp(left, depth - 1, walls, rooms, rng)
        _bsp(right, depth - 1, walls, rooms, rng)
    else:
        split_y = rect["y"] + rng.uniform(rect["h"] * 0.35, rect["h"] * 0.65)
        walls.extend(_split_wall("horizontal", split_y, rect, rng))
        top = {"x": rect["x"], "y": rect["y"], "w": rect["w"], "h": split_y - rect["y"]}
        bottom = {"x": rect["x"], "y": split_y, "w": rect["w"], "h": rect["y"] + rect["h"] - split_y}
        _bsp(top, depth - 1, walls, rooms, rng)
        _bsp(bottom, depth - 1, walls, rooms, rng)


def _generate_floor_plan(width, height, rng):
    walls = [
        {"x": 0, "y": 0, "w": width, "h": WALL_THICKNESS},
        {"x": 0, "y": height - WALL_THICKNESS, "w": width, "h": WALL_THICKNESS},
        {"x": 0, "y": 0, "w": WALL_THICKNESS, "h": height},
        {"x": width - WALL_THICKNESS, "y": 0, "w": WALL_THICKNESS, "h": height},
    ]
    rooms = []
    interior = {
        "x": WALL_THICKNESS,
        "y": WALL_THICKNESS,
        "w": width - 2 * WALL_THICKNESS,
        "h": height - 2 * WALL_THICKNESS,
    }
    _bsp(interior, rng.randint(2, 3), walls, rooms, rng)
    return walls, rooms


def _rects_overlap(a, b):
    return (
        a["x"] < b["x"] + b["w"]
        and a["x"] + a["w"] > b["x"]
        and a["y"] < b["y"] + b["h"]
        and a["y"] + a["h"] > b["y"]
    )


def _overlaps_wall(x, y, radius, walls):
    for wall in walls:
        if (
            x + radius > wall["x"]
            and x - radius < wall["x"] + wall["w"]
            and y + radius > wall["y"]
            and y - radius < wall["y"] + wall["h"]
        ):
            return True
    return False


def _ray_aabb(ox, oy, dx, dy, wall):
    """Distance along ray (ox,oy)+(dx,dy) to wall AABB, or None if no hit."""
    tmin, tmax = 0.0, math.inf
    for origin, direction, lo, hi in (
        (ox, dx, wall["x"], wall["x"] + wall["w"]),
        (oy, dy, wall["y"], wall["y"] + wall["h"]),
    ):
        if abs(direction) < 1e-9:
            if origin < lo or origin > hi:
                return None
        else:
            t1 = (lo - origin) / direction
            t2 = (hi - origin) / direction
            if t1 > t2:
                t1, t2 = t2, t1
            tmin = max(tmin, t1)
            tmax = min(tmax, t2)
            if tmin > tmax:
                return None
    return tmin


def _rotate(px, py, angle):
    cos_a, sin_a = math.cos(angle), math.sin(angle)
    return px * cos_a - py * sin_a, px * sin_a + py * cos_a


def _wrap_angle(angle):
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


class SeekController:
    """Walks toward a clicked target. Drives the creature purely through
    (forward_speed, turn_rate) motor commands - same interface a brain gets."""

    def __init__(self):
        self.target = None

    def set_target(self, x, y):
        self.target = (x, y)

    def commands(self, creature, dt):
        if self.target is None:
            return 0.0, 0.0
        dx = self.target[0] - creature.x
        dy = self.target[1] - creature.y
        distance = math.hypot(dx, dy)
        if distance <= STOP_DISTANCE:
            self.target = None
            return 0.0, 0.0

        desired = math.atan2(dy, dx)
        diff = _wrap_angle(desired - creature.heading)
        turn_rate = max(-MAX_TURN_RATE, min(MAX_TURN_RATE, diff / max(dt, 1e-6)))
        # Turn in place when facing far away from the target, walk otherwise.
        forward = MAX_SPEED if abs(diff) < math.pi / 2 else 0.0
        forward = min(forward, distance / max(dt, 1e-6))
        return forward, turn_rate


class WanderController:
    """Random-walk motor babbling so the creature gathers experience on its own.

    Curiosity: when a brain is present, its anomaly (surprise) signal is fed
    in as an intrinsic reward. Low anomaly means the current surroundings are
    already well-predicted - boring - so we re-roll direction more often to
    go find somewhere unfamiliar. High anomaly means something novel is
    nearby, so we let the current heading run longer to investigate it.
    With no signal (curiosity=None, e.g. brain offline) it's plain
    random-walk babbling, unchanged from before.
    """

    BORED_ANOMALY = 0.15
    BORED_TIMER_RANGE = (0.2, 0.8)
    CURIOUS_TIMER_RANGE = (0.5, 2.0)

    def __init__(self):
        self.turn_bias = 0.0
        self.timer = 0.0

    def commands(self, creature, dt, curiosity=None):
        self.timer -= dt
        if self.timer <= 0:
            bored = curiosity is not None and curiosity < self.BORED_ANOMALY
            self.timer = random.uniform(*(self.BORED_TIMER_RANGE if bored else self.CURIOUS_TIMER_RANGE))
            self.turn_bias = random.uniform(-1.5, 1.5)
        if creature.touch:
            # Bumped a wall: turn away decisively.
            self.turn_bias = random.choice([-1, 1]) * random.uniform(2.0, MAX_TURN_RATE)
        return MAX_SPEED * 0.7, self.turn_bias


class Creature:
    def __init__(self, x, y, heading=None):
        self.id = uuid.uuid4().hex[:8]
        self.x = x
        self.y = y
        self.heading = heading if heading is not None else random.uniform(0, 2 * math.pi)
        self.body_length = BODY_LENGTH
        self.body_width = BODY_WIDTH
        self.head_radius = HEAD_RADIUS
        self.color = random.choice(COLORS)
        self.moving = False
        self.leg_phase = 0.0
        self.speed = 0.0
        self.turn_rate = 0.0
        self.touch = False
        self.vision = []
        self.energy = 1.0
        self.pain = 0.0
        self.hearing = 0.0  # set by the World: predator-footstep loudness

    def head_pos(self):
        offset = self.body_length / 2
        return (
            self.x + math.cos(self.heading) * offset,
            self.y + math.sin(self.heading) * offset,
        )

    def step(self, dt, forward_speed, turn_rate, walls, boxes=()):
        forward_speed = max(0.0, min(MAX_SPEED, forward_speed))
        turn_rate = max(-MAX_TURN_RATE, min(MAX_TURN_RATE, turn_rate))

        # Hunger weakens the body: below LOW_ENERGY, top speed tapers off.
        if self.energy < LOW_ENERGY:
            weakness = WEAK_SPEED_FLOOR + (1 - WEAK_SPEED_FLOOR) * (self.energy / LOW_ENERGY)
            forward_speed *= weakness

        drain = ENERGY_DRAIN_IDLE + ENERGY_DRAIN_MOVING * (forward_speed / MAX_SPEED)
        self.energy = max(0.0, self.energy - drain * dt)
        self.pain = max(0.0, self.pain - PAIN_DECAY_PER_SEC * dt)

        self.heading = _wrap_angle(self.heading + turn_rate * dt)

        dx = math.cos(self.heading) * forward_speed * dt
        dy = math.sin(self.heading) * forward_speed * dt

        touched = False
        for axis_dx, axis_dy in ((dx, 0.0), (0.0, dy)):
            moved, contact = self._move_axis(axis_dx, axis_dy, walls, boxes)
            touched = touched or contact

        self.touch = touched
        self.speed = forward_speed
        self.turn_rate = turn_rate
        self.moving = forward_speed > 1 or abs(turn_rate) > 0.2
        if self.moving:
            self.leg_phase += dt * LEG_CYCLE_RATE

    def _move_axis(self, dx, dy, walls, boxes):
        """Try to move along one axis, pushing a box out of the way if the
        body meets one. Returns (moved, touched) - touched is any body
        contact: a blocking wall, a blocked box, or a successful push."""
        if dx == 0.0 and dy == 0.0:
            return False, False
        new_x, new_y = self.x + dx, self.y + dy

        if _overlaps_wall(new_x, new_y, COLLISION_RADIUS, walls):
            return False, True

        hit = None
        for box in boxes:
            if _overlaps_wall(new_x, new_y, COLLISION_RADIUS, [box]):
                hit = box
                break
        if hit is None:
            self.x, self.y = new_x, new_y
            return True, False

        # Push: the box moves by the same displacement, if nothing stops it.
        pushed = {"x": hit["x"] + dx, "y": hit["y"] + dy, "w": hit["w"], "h": hit["h"]}
        clear = not any(_rects_overlap(pushed, wall) for wall in walls) and not any(
            other is not hit and _rects_overlap(pushed, other) for other in boxes
        )
        if not clear:
            return False, True  # box jammed against something; it blocks us

        hit["x"], hit["y"] = pushed["x"], pushed["y"]
        self.x, self.y = new_x, new_y
        return True, True  # moved, and we feel the box against our body

    def sense(self, obstacles):
        """Recompute the sensory snapshot. Vision rays fan out from the head.
        Obstacles are anything opaque: walls and boxes alike - the creature
        sees surfaces, not categories."""
        ox, oy = self.head_pos()
        rays = []
        for i in range(NUM_VISION_RAYS):
            frac = i / (NUM_VISION_RAYS - 1) if NUM_VISION_RAYS > 1 else 0.5
            angle = self.heading + (frac - 0.5) * VISION_ARC
            dx, dy = math.cos(angle), math.sin(angle)
            nearest = VISION_RANGE
            for obstacle in obstacles:
                t = _ray_aabb(ox, oy, dx, dy, obstacle)
                if t is not None and t < nearest:
                    nearest = t
            rays.append(
                {
                    "angle": round(angle, 4),
                    "distance": round(nearest, 2),
                    "hit_x": round(ox + dx * nearest, 2),
                    "hit_y": round(oy + dy * nearest, 2),
                    "normalized": round(nearest / VISION_RANGE, 4),
                }
            )
        self.vision = rays

    def senses_dict(self):
        return {
            "vision": self.vision,
            "vision_range": VISION_RANGE,
            "touch": self.touch,
            "hearing": round(self.hearing, 4),
            "interoception": {
                "energy": round(self.energy, 4),
                "pain": round(self.pain, 4),
            },
            "proprioception": {
                "heading_sin": round(math.sin(self.heading), 4),
                "heading_cos": round(math.cos(self.heading), 4),
                "speed": round(self.speed, 2),
                "turn_rate": round(self.turn_rate, 4),
                "leg_phase": round(self.leg_phase % (2 * math.pi), 4),
            },
        }

    def _legs(self):
        legs = []
        for along_sign, side_sign, phase_offset in LEG_LAYOUT:
            base_local = (along_sign * self.body_length * 0.25, side_sign * self.body_width / 2)
            swing = LEG_SWING * math.sin(self.leg_phase + phase_offset) if self.moving else 0
            foot_local = (base_local[0] + swing, base_local[1] + side_sign * LEG_LENGTH)

            bx, by = _rotate(*base_local, self.heading)
            fx, fy = _rotate(*foot_local, self.heading)
            legs.append(
                {
                    "x1": round(self.x + bx, 2),
                    "y1": round(self.y + by, 2),
                    "x2": round(self.x + fx, 2),
                    "y2": round(self.y + fy, 2),
                }
            )
        return legs

    def to_dict(self):
        head_x, head_y = self.head_pos()
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "heading": round(self.heading, 4),
            "body_length": self.body_length,
            "body_width": self.body_width,
            "head_x": round(head_x, 2),
            "head_y": round(head_y, 2),
            "head_radius": self.head_radius,
            "legs": self._legs(),
            "color": self.color,
            "senses": self.senses_dict(),
        }


class Predator:
    """Scripted hunter: seeks straight toward the creature, same
    walls-stop-it-honestly collision as everything else (no pathfinding).
    A bite sates it: it retreats to its home spot and doesn't hunt again
    until hunger returns. That episodic rhythm (quiet -> approach -> bite ->
    retreat) is what makes danger *learnable* - constant chain-biting would
    just be uniform background pain with nothing to predict."""

    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.home = (x, y)
        self.heading = random.uniform(-math.pi, math.pi)
        self.satiated_timer = 0.0
        self.stuck_timer = 0.0
        self.detour_timer = 0.0

    @property
    def hunting(self):
        return self.satiated_timer <= 0

    def bite(self):
        self.satiated_timer = SATIATED_SECONDS

    def rect(self):
        return {
            "x": self.x - PREDATOR_RADIUS,
            "y": self.y - PREDATOR_RADIUS,
            "w": PREDATOR_RADIUS * 2,
            "h": PREDATOR_RADIUS * 2,
        }

    def step(self, dt, target_x, target_y, obstacles):
        self.satiated_timer = max(0.0, self.satiated_timer - dt)
        if not self.hunting:
            target_x, target_y = self.home
            if math.hypot(target_x - self.x, target_y - self.y) < PREDATOR_RADIUS:
                return  # digesting at home

        # No pathfinding: straight-line seeking pins it against walls. When
        # it stops making progress, it takes a short random-heading detour -
        # dumb, but it slides off walls and eventually rounds doorways.
        self.detour_timer = max(0.0, self.detour_timer - dt)
        if self.detour_timer <= 0:
            desired = math.atan2(target_y - self.y, target_x - self.x)
            diff = _wrap_angle(desired - self.heading)
            turn_rate = max(-PREDATOR_TURN_RATE, min(PREDATOR_TURN_RATE, diff / max(dt, 1e-6)))
            self.heading = _wrap_angle(self.heading + turn_rate * dt)

        old_x, old_y = self.x, self.y
        dx = math.cos(self.heading) * PREDATOR_MAX_SPEED * dt
        dy = math.sin(self.heading) * PREDATOR_MAX_SPEED * dt
        new_x = self.x + dx
        if not _overlaps_wall(new_x, self.y, PREDATOR_RADIUS, obstacles):
            self.x = new_x
        new_y = self.y + dy
        if not _overlaps_wall(self.x, new_y, PREDATOR_RADIUS, obstacles):
            self.y = new_y

        moved = math.hypot(self.x - old_x, self.y - old_y)
        if moved < PREDATOR_MAX_SPEED * dt * 0.25:
            self.stuck_timer += dt
            if self.stuck_timer > 1.2:
                self.detour_timer = random.uniform(0.8, 1.8)
                self.heading = random.uniform(-math.pi, math.pi)
                self.stuck_timer = 0.0
        else:
            self.stuck_timer = 0.0

    def to_dict(self):
        return {
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "radius": PREDATOR_RADIUS,
            "state": "hunting" if self.hunting else "satiated",
        }


class World:
    def __init__(self, width=800, height=600, num_creatures=1, seed=None):
        if seed is None:
            seed = int(os.environ.get("WORLD_SEED", DEFAULT_WORLD_SEED))
        self.seed = seed
        rng = random.Random(seed)
        self.width = width
        self.height = height
        self.walls, self.rooms = _generate_floor_plan(width, height, rng)
        self.creatures = [self._spawn_creature(rng) for _ in range(num_creatures)]
        self.boxes = []
        for _ in range(NUM_BOXES):
            box = self._spawn_box(rng)
            if box is not None:
                self.boxes.append(box)
        self.food = []
        for _ in range(NUM_FOOD):
            pellet = self._spawn_food(rng)
            if pellet is not None:
                self.food.append(pellet)
        self.predators = []
        for _ in range(NUM_PREDATORS):
            predator = self._spawn_predator(rng)
            if predator is not None:
                self.predators.append(predator)
        self.seek = SeekController()
        self.wander = WanderController()
        self.mode = "manual"  # "manual" (click-to-move) or "wander"
        for creature in self.creatures:
            creature.hearing = self.hearing_proximity()
            creature.sense(self.sense_obstacles())

    def obstacles(self):
        """Everything solid: walls plus boxes. Used for movement/placement -
        predators are a proximity threat, not something bodies collide with."""
        return self.walls + self.boxes

    def sense_obstacles(self):
        """Everything vision can see: obstacles plus predators, so the
        creature can spot one coming before it's in biting range."""
        return self.obstacles() + [p.rect() for p in self.predators]

    def _spawn_box(self, rng, max_attempts=100):
        margin = WALL_THICKNESS + 4
        for _ in range(max_attempts):
            room = rng.choice(self.rooms)
            if room["w"] <= 2 * margin + BOX_SIZE or room["h"] <= 2 * margin + BOX_SIZE:
                continue
            box = {
                "x": rng.uniform(room["x"] + margin, room["x"] + room["w"] - margin - BOX_SIZE),
                "y": rng.uniform(room["y"] + margin, room["y"] + room["h"] - margin - BOX_SIZE),
                "w": BOX_SIZE,
                "h": BOX_SIZE,
            }
            if any(_rects_overlap(box, wall) for wall in self.walls):
                continue
            if any(_rects_overlap(box, other) for other in self.boxes):
                continue
            creature = self.creatures[0] if self.creatures else None
            if creature and _overlaps_wall(creature.x, creature.y, COLLISION_RADIUS + 4, [box]):
                continue
            return box
        return None

    def _spawn_food(self, rng, max_attempts=100):
        margin = WALL_THICKNESS + FOOD_RADIUS + 4
        for _ in range(max_attempts):
            room = rng.choice(self.rooms)
            if room["w"] <= 2 * margin or room["h"] <= 2 * margin:
                continue
            x = rng.uniform(room["x"] + margin, room["x"] + room["w"] - margin)
            y = rng.uniform(room["y"] + margin, room["y"] + room["h"] - margin)
            if _overlaps_wall(x, y, FOOD_RADIUS, self.obstacles()):
                continue
            return {"x": round(x, 2), "y": round(y, 2)}
        return None

    def _eat(self):
        """Food within body reach is eaten; each pellet respawns elsewhere."""
        if not self.creatures:
            return
        creature = self.creatures[0]
        for i, pellet in enumerate(self.food):
            if math.hypot(creature.x - pellet["x"], creature.y - pellet["y"]) < COLLISION_RADIUS + FOOD_RADIUS:
                creature.energy = min(1.0, creature.energy + FOOD_ENERGY)
                fresh = self._spawn_food(random)
                if fresh is not None:
                    self.food[i] = fresh

    def _spawn_predator(self, rng, max_attempts=100):
        margin = WALL_THICKNESS + PREDATOR_RADIUS + 4
        creature = self.creatures[0] if self.creatures else None
        start_room = self.room_index(creature.x, creature.y) if creature else -1
        candidates = [r for i, r in enumerate(self.rooms) if i != start_room] or self.rooms
        for _ in range(max_attempts):
            room = rng.choice(candidates)
            if room["w"] <= 2 * margin or room["h"] <= 2 * margin:
                continue
            x = rng.uniform(room["x"] + margin, room["x"] + room["w"] - margin)
            y = rng.uniform(room["y"] + margin, room["y"] + room["h"] - margin)
            if _overlaps_wall(x, y, PREDATOR_RADIUS, self.obstacles()):
                continue
            return Predator(x, y)
        return None

    def _hunt(self, dt):
        """Predators pursue the creature while hungry; a bite drains energy,
        fires the pain sense, and sates the predator (it retreats home)."""
        if not self.creatures:
            return
        creature = self.creatures[0]
        obstacles = self.obstacles()
        for predator in self.predators:
            predator.step(dt, creature.x, creature.y, obstacles)
            if predator.hunting and math.hypot(
                creature.x - predator.x, creature.y - predator.y
            ) < COLLISION_RADIUS + PREDATOR_RADIUS:
                creature.energy = max(0.0, creature.energy - BITE_ENERGY_LOSS)
                creature.pain = 1.0
                predator.bite()

    def hearing_proximity(self):
        """Omnidirectional hearing: how loud the nearest predator's footsteps
        are (1 = on top of us, 0 = out of range). Sound carries through walls
        - this is what lets the creature perceive a pursuer it cannot see."""
        if not self.creatures or not self.predators:
            return 0.0
        creature = self.creatures[0]
        nearest = min(
            math.hypot(creature.x - p.x, creature.y - p.y) for p in self.predators
        )
        return max(0.0, 1.0 - nearest / HEARING_RANGE)

    def _spawn_creature(self, rng, max_attempts=100):
        jitter_x = self.width * 0.15
        jitter_y = self.height * 0.15
        for _ in range(max_attempts):
            x = self.width / 2 + rng.uniform(-jitter_x, jitter_x)
            y = self.height / 2 + rng.uniform(-jitter_y, jitter_y)
            if not _overlaps_wall(x, y, COLLISION_RADIUS + 2, self.walls):
                return Creature(x, y)
        return Creature(self.width / 2, self.height / 2)

    def room_index(self, x, y):
        """Index of the room rect containing (x, y), or -1 (e.g. inside a
        boundary wall). Ground truth for the localization readout - the brain
        never sees coordinates, only the room *label* during training."""
        for i, room in enumerate(self.rooms):
            if room["x"] <= x <= room["x"] + room["w"] and room["y"] <= y <= room["y"] + room["h"]:
                return i
        return -1

    def creature_room(self):
        if not self.creatures:
            return -1
        creature = self.creatures[0]
        return self.room_index(creature.x, creature.y)

    def kidnap(self, max_attempts=100):
        """Teleport the creature to a random spot in a different room, brain
        intact. The kidnapped-creature test: watch the room belief re-converge
        as it looks around."""
        if not self.creatures:
            return
        creature = self.creatures[0]
        current = self.creature_room()
        candidates = [i for i in range(len(self.rooms)) if i != current] or list(range(len(self.rooms)))
        if not candidates:
            return
        margin = COLLISION_RADIUS + WALL_THICKNESS
        for _ in range(max_attempts):
            room = self.rooms[random.choice(candidates)]
            if room["w"] <= 2 * margin or room["h"] <= 2 * margin:
                continue
            x = random.uniform(room["x"] + margin, room["x"] + room["w"] - margin)
            y = random.uniform(room["y"] + margin, room["y"] + room["h"] - margin)
            if _overlaps_wall(x, y, COLLISION_RADIUS + 2, self.obstacles()):
                continue
            creature.x = x
            creature.y = y
            creature.heading = random.uniform(-math.pi, math.pi)
            self.seek.target = None
            creature.hearing = self.hearing_proximity()
            creature.sense(self.sense_obstacles())
            return

    def set_target(self, x, y):
        if not self.creatures:
            return
        x = max(0.0, min(float(self.width), float(x)))
        y = max(0.0, min(float(self.height), float(y)))
        self.mode = "manual"
        self.seek.set_target(x, y)

    def set_mode(self, mode):
        if mode in ("manual", "wander"):
            self.mode = mode
            if mode == "wander":
                self.seek.target = None

    def step(self, dt, curiosity=None):
        if not self.creatures:
            return
        creature = self.creatures[0]
        if self.mode == "wander":
            forward, turn = self.wander.commands(creature, dt, curiosity)
        else:
            forward, turn = self.seek.commands(creature, dt)
        creature.step(dt, forward, turn, self.walls, self.boxes)
        self._eat()
        self._hunt(dt)
        creature.hearing = self.hearing_proximity()
        creature.sense(self.sense_obstacles())

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "walls": self.walls,
            "rooms": self.rooms,
            "boxes": self.boxes,
            "food": self.food,
            "predators": [p.to_dict() for p in self.predators],
            "creature_room": self.creature_room(),
            "mode": self.mode,
            "target": list(self.seek.target) if self.seek.target else None,
            "creatures": [c.to_dict() for c in self.creatures],
        }
