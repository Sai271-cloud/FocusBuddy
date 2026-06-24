// On-device face sensors (MediaPipe Face Landmarker).
//
// Runs the webcam through MediaPipe locally (~4 fps), turns the landmarks into a few
// SMOOTHED semantic labels — eyes open/closed, head facing/away/down, face present —
// and exposes them as a short string via getSensorLabels(). The focus detector reads
// that string and sends it (text only) alongside the frame to Gemini, which fuses it
// with the image. Landmarks/EAR never leave the browser.
//
// Fail-safe by design: if MediaPipe can't load or errors, getSensorLabels() returns
// null and the app behaves exactly as before (no on-device sensors, no crash).
(function () {
  // @latest keeps the JS bundle and the /wasm assets on the same version. Pin a
  // specific version for production if you want fully reproducible loads.
  var TASKS_VISION = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/+esm';
  var WASM_ROOT = 'https://cdn.jsdelivr.net/npm/@mediapipe/tasks-vision@latest/wasm';
  var MODEL = 'https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/1/face_landmarker.task';

  // Tuning constants (eye-aspect-ratio + head geometry). Easy to adjust.
  var EAR_CLOSED = 0.18;   // smoothed EAR below this → eyes closed
  var EAR_DROWSY = 0.22;   // between closed and this → half-closed
  var YAW_AWAY = 0.16;     // |nose offset| / eye-width above this → head turned away
  var PITCH_DOWN = 0.78;   // (eyes→nose)/(eyes→chin) above this → head tilted down
  var SAMPLE_MS = 250;     // ~4 fps (per the browser-vision skill: 1–5 fps, not rAF)
  var WINDOW_MS = 1500;    // EAR smoothing window (rejects blinks)

  // EAR landmark indices [p1 outer, p2 top, p3 top, p4 inner, p5 bottom, p6 bottom].
  var LEFT_EYE = [33, 160, 158, 133, 153, 144];
  var RIGHT_EYE = [362, 385, 387, 263, 373, 380];

  var landmarker = null;
  var ready = false;
  var failed = false;
  var loading = false;
  var _video = null;
  var _interval = null;
  var _earWindow = [];     // [{ t, ear }]
  var _closedSince = null; // performance.now() when eyes first closed
  var _last = null;        // latest derived metrics

  function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }

  function earFor(lms, idx) {
    var v = dist(lms[idx[1]], lms[idx[5]]) + dist(lms[idx[2]], lms[idx[4]]);
    var h = 2 * dist(lms[idx[0]], lms[idx[3]]);
    return h > 0 ? v / h : 0;
  }

  async function load() {
    if (ready || failed || loading) return;
    loading = true;
    try {
      var vision = await import(TASKS_VISION);
      var fileset = await vision.FilesetResolver.forVisionTasks(WASM_ROOT);
      landmarker = await vision.FaceLandmarker.createFromOptions(fileset, {
        baseOptions: { modelAssetPath: MODEL, delegate: 'GPU' },
        runningMode: 'VIDEO',
        numFaces: 1,
      });
      ready = true;
    } catch (e) {
      console.warn('face-metrics: MediaPipe unavailable — continuing without on-device sensors', e);
      failed = true;
    } finally {
      loading = false;
    }
  }

  function analyze() {
    if (!ready || !_video || _video.readyState < 2) return;
    var res;
    try { res = landmarker.detectForVideo(_video, performance.now()); }
    catch (e) { return; }

    var now = performance.now();
    if (!res || !res.faceLandmarks || res.faceLandmarks.length === 0) {
      _last = { present: false };
      _earWindow = [];
      _closedSince = null;
      return;
    }

    var lms = res.faceLandmarks[0];
    var ear = (earFor(lms, LEFT_EYE) + earFor(lms, RIGHT_EYE)) / 2;
    _earWindow.push({ t: now, ear: ear });
    _earWindow = _earWindow.filter(function (e) { return now - e.t <= WINDOW_MS; });
    var avg = _earWindow.reduce(function (s, e) { return s + e.ear; }, 0) / _earWindow.length;

    var eyesClosed = avg < EAR_CLOSED;
    var drowsy = !eyesClosed && avg < EAR_DROWSY;
    if (eyesClosed) { if (_closedSince === null) _closedSince = now; }
    else { _closedSince = null; }

    // Head yaw: nose tip (1) horizontal offset from the eye-corner midpoint.
    var midX = (lms[33].x + lms[263].x) / 2;
    var eyeW = Math.abs(lms[263].x - lms[33].x) || 1e-6;
    var yaw = Math.abs(lms[1].x - midX) / eyeW;
    // Head pitch (down): nose drops toward the chin relative to the eye line.
    var eyeY = (lms[33].y + lms[263].y) / 2;
    var span = (lms[152].y - eyeY) || 1e-6;
    var pitchRatio = (lms[1].y - eyeY) / span;

    _last = {
      present: true,
      eyesClosed: eyesClosed,
      drowsy: drowsy,
      closedMs: (eyesClosed && _closedSince !== null) ? (now - _closedSince) : 0,
      turnedAway: yaw > YAW_AWAY,
      headDown: pitchRatio > PITCH_DOWN,
    };
  }

  function getSensorLabels() {
    if (failed || !ready || !_last) return null;
    if (!_last.present) return 'no face detected';
    var parts = [];
    if (_last.eyesClosed) {
      parts.push('eyes closed' + (_last.closedMs >= 1500 ? ' (~' + Math.round(_last.closedMs / 1000) + 's)' : ''));
    } else if (_last.drowsy) {
      parts.push('eyes half-closed');
    } else {
      parts.push('eyes open');
    }
    parts.push(_last.turnedAway ? 'head turned away' : (_last.headDown ? 'head tilted down' : 'facing screen'));
    parts.push('face present');
    return parts.join(' · ');
  }

  function start(videoEl) {
    _video = videoEl;
    load();   // best-effort; analyze() is a no-op until ready
    if (_interval) clearInterval(_interval);
    _interval = setInterval(analyze, SAMPLE_MS);
  }

  function stop() {
    if (_interval) { clearInterval(_interval); _interval = null; }
    _video = null;
    _earWindow = [];
    _closedSince = null;
    _last = null;
  }

  window.faceMetrics = { start: start, stop: stop, getSensorLabels: getSensorLabels };
})();
