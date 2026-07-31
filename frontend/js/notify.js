(function () {
  function esc(s) {
    return String(s).replace(/[&<>"']/g, function (c) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c];
    });
  }

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
    t.className = 'toast' + (opts.danger ? ' toast-danger' : '');
    t.setAttribute('role', opts.danger ? 'alert' : 'status');
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
    } catch (e) {  }
  };

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

  // Keeps Tab cycling inside an open modal and returns focus to the element
  // that opened it. Returns a release() to call when the modal closes.
  window.trapModalFocus = function (modalEl, opener) {
    function focusables() {
      var nodes = modalEl.querySelectorAll(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])');
      return Array.prototype.filter.call(nodes, function (el) {
        return !el.disabled && el.getClientRects().length > 0;
      });
    }
    function onKey(e) {
      if (e.key !== 'Tab') return;
      var els = focusables();
      if (!els.length) return;
      var first = els[0], last = els[els.length - 1];
      var inside = modalEl.contains(document.activeElement);
      if (e.shiftKey && (document.activeElement === first || !inside)) {
        e.preventDefault(); last.focus();
      } else if (!e.shiftKey && (document.activeElement === last || !inside)) {
        e.preventDefault(); first.focus();
      }
    }
    document.addEventListener('keydown', onKey, true);
    return function release() {
      document.removeEventListener('keydown', onKey, true);
      if (opener && typeof opener.focus === 'function' && document.contains(opener)) {
        try { opener.focus(); } catch (e) {}
      }
    };
  };

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
      var releaseTrap = window.trapModalFocus(overlay.querySelector('.modal'), document.activeElement);

      function close(result) {
        document.body.style.overflow = prevOverflow;
        overlay.remove();
        document.removeEventListener('keydown', onKey);
        releaseTrap();
        resolve(result);
      }
      function onKey(e) { if (e.key === 'Escape') close(false); }

      overlay.addEventListener('click', function (e) {
        if (e.target === overlay) close(false);
        var act = e.target.closest('[data-act]');
        if (act) close(act.dataset.act === 'ok');
      });
      document.addEventListener('keydown', onKey);
      // A destructive confirm starts on Cancel so Enter can't instantly delete.
      overlay.querySelector(opts.danger ? '[data-act="cancel"]' : '[data-act="ok"]').focus();
    });
  };
})();
