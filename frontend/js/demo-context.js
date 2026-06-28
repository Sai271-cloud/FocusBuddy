(function () {
  var SEEDED = ['early-morning', 'doomscroller', 'overplanner', 'night-owl', 'self-improver'];
  var DEMO_NOW = new Date(2026, 5, 28, 9, 0, 0);
  var STORAGE_ANON = 'fb-demo-anon-id';

  function escapeHtml(value) {
    return String(value == null ? '' : value)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function localDayKey(date) {
    var d = date || now();
    return d.getFullYear() + '-' + pad(d.getMonth() + 1) + '-' + pad(d.getDate());
  }

  function isoWithLocalOffset(date) {
    var offsetMin = -date.getTimezoneOffset();
    var sign = offsetMin >= 0 ? '+' : '-';
    var abs = Math.abs(offsetMin);
    return date.getFullYear() + '-' + pad(date.getMonth() + 1) + '-' + pad(date.getDate()) +
      'T' + pad(date.getHours()) + ':' + pad(date.getMinutes()) + ':' + pad(date.getSeconds()) +
      sign + pad(Math.floor(abs / 60)) + ':' + pad(abs % 60);
  }

  function parsePathSlug() {
    var m = window.location.pathname.match(/\/demo\/([^\/?#]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  function parseQuerySlug() {
    try { return new URLSearchParams(window.location.search).get('demo') || ''; }
    catch { return ''; }
  }

  function validSlug(slug) {
    return slug === 'new' || SEEDED.indexOf(slug) !== -1;
  }

  function randomId() {
    if (window.crypto && window.crypto.getRandomValues) {
      var arr = new Uint32Array(2);
      window.crypto.getRandomValues(arr);
      return Array.prototype.map.call(arr, function (n) { return n.toString(36); }).join('');
    }
    return String(Date.now()) + String(Math.floor(Math.random() * 100000));
  }

  var explicit = parsePathSlug() || parseQuerySlug();
  var slug = validSlug(explicit) ? explicit : '';
  var active = !!slug;
  var anonymousId = '';
  if (slug === 'new') {
    try {
      anonymousId = localStorage.getItem(STORAGE_ANON) || '';
      if (!anonymousId) {
        anonymousId = randomId();
        localStorage.setItem(STORAGE_ANON, anonymousId);
      }
    } catch {
      anonymousId = randomId();
    }
  }

  function now() {
    return active ? new Date(DEMO_NOW.getTime()) : new Date();
  }

  function headers() {
    if (!active) return {};
    if (slug === 'new') return { 'X-Demo-Anonymous-Id': anonymousId };
    return { 'X-Demo-Slug': slug };
  }

  function href(page, params) {
    var out = page || 'index.html';
    if (!active) return out;
    var url = new URL(out, window.location.origin + '/');
    url.searchParams.set('demo', slug);
    Object.keys(params || {}).forEach(function (key) {
      if (params[key] != null && params[key] !== '') url.searchParams.set(key, params[key]);
    });
    return url.pathname + url.search;
  }

  function sessionStartIso() {
    return active ? isoWithLocalOffset(DEMO_NOW) : new Date().toISOString();
  }

  function sessionEndIso(startIso, elapsedSeconds) {
    if (!active) return new Date().toISOString();
    var start = new Date(startIso || sessionStartIso());
    return new Date(start.getTime() + Math.max(0, Number(elapsedSeconds) || 0) * 1000).toISOString();
  }

  function decorateLinks() {
    if (!active) return;
    document.querySelectorAll('a[href]').forEach(function (a) {
      var raw = a.getAttribute('href') || '';
      if (!/^(index|plan|analytics|tracker)\.html(\?|$)/.test(raw)) return;
      var parts = raw.split('?');
      var params = {};
      if (parts[1]) {
        try {
          new URLSearchParams(parts[1]).forEach(function (value, key) { params[key] = value; });
        } catch {}
      }
      a.setAttribute('href', href(parts[0], params));
    });
  }

  function dayLabel(key) {
    var parts = String(key || '').split('-').map(Number);
    var d = new Date(parts[0], parts[1] - 1, parts[2]);
    return d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
  }

  function sessionSeconds(s) {
    return (s.seconds_focused || 0) + (s.seconds_distracted || 0) +
      (s.seconds_uncertain || 0) + (s.seconds_away || 0);
  }

  function sumStates(sessions) {
    return (sessions || []).reduce(function (sum, s) {
      sum.focused += s.seconds_focused || 0;
      sum.distracted += s.seconds_distracted || 0;
      sum.uncertain += s.seconds_uncertain || 0;
      sum.away += s.seconds_away || 0;
      return sum;
    }, { focused: 0, distracted: 0, uncertain: 0, away: 0 });
  }

  function recentAverage(sessions, todayKey) {
    var totals = {};
    (sessions || []).forEach(function (s) {
      var k = localDayKey(new Date(s.started_at));
      if (k === todayKey) return;
      if (!totals[k]) totals[k] = { focused: 0, total: 0 };
      totals[k].focused += s.seconds_focused || 0;
      totals[k].total += sessionSeconds(s);
    });
    var rows = Object.keys(totals).map(function (k) { return totals[k]; }).filter(function (x) { return x.total > 0; });
    if (!rows.length) return null;
    var avg = rows.reduce(function (sum, x) { return sum + (100 * x.focused / x.total); }, 0) / rows.length;
    return Math.round(avg);
  }

  function parseRecap(raw) {
    if (!raw) return null;
    try {
      var recap = typeof raw === 'string' ? JSON.parse(raw) : raw;
      return recap && (recap.summary || recap.win || recap.next_action) ? recap : null;
    } catch {
      return null;
    }
  }

  function parsePlanReality(raw) {
    if (!raw) return null;
    try {
      var report = typeof raw === 'string' ? JSON.parse(raw) : raw;
      return report && report.has_plan ? report : null;
    } catch {
      return null;
    }
  }

  function formatHM(seconds) {
    seconds = Math.max(0, Math.round(Number(seconds) || 0));
    var h = Math.floor(seconds / 3600);
    var m = Math.round((seconds % 3600) / 60);
    return h > 0 ? h + 'h ' + m + 'm' : m + 'm';
  }

  function focusPct(sum) {
    var total = (sum.focused || 0) + (sum.distracted || 0) + (sum.uncertain || 0) + (sum.away || 0);
    return total > 0 ? Math.round(100 * (sum.focused || 0) / total) : 0;
  }

  function sessionSummary(sessions) {
    var sum = sumStates(sessions);
    return sessions.length + ' session' + (sessions.length === 1 ? '' : 's') +
      ' - ' + formatHM(sum.focused) + ' focused - ' + focusPct(sum) + '% focused';
  }

  function isoForDayAt(dayKey, hour, minute) {
    var parts = String(dayKey || '').split('-').map(Number);
    return isoWithLocalOffset(new Date(parts[0], parts[1] - 1, parts[2], hour, minute || 0, 0));
  }

  function fmtMinuteOfDay(min) {
    if (min == null || min === '') return 'Unscheduled';
    min = Number(min);
    if (!Number.isFinite(min)) return 'Unscheduled';
    min = ((min % 1440) + 1440) % 1440;
    var h = Math.floor(min / 60);
    var m = min % 60;
    var ap = h < 12 ? 'am' : 'pm';
    return (h % 12 || 12) + ':' + pad(m) + ap;
  }

  function statusLabel(status) {
    return {
      not_started: 'Not started',
      on_track: 'Close to plan',
      started_late: 'Started late',
      started_early: 'Started early',
      ran_short: 'Ran short',
      ran_long: 'Ran long',
      unscheduled_work: 'Unplanned work',
    }[status] || 'Logged';
  }

  function renderPlanRealityHtml(report) {
    if (!report || !report.has_plan) return '';
    var rows = (report.rows || []).map(function (row) {
      var planned = row.status === 'unscheduled_work'
        ? 'Unplanned'
        : fmtMinuteOfDay(row.planned_start_min) + ' / ' + (row.planned_estimate_min || 0) + 'm';
      var actual = row.actual_total_min > 0
        ? fmtMinuteOfDay(row.actual_start_min) + ' / ' + row.actual_total_min + 'm'
        : 'No session';
      var statusClass = String(row.status || 'logged').replace(/[^a-z0-9_-]/gi, '-');
      return '<div class="plan-reality-row">' +
        '<span data-label="Task">' + escapeHtml(row.name || 'Untitled') + '</span>' +
        '<span data-label="Planned">' + escapeHtml(planned) + '</span>' +
        '<span data-label="Actual">' + escapeHtml(actual) + '</span>' +
        '<span data-label="Status"><span class="plan-reality-status ' + statusClass + '">' + escapeHtml(statusLabel(row.status)) + '</span></span>' +
      '</div>';
    }).join('');
    return '<div class="plan-reality-card" style="margin:10px 0 10px">' +
      '<div class="flex items-center justify-between gap-3">' +
        '<p class="section-label" style="margin:0">Plan vs reality</p>' +
        '<p class="text-xs" style="color:var(--text-faint);margin:0">' + (report.planned_total_min || 0) + 'm planned - ' + (report.actual_total_min || 0) + 'm tracked</p>' +
      '</div>' +
      '<p class="text-xs" style="color:var(--text-muted);margin:6px 0 10px">' + escapeHtml(report.summary || '') + '</p>' +
      '<div class="plan-reality-head"><span>Task</span><span>Planned</span><span>Actual</span><span>Status</span></div>' +
      rows +
    '</div>';
  }

  function historicalDays(sessions) {
    var todayKey = localDayKey(now());
    var byKey = {};
    (sessions || []).forEach(function (s) {
      var key = localDayKey(new Date(s.started_at));
      if (key >= todayKey || sessionSeconds(s) <= 0) return;
      if (!byKey[key]) byKey[key] = [];
      byKey[key].push(s);
    });
    return Object.keys(byKey).sort().map(function (key) {
      return { period_key: key, sessions: byKey[key] };
    });
  }

  function workPeriodsByDay(periods) {
    var out = {};
    (periods || []).forEach(function (p) {
      if (p.kind === 'day') out[p.period_key] = p;
    });
    return out;
  }

  function renderRecapHtml(recap) {
    if (!recap) return '';
    var items = [];
    if (recap.win) items.push('<p><strong>Win:</strong> ' + escapeHtml(recap.win) + '</p>');
    if (recap.next_action) items.push('<p><strong>Next:</strong> ' + escapeHtml(recap.next_action) + '</p>');
    return '<div class="demo-recap-result">' +
      '<p>' + escapeHtml(recap.summary || 'Daily unwind generated.') + '</p>' +
      items.join('') +
      '</div>';
  }

  function renderHistoryStatusHtml(recap, planReality) {
    var planHtml = renderPlanRealityHtml(planReality);
    var recapHtml = recap
      ? renderRecapHtml(recap)
      : '<p style="margin:0">Not generated yet. Use this day\'s seeded sessions to generate the unwind live.</p>';
    return planHtml + recapHtml;
  }

  async function generateTodayDailyUnwind(bodyEl) {
    var status = bodyEl.querySelector('#judge-demo-status');
    status.textContent = 'Checking June 28 sessions...';
    try {
      var sessions = await window.getSessions();
      var todayKey = localDayKey(now());
      var today = sessions.filter(function (s) { return localDayKey(new Date(s.started_at)) === todayKey; });
      if (!today.length) {
        status.textContent = 'June 28 has no sessions yet. Start and finish a session first, then generate the daily unwind.';
        return;
      }
      var sum = sumStates(today);
      status.textContent = 'Generating daily unwind...';
      var recap = await window.getDailyUnwind({
        session_ids: today.map(function (s) { return s.id; }),
        recent_avg_focus_pct: recentAverage(sessions, todayKey),
        period_key: todayKey,
      });
      await window.createWorkPeriod({
        kind: 'day',
        period_key: todayKey,
        ended_at: isoWithLocalOffset(now()),
        seconds_focused: sum.focused,
        seconds_distracted: sum.distracted,
        seconds_uncertain: sum.uncertain,
        seconds_away: sum.away,
        ai_recap: JSON.stringify(recap),
      });
      status.innerHTML = renderRecapHtml(recap);
    } catch (err) {
      status.textContent = generationErrorText(err, false);
    }
  }

  function generationErrorText(err, historical) {
    var msg = String(err && err.message || '');
    if (msg.indexOf('502') !== -1 || msg.indexOf('503') !== -1 || msg.indexOf('429') !== -1 || /quota|credit|temporarily|model/i.test(msg)) {
      return 'AI credits are unavailable or the model is unreachable right now, so live daily unwind generation could not run. Check the backend or Gemini quota, then try again.';
    }
    return historical
      ? 'Could not generate this saved day yet. Check that the backend is running, then try again.'
      : 'Could not generate the daily unwind yet. Finish a June 28 session and check that the backend is running.';
  }

  function renderHistoryRows(days, periodsByKey) {
    if (!days.length) {
      return '<p class="text-sm" style="color:var(--text-muted);line-height:1.55;margin:0">No seeded history loaded yet.</p>';
    }
    return '<div class="judge-unwind-list">' +
      days.map(function (day) {
        var key = day.period_key;
        var period = periodsByKey[key] || {};
        var recap = parseRecap(period.ai_recap);
        var planReality = parsePlanReality(period.plan_reality_json);
        return '<article class="judge-unwind-row" data-history-row="' + escapeHtml(key) + '">' +
          '<div class="flex items-start justify-between gap-3 flex-wrap">' +
            '<div>' +
              '<p class="section-label" style="margin:0 0 4px">' + escapeHtml(dayLabel(key)) + '</p>' +
              '<p class="text-sm" style="color:var(--text);line-height:1.45;margin:0">' + escapeHtml(sessionSummary(day.sessions)) + '</p>' +
            '</div>' +
            '<button class="' + (recap ? 'btn-ghost' : 'btn-primary') + '" data-act="generate-history-daily" data-period-key="' + escapeHtml(key) + '">' + (recap ? 'Regenerate' : 'Generate daily unwind') + '</button>' +
          '</div>' +
          '<div data-history-status="' + escapeHtml(key) + '" class="text-sm" style="color:var(--text-muted);margin-top:10px;line-height:1.5">' +
            renderHistoryStatusHtml(recap, planReality) +
          '</div>' +
        '</article>';
      }).join('') +
    '</div>';
  }

  async function renderSeededDemoBody(bodyEl) {
    var sessions = await window.getSessions();
    var periods = await window.getWorkPeriods();
    var days = historicalDays(sessions);
    var periodsByKey = workPeriodsByDay(periods);
    bodyEl.innerHTML =
      '<p class="text-sm" style="color:var(--text-muted);line-height:1.55;margin:0 0 12px">This seeded persona shows the week before June 28. Generate a historical daily unwind live from the saved sessions, or keep June 28 blank for a judge-run session.</p>' +
      renderHistoryRows(days, periodsByKey) +
      '<div class="judge-demo-actions">' +
        '<button class="btn-primary" data-act="generate-daily">Generate daily unwind for June 28</button>' +
        '<button class="btn-ghost" data-act="reset-demo">Reset demo data</button>' +
      '</div>' +
      '<div id="judge-demo-status" class="text-sm" style="color:var(--text-muted);margin-top:12px"></div>';
  }

  async function generateHistoricalDailyUnwind(bodyEl, periodKey) {
    var row = bodyEl.querySelector('[data-history-row="' + periodKey + '"]');
    var status = bodyEl.querySelector('[data-history-status="' + periodKey + '"]');
    var button = row ? row.querySelector('[data-act="generate-history-daily"]') : null;
    if (button) {
      button.disabled = true;
      button.textContent = 'Generating...';
    }
    if (status) status.textContent = 'Generating live daily unwind...';
    try {
      var sessions = await window.getSessions();
      var daySessions = sessions.filter(function (s) { return localDayKey(new Date(s.started_at)) === periodKey; });
      if (!daySessions.length) {
        if (status) status.textContent = 'No sessions were found for this seeded day.';
        if (button) {
          button.disabled = false;
          button.textContent = 'Generate daily unwind';
        }
        return;
      }
      var periods = await window.getWorkPeriods();
      var existing = (periods || []).find(function (p) { return p.kind === 'day' && p.period_key === periodKey; });
      var planReality = parsePlanReality(existing && existing.plan_reality_json);
      var sum = sumStates(daySessions);
      if (status) {
        status.innerHTML = renderPlanRealityHtml(planReality) + '<p style="margin:0">Generating live daily unwind...</p>';
      }
      var recap = await window.getDailyUnwind({
        session_ids: daySessions.map(function (s) { return s.id; }),
        recent_avg_focus_pct: recentAverage(sessions, periodKey),
        period_key: periodKey,
        plan_reality_summary: planReality && planReality.has_plan ? planReality.summary : null,
      });
      await window.createWorkPeriod({
        kind: 'day',
        period_key: periodKey,
        ended_at: existing && existing.ended_at ? existing.ended_at : isoForDayAt(periodKey, 21, 0),
        seconds_focused: sum.focused,
        seconds_distracted: sum.distracted,
        seconds_uncertain: sum.uncertain,
        seconds_away: sum.away,
        ai_recap: JSON.stringify(recap),
        plan_reality_json: existing && existing.plan_reality_json ? existing.plan_reality_json : null,
      });
      await renderSeededDemoBody(bodyEl);
    } catch (err) {
      if (status) status.textContent = generationErrorText(err, true);
      if (button) {
        button.disabled = false;
        button.textContent = 'Try again';
      }
    }
  }

  async function resetOrClear() {
    var isNew = slug === 'new';
    var message = isNew
      ? 'Clear your blank demo data in this browser?'
      : 'Reset demo data for ' + slug + '? This restores the seeded persona.';
    var ok = window.confirmDialog ? await window.confirmDialog(message, { danger: true, confirmText: isNew ? 'Clear' : 'Reset' }) : window.confirm(message);
    if (!ok) return;
    if (isNew) await window.clearNewDemoWorkspace();
    else await window.resetDemoWorkspace(slug);
    window.location.reload();
  }

  async function openJudgeDemo() {
    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML =
      '<div class="modal judge-demo-modal" role="dialog" aria-modal="true" aria-labelledby="judge-demo-title">' +
        '<div class="flex items-start justify-between gap-3">' +
          '<div><p class="section-label" style="margin:0 0 4px">Judge Demo</p>' +
          '<h2 id="judge-demo-title" class="serif" style="font-size:1.18rem;font-weight:600;margin:0">Loading demo...</h2></div>' +
          '<button class="btn-ghost" data-act="close" aria-label="Close" style="padding:2px 9px;border:none;font-size:1rem;color:var(--text-muted)">x</button>' +
        '</div>' +
        '<div id="judge-demo-body" style="margin-top:14px"><p class="text-sm" style="color:var(--text-muted)">Loading...</p></div>' +
      '</div>';
    document.body.appendChild(overlay);
    var body = overlay.querySelector('#judge-demo-body');
    var title = overlay.querySelector('#judge-demo-title');
    function close() { overlay.remove(); document.removeEventListener('keydown', onKey); }
    function onKey(e) { if (e.key === 'Escape') close(); }
    overlay.addEventListener('click', function (e) {
      if (e.target === overlay || e.target.closest('[data-act="close"]')) close();
      var hist = e.target.closest('[data-act="generate-history-daily"]');
      if (hist) generateHistoricalDailyUnwind(body, hist.getAttribute('data-period-key'));
      var gen = e.target.closest('[data-act="generate-daily"]');
      if (gen) generateTodayDailyUnwind(body);
      var reset = e.target.closest('[data-act="reset-demo"]');
      if (reset) resetOrClear().catch(function () {
        var status = body.querySelector('#judge-demo-status');
        if (status) status.textContent = 'Could not reset the demo data right now.';
      });
    });
    document.addEventListener('keydown', onKey);

    try {
      var meta = await window.getDemoWorkspace(slug);
      title.textContent = meta.display_name || (slug === 'new' ? 'Blank Demo' : slug);
      if (slug === 'new') {
        body.innerHTML =
          '<p class="text-sm" style="color:var(--text-muted);line-height:1.55">This is a blank per-browser sandbox. It behaves like the normal app and keeps this browser in its own anonymous demo workspace.</p>' +
          '<div class="flex gap-2" style="margin-top:14px"><button class="btn-ghost" data-act="reset-demo">Clear my demo data</button></div>' +
          '<div id="judge-demo-status" class="text-sm" style="color:var(--text-muted);margin-top:12px"></div>';
        return;
      }
      await renderSeededDemoBody(body);
    } catch {
      body.innerHTML = '<p class="text-sm" style="color:var(--terracotta)">Could not load the Judge Demo panel. Check that the backend is running.</p>';
    }
  }

  function installJudgeNav() {
    if (!active) return;
    var nav = document.querySelector('.page-nav');
    if (!nav || document.getElementById('judge-demo-nav')) return;
    var settings = nav.querySelector('.settings-menu');
    var link = document.createElement('a');
    link.href = '#';
    link.id = 'judge-demo-nav';
    link.textContent = 'Judge Demo';
    link.addEventListener('click', function (e) {
      e.preventDefault();
      openJudgeDemo();
    });
    if (settings) nav.insertBefore(link, settings);
    else nav.appendChild(link);
  }

  window.FocusBuddyDemo = {
    active: active,
    slug: slug,
    anonymousId: anonymousId,
    seededSlugs: SEEDED.slice(),
    now: now,
    headers: headers,
    href: href,
    localDayKey: localDayKey,
    isoWithLocalOffset: isoWithLocalOffset,
    sessionStartIso: sessionStartIso,
    sessionEndIso: sessionEndIso,
  };

  function start() {
    decorateLinks();
    installJudgeNav();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', start);
  else start();
})();
