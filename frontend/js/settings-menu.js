// Gear-icon settings dropdown. Enhances a #settings-btn trigger in the header
// with a popover (appearance, focus-check interval, notifications). Shared by
// every page that shows the gear, so the markup/logic lives in one place.
(function () {
  function get(key, fallback) {
    try { var v = localStorage.getItem(key); return v === null ? fallback : v; } catch (e) { return fallback; }
  }
  function set(key, val) { try { localStorage.setItem(key, val); } catch (e) {} }

  function row(labelHtml, subHtml, controlHtml) {
    return '<div class="flex items-center justify-between gap-4" style="margin-top:2px">' +
             '<div class="min-w-0"><p class="text-sm font-medium" style="color:var(--text);margin:0">' + labelHtml + '</p>' +
             (subHtml ? '<p class="text-xs" style="color:var(--text-muted);margin:2px 0 0">' + subHtml + '</p>' : '') +
             '</div>' + controlHtml +
           '</div>';
  }
  function toggle(id, checked) {
    return '<label class="switch" style="margin-top:2px"><input type="checkbox" id="' + id + '"' + (checked ? ' checked' : '') + ' /><span class="slider"></span></label>';
  }

  function escapeHtml(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  // Colored chip for a pattern's confidence status.
  function statusBadge(status) {
    var map = {
      confirmed: ['#16794422', '#0f6b3e', 'confirmed'],
      emerging:  ['var(--surface-2, #00000010)', 'var(--text-muted)', 'emerging'],
      retired:   ['#9aa0a610', 'var(--text-muted)', 'retired'],
    };
    var c = map[status] || map.emerging;
    return '<span style="flex:none;font-size:10px;font-weight:600;padding:2px 7px;border-radius:999px;' +
      'background:' + c[0] + ';color:' + c[1] + '">' + c[2] + '</span>';
  }

  // Compact 12-hour labels for the focus-by-hour grid: 0 -> "12a", 9 -> "9a", 15 -> "3p".
  function hourLabelShort(h) {
    var ap = h < 12 ? 'a' : 'p';
    var hh = h % 12; if (hh === 0) hh = 12;
    return hh + ap;
  }
  function hourLabelFull(h) {
    var ap = h < 12 ? 'AM' : 'PM';
    var hh = h % 12; if (hh === 0) hh = 12;
    return hh + ':00 ' + ap;
  }

  // Parts of the day — each hour is tagged by the section it falls in. Night wraps
  // past midnight, so its hours are listed in reading order (9pm → 4am).
  var DAY_SECTIONS = [
    { label: 'Morning',   range: '5am–12pm', hours: [5, 6, 7, 8, 9, 10, 11] },
    { label: 'Afternoon', range: '12pm–5pm', hours: [12, 13, 14, 15, 16] },
    { label: 'Evening',   range: '5pm–9pm',  hours: [17, 18, 19, 20] },
    { label: 'Night',     range: '9pm–5am',  hours: [21, 22, 23, 0, 1, 2, 3, 4] },
  ];

  // One hour cell: short label + focus % (or “—” when no data), tinted by focus level.
  function hourCellHtml(h) {
    var has = h.sessions > 0;
    var pct = Math.round(h.focus_pct || 0);
    var bg = has ? 'rgba(22,121,68,' + (0.10 + (pct / 100) * 0.55).toFixed(2) + ')' : 'transparent';
    var border = has ? 'transparent' : 'var(--border, #00000014)';
    var tip = hourLabelFull(h.hour) + (has ? (' · ' + pct + '% focus · ' + h.sessions + ' session' + (h.sessions === 1 ? '' : 's')) : ' · no data');
    return '<div title="' + tip + '" style="text-align:center;border-radius:8px;padding:6px 2px;background:' + bg + ';border:1px solid ' + border + '">' +
        '<div style="font-size:10px;color:var(--text-muted);line-height:1">' + hourLabelShort(h.hour) + '</div>' +
        '<div class="text-sm" style="font-weight:600;color:var(--text);line-height:1.3">' + (has ? pct + '%' : '—') + '</div>' +
      '</div>';
  }

  // "About you" editor + the read-only "Pattern Memory" the AI builds over time.
  // Built on demand, available on any page that loads this script + api.js.
  function openAboutModal() {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML =
      '<div class="modal" role="dialog" aria-modal="true" aria-label="About you" style="max-width:460px;max-height:88vh;overflow-y:auto">' +
        '<h2 class="serif" style="font-size:1.15rem;font-weight:600;margin:0 0 6px">About you</h2>' +
        '<p class="text-xs" style="color:var(--text-muted);margin:0 0 12px;line-height:1.5">Tell the AI about your setup, schedule, and habits so it reads your sessions better — e.g. “I work in an office with 3 monitors and take a break around 3pm.” This is shared with the AI to improve detection.</p>' +
        '<textarea id="about-text" class="input" rows="6" maxlength="1000" style="width:100%;resize:vertical" placeholder="Anything that helps the AI understand your environment…"></textarea>' +
        '<div class="flex gap-3 justify-end" style="margin-top:14px">' +
          '<button class="btn-ghost" data-act="cancel" style="min-height:42px">Cancel</button>' +
          '<button class="btn-primary" data-act="save" style="min-height:42px">Save</button>' +
        '</div>' +
        '<div style="border-top:1px solid var(--border, #00000014);margin:18px 0 0;padding-top:16px">' +
          '<h3 class="serif" style="font-size:1rem;font-weight:600;margin:0 0 4px">What Focus Buddy has noticed</h3>' +
          '<p class="text-xs" style="color:var(--text-muted);margin:0 0 10px;line-height:1.5">Patterns the AI learns from your sessions. It confirms or drops these over time. Remove any that don’t fit you.</p>' +
          '<div id="patterns-list"><p class="text-xs" style="color:var(--text-muted);margin:0">Loading…</p></div>' +
        '</div>' +
        '<div style="border-top:1px solid var(--border, #00000014);margin:18px 0 0;padding-top:16px">' +
          '<h3 class="serif" style="font-size:1rem;font-weight:600;margin:0 0 4px">Focus by hour</h3>' +
          '<p class="text-xs" style="color:var(--text-muted);margin:0 0 10px;line-height:1.5">Your average focus for each hour of the day, learned from your sessions. Hours with no sessions yet show “—”.</p>' +
          '<div id="hourly-grid"><p class="text-xs" style="color:var(--text-muted);margin:0">Loading…</p></div>' +
        '</div>' +
      '</div>';
    document.body.appendChild(overlay);

    var ta = overlay.querySelector('#about-text');
    var initialAbout = '';        // the loaded value, so we can warn before discarding edits
    var confirming = false;       // a discard-confirm is open (avoid stacking a second one)
    if (window.getProfile) {
      window.getProfile().then(function (p) { ta.value = (p && p.about) || ''; initialAbout = ta.value; }).catch(function () {
        // Don't silently show a blank box that could be saved over the real value.
        if (window.showToast) showToast('Couldn’t load your About-me — check the backend before saving.', { danger: true });
      });
    }

    var listEl = overlay.querySelector('#patterns-list');
    function renderPatterns() {
      if (!window.getObservations) { listEl.innerHTML = ''; return; }
      window.getObservations().then(function (items) {
        if (!items || !items.length) {
          listEl.innerHTML = '<p class="text-xs" style="color:var(--text-muted);margin:0">Nothing learned yet — finish a few sessions.</p>';
          return;
        }
        listEl.innerHTML = items.map(function (o) {
          var faded = o.active ? '' : 'opacity:.55;';
          return '<div class="flex items-center gap-2" style="padding:6px 0;' + faded + '">' +
            statusBadge(o.status) +
            '<span class="text-sm" style="flex:1 1 auto;color:var(--text);line-height:1.35">' + escapeHtml(o.text) + '</span>' +
            '<button data-act="del" data-id="' + o.id + '" title="Remove this pattern" aria-label="Remove pattern" ' +
              'style="flex:none;border:none;background:none;cursor:pointer;color:var(--text-muted);font-size:18px;line-height:1;padding:0 4px">×</button>' +
          '</div>';
        }).join('');
      }).catch(function () {
        listEl.innerHTML = '<p class="text-xs" style="color:var(--text-muted);margin:0">Couldn’t load patterns.</p>';
      });
    }
    renderPatterns();

    var gridEl = overlay.querySelector('#hourly-grid');
    function renderHourly() {
      if (!window.getHourlyFocus) { gridEl.innerHTML = ''; return; }
      window.getHourlyFocus().then(function (hours) {
        if (!hours || !hours.length) { gridEl.innerHTML = ''; return; }
        gridEl.style.display = 'block';
        var byHour = {};
        hours.forEach(function (h) { byHour[h.hour] = h; });
        // One labeled block per part of day; that label is each hour's "tag".
        gridEl.innerHTML = DAY_SECTIONS.map(function (sec) {
          var cells = sec.hours.map(function (hr) {
            return byHour[hr] ? hourCellHtml(byHour[hr]) : '';
          }).join('');
          return '<div style="margin-top:10px">' +
              '<div class="section-label" style="margin:0 0 5px">' + sec.label +
                ' <span style="font-weight:400;text-transform:none;letter-spacing:0;color:var(--text-muted)">' + sec.range + '</span></div>' +
              '<div style="display:grid;grid-template-columns:repeat(6,1fr);gap:4px">' + cells + '</div>' +
            '</div>';
        }).join('');
      }).catch(function () {
        gridEl.innerHTML = '<p class="text-xs" style="color:var(--text-muted);margin:0">Couldn’t load hourly focus.</p>';
      });
    }
    renderHourly();

    function closeModal() { overlay.remove(); document.removeEventListener('keydown', onKey); }
    // Warn before losing typed-but-unsaved edits (Cancel / backdrop / Escape).
    function requestClose() {
      if (confirming) return;
      if (ta.value.trim() === initialAbout.trim() || !window.confirmDialog) { closeModal(); return; }
      confirming = true;
      window.confirmDialog('Discard your unsaved changes?', { danger: true, confirmText: 'Discard' })
        .then(function (ok) { confirming = false; if (ok) closeModal(); });
    }
    function onKey(e) { if (e.key === 'Escape') requestClose(); }

    overlay.addEventListener('click', function (e) {
      if (e.target === overlay) return requestClose();   // backdrop
      var act = e.target.closest('[data-act]');
      if (!act) return;
      if (act.dataset.act === 'del' && window.deleteObservation) {
        act.disabled = true;
        window.deleteObservation(act.dataset.id).then(renderPatterns).catch(function () { act.disabled = false; });
      } else if (act.dataset.act === 'save' && window.saveProfile) {
        act.disabled = true; act.textContent = 'Saving…';
        window.saveProfile(ta.value)
          .then(closeModal)
          .catch(function () {
            act.disabled = false; act.textContent = 'Save';   // keep the modal open so the text isn't lost
            if (window.showToast) showToast('Couldn’t save your About-me — is the backend running?', { danger: true });
          });
      } else if (act.dataset.act === 'cancel') {
        requestClose();
      }
    });
    document.addEventListener('keydown', onKey);
    ta.focus();
  }

  function init() {
    var btn = document.getElementById('settings-btn');
    if (!btn) return;
    var wrap = btn.parentElement;

    var interval = get('fb-detect-interval', '10000');
    var opts = [['5000', '5s'], ['10000', '10s'], ['15000', '15s'], ['30000', '30s']]
      .map(function (o) { return '<option value="' + o[0] + '"' + (o[0] === interval ? ' selected' : '') + '>' + o[1] + '</option>'; }).join('');
    var notifySupported = ('Notification' in window);
    var notifyOn = notifySupported && get('fb-notify', 'off') === 'on' && Notification.permission === 'granted';
    var notifyDenied = notifySupported && Notification.permission === 'denied';

    var panel = document.createElement('div');
    panel.id = 'settings-panel';
    panel.className = 'settings-panel';
    panel.setAttribute('role', 'dialog');
    panel.setAttribute('aria-label', 'Settings');
    panel.hidden = true;
    panel.innerHTML =
      '<p class="section-label" style="margin:0 0 8px">Appearance</p>' +
      row('Dark mode', 'Remembered on this device.', toggle('dark-toggle', false)) +

      '<p class="section-label" style="margin:16px 0 8px">Focus</p>' +
      row('Check every', 'How often the camera is analyzed.',
        '<select id="detect-interval" class="settings-select">' + opts + '</select>') +

      '<p class="section-label" style="margin:16px 0 8px">Nudges</p>' +
      row('Gentle nudges', 'A reminder when you drift for a while.', toggle('nudge-toggle', get('fb-nudges', 'on') !== 'off')) +
      row('Sounds', 'A soft chime on goal &amp; nudges.', toggle('sound-toggle', get('fb-sounds', 'off') === 'on')) +
      row('Desktop notifications', notifyDenied ? 'Blocked in your browser settings.' : 'Alerts even when the tab is hidden.',
        toggle('notify-toggle', notifyOn)) +

      '<p class="section-label" style="margin:16px 0 8px">Website</p>' +
      row('Website awareness',
        'Sends your current tab’s address to the AI to judge relevance. Needs the Focus Buddy extension. Off = camera only.',
        toggle('website-toggle', get('fb-website-tracking', 'off') === 'on')) +

      '<p class="section-label" style="margin:16px 0 8px">Developer</p>' +
      row('Show AI reasoning', 'Shows the AI’s reason for each focus call on the tracker.',
        toggle('reasoning-toggle', get('fb-show-reasoning', 'off') === 'on'));

    wrap.appendChild(panel);

    // Dark mode
    var dark = panel.querySelector('#dark-toggle');
    dark.checked = (window.getTheme && window.getTheme() === 'dark');
    dark.addEventListener('change', function () {
      if (window.setTheme) window.setTheme(dark.checked ? 'dark' : 'light');
    });

    // Focus check interval
    panel.querySelector('#detect-interval').addEventListener('change', function (e) {
      set('fb-detect-interval', e.target.value);
    });

    // Nudges
    panel.querySelector('#nudge-toggle').addEventListener('change', function (e) {
      set('fb-nudges', e.target.checked ? 'on' : 'off');
    });

    // Sounds (play a chime as confirmation when turning on)
    panel.querySelector('#sound-toggle').addEventListener('change', function (e) {
      set('fb-sounds', e.target.checked ? 'on' : 'off');
      if (e.target.checked && window.playChime) window.playChime();
    });

    // Website awareness (opt-in; the tracker reads this flag each sample)
    panel.querySelector('#website-toggle').addEventListener('change', function (e) {
      set('fb-website-tracking', e.target.checked ? 'on' : 'off');
    });

    // Developer: show AI reasoning on the tracker
    panel.querySelector('#reasoning-toggle').addEventListener('change', function (e) {
      set('fb-show-reasoning', e.target.checked ? 'on' : 'off');
    });

    // Desktop notifications (request permission on enable)
    var notify = panel.querySelector('#notify-toggle');
    if (!notifySupported || notifyDenied) {
      notify.disabled = true;
      notify.checked = false;
    }
    notify.addEventListener('change', function () {
      if (!notify.checked) { set('fb-notify', 'off'); return; }
      if (window.requestNotifyPermission) {
        window.requestNotifyPermission().then(function (perm) {
          if (perm === 'granted') { set('fb-notify', 'on'); }
          else { notify.checked = false; set('fb-notify', 'off'); }
        });
      }
    });

    function open() { panel.hidden = false; btn.setAttribute('aria-expanded', 'true'); }
    function close() { panel.hidden = true; btn.setAttribute('aria-expanded', 'false'); }

    btn.addEventListener('click', function (e) { e.stopPropagation(); panel.hidden ? open() : close(); });
    document.addEventListener('click', function (e) { if (!panel.hidden && !wrap.contains(e.target)) close(); });
    document.addEventListener('keydown', function (e) { if (e.key === 'Escape' && !panel.hidden) { close(); btn.focus(); } });
  }

  // Expose the editor + wire the "About me" nav button (present on every page).
  window.openAboutModal = openAboutModal;
  function start() {
    init();
    var link = document.getElementById('about-nav');
    if (link) link.addEventListener('click', function (e) { e.preventDefault(); openAboutModal(); });
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
