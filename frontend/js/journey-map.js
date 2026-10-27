(function () {
  var PATH_SAMPLES = 120;
  var SVG_HEIGHT = 90;
  var X_PAD = 26;
  var NO_PLAN_REF_MIN = 60;

  function pad(n) { return String(n).padStart(2, '0'); }


  function hashString(str) {
    var h = 1779033703 ^ str.length;
    for (var i = 0; i < str.length; i += 1) {
      h = Math.imul(h ^ str.charCodeAt(i), 3432918353);
      h = (h << 13) | (h >>> 19);
    }
    return h >>> 0;
  }

  function mulberry32(seed) {
    return function () {
      seed |= 0; seed = (seed + 0x6D2B79F5) | 0;
      var t = Math.imul(seed ^ (seed >>> 15), 1 | seed);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  function curveForMonth(monthKey) {
    var rand = mulberry32(hashString(monthKey));
    return {
      a1: 7 + rand() * 7,
      f1: 0.008 + rand() * 0.006,
      p1: rand() * Math.PI * 2,
      a2: 3 + rand() * 5,
      f2: 0.02 + rand() * 0.01,
      p2: rand() * Math.PI * 2,
    };
  }

  function curveY(frac, curve) {
    var x = frac * 1000;
    return SVG_HEIGHT / 2 +
      curve.a1 * Math.sin(x * curve.f1 + curve.p1) +
      curve.a2 * Math.sin(x * curve.f2 + curve.p2);
  }


  function fmtDur(minutes) {
    var m = Math.max(0, Math.round(minutes));
    if (m < 60) return m + 'm';
    return Math.floor(m / 60) + 'h ' + pad(m % 60) + 'm';
  }

  function fmtHours(seconds) {
    var h = seconds / 3600;
    var out = h.toFixed(1);
    return out.endsWith('.0') ? out.slice(0, -2) : out;
  }

  function monthName(date) {
    return date.toLocaleDateString(undefined, { month: 'long' });
  }

  function campLabel(dayKey, focusedMin) {
    var d = window.PlanningInsights.dateFromKey(dayKey);
    var when = d.toLocaleDateString(undefined, { weekday: 'short', month: 'short', day: 'numeric' });
    return when + ' · ' + fmtDur(focusedMin) + ' focused';
  }


  var LANDMARK_LABELS = {
    'first-camp': 'The first camp',
    'first-daily-unwind': 'First daily unwind',
    'first-weekly-unwind': 'First weekly unwind',
    'first-monthly-unwind': 'First monthly unwind',
    'first-plan': 'First plan made',
    'unbroken-25': '25 minutes unbroken',
    'deep-day': 'A 2-hour day',
    'camps-10': 'The 10th camp',
    'camps-25': 'The 25th camp',
    'camps-50': 'The 50th camp',
    'camps-100': 'The 100th camp',
    'plan-match': 'Plan met reality',
    'streak-7': '7 days on the trail',
  };
  var CAMP_MILESTONES = { 'camps-10': 10, 'camps-25': 25, 'camps-50': 50, 'camps-100': 100 };

  function parseJsonQuiet(text) {
    if (!text) return null;
    try { return JSON.parse(text); } catch (e) { return null; }
  }

  function hasUnbroken25(timeline) {
    var run = 0, prevMinute = null;
    for (var i = 0; i < (timeline || []).length; i += 1) {
      var e = timeline[i];
      if (e && e.state === 'focused' && (prevMinute === null || e.minute === prevMinute + 1)) {
        run = (prevMinute === null) ? 1 : run + 1;
      } else {
        run = (e && e.state === 'focused') ? 1 : 0;
      }
      prevMinute = (e && e.state === 'focused') ? e.minute : null;
      if (run >= 25) return true;
    }
    return false;
  }

  function buildLandmarks(opts) {
    var PI = window.PlanningInsights;
    var sessions = (opts && opts.sessions) || [];
    var workPeriods = (opts && opts.workPeriods) || [];
    var now = (opts && opts.now) || PI.currentDate();
    var earned = [];
    function add(code, dayKey) { if (dayKey) earned.push({ code: code, day_key: dayKey }); }

    var byKey = focusedSecondsByDay(sessions);
    var campDays = Object.keys(byKey).filter(function (k) { return byKey[k] >= 60; }).sort();

    if (campDays.length) add('first-camp', campDays[0]);
    Object.keys(CAMP_MILESTONES).forEach(function (code) {
      var n = CAMP_MILESTONES[code];
      if (campDays.length >= n) add(code, campDays[n - 1]);
    });

    var run = 1;
    for (var i = 1; i < campDays.length; i += 1) {
      var prev = PI.dateFromKey(campDays[i - 1]);
      var next = PI.localDayKey(new Date(prev.getFullYear(), prev.getMonth(), prev.getDate() + 1));
      run = (campDays[i] === next) ? run + 1 : 1;
      if (run >= 7) { add('streak-7', campDays[i]); break; }
    }

    for (var d = 0; d < campDays.length; d += 1) {
      if (byKey[campDays[d]] >= 7200) { add('deep-day', campDays[d]); break; }
    }

    var ordered = sessions.slice().sort(function (a, b) {
      return new Date(a.started_at) - new Date(b.started_at);
    });
    for (var s = 0; s < ordered.length; s += 1) {
      if (hasUnbroken25(parseJsonQuiet(ordered[s].timeline_json))) {
        add('unbroken-25', PI.localDayKey(new Date(ordered[s].started_at)));
        break;
      }
    }

    ['day', 'week', 'month'].forEach(function (kind) {
      var rows = workPeriods.filter(function (p) {
        return p.kind === kind && ((p.ai_recap || '') !== '' || (p.reflection || '') !== '');
      }).sort(function (a, b) { return new Date(a.ended_at) - new Date(b.ended_at); });
      if (!rows.length) return;
      var code = kind === 'day' ? 'first-daily-unwind'
        : kind === 'week' ? 'first-weekly-unwind' : 'first-monthly-unwind';
      add(code, kind === 'day' ? rows[0].period_key : PI.localDayKey(new Date(rows[0].ended_at)));
    });

    var planEntries = opts && opts.todayPlan ? PI.parsePlanEntries(opts.todayPlan) : [];
    var realityDays = workPeriods.filter(function (p) {
      var r = parseJsonQuiet(p.plan_reality_json);
      return p.kind === 'day' && r && r.has_plan;
    }).sort(function (a, b) { return a.period_key < b.period_key ? -1 : 1; });
    if (planEntries.length) add('first-plan', PI.localDayKey(now));
    else if (realityDays.length) add('first-plan', realityDays[0].period_key);

    for (var r = 0; r < realityDays.length; r += 1) {
      var rep = parseJsonQuiet(realityDays[r].plan_reality_json);
      var planned = (rep && rep.planned_total_min) || 0;
      if (planned > 0 && Math.abs((rep.actual_total_min || 0) - planned) <= 0.2 * planned) {
        add('plan-match', realityDays[r].period_key);
        break;
      }
    }

    return earned;
  }

  function cairnsForCamps(landmarks, camps, monthKey) {
    var byCamp = {};
    (landmarks || []).forEach(function (lm) {
      var dayKey = lm.day_key || '';
      if (dayKey.slice(0, 7) !== monthKey || !LANDMARK_LABELS[lm.code]) return;
      var anchor = null;
      for (var i = 0; i < camps.length; i += 1) {
        if (camps[i].key <= dayKey) anchor = camps[i];
      }
      if (!anchor) return;
      if (!byCamp[anchor.key]) byCamp[anchor.key] = { pos: anchor.pos, names: [] };
      byCamp[anchor.key].names.push(LANDMARK_LABELS[lm.code]);
    });
    return Object.keys(byCamp).sort().map(function (key) {
      var c = byCamp[key];
      var d = window.PlanningInsights.dateFromKey(key);
      var when = d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
      return { pos: c.pos, label: 'Cairn · ' + c.names.join(' · ') + ' — ' + when };
    });
  }


  function focusedSecondsByDay(sessions) {
    var byKey = {};
    (sessions || []).forEach(function (s) {
      var key = window.PlanningInsights.localDayKey(new Date(s.started_at));
      byKey[key] = (byKey[key] || 0) + (s.seconds_focused || 0);
    });
    return byKey;
  }

  function streakDays(byKey, todayKey) {
    var PI = window.PlanningInsights;
    var count = (byKey[todayKey] || 0) >= 60 ? 1 : 0;
    var d = PI.dateFromKey(todayKey);
    for (var i = 0; i < 90; i += 1) {
      d = new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1);
      if ((byKey[PI.localDayKey(d)] || 0) < 60) break;
      count += 1;
    }
    return count;
  }

  function plannedMinutes(todayPlan) {
    if (!todayPlan) return 0;
    return window.PlanningInsights.parsePlanEntries(todayPlan)
      .reduce(function (sum, e) { return sum + (e.estimate_min || 0); }, 0);
  }

  function splitAroundUnwind(sessions, todayKey, unwindAt) {
    var PI = window.PlanningInsights;
    var pre = 0, post = 0;
    (sessions || []).forEach(function (s) {
      if (PI.localDayKey(new Date(s.started_at)) !== todayKey) return;
      var focused = (s.seconds_focused || 0) / 60;
      if (new Date(s.ended_at) <= unwindAt) pre += focused;
      else post += focused;
    });
    return { preMin: pre, postMin: post };
  }

  function buildTrailModel(opts) {
    var PI = window.PlanningInsights;
    var now = opts.now || PI.currentDate();
    var sessions = opts.sessions || [];
    var year = now.getFullYear();
    var month = now.getMonth();
    var daysInMonth = opts.daysInMonth || new Date(year, month + 1, 0).getDate();
    var todayDay = now.getDate();
    var monthKey = year + '-' + pad(month + 1);
    var todayKey = PI.localDayKey(now);
    var segLen = 1 / daysInMonth;
    var completed = !!opts.completed;

    var byKey = focusedSecondsByDay(sessions);

    var camps = [];
    var lastPastDay = completed ? daysInMonth + 1 : todayDay;
    for (var day = 1; day < lastPastDay; day += 1) {
      var key = monthKey + '-' + pad(day);
      if ((byKey[key] || 0) >= 60) {
        camps.push({
          key: key,
          focusedMin: Math.round((byKey[key] || 0) / 60),
          pos: (camps.length + 1) * segLen,
          label: campLabel(key, (byKey[key] || 0) / 60),
        });
      }
    }

    var segStart = camps.length * segLen;
    var todayFocusedMin = completed ? 0 : (byKey[todayKey] || 0) / 60;
    var planMin = plannedMinutes(opts.todayPlan);
    var refMin = planMin > 0 ? planMin : NO_PLAN_REF_MIN;
    var wp = opts.todayWorkPeriod;
    var unwound = !!(wp && ((wp.ai_recap && wp.ai_recap !== '') || (wp.reflection && wp.reflection !== '')));

    var walker = null;
    var targetRing = (!completed && planMin > 0) ? { pos: Math.min(segStart + segLen, 1), reached: false } : null;

    if (completed) {
    } else if (unwound && todayFocusedMin >= 1) {
      var split = splitAroundUnwind(sessions, todayKey, new Date(wp.ended_at));
      var campPos = Math.min(segStart + segLen * Math.min(split.preMin / refMin, 1), 1);
      camps.push({
        key: todayKey,
        focusedMin: Math.round(todayFocusedMin),
        pos: campPos,
        label: campLabel(todayKey, todayFocusedMin),
        planted: true,
      });
      targetRing = null;
      if (split.postMin >= 1) {
        walker = {
          pos: Math.min(campPos + segLen * Math.min(split.postMin / NO_PLAN_REF_MIN, 0.5), 1),
          state: 'overtime',
          label: '+' + fmtDur(split.postMin) + ' after your unwind — bonus ground',
        };
      } else {
        walker = { pos: campPos, state: 'camped', label: 'Camped for today' };
      }
    } else if (todayFocusedMin >= 1) {
      if (planMin > 0 && todayFocusedMin >= planMin) {
        var overtimeMin = todayFocusedMin - planMin;
        targetRing.reached = true;
        walker = {
          pos: Math.min(segStart + segLen * (1 + Math.min(overtimeMin / planMin, 0.5)), 1),
          state: 'overtime',
          label: '+' + fmtDur(overtimeMin) + ' past the plan — bonus ground',
        };
      } else {
        walker = {
          pos: Math.min(segStart + segLen * Math.min(todayFocusedMin / refMin, 1), 1),
          state: 'walking',
          label: planMin > 0
            ? fmtDur(todayFocusedMin) + ' of ' + fmtDur(planMin) + ' planned'
            : fmtDur(todayFocusedMin) + ' focused today',
        };
      }
    } else if (camps.length) {
      walker = { pos: camps[camps.length - 1].pos, state: 'resting', label: 'Resting at camp' };
    }

    var cairns = cairnsForCamps(opts.landmarks, camps, monthKey);

    var empty = !camps.length && todayFocusedMin < 1;

    var league = opts.league || null;
    var badge = null;
    if (league && (league.points_min || 0) >= 1 && league.rank_name) {
      badge = {
        rankName: String(league.rank_name),
        level: league.level || 1,
        levelProgress: Math.min(1, Math.max(0, league.level_progress || 0)),
        imgSrc: 'img/badges/' + String(league.rank_name).toLowerCase() + '.png',
        pulse: !completed && !!opts.levelPulse,
      };
    }

    var monthSeconds = 0;
    var lastCountDay = completed ? daysInMonth : todayDay;
    for (var dd = 1; dd <= lastCountDay; dd += 1) {
      monthSeconds += byKey[monthKey + '-' + pad(dd)] || 0;
    }
    var caption = null;
    if (!empty) {
      var streak = completed ? 0 : streakDays(byKey, todayKey);
      caption = ((!completed && badge) ? badge.rankName + ' ' + badge.level + ' · ' : '') +
        monthName(now) + ' · ' + camps.length + ' camp' + (camps.length === 1 ? '' : 's') +
        ' · ' + fmtHours(monthSeconds) + ' focused hrs' +
        (streak >= 2 ? ' · ' + streak + '-day streak' : '');
    }

    var monthNote = null;
    var noteMonthKey = null;
    if (!completed && todayDay <= 3 && !opts.noteDismissed) {
      var lastMonthEnd = new Date(year, month, 0);
      var lmKey = lastMonthEnd.getFullYear() + '-' + pad(lastMonthEnd.getMonth() + 1);
      var lmCamps = 0, lmSeconds = 0;
      for (var ld = 1; ld <= lastMonthEnd.getDate(); ld += 1) {
        var lsec = byKey[lmKey + '-' + pad(ld)] || 0;
        if (lsec >= 60) lmCamps += 1;
        lmSeconds += lsec;
      }
      if (lmCamps >= 1) {
        monthNote = monthName(lastMonthEnd) + "'s region is complete — " + lmCamps +
          ' camp' + (lmCamps === 1 ? '' : 's') + ', ' + fmtHours(lmSeconds) +
          ' focused hours. A new region begins.';
        noteMonthKey = lmKey;
      }
    }

    return {
      monthKey: monthKey,
      curve: curveForMonth(monthKey),
      camps: camps,
      cairns: cairns,
      walker: walker,
      targetRing: targetRing,
      traveledFrac: walker ? walker.pos : (camps.length ? camps[camps.length - 1].pos : 0),
      caption: caption,
      monthNote: monthNote,
      noteKey: 'fb-trail-note-' + monthKey,
      noteMonthKey: noteMonthKey,
      completed: completed,
      badge: badge,
      league: league,
      empty: empty,
    };
  }


  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
  }

  function pathD(curve, fromFrac, toFrac, width) {
    var x0 = X_PAD, x1 = width - X_PAD;
    var pts = [];
    var steps = Math.max(2, Math.round(PATH_SAMPLES * (toFrac - fromFrac)));
    for (var i = 0; i <= steps; i += 1) {
      var f = fromFrac + (toFrac - fromFrac) * (i / steps);
      pts.push((x0 + f * (x1 - x0)).toFixed(1) + ' ' + curveY(f, curve).toFixed(1));
    }
    return 'M ' + pts.join(' L ');
  }

  function pointAt(curve, frac, width) {
    var x0 = X_PAD, x1 = width - X_PAD;
    return { x: x0 + frac * (x1 - x0), y: curveY(frac, curve) };
  }

  function badgeHtml(badge) {
    var C = 2 * Math.PI * 24;
    var pips = '';
    for (var i = 1; i <= 3; i += 1) {
      var cls = 'trail-pip' + (i <= badge.level ? ' filled' : '') +
        (badge.pulse && i === badge.level ? ' pip-pulse' : '');
      pips += '<span class="' + cls + '"></span>';
    }
    return '<div class="trail-badge" role="button" tabindex="0" ' +
      'aria-label="View the league ranks" title="' + esc(badge.rankName + ' ' + badge.level) + '">' +
      '<span class="trail-badge-disc">' +
        '<svg class="trail-badge-arc" viewBox="0 0 56 56" aria-hidden="true">' +
          '<circle class="arc-track" cx="28" cy="28" r="24"/>' +
          '<circle class="arc-fill" cx="28" cy="28" r="24" stroke-dasharray="' +
            (C * badge.levelProgress).toFixed(1) + ' ' + C.toFixed(1) + '"/>' +
        '</svg>' +
        '<img class="trail-badge-img" src="' + esc(badge.imgSrc) + '" alt="' + esc(badge.rankName) + ' badge"/>' +
      '</span>' +
      '<span class="trail-pips">' + pips + '</span>' +
    '</div>';
  }

  function render(container, model) {
    if (!container || !model) return;
    var width = Math.max(320, (container.clientWidth || 900) - (model.badge ? 70 : 0));
    var c = model.curve;
    var parts = [];

    parts.push('<div class="trail-row">');
    if (model.badge) parts.push(badgeHtml(model.badge));
    parts.push('<div class="trail-svg-wrap">');

    parts.push('<svg class="trail-svg" width="100%" height="' + SVG_HEIGHT + '" viewBox="0 0 ' +
      width + ' ' + SVG_HEIGHT + '" role="img" aria-label="Your trail this month">');

    if (model.traveledFrac > 0) {
      parts.push('<path class="trail-path-done" d="' + pathD(c, 0, Math.min(model.traveledFrac, 1), width) + '"/>');
    }
    if (model.traveledFrac < 1) {
      parts.push('<path class="trail-path-ahead" d="' + pathD(c, Math.min(model.traveledFrac, 1), 1, width) + '"/>');
    }

    model.camps.forEach(function (camp) {
      var p = pointAt(c, camp.pos, width);
      parts.push('<circle class="trail-camp" cx="' + p.x.toFixed(1) + '" cy="' + p.y.toFixed(1) +
        '" r="5"><title>' + esc(camp.label) + '</title></circle>');
    });

    (model.cairns || []).forEach(function (cairn) {
      var cp = pointAt(c, cairn.pos, width);
      parts.push('<g class="trail-cairn" transform="translate(' + cp.x.toFixed(1) + ' ' +
        (cp.y - 12).toFixed(1) + ')">' +
        '<title>' + esc(cairn.label) + '</title>' +
        '<ellipse cx="0" cy="0" rx="4.2" ry="1.9"/>' +
        '<ellipse cx="0" cy="-3.2" rx="3" ry="1.6"/>' +
        '<ellipse cx="0" cy="-5.8" rx="1.9" ry="1.3"/>' +
      '</g>');
    });

    if (model.targetRing) {
      var rp = pointAt(c, model.targetRing.pos, width);
      parts.push('<circle class="trail-ring' + (model.targetRing.reached ? ' reached' : '') +
        '" cx="' + rp.x.toFixed(1) + '" cy="' + rp.y.toFixed(1) + '" r="8">' +
        '<title>' + (model.targetRing.reached ? 'Plan complete' : "Tonight's planned camp") + '</title></circle>');
    }

    if (model.walker) {
      var wpnt = pointAt(c, model.walker.pos, width);
      var ember = model.walker.state === 'overtime' ? ' ember' : '';
      parts.push('<g class="trail-walker' + ember + '">' +
        '<circle class="trail-walker-pulse" cx="' + wpnt.x.toFixed(1) + '" cy="' + wpnt.y.toFixed(1) + '" r="8"/>' +
        '<circle class="trail-walker-core" cx="' + wpnt.x.toFixed(1) + '" cy="' + wpnt.y.toFixed(1) + '" r="6">' +
        '<title>' + esc(model.walker.label) + '</title></circle></g>');
    }

    parts.push('</svg>');
    parts.push('</div></div>');

    var captionText = model.empty
      ? (model.completed
          ? 'No camps this month — the trail waited.'
          : 'Your trail starts with today’s first focused minute.')
      : model.caption;
    parts.push('<p class="trail-caption">' + esc(captionText) + '</p>');

    if (model.monthNote) {
      var unwindLink = model.noteMonthKey
        ? ' <a class="trail-note-unwind" href="analytics.html?unwind=month&amp;month=' +
          esc(model.noteMonthKey) + '">Unwind the month →</a>'
        : '';
      parts.push('<div class="trail-note"><span>' + esc(model.monthNote) + unwindLink + '</span>' +
        '<button class="trail-note-dismiss" aria-label="Dismiss note" title="Dismiss">×</button></div>');
    }

    container.innerHTML = parts.join('');

    var dismiss = container.querySelector('.trail-note-dismiss');
    if (dismiss) {
      dismiss.addEventListener('click', function () {
        try { localStorage.setItem(model.noteKey, 'dismissed'); } catch (e) {}
        var note = container.querySelector('.trail-note');
        if (note) note.remove();
      });
    }

    var badgeImg = container.querySelector('.trail-badge-img');
    if (badgeImg && model.badge) {
      badgeImg.addEventListener('error', function () {
        var fb = document.createElement('span');
        fb.className = 'trail-badge-fallback';
        fb.textContent = model.badge.rankName.charAt(0);
        badgeImg.replaceWith(fb);
      });
    }

    var badgeEl = container.querySelector('.trail-badge');
    if (badgeEl) {
      badgeEl.addEventListener('click', function () { openLeagueModal(model, badgeEl); });
      badgeEl.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          openLeagueModal(model, badgeEl);
        }
      });
    }
  }


  var CHECK_SVG = '<svg class="league-check" viewBox="0 0 20 20" aria-hidden="true">' +
    '<path d="M5 10.5l3.2 3.2L15 6.8" fill="none" stroke="currentColor" stroke-width="2.2" ' +
    'stroke-linecap="round" stroke-linejoin="round"/></svg>';

  function hoursLabel(minutes) {
    var h = minutes / 60;
    var out = h.toFixed(1);
    if (out.endsWith('.0')) out = out.slice(0, -2);
    return out + ' h';
  }

  function buildLeagueBreakdown(league) {
    if (!league || !league.ladder || !league.ladder.length) return null;
    var points = league.points_min || 0;

    var ranks = league.ladder.map(function (row) {
      var state = 'future';
      if (row.rank_name === league.rank_name) state = 'current';
      else if (points >= (row.levels[0] || 0)) state = 'reached';
      return {
        rankName: row.rank_name,
        imgSrc: 'img/badges/' + String(row.rank_name).toLowerCase() + '.png',
        levels: row.levels.map(hoursLabel),
        levelsShort: row.levels.map(function (m) { return hoursLabel(m).replace(' h', ''); }),
        state: state,
      };
    });

    var flat = [];
    league.ladder.forEach(function (row) {
      row.levels.forEach(function (start, idx) {
        flat.push({ label: row.rank_name + ' ' + (idx + 1), start: start });
      });
    });
    flat.sort(function (a, b) { return a.start - b.start; });
    var curIdx = 0;
    for (var k = 0; k < flat.length; k += 1) { if (flat[k].start <= points) curIdx = k; }
    var cur = flat[curIdx];
    var nxt = flat[curIdx + 1] || null;

    var nextHint = 'You’ve reached the summit.';
    var progress = { atSummit: true, pct: 100, fromLabel: cur.label, fromHours: hoursLabel(cur.start) };
    if (nxt) {
      var span = nxt.start - cur.start;
      var frac = span > 0 ? Math.min(1, Math.max(0, (points - cur.start) / span)) : 1;
      var leftText = ((nxt.start - points) / 60).toFixed(1);
      if (leftText.endsWith('.0')) leftText = leftText.slice(0, -2);
      nextHint = leftText + ' h to ' + nxt.label;
      progress = {
        atSummit: false,
        pct: Math.round(frac * 100),
        hoursLeftText: leftText + ' h',
        nextLabel: nxt.label,
        fromLabel: cur.label,
        toLabel: nxt.label,
        fromHours: hoursLabel(cur.start),
        toHours: hoursLabel(nxt.start),
      };
    }

    return {
      pointsMin: points,
      hoursText: fmtHours(points * 60) + ' focused hours so far',
      currentRank: league.rank_name,
      currentLevel: league.level || 1,
      nextHint: nextHint,
      progress: progress,
      ranks: ranks,
    };
  }

  function openLeagueModal(model, openerEl) {
    var info = buildLeagueBreakdown(model && model.league);
    if (!info || document.querySelector('.league-overlay')) return;

    var pips = '';
    for (var i = 1; i <= 3; i += 1) {
      pips += '<span class="trail-pip' + (i <= info.currentLevel ? ' filled' : '') + '"></span>';
    }

    var tiles = info.ranks.map(function (r) {
      var entry = r.levelsShort[0] === '0' ? 'Start' : r.levelsShort[0] + ' h';
      var sub = esc('L2 at ' + r.levelsShort[1] + ' h') + '<br>' + esc('L3 at ' + r.levelsShort[2] + ' h');
      return '<div class="league-tile ' + r.state + '">' +
        (r.state === 'reached' ? CHECK_SVG : '') +
        '<img class="league-tile-img" src="' + esc(r.imgSrc) + '" alt="' + esc(r.rankName) + ' badge"/>' +
        '<p class="league-tile-name">' + esc(r.rankName) + '</p>' +
        '<p class="league-tile-entry">' + esc(entry) + '</p>' +
        '<p class="league-tile-sub">' + sub + '</p>' +
        (r.state === 'current' ? '<p class="league-here">you are here</p>' : '') +
      '</div>';
    }).join('');

    var pg = info.progress;
    var progressBlock;
    if (pg.atSummit) {
      progressBlock = '<p class="league-next league-summit">You’ve reached the summit.</p>';
    } else {
      progressBlock =
        '<div class="league-progress">' +
          '<p class="league-progress-lead"><strong>' + esc(pg.hoursLeftText) + '</strong> to ' + esc(pg.nextLabel) + '</p>' +
          '<div class="league-progress-track"><div class="league-progress-fill" style="width:0" data-target="' + pg.pct + '"></div></div>' +
          '<div class="league-progress-scale"><span>' + esc(pg.fromLabel) + '</span>' +
            '<span>' + esc(pg.toLabel) + ' · ' + esc(pg.toHours) + '</span></div>' +
        '</div>';
    }

    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay league-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML =
      '<div class="modal league-modal" role="dialog" aria-modal="true" aria-labelledby="league-title">' +
        '<div class="league-head">' +
          '<h2 id="league-title" class="serif">The League</h2>' +
          '<button class="league-close" aria-label="Close">×</button>' +
        '</div>' +
        '<div class="league-hero">' +
          '<img class="league-hero-img" src="img/badges/' + esc(String(info.currentRank).toLowerCase()) + '.png" ' +
            'alt="' + esc(info.currentRank) + ' badge"/>' +
          '<p class="league-hero-rank serif">' + esc(info.currentRank + ' ' + info.currentLevel) + '</p>' +
          '<span class="trail-pips league-hero-pips">' + pips + '</span>' +
          '<p class="league-hero-hours">' + esc(info.hoursText) + '</p>' +
          progressBlock +
        '</div>' +
        '<p class="section-label league-ranks-label">The six ranks</p>' +
        '<div class="league-ranks">' + tiles + '</div>' +
        '<p class="league-blurb">Every focused minute counts toward your rank — whatever the day’s plan was. ' +
          'Progress never goes down: deleting sessions can’t take a rank away. ' +
          'Your badge upgrades in place as you climb; the ring around it fills toward your next level.</p>' +
      '</div>';
    document.body.appendChild(overlay);

    function close() {
      overlay.remove();
      document.removeEventListener('keydown', onKey);
      if (openerEl && openerEl.focus) { try { openerEl.focus(); } catch (e) {} }
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('.league-close').addEventListener('click', close);
    document.addEventListener('keydown', onKey);
    overlay.querySelector('.league-close').focus();

    requestAnimationFrame(function () {
      var fill = overlay.querySelector('.league-progress-fill');
      if (fill) fill.style.width = (fill.getAttribute('data-target') || '0') + '%';
    });

    overlay.querySelectorAll('.league-tile-img, .league-hero-img').forEach(function (img) {
      img.addEventListener('error', function () {
        var fb = document.createElement('span');
        fb.className = 'trail-badge-fallback ' + img.className;
        fb.textContent = (img.alt || '?').charAt(0);
        img.replaceWith(fb);
      });
    });
  }


  function monthKeyOfDate(d) {
    return d.getFullYear() + '-' + pad(d.getMonth() + 1);
  }

  function monthLabelFromKey(monthKey, now, alwaysYear) {
    var parts = monthKey.split('-');
    var d = new Date(Number(parts[0]), Number(parts[1]) - 1, 1);
    var label = d.toLocaleDateString(undefined, { month: 'long' });
    if (alwaysYear || d.getFullYear() !== now.getFullYear()) label += ' ' + d.getFullYear();
    return label;
  }

  function listRegionMonths(sessions, now) {
    var currentKey = monthKeyOfDate(now);
    var firstKey = currentKey;
    (sessions || []).forEach(function (s) {
      var k = monthKeyOfDate(new Date(s.started_at));
      if (k < firstKey) firstKey = k;
    });
    var keys = [];
    var y = Number(firstKey.slice(0, 4));
    var m = Number(firstKey.slice(5, 7));
    for (var guard = 0; guard < 1200; guard += 1) {
      var key = y + '-' + pad(m);
      keys.push(key);
      if (key === currentKey) break;
      m += 1;
      if (m > 12) { m = 1; y += 1; }
    }
    return keys;
  }

  function buildTrailNav(sessions, browseKey, now) {
    var months = listRegionMonths(sessions, now);
    var currentKey = months[months.length - 1];
    var key = browseKey || currentKey;
    var idx = months.indexOf(key);
    if (idx === -1) { key = currentKey; idx = months.length - 1; }
    var hasData = (sessions || []).some(function (s) {
      return monthKeyOfDate(new Date(s.started_at)) === key;
    });
    return {
      monthKey: key,
      label: monthLabelFromKey(key, now, false),
      prevKey: idx > 0 ? months[idx - 1] : null,
      nextKey: idx < months.length - 1 ? months[idx + 1] : null,
      isCurrent: key === currentKey,
      hasData: hasData,
    };
  }

  function buildAtlasModel(opts) {
    var sessions = (opts && opts.sessions) || [];
    var workPeriods = (opts && opts.workPeriods) || [];
    var now = (opts && opts.now) || new Date();
    var months = listRegionMonths(sessions, now);
    var currentKey = months[months.length - 1];

    var out = months.map(function (key) {
      var first = new Date(Number(key.slice(0, 4)), Number(key.slice(5, 7)) - 1, 1);
      var model = buildTrailModel({ sessions: sessions, now: first, completed: true });
      var campCount = model.camps.length;
      var focusedSecs = 0;
      sessions.forEach(function (s) {
        if (monthKeyOfDate(new Date(s.started_at)) === key) focusedSecs += (s.seconds_focused || 0);
      });
      var statLine = campCount
        ? campCount + ' camp' + (campCount === 1 ? '' : 's') + ' · ' + fmtHours(focusedSecs) + ' h'
        : 'No camps';
      var hasRecap = workPeriods.some(function (p) {
        return p.kind === 'month' && p.period_key === key && (p.ai_recap || '') !== '';
      });
      return {
        monthKey: key,
        label: monthLabelFromKey(key, now, true),
        campCount: campCount,
        statLine: statLine,
        hasRecap: hasRecap,
        isCurrent: key === currentKey,
        empty: model.empty,
        model: model,
      };
    });
    out.reverse();
    return { months: out };
  }

  function openAtlasModal(atlasModel, openerEl, onPick) {
    if (!atlasModel || !atlasModel.months || !atlasModel.months.length) return;
    if (document.querySelector('.atlas-overlay')) return;

    var tiles = atlasModel.months.map(function (m) {
      return '<button class="atlas-tile' + (m.isCurrent ? ' current' : '') + (m.empty ? ' quiet' : '') +
        '" data-month="' + esc(m.monthKey) + '" aria-label="' + esc(m.label + ' — ' + m.statLine) + '">' +
        (m.hasRecap ? CHECK_SVG : '') +
        '<div class="atlas-tile-map"></div>' +
        '<p class="atlas-tile-name">' + esc(m.label) + (m.isCurrent ? ' · now' : '') + '</p>' +
        '<p class="atlas-tile-stat">' + esc(m.statLine) + '</p>' +
      '</button>';
    }).join('');

    var overlay = document.createElement('div');
    overlay.className = 'modal-overlay atlas-overlay';
    overlay.style.display = 'flex';
    overlay.innerHTML =
      '<div class="modal atlas-modal" role="dialog" aria-modal="true" aria-labelledby="atlas-title">' +
        '<div class="league-head">' +
          '<h2 id="atlas-title" class="serif">The Atlas</h2>' +
          '<button class="league-close" aria-label="Close">×</button>' +
        '</div>' +
        '<div class="atlas-grid">' + tiles + '</div>' +
        '<p class="league-blurb">Every month is a region — the same trail, drawn from your real ' +
          'sessions. Click a region to walk back to it.</p>' +
      '</div>';
    document.body.appendChild(overlay);

    function close() {
      overlay.remove();
      document.removeEventListener('keydown', onKey);
      if (openerEl && openerEl.focus) { try { openerEl.focus(); } catch (e) {} }
    }
    function onKey(e) { if (e.key === 'Escape') close(); }
    overlay.addEventListener('click', function (e) { if (e.target === overlay) close(); });
    overlay.querySelector('.league-close').addEventListener('click', close);
    document.addEventListener('keydown', onKey);
    overlay.querySelector('.league-close').focus();

    requestAnimationFrame(function () {
      var tileEls = overlay.querySelectorAll('.atlas-tile');
      atlasModel.months.forEach(function (m, i) {
        var mapEl = tileEls[i] && tileEls[i].querySelector('.atlas-tile-map');
        if (!mapEl) return;
        render(mapEl, m.model);
        var cap = mapEl.querySelector('.trail-caption');
        if (cap) cap.remove();
      });
    });

    overlay.querySelectorAll('.atlas-tile').forEach(function (tile) {
      tile.addEventListener('click', function () {
        var key = tile.getAttribute('data-month');
        close();
        if (typeof onPick === 'function') onPick(key);
      });
    });
  }


  function prefersReducedMotion() {
    try {
      return window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    } catch (e) { return false; }
  }

  function rippleFrom(originEl) {
    var origin = originEl.getBoundingClientRect();
    var ox = origin.left + origin.width / 2;
    var oy = origin.top + origin.height / 2;
    document.querySelectorAll('.card, header').forEach(function (el) {
      if (el.contains(originEl)) return;
      var r = el.getBoundingClientRect();
      if (!r.width && !r.height) return;
      var dx = r.left + r.width / 2 - ox;
      var dy = r.top + r.height / 2 - oy;
      var dist = Math.sqrt(dx * dx + dy * dy) || 1;
      var push = Math.max(3, 12 - dist / 90);
      var delay = Math.min(240, dist * 0.25);
      el.style.transition = 'transform 0.18s ease-out ' + delay.toFixed(0) + 'ms';
      el.style.transform = 'translate(' + (dx / dist * push).toFixed(1) + 'px,' +
        (dy / dist * push).toFixed(1) + 'px)';
      setTimeout(function () {
        el.style.transition = 'transform 0.45s cubic-bezier(0.22, 1, 0.36, 1)';
        el.style.transform = '';
        setTimeout(function () { el.style.transition = ''; }, 500);
      }, delay + 190);
    });
  }

  function playPromotion(container, rankName, opts) {
    opts = opts || {};
    var disc = container && container.querySelector('.trail-badge-disc');
    if (!disc) return;
    var img = disc.querySelector('.trail-badge-img');

    if (prefersReducedMotion()) {
      if (img) {
        img.style.transition = 'opacity 0.6s ease';
        img.style.opacity = '0';
        setTimeout(function () { img.style.opacity = '1'; }, 40);
      }
      return;
    }

    var overlay = document.createElement('div');
    overlay.className = 'trail-slam-overlay';
    var big = document.createElement('img');
    big.className = 'trail-slam-badge';
    big.src = 'img/badges/' + String(rankName).toLowerCase() + '.png';
    big.alt = rankName + ' badge';
    overlay.appendChild(big);
    document.body.appendChild(overlay);
    if (img) img.style.visibility = 'hidden';

    requestAnimationFrame(function () { overlay.classList.add('show'); });

    var HOLD_MS = 1100, SLAM_MS = 420;
    setTimeout(function () {
      var target = disc.getBoundingClientRect();
      var from = big.getBoundingClientRect();
      if (!from.width) { overlay.remove(); if (img) img.style.visibility = ''; return; }
      var dx = target.left + target.width / 2 - (from.left + from.width / 2);
      var dy = target.top + target.height / 2 - (from.top + from.height / 2);
      big.style.transition = 'transform ' + SLAM_MS + 'ms cubic-bezier(0.55, 0, 1, 0.45)';
      big.style.transform = 'translate(' + dx.toFixed(1) + 'px,' + dy.toFixed(1) + 'px) ' +
        'scale(' + (target.width / from.width).toFixed(3) + ')';
      setTimeout(function () {
        if (img) img.style.visibility = '';
        overlay.remove();
        if (typeof opts.onImpact === 'function') { try { opts.onImpact(); } catch (e) {} }
        rippleFrom(disc);
      }, SLAM_MS + 30);
    }, HOLD_MS);
  }

  var api = {
    buildTrailModel: buildTrailModel,
    buildLandmarks: buildLandmarks,
    LANDMARK_LABELS: LANDMARK_LABELS,
    focusedSecondsByDay: focusedSecondsByDay,
    hasUnbroken25: hasUnbroken25,
    render: render,
    playPromotion: playPromotion,
    buildLeagueBreakdown: buildLeagueBreakdown,
    openLeagueModal: openLeagueModal,
    listRegionMonths: listRegionMonths,
    buildTrailNav: buildTrailNav,
    buildAtlasModel: buildAtlasModel,
    openAtlasModal: openAtlasModal,
    curveY: curveY,
    curveForMonth: curveForMonth,
  };
  if (typeof window !== 'undefined') window.JourneyMap = api;
})();
