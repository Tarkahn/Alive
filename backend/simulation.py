import math
import random
import uuid

COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#1abc9c", "#e67e22"]


class Creature:
    def __init__(self, x, y, radius=8):
        self.id = uuid.uuid4().hex[:8]
        self.x = x
        self.y = y
        self.radius = radius
        self.color = random.choice(COLORS)
        angle = random.uniform(0, 2 * math.pi)
        speed = random.uniform(20, 60)  # pixels per second
        self.vx = speed * math.cos(angle)
        self.vy = speed * math.sin(angle)

    def step(self, dt, width, height):
        # Small random wander so movement doesn't look robotic.
        if random.random() < 0.05:
            self.vx += random.uniform(-15, 15)
            self.vy += random.uniform(-15, 15)

        self.x += self.vx * dt
        self.y += self.vy * dt

        if self.x - self.radius < 0:
            self.x = self.radius
            self.vx = abs(self.vx)
        elif self.x + self.radius > width:
            self.x = width - self.radius
            self.vx = -abs(self.vx)

        if self.y - self.radius < 0:
            self.y = self.radius
            self.vy = abs(self.vy)
        elif self.y + self.radius > height:
            self.y = height - self.radius
            self.vy = -abs(self.vy)

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
        self.creatures = [
            Creature(random.uniform(0, width), random.uniform(0, height))
            for _ in range(num_creatures)
        ]

    def step(self, dt):
        for creature in self.creatures:
            creature.step(dt, self.width, self.height)

    def to_dict(self):
        return {
            "width": self.width,
            "height": self.height,
            "creatures": [c.to_dict() for c in self.creatures],
        }
