// Shared notification helpers: in-app toasts, a subtle chime, browser
// notifications, and a styled confirm dialog. Loaded on every page.
// Exposes: showToast, playChime, notifyUser, requestNotifyPermission, confirmDialog.
(function () {
  // Escape user-controlled text before it goes into innerHTML. These helpers
  // escape the message internally so callers can pass raw text safely.
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

  /* ---------- in-app toast ---------- */
  function toastWrap() {
    var w = document.getElementById('toast-wrap');
    if (!w) {
      w = document.createElement('div');
      w.id = 'toast-wrap';
      w.className = 'toast-wrap';
      document.body.appendChild(w);
    }
    return w;
  }

  window.showToast = function (message, opts) {
    opts = opts || {};
    var t = document.createElement('div');
    t.className = 'toast';
    t.setAttribute('role', 'status');
    t.innerHTML = (opts.icon ? '<span style="font-size:1.1rem;line-height:1">' + opts.icon + '</span>' : '') +
      '<span>' + esc(message) + '</span>';
    toastWrap().appendChild(t);
    var done = false;
    function dismiss() {
      if (done) return; done = true;
      t.style.opacity = '0';
      t.style.transform = 'translateY(6px)';
      setTimeout(function () { t.remove(); }, 220);
    }
    t.addEventListener('click', dismiss);
    setTimeout(dismiss, opts.duration || 4500);
  };

  /* ---------- subtle chime (Web Audio, no asset) ---------- */
  var _audioCtx = null;
  window.playChime = function () {
    var on = false;
    try { on = localStorage.getItem('fb-sounds') === 'on'; } catch (e) {}
    if (!on) return;
    try {
      var Ctx = window.AudioContext || window.webkitAudioContext;
      if (!Ctx) return;
      _audioCtx = _audioCtx || new Ctx();
      if (_audioCtx.state === 'suspended') _audioCtx.resume();
      var now = _audioCtx.currentTime;
      [ [880, 0], [1175, 0.13] ].forEach(function (pair) {
        var osc = _audioCtx.createOscillator();
        var gain = _audioCtx.createGain();
        osc.type = 'sine';
        osc.frequency.value = pair[0];
        var t0 = now + pair[1];
        gain.gain.setValueAtTime(0.0001, t0);
        gain.gain.exponentialRampToValueAtTime(0.18, t0 + 0.02);
        gain.gain.exponentialRampToValueAtTime(0.0001, t0 + 0.22);
        osc.connect(gain); gain.connect(_audioCtx.destination);
        osc.start(t0); osc.stop(t0 + 0.24);
      });
    } catch (e) { /* audio blocked — ignore */ }
  };

  /* ---------- browser notifications (opt-in) ---------- */
  window.requestNotifyPermission = function () {
    if (!('Notification' in window)) return Promise.resolve('unsupported');
    return Notification.requestPermission();
  };

  window.notifyUser = function (title, body) {
    var on = false;
    try { on = localStorage.getItem('fb-notify') === 'on'; } catch (e) {}
    if (!on || !('Notification' in window) || Notification.permission !== 'granted') return;
    try { new Notification(title, { body: body, silent: true }); } catch (e) {}
  };

  /* ---------- styled confirm dialog (replaces window.confirm) ---------- */
  window.confirmDialog = function (message, opts) {
    opts = opts || {};
    return new Promise(function (resolve) {
      var overlay = document.createElement('div');
      overlay.className = 'modal-overlay';
      overlay.style.display = 'flex';
      overlay.innerHTML =
        '<div class="modal" role="dialog" aria-modal="true" style="max-width:380px">' +
          '<p class="text-sm" style="color:var(--text);margin:0 0 18px;line-height:1.5">' + esc(message) + '</p>' +
          '<div class="flex gap-3 justify-end">' +
            '<button class="btn-ghost" data-act="cancel" style="min-height:42px">' + (opts.cancelText || 'Cancel') + '</button>' +
            '<button class="' + (opts.danger ? 'btn-danger' : 'btn-primary') + '" data-act="ok" style="min-height:42px">' + (opts.confirmText || 'Confirm') + '</button>' +
          '</div>' +
        '</div>';
      document.body.appendChild(overlay);
      var prevOverflow = document.body.style.overflow;
      document.body.style.overflow = 'hidden';

      function close(result) {
        document.body.style.overflow = prevOverflow;
        overlay.remove();
        document.removeEventListener('keydown', onKey);
        resolve(result);
      }
      function onKey(e) { if (e.key === 'Escape') close(false); }

      overlay.addEventListener('click', function (e) {
        if (e.target === overlay) close(false);
        var act = e.target.closest('[data-act]');
        if (act) close(act.dataset.act === 'ok');
      });
      document.addEventListener('keydown', onKey);
      overlay.querySelector('[data-act="ok"]').focus();
    });
  };
})();
