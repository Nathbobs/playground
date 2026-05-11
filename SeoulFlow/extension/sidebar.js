// Swap this for your ngrok URL when tunnelling to the Ubuntu backend
const API_BASE = "http://localhost:8000";

let pollInterval = null;

async function startMonitoring() {
  const videoPath = document.getElementById("video-path").value.trim();
  try {
    await fetch(`${API_BASE}/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ video_path: videoPath }),
    });
  } catch (e) {
    setConnectionError();
    return;
  }
  pollInterval = setInterval(fetchStatus, 1000);
  setControls(true);
}

async function stopMonitoring() {
  clearInterval(pollInterval);
  pollInterval = null;
  try {
    await fetch(`${API_BASE}/stop`, { method: "POST" });
  } catch (_) {
    // Best-effort stop
  }
  setControls(false);
}

async function fetchStatus() {
  try {
    const res = await fetch(`${API_BASE}/status`);
    if (!res.ok) return;
    renderStatus(await res.json());
  } catch (_) {
    setConnectionError();
  }
}

function renderStatus(data) {
  document.getElementById("total").textContent = data.total_vehicles;
  document.getElementById("moving").textContent = data.moving;
  document.getElementById("stationary").textContent = data.stationary;
  document.getElementById("fps").textContent = data.fps.toFixed(1);

  const badge = document.getElementById("status-badge");
  badge.textContent = data.status;
  badge.className = "badge " + data.status.toLowerCase();

  const pct = Math.round(data.congestion_score * 100);
  document.getElementById("score-bar").style.width = `${pct}%`;
  document.getElementById("score-value").textContent = data.congestion_score.toFixed(2);
}

function setControls(running) {
  document.getElementById("btn-start").disabled = running;
  document.getElementById("btn-stop").disabled = !running;
  document.getElementById("video-path").disabled = running;
}

function setConnectionError() {
  const badge = document.getElementById("status-badge");
  badge.textContent = "OFFLINE";
  badge.className = "badge offline";
}

document.getElementById("btn-start").addEventListener("click", startMonitoring);
document.getElementById("btn-stop").addEventListener("click", stopMonitoring);
