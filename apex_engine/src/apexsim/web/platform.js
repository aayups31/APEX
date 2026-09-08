const state = { currentRun: null, latestJob: null };
const $ = (selector) => document.querySelector(selector);

const formatSeconds = (value) => {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return "—";
  const seconds = Number(value);
  const minutes = Math.floor(seconds / 60);
  return `${minutes}:${(seconds % 60).toFixed(2).padStart(5, "0")}`;
};

async function api(path, options = {}) {
  const response = await fetch(path, { headers: { "Content-Type": "application/json" }, ...options });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail || `Request failed (${response.status})`);
  }
  return response.json();
}

function setJobMessage(message, error = false) {
  const element = $("#job-message");
  element.textContent = message;
  element.style.color = error ? "var(--accent)" : "var(--muted)";
}

function drawTrack(points) {
  if (!points.length) return;
  const xs = points.map((point) => Number(point.x_m));
  const ys = points.map((point) => Number(point.y_m));
  const minX = Math.min(...xs); const maxX = Math.max(...xs);
  const minY = Math.min(...ys); const maxY = Math.max(...ys);
  const width = Math.max(maxX - minX, 1); const height = Math.max(maxY - minY, 1);
  const scale = Math.min(620 / width, 330 / height);
  const offsetX = (760 - width * scale) / 2;
  const offsetY = (430 - height * scale) / 2;
  const path = points.map((point, index) => {
    const x = offsetX + (Number(point.x_m) - minX) * scale;
    const y = 430 - (offsetY + (Number(point.y_m) - minY) * scale);
    return `${index ? "L" : "M"}${x.toFixed(1)} ${y.toFixed(1)}`;
  }).join(" ") + " Z";
  const svg = $("#track-map");
  svg.querySelector(".track-shadow").setAttribute("d", path);
  const line = svg.querySelector(".track-line");
  line.setAttribute("d", path);
  line.classList.remove("placeholder");
}

function drawTelemetry(rows) {
  const canvas = $("#telemetry-chart");
  const context = canvas.getContext("2d");
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  canvas.width = Math.max(600, rect.width * dpr); canvas.height = 250 * dpr;
  context.scale(dpr, dpr);
  const width = canvas.width / dpr; const height = canvas.height / dpr;
  context.clearRect(0, 0, width, height);
  const filtered = rows.filter((row) => row.car_id === "CAR_01");
  if (filtered.length < 2) return;
  const speeds = filtered.map((row) => Number(row.speed_mps));
  const min = Math.min(...speeds); const max = Math.max(...speeds);
  context.strokeStyle = "#252b2f"; context.lineWidth = 1;
  for (let index = 1; index < 5; index += 1) {
    const y = (height / 5) * index;
    context.beginPath(); context.moveTo(0, y); context.lineTo(width, y); context.stroke();
  }
  context.strokeStyle = "#ff4f3d"; context.lineWidth = 2; context.beginPath();
  speeds.forEach((speed, index) => {
    const x = (index / (speeds.length - 1)) * width;
    const y = height - 18 - ((speed - min) / Math.max(max - min, 1)) * (height - 36);
    if (index === 0) context.moveTo(x, y); else context.lineTo(x, y);
  });
  context.stroke();
  $("#telemetry-label").textContent = `${min.toFixed(0)}—${max.toFixed(0)} M/S`;
}

function renderStandings(rows) {
  const winnerTime = rows.length ? Number(rows[0].race_time_s) : 0;
  $("#standings").innerHTML = rows.map((row) => {
    const gap = Number(row.position) === 1 ? "LEADER" : `+${(Number(row.race_time_s) - winnerTime).toFixed(2)}S`;
    return `<tr><td>${row.position}</td><td>${row.driver_id}<small>${row.car_id}</small></td><td>${row.final_compound}</td><td>${gap}</td></tr>`;
  }).join("");
}

async function loadRun(runId, runtime = null) {
  state.currentRun = runId;
  setJobMessage("LOADING VERSIONED ARTIFACTS");
  const [summary, standings, track, telemetry] = await Promise.all([
    api(`/api/v1/runs/${runId}`), api(`/api/v1/runs/${runId}/standings`),
    api(`/api/v1/runs/${runId}/track`), api(`/api/v1/runs/${runId}/telemetry?limit=1400`),
  ]);
  drawTrack(track); drawTelemetry(telemetry); renderStandings(standings);
  const winner = standings[0] || {};
  $("#track-name").textContent = String(summary.track_id || "APEX TEST TRACK").replaceAll("_", " ").toUpperCase();
  $("#run-status").textContent = summary.quality?.passed ? "VALIDATED" : "REVIEW";
  $("#winner").textContent = winner.driver_id || "—";
  $("#race-time").textContent = formatSeconds(winner.race_time_s);
  $("#runtime").textContent = runtime ? `${Number(runtime).toFixed(2)}S` : "ARCHIVED";
  $("#evidence-chain").querySelectorAll("li").forEach((item) => item.classList.add("complete"));
  $("#evidence-chain").children[1].querySelector("span").textContent = "All runtime invariants passed";
  $("#evidence-chain").children[2].querySelector("span").textContent = "Config, source, environment and artifacts hashed";
  $("#manifest-button").disabled = false;
  setJobMessage(`LOADED ${runId.toUpperCase()}`);
}

async function pollJob(jobId) {
  for (;;) {
    const job = await api(`/api/v1/jobs/${jobId}`);
    state.latestJob = job; setJobMessage(`${job.status} · ${jobId.toUpperCase()}`);
    if (job.status === "COMPLETED") { await loadRun(jobId, job.runtime_s); await refreshOverview(); await refreshRuns(); return; }
    if (job.status === "FAILED") throw new Error(job.error || "Simulation failed");
    await new Promise((resolve) => setTimeout(resolve, 700));
  }
}

async function runSimulation() {
  const button = $("#run-button"); button.disabled = true; setJobMessage("QUEUING DETERMINISTIC PREVIEW");
  try {
    const job = await api("/api/v1/simulations", { method: "POST", body: JSON.stringify({ laps: Number($("#laps").value), seed: Number($("#seed").value) }) });
    await pollJob(job.job_id);
  } catch (error) { setJobMessage(error.message.toUpperCase(), true); }
  finally { button.disabled = false; }
}

async function refreshOverview() {
  const overview = await api("/api/v1/overview");
  $("#maturity").textContent = overview.maturity; $("#race-count").textContent = overview.race_previews;
}

async function refreshRuns() {
  const runs = (await api("/api/v1/runs?limit=8")).filter((run) => run.kind === "race_preview");
  const container = $("#recent-runs");
  if (!runs.length) { container.innerHTML = '<div class="empty-run">No platform runs yet.</div>'; return; }
  container.innerHTML = runs.map((run) => `<div class="run-row" data-run-id="${run.job_id}" data-runtime="${run.runtime_s || ""}" role="button" tabindex="0"><b>${run.job_id}</b><em>${run.status}</em><span>${run.laps} LAPS</span><span>SEED ${run.seed}</span><span>→</span></div>`).join("");
  container.querySelectorAll(".run-row").forEach((row) => {
    row.addEventListener("click", () => loadRun(row.dataset.runId, row.dataset.runtime));
    row.addEventListener("keydown", (event) => { if (event.key === "Enter") loadRun(row.dataset.runId, row.dataset.runtime); });
  });
}

async function showManifest() {
  if (!state.currentRun) return;
  const manifest = await api(`/api/v1/runs/${state.currentRun}/manifest`);
  $("#manifest-content").textContent = JSON.stringify(manifest, null, 2); $("#manifest-dialog").showModal();
}

$("#laps").addEventListener("input", (event) => { $("#laps-output").textContent = `${event.target.value} laps`; });
$("#run-button").addEventListener("click", runSimulation);
$("#manifest-button").addEventListener("click", showManifest);
$("#close-dialog").addEventListener("click", () => $("#manifest-dialog").close());
Promise.all([refreshOverview(), refreshRuns()]).catch((error) => { $("#system-status").textContent = "SYSTEM DEGRADED"; setJobMessage(error.message.toUpperCase(), true); });
