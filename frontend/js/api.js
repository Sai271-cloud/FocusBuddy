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

async function updateSession(sessionId, data) {
  return requestJson(`${API}/sessions/${sessionId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function finishSession(sessionId, data) {
  return requestJson(`${API}/sessions/${sessionId}/finish`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
}

async function analyzeFocus(frameBase64, taskName, description = '') {
  const r = await fetch(`${API}/focus/analyze`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ frame_base64: frameBase64, task_name: taskName, description }),
  });
  if (!r.ok) throw new Error(`analyzeFocus failed: ${r.status}`);
  return r.json();
}
