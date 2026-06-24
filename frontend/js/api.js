const API = window.FOCUS_BUDDY_API || 'http://127.0.0.1:8000';

async function requestJson(url, options = {}) {
  const r = await fetch(url, options);
  if (!r.ok) throw new Error(`${options.method || 'GET'} ${url} failed: ${r.status}`);
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

async function startSession(taskId) {
  return requestJson(`${API}/sessions/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ task_id: taskId }),
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
  // `extra` lets callers pass fetch options like { keepalive: true } for saves
  // that must survive the page closing.
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

async function getDebrief(sessionId) {
  // AI focus-coach feedback for one finished session. Best-effort: callers must
  // handle failure gracefully (the session is already saved before this runs).
  return requestJson(`${API}/sessions/${sessionId}/debrief`, { method: 'POST' });
}

async function getDailyUnwind(payload) {
  // AI coaching for one day. Best-effort: callers handle failure gracefully.
  return requestJson(`${API}/unwind/daily`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}

async function getWeeklyUnwind(payload) {
  // AI coaching for a week (+ optional Pomodoro recommendation). Best-effort.
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
  // Latest active-tab URL reported by the browser extension (null if none/stale).
  return requestJson(`${API}/activity`);
}

async function setTrackingState(active, extra = {}) {
  // Tell the backend whether the tracker is actively tracking (with website
  // awareness on). The extension checks this before reporting. `extra` allows
  // { keepalive: true } so the "off" signal survives the page closing.
  return requestJson(`${API}/tracking-state`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ active: !!active }),
    ...extra,
  });
}

async function getObservations() {
  // The Pattern Memory: AI-learned focus patterns (with affirm/reject counts + status).
  return requestJson(`${API}/observations`);
}

async function deleteObservation(obsId) {
  return requestJson(`${API}/observations/${obsId}`, { method: 'DELETE' });
}

async function learnFromSession(sessionId, startHour = null, endHour = null) {
  // Background "learn" call after a session — updates the hourly focus profile and
  // affirms/rejects/adds focus patterns. Best-effort: callers ignore failure.
  return requestJson(`${API}/sessions/${sessionId}/learn`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ start_hour: startHour, end_hour: endHour }),
  });
}

async function getHourlyFocus() {
  // The 24-hour "focus by hour" profile (focus % + session count per local hour).
  return requestJson(`${API}/hourly-focus`);
}

async function analyzeFocus(frameBase64, taskName, description = '', activity = null, explain = false, sensors = null) {
  const r = await fetch(`${API}/focus/analyze`, {
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
  });
  if (!r.ok) throw new Error(`analyzeFocus failed: ${r.status}`);
  return r.json();
}
