const DEFAULT_INTERVAL_MS = 10000;

function _sampleIntervalMs() {
  let v = NaN;
  try { v = parseInt(localStorage.getItem('fb-detect-interval'), 10); } catch (e) {}
  return Number.isFinite(v) && v >= 1000 ? v : DEFAULT_INTERVAL_MS;
}

function _websiteTrackingOn() {
  try { return localStorage.getItem('fb-website-tracking') === 'on'; } catch (e) { return false; }
}

function _explainOn() {
  try { return localStorage.getItem('fb-show-reasoning') === 'on'; } catch (e) { return false; }
}

let _stream = null;
let _videoEl = null;
let _intervalId = null;
let _canvas = null;
let _ctx = null;
let _taskName = '';
let _description = '';
let _onStateChange = null;
let _onStatus = null;
let _onActivity = null;
let _paused = false;
let _sampling = false;

async function startDetection(videoEl, taskName, description, onStateChange, onStatus, onActivity) {
  _videoEl = videoEl;
  _taskName = taskName;
  _description = description || '';
  _onStateChange = onStateChange;
  _onStatus = onStatus || null;
  _onActivity = onActivity || null;
  _paused = false;

  _stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  _videoEl.srcObject = _stream;
  await _videoEl.play();

  _canvas = document.createElement('canvas');
  _canvas.width = 320;
  _canvas.height = 240;
  _ctx = _canvas.getContext('2d');

  // On-device face sensors (best-effort; degrades to nothing if MediaPipe can't load).
  if (window.faceMetrics) window.faceMetrics.start(_videoEl);

  _sampleFrame();
  _intervalId = setInterval(_sampleFrame, _sampleIntervalMs());
}

function pauseDetection() {
  _paused = true;
}

function resumeDetection() {
  _paused = false;
  _sampleFrame();
}

function stopDetection() {
  if (window.faceMetrics) window.faceMetrics.stop();
  clearInterval(_intervalId);
  _intervalId = null;
  if (_stream) {
    _stream.getTracks().forEach(t => t.stop());
    _stream = null;
  }
  _videoEl = null;
}

async function _sampleFrame() {
  if (_paused || !_stream || !_videoEl || _sampling) return;
  if (_videoEl.readyState < 2) return;

  _sampling = true;
  try {
    _ctx.drawImage(_videoEl, 0, 0, _canvas.width, _canvas.height);
    const dataUrl = _canvas.toDataURL('image/jpeg', 0.7);
    const base64 = dataUrl.split(',')[1];

    // If the user opted in (and the extension is reporting), fold the active-tab
    // URL + title into the same focus call. Off by default → behaves as before.
    let activity = null;
    if (_websiteTrackingOn()) {
      try {
        const act = await getActivity();
        if (act && act.url) activity = { url: act.url, title: act.title || '' };
      } catch (e) { activity = null; }
      if (_onActivity) _onActivity(activity);
    }

    const sensors = window.faceMetrics ? window.faceMetrics.getSensorLabels() : null;
    const result = await getFocusState(base64, _taskName, _description, activity, _explainOn(), sensors);

    if (_onStatus) _onStatus(true);
    if (!_paused && _onStateChange) {
      _onStateChange(result.state, result.note, result.reason);
    }
  } catch (err) {
    // AI call failed — flag it (with the reason), but keep the last known state (don't reset).
    console.warn('focus-detector: frame sample failed', err);
    if (_onStatus) _onStatus(false, err);
  } finally {
    _sampling = false;
  }
}
