import math
import random
import uuid

COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22"]

WALL_THICKNESS = 8
DOOR_WIDTH = 48
MIN_ROOM_SIZE = 90


def _split_wall(axis, split_pos, rect):
    """Wall rects along a split line, with a doorway-sized gap cut into it."""
    walls = []
    if axis == "vertical":
        wall_x = split_pos - WALL_THICKNESS / 2
        y0, y1 = rect["y"], rect["y"] + rect["h"]
        span = y1 - y0
        door_w = min(DOOR_WIDTH, span * 0.4)
        door_start = random.uniform(y0 + span * 0.2, y1 - span * 0.2 - door_w)
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
        door_start = random.uniform(x0 + span * 0.2, x1 - span * 0.2 - door_w)
        door_end = door_start + door_w
        if door_start - x0 > 1:
            walls.append({"x": x0, "y": wall_y, "w": door_start - x0, "h": WALL_THICKNESS})
        if x1 - door_end > 1:
            walls.append({"x": door_end, "y": wall_y, "w": x1 - door_end, "h": WALL_THICKNESS})
    return walls


def _bsp(rect, depth, walls):
    if depth <= 0:
        return

    can_split_v = rect["w"] >= MIN_ROOM_SIZE * 2 + WALL_THICKNESS
    can_split_h = rect["h"] >= MIN_ROOM_SIZE * 2 + WALL_THICKNESS
    if not can_split_v and not can_split_h:
        return
    if can_split_v and can_split_h:
        axis = random.choice(["vertical", "horizontal"])
    else:
        axis = "vertical" if can_split_v else "horizontal"

    if axis == "vertical":
        split_x = rect["x"] + random.uniform(rect["w"] * 0.35, rect["w"] * 0.65)
        walls.extend(_split_wall("vertical", split_x, rect))
        left = {"x": rect["x"], "y": rect["y"], "w": split_x - rect["x"], "h": rect["h"]}
        right = {"x": split_x, "y": rect["y"], "w": rect["x"] + rect["w"] - split_x, "h": rect["h"]}
        _bsp(left, depth - 1, walls)
        _bsp(right, depth - 1, walls)
    else:
        split_y = rect["y"] + random.uniform(rect["h"] * 0.35, rect["h"] * 0.65)
        walls.extend(_split_wall("horizontal", split_y, rect))
        top = {"x": rect["x"], "y": rect["y"], "w": rect["w"], "h": split_y - rect["y"]}
        bottom = {"x": rect["x"], "y": split_y, "w": rect["w"], "h": rect["y"] + rect["h"] - split_y}
        _bsp(top, depth - 1, walls)
        _bsp(bottom, depth - 1, walls)


def _generate_floor_plan(width, height):
    walls = [
        {"x": 0, "y": 0, "w": width, "h": WALL_THICKNESS},
        {"x": 0, "y": height - WALL_THICKNESS, "w": width, "h": WALL_THICKNESS},
        {"x": 0, "y": 0, "w": WALL_THICKNESS, "h": height},
        {"x": width - WALL_THICKNESS, "y": 0, "w": WALL_THICKNESS, "h": height},
    ]
    interior = {
        "x": WALL_THICKNESS,
        "y": WALL_THICKNESS,
        "w": width - 2 * WALL_THICKNESS,
        "h": height - 2 * WALL_THICKNESS,
    }
    _bsp(interior, random.randint(2, 3), walls)
    return walls


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


BODY_LENGTH = 20
BODY_WIDTH = 12
HEAD_RADIUS = 5


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

    def bounding_radius(self):
        return self.body_length / 2 + self.head_radius * 2

    def to_dict(self):
        head_offset = self.body_length / 2
        head_x = self.x + math.cos(self.heading) * head_offset
        head_y = self.y + math.sin(self.heading) * head_offset
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
            "color": self.color,
        }


class World:
    def __init__(self, width=800, height=600, num_creatures=1):
        self.width = width
        self.height = height
        self.walls = _generate_floor_plan(width, height)
        self.creatures = [self._spawn_creature() for _ in range(num_creatures)]

    def _spawn_creature(self, max_attempts=50):
        jitter_x = self.width * 0.15
        jitter_y = self.height * 0.15
        probe_radius = BODY_LENGTH / 2 + HEAD_RADIUS * 2
        for _ in range(max_attempts):
            x = self.width / 2 + random.uniform(-jitter_x, jitter_x)
            y = self.height / 2 + random.uniform(-jitter_y, jitter_y)
            if not _overlaps_wall(x, y, probe_radius, self.walls):
                return Creature(x, y)
        return Creature(self.width / 2, self.height / 2)

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "walls": self.walls,
            "creatures": [c.to_dict() for c in self.creatures],
        }
