const canvas = document.getElementById("world");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");

function connect() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onopen = () => {
    statusEl.textContent = "connected";
  };

  ws.onmessage = (event) => {
    const world = JSON.parse(event.data);
    render(world);
  };

  ws.onclose = () => {
    statusEl.textContent = "disconnected, retrying...";
    setTimeout(connect, 1000);
  };

  ws.onerror = () => ws.close();
}

function render(world) {
  if (canvas.width !== world.width || canvas.height !== world.height) {
    canvas.width = world.width;
    canvas.height = world.height;
  }

  ctx.clearRect(0, 0, canvas.width, canvas.height);

  for (const wall of world.walls) {
    ctx.fillStyle = "#2a2e3f";
    ctx.strokeStyle = "#454b63";
    ctx.fillRect(wall.x, wall.y, wall.w, wall.h);
    ctx.strokeRect(wall.x, wall.y, wall.w, wall.h);
  }

  for (const creature of world.creatures) {
    ctx.fillStyle = creature.color;

    ctx.save();
    ctx.translate(creature.x, creature.y);
    ctx.rotate(creature.heading);
    ctx.beginPath();
    ctx.ellipse(0, 0, creature.body_length / 2, creature.body_width / 2, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.restore();

    ctx.beginPath();
    ctx.arc(creature.head_x, creature.head_y, creature.head_radius, 0, Math.PI * 2);
    ctx.fill();
  }
}

connect();
