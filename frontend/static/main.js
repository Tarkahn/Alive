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
  for (const creature of world.creatures) {
    ctx.beginPath();
    ctx.arc(creature.x, creature.y, creature.radius, 0, Math.PI * 2);
    ctx.fillStyle = creature.color;
    ctx.fill();
  }
}

connect();
