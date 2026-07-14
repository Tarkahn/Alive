import random
import uuid

COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22"]


def _generate_walls(width, height):
    count = random.randint(6, 10)
    walls = []
    for _ in range(count):
        w = random.randint(round(width * 0.08), round(width * 0.22))
        h = random.randint(round(height * 0.08), round(height * 0.22))
        x = random.uniform(0, width - w)
        y = random.uniform(0, height - h)
        walls.append({"x": round(x, 1), "y": round(y, 1), "w": w, "h": h})
    return walls


class Creature:
    def __init__(self, x, y, radius=8):
        self.id = uuid.uuid4().hex[:8]
        self.x = x
        self.y = y
        self.radius = radius
        self.color = random.choice(COLORS)

    def to_dict(self):
        return {
            "id": self.id,
            "x": round(self.x, 2),
            "y": round(self.y, 2),
            "radius": self.radius,
            "color": self.color,
        }


class World:
    def __init__(self, width=800, height=600, num_creatures=1):
        self.width = width
        self.height = height
        self.walls = _generate_walls(width, height)
        self.creatures = [self._spawn_creature() for _ in range(num_creatures)]

    def _spawn_creature(self):
        jitter_x = self.width * 0.15
        jitter_y = self.height * 0.15
        x = self.width / 2 + random.uniform(-jitter_x, jitter_x)
        y = self.height / 2 + random.uniform(-jitter_y, jitter_y)
        return Creature(x, y)

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "walls": self.walls,
            "creatures": [c.to_dict() for c in self.creatures],
        }
