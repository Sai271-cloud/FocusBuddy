const SAMPLE_INTERVAL_MS = 5000;

let _stream = null;
let _videoEl = null;
let _intervalId = null;
let _canvas = null;
let _ctx = null;
let _taskName = '';
let _description = '';
let _onStateChange = null;
let _paused = false;
let _sampling = false;

async function startDetection(videoEl, taskName, description, onStateChange) {
  _videoEl = videoEl;
  _taskName = taskName;
  _description = description || '';
  _onStateChange = onStateChange;
  _paused = false;

  _stream = await navigator.mediaDevices.getUserMedia({ video: true, audio: false });
  _videoEl.srcObject = _stream;
  await _videoEl.play();

  _canvas = document.createElement('canvas');
  _canvas.width = 320;
  _canvas.height = 240;
  _ctx = _canvas.getContext('2d');

  _sampleFrame();
  _intervalId = setInterval(_sampleFrame, SAMPLE_INTERVAL_MS);
}

function pauseDetection() {
  _paused = true;
}

function resumeDetection() {
  _paused = false;
  _sampleFrame();
}

function stopDetection() {
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

    const state = await getFocusState(base64, _taskName, _description);

    if (!_paused && _onStateChange) {
      _onStateChange(state);
    }
  } catch (err) {
    console.warn('focus-detector: frame sample failed', err);
  } finally {
    _sampling = false;
  }
}
