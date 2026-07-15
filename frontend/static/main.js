const canvas = document.getElementById("world");
const ctx = canvas.getContext("2d");
const statusEl = document.getElementById("status");

const overlayToggle = document.getElementById("overlay-toggle");
const wanderToggle = document.getElementById("wander-toggle");
const brainStatusEl = document.getElementById("brain-status");
const anomalyValueEl = document.getElementById("anomaly-value");
const anomalyBarEl = document.getElementById("anomaly-bar");
const sparkCanvas = document.getElementById("anomaly-spark");
const sparkCtx = sparkCanvas.getContext("2d");
const visionBarsEl = document.getElementById("vision-bars");
const roomBarsEl = document.getElementById("room-bars");
const kidnapBtn = document.getElementById("kidnap-btn");
const touchEl = document.querySelector("#touch-indicator span");
const energyValueEl = document.getElementById("energy-value");
const energyBarEl = document.getElementById("energy-bar");
const proprioEl = document.getElementById("proprio");

let socket = null;
const anomalyHistory = [];
const SPARK_POINTS = 220;

function connect() {
  const protocol = location.protocol === "https:" ? "wss:" : "ws:";
  const ws = new WebSocket(`${protocol}//${location.host}/ws`);

  ws.onopen = () => {
    socket = ws;
    statusEl.textContent = "connected";
  };

  ws.onmessage = (event) => {
    const world = JSON.parse(event.data);
    render(world);
    updatePanel(world);
  };

  ws.onclose = () => {
    socket = null;
    statusEl.textContent = "disconnected, retrying...";
    setTimeout(connect, 1000);
  };

  ws.onerror = () => ws.close();
}

canvas.addEventListener("click", (event) => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  const rect = canvas.getBoundingClientRect();
  const x = (event.clientX - rect.left) * (canvas.width / rect.width);
  const y = (event.clientY - rect.top) * (canvas.height / rect.height);
  wanderToggle.checked = false;
  socket.send(JSON.stringify({ type: "move_to", x, y }));
});

kidnapBtn.addEventListener("click", () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  socket.send(JSON.stringify({ type: "kidnap" }));
});

wanderToggle.addEventListener("change", () => {
  if (!socket || socket.readyState !== WebSocket.OPEN) return;
  const mode = wanderToggle.checked ? "wander" : "manual";
  socket.send(JSON.stringify({ type: "set_mode", mode }));
});

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

  for (const box of world.boxes || []) {
    ctx.fillStyle = "#8a6d3b";
    ctx.strokeStyle = "#b59460";
    ctx.fillRect(box.x, box.y, box.w, box.h);
    ctx.strokeRect(box.x, box.y, box.w, box.h);
  }

  for (const pellet of world.food || []) {
    ctx.fillStyle = "#2ecc71";
    ctx.beginPath();
    ctx.arc(pellet.x, pellet.y, 4, 0, Math.PI * 2);
    ctx.fill();
  }

  ctx.font = "16px system-ui, sans-serif";
  ctx.textAlign = "center";
  ctx.textBaseline = "middle";
  world.rooms.forEach((room, i) => {
    ctx.fillStyle = i === world.creature_room ? "rgba(46, 204, 113, 0.5)" : "rgba(138, 145, 168, 0.28)";
    ctx.fillText(String(i + 1), room.x + room.w / 2, room.y + room.h / 2);
  });

  if (world.target) {
    ctx.strokeStyle = "#8a91a8";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.arc(world.target[0], world.target[1], 6, 0, Math.PI * 2);
    ctx.stroke();
  }

  for (const creature of world.creatures) {
    if (overlayToggle.checked && creature.senses) {
      drawSenses(creature);
    }
    drawCreature(creature);
  }
}

function drawSenses(creature) {
  const senses = creature.senses;
  for (const ray of senses.vision) {
    const closeness = 1 - ray.normalized;
    ctx.strokeStyle = `rgba(52, 152, 219, ${0.15 + 0.5 * closeness})`;
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(creature.head_x, creature.head_y);
    ctx.lineTo(ray.hit_x, ray.hit_y);
    ctx.stroke();
    if (ray.normalized < 1) {
      ctx.fillStyle = "rgba(52, 152, 219, 0.9)";
      ctx.beginPath();
      ctx.arc(ray.hit_x, ray.hit_y, 2, 0, Math.PI * 2);
      ctx.fill();
    }
  }
}

function drawCreature(creature) {
  if (creature.senses && creature.senses.touch) {
    ctx.strokeStyle = "#e74c3c";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(creature.x, creature.y, creature.body_length * 0.9, 0, Math.PI * 2);
    ctx.stroke();
  }

  ctx.strokeStyle = creature.color;
  ctx.lineWidth = 2;
  for (const leg of creature.legs) {
    ctx.beginPath();
    ctx.moveTo(leg.x1, leg.y1);
    ctx.lineTo(leg.x2, leg.y2);
    ctx.stroke();
  }

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

function updatePanel(world) {
  const creature = world.creatures[0];
  if (!creature) return;
  const senses = creature.senses;

  if (visionBarsEl.childElementCount !== senses.vision.length) {
    visionBarsEl.innerHTML = "";
    for (let i = 0; i < senses.vision.length; i++) {
      const bar = document.createElement("div");
      bar.className = "vbar";
      visionBarsEl.appendChild(bar);
    }
  }
  senses.vision.forEach((ray, i) => {
    const bar = visionBarsEl.children[i];
    const closeness = 1 - ray.normalized;
    bar.style.height = `${Math.max(4, closeness * 100)}%`;
    bar.style.background = closeness > 0.8 ? "#e74c3c" : "#3498db";
  });

  touchEl.textContent = senses.touch ? "YES" : "no";
  touchEl.className = senses.touch ? "on" : "";

  const energy = senses.interoception ? senses.interoception.energy : null;
  if (energy !== null) {
    energyValueEl.textContent = energy.toFixed(2);
    energyBarEl.style.width = `${Math.round(energy * 100)}%`;
  }

  const p = senses.proprioception;
  proprioEl.textContent =
    `speed: ${p.speed}\n` +
    `turn rate: ${p.turn_rate}\n` +
    `heading: (${p.heading_cos}, ${p.heading_sin})\n` +
    `mode: ${world.mode}`;

  updateRoomBars(world);

  const brain = world.brain || { available: false };
  if (brain.available) {
    brainStatusEl.textContent = "online";
    brainStatusEl.className = "online";
    anomalyValueEl.textContent = brain.anomaly.toFixed(3);
    anomalyBarEl.style.width = `${Math.round(brain.anomaly * 100)}%`;
    anomalyHistory.push(brain.anomaly);
    if (anomalyHistory.length > SPARK_POINTS) anomalyHistory.shift();
    drawSparkline();
  } else {
    brainStatusEl.textContent = "offline — brain runs in local dev (see README)";
    brainStatusEl.className = "";
    anomalyValueEl.textContent = "–";
    anomalyBarEl.style.width = "0%";
    drawOfflineSparkline();
  }

  wanderToggle.checked = world.mode === "wander";
}

function updateRoomBars(world) {
  const numRooms = world.rooms.length;
  if (roomBarsEl.childElementCount !== numRooms) {
    roomBarsEl.innerHTML = "";
    for (let i = 0; i < numRooms; i++) {
      const row = document.createElement("div");
      row.className = "room-row";
      row.innerHTML =
        `<span class="room-label">${i + 1}</span>` +
        `<div class="room-meter"><div class="room-fill"></div></div>` +
        `<span class="room-pct">–</span>`;
      roomBarsEl.appendChild(row);
    }
  }

  const belief = (world.brain && world.brain.room_belief) || null;
  for (let i = 0; i < numRooms; i++) {
    const row = roomBarsEl.children[i];
    const label = row.querySelector(".room-label");
    const fill = row.querySelector(".room-fill");
    const pct = row.querySelector(".room-pct");
    label.classList.toggle("actual", i === world.creature_room);
    if (belief && belief.length === numRooms) {
      const p = belief[i];
      fill.style.width = `${Math.round(p * 100)}%`;
      pct.textContent = `${Math.round(p * 100)}%`;
    } else {
      fill.style.width = "0%";
      pct.textContent = "–";
    }
  }
}

function drawOfflineSparkline() {
  const w = sparkCanvas.width;
  const h = sparkCanvas.height;
  sparkCtx.clearRect(0, 0, w, h);
  sparkCtx.strokeStyle = "#3a4055";
  sparkCtx.lineWidth = 1;
  sparkCtx.beginPath();
  sparkCtx.moveTo(0, h / 2);
  sparkCtx.lineTo(w, h / 2);
  sparkCtx.stroke();
}

function drawSparkline() {
  const w = sparkCanvas.width;
  const h = sparkCanvas.height;
  sparkCtx.clearRect(0, 0, w, h);
  sparkCtx.strokeStyle = "#f1c40f";
  sparkCtx.lineWidth = 1;
  sparkCtx.beginPath();
  anomalyHistory.forEach((value, i) => {
    const x = (i / (SPARK_POINTS - 1)) * w;
    const y = h - value * (h - 2) - 1;
    if (i === 0) sparkCtx.moveTo(x, y);
    else sparkCtx.lineTo(x, y);
  });
  sparkCtx.stroke();
}

connect();
