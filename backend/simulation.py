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
    """Random-walk motor babbling so the creature gathers experience on its own."""

    def __init__(self):
        self.turn_bias = 0.0
        self.timer = 0.0

    def commands(self, creature, dt):
        self.timer -= dt
        if self.timer <= 0:
            self.timer = random.uniform(0.5, 2.0)
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

    def head_pos(self):
        offset = self.body_length / 2
        return (
            self.x + math.cos(self.heading) * offset,
            self.y + math.sin(self.heading) * offset,
        )

    def step(self, dt, forward_speed, turn_rate, walls):
        forward_speed = max(0.0, min(MAX_SPEED, forward_speed))
        turn_rate = max(-MAX_TURN_RATE, min(MAX_TURN_RATE, turn_rate))

        self.heading = _wrap_angle(self.heading + turn_rate * dt)

        dx = math.cos(self.heading) * forward_speed * dt
        dy = math.sin(self.heading) * forward_speed * dt

        blocked = False
        new_x = self.x + dx
        if _overlaps_wall(new_x, self.y, COLLISION_RADIUS, walls):
            blocked = True
        else:
            self.x = new_x
        new_y = self.y + dy
        if _overlaps_wall(self.x, new_y, COLLISION_RADIUS, walls):
            blocked = True
        else:
            self.y = new_y

        self.touch = blocked
        self.speed = forward_speed
        self.turn_rate = turn_rate
        self.moving = forward_speed > 1 or abs(turn_rate) > 0.2
        if self.moving:
            self.leg_phase += dt * LEG_CYCLE_RATE

    def sense(self, walls):
        """Recompute the sensory snapshot. Vision rays fan out from the head."""
        ox, oy = self.head_pos()
        rays = []
        for i in range(NUM_VISION_RAYS):
            frac = i / (NUM_VISION_RAYS - 1) if NUM_VISION_RAYS > 1 else 0.5
            angle = self.heading + (frac - 0.5) * VISION_ARC
            dx, dy = math.cos(angle), math.sin(angle)
            nearest = VISION_RANGE
            for wall in walls:
                t = _ray_aabb(ox, oy, dx, dy, wall)
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
        self.seek = SeekController()
        self.wander = WanderController()
        self.mode = "manual"  # "manual" (click-to-move) or "wander"
        for creature in self.creatures:
            creature.sense(self.walls)

    def _spawn_creature(self, rng, max_attempts=100):
        jitter_x = self.width * 0.15
        jitter_y = self.height * 0.15
        for _ in range(max_attempts):
            x = self.width / 2 + rng.uniform(-jitter_x, jitter_x)
            y = self.height / 2 + rng.uniform(-jitter_y, jitter_y)
            if not _overlaps_wall(x, y, COLLISION_RADIUS + 2, self.walls):
                return Creature(x, y)
        return Creature(self.width / 2, self.height / 2)

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

    def step(self, dt):
        if not self.creatures:
            return
        creature = self.creatures[0]
        controller = self.wander if self.mode == "wander" else self.seek
        forward, turn = controller.commands(creature, dt)
        creature.step(dt, forward, turn, self.walls)
        creature.sense(self.walls)

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "walls": self.walls,
            "rooms": self.rooms,
            "mode": self.mode,
            "target": list(self.seek.target) if self.seek.target else None,
            "creatures": [c.to_dict() for c in self.creatures],
        }
