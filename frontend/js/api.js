const API = window.FOCUS_BUDDY_API !== undefined ? window.FOCUS_BUDDY_API : 'http://127.0.0.1:8000';

function demoHeaders() {
  return window.FocusBuddyDemo && window.FocusBuddyDemo.headers
    ? window.FocusBuddyDemo.headers()
    : {};
}

function withHeaders(options = {}, extra = {}) {
  return {
    ...options,
    headers: {
      ...demoHeaders(),
      ...(options.headers || {}),
      ...extra,
    },
  };
}

async function requestJson(url, options = {}) {
  const r = await fetch(url, withHeaders(options));
  if (!r.ok) {
    let detail = '';
    try {
      const body = await r.json();
      detail = body && body.detail ? `: ${body.detail}` : '';
    } catch {}
    throw new Error(`${options.method || 'GET'} ${url} failed: ${r.status}${detail}`);
  }
  return r.json();
}

async function createTask(name, description = '') {
  return requestJson(`${API}/tasks`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ name, description }),
  });
}

async function getTasks() {
  return requestJson(`${API}/tasks`);
}

async function getTask(taskId) {
  return requestJson(`${API}/tasks/${taskId}`);
}

async function updateTask(taskId, data) {
  return requestJson(`${API}/tasks/${taskId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function deleteTask(taskId) {
  return requestJson(`${API}/tasks/${taskId}`, { method: 'DELETE' });
}

async function deleteSession(sessionId) {
  return requestJson(`${API}/sessions/${sessionId}`, { method: 'DELETE' });
}

async function startSession(taskId, startedAt = null) {
  const payload = { task_id: taskId };
  if (startedAt) payload.started_at = startedAt;
  return requestJson(`${API}/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function createSession(data) {
  return requestJson(`${API}/sessions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function getSessions() {
  return requestJson(`${API}/sessions`);
}

async function updateSession(sessionId, data, extra = {}) {
  return requestJson(`${API}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
    ...extra,
  });
}

async function finishSession(sessionId, data) {
  return requestJson(`${API}/sessions/${sessionId}/finish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function createWorkPeriod(data) {
  return requestJson(`${API}/work-periods`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function getWorkPeriods() {
  return requestJson(`${API}/work-periods`);
}

async function getDemoWorkspace(slug) {
  return requestJson(`${API}/demo/${encodeURIComponent(slug)}`);
}

async function getDemoDailyUnwinds(slug) {
  return requestJson(`${API}/demo/${encodeURIComponent(slug)}/daily-unwinds`);
}

async function resetDemoWorkspace(slug) {
  return requestJson(`${API}/demo/${encodeURIComponent(slug)}/reset`, { method: 'POST' });
}

async function clearNewDemoWorkspace() {
  return requestJson(`${API}/demo/new/clear`, { method: 'POST' });
}

async function getDebrief(sessionId) {
  return requestJson(`${API}/sessions/${sessionId}/debrief`, { method: 'POST' });
}

async function getDailyUnwind(payload) {
  return requestJson(`${API}/unwind/daily`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function getWeeklyUnwind(payload) {
  return requestJson(`${API}/unwind/weekly`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function getProfile() {
  return requestJson(`${API}/profile`);
}

async function saveProfile(about) {
  return requestJson(`${API}/profile`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ about }),
  });
}

async function getActivity() {
  return requestJson(`${API}/activity`);
}

async function setTrackingState(active, extra = {}) {
  return requestJson(`${API}/tracking-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active: !!active }),
    ...extra,
  });
}

async function getObservations() {
  return requestJson(`${API}/observations`);
}

async function deleteObservation(obsId) {
  return requestJson(`${API}/observations/${obsId}`, { method: 'DELETE' });
}

async function learnFromSession(sessionId, startHour = null, endHour = null) {
  return requestJson(`${API}/sessions/${sessionId}/learn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_hour: startHour, end_hour: endHour }),
  });
}

async function getHourlyFocus() {
  return requestJson(`${API}/hourly-focus`);
}

async function getPlan(periodKey) {
  return requestJson(`${API}/plan/${periodKey}`);
}

async function getPlanReality(periodKey, bounds) {
  const params = new URLSearchParams({
    day_start: bounds.day_start,
    day_end: bounds.day_end,
  });
  return requestJson(`${API}/plan/${periodKey}/reality?${params.toString()}`);
}

async function getPlanCalibration(limit = 14) {
  return requestJson(`${API}/plan/calibration?limit=${encodeURIComponent(limit)}`);
}

async function savePlan(data) {
  return requestJson(`${API}/plan`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function deletePlan(periodKey) {
  return requestJson(`${API}/plan/${periodKey}`, { method: 'DELETE' });
}

async function getPlanAdvice(payload) {
  return requestJson(`${API}/plan/advice`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function analyzeFocus(frameBase64, taskName, description = '', activity = null, explain = false, sensors = null) {
  const r = await fetch(`${API}/focus/analyze`, withHeaders({
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      frame_base64: frameBase64,
      task_name: taskName,
      description,
      current_url: (activity && activity.url) || null,
      current_title: (activity && activity.title) || null,
      explain: !!explain,
      sensors: sensors || null,
    }),
  }));
  if (!r.ok) {
    let detail = '';
    try {
      const body = await r.json();
      detail = (body && body.detail) || '';
    } catch {}
    const err = new Error(detail || `Focus analysis failed (${r.status})`);
    err.status = r.status;
    err.detail = detail;
    throw err;
  }
  return r.json();
}
