(function () {
  'use strict';

  const CATALOG = [
    {
      code: 'cat-any-session',
      title: 'Take one real focus session',
      why: 'Showing up is the whole habit — one session a day keeps the trail moving.',
      kind: 'auto',
      check: { template: 'any-session', params: {} },
    },
    {
      code: 'cat-before-10',
      title: 'Start something before 10:00',
      why: 'An early first session sets the tone before the day gets loud.',
      kind: 'auto',
      check: { template: 'session-before', params: { time: '10:00' } },
    },
    {
      code: 'cat-focus-25',
      title: 'Complete 25 focused minutes',
      why: 'A quarter hour of real focus, every day, outgrows any single big push.',
      kind: 'auto',
      check: { template: 'focus-minutes', params: { min: 25 } },
    },
    {
      code: 'cat-make-plan',
      title: 'Sketch a plan for the day',
      why: 'Days with a rough plan wander less often.',
      kind: 'auto',
      check: { template: 'made-a-plan', params: {} },
    },
    {
      code: 'cat-daily-unwind',
      title: 'Close the day with a daily unwind',
      why: 'A two-minute look back is where the learning actually happens.',
      kind: 'auto',
      check: { template: 'did-daily-unwind', params: {} },
    },
    {
      code: 'cat-phone-away',
      title: 'Put the phone in another room before starting',
      why: 'Distance beats willpower — you tick this one yourself.',
      kind: 'manual',
      check: null,
    },
  ];

  function parseJsonQuiet(text) {
    try { return JSON.parse(text); } catch (e) { return null; }
  }

  function checkSpec(habit) {
    if (!habit || habit.kind !== 'auto') return null;
    const spec = typeof habit.check_json === 'string'
      ? parseJsonQuiet(habit.check_json)
      : habit.check_json;
    return spec && spec.template ? spec : null;
  }

  function verifyHabit(habit, dayKey, ctx) {
    const PI = window.PlanningInsights;
    const spec = checkSpec(habit);
    if (!spec || !PI) return false;
    const sessions = (ctx && ctx.sessions) || [];
    const workPeriods = (ctx && ctx.workPeriods) || [];
    const daySessions = PI.sessionsForDay(sessions, dayKey);

    switch (spec.template) {
      case 'any-session':
        return daySessions.some(s => PI.sessionSeconds(s) > 0);
      case 'focus-minutes': {
        const min = (spec.params && spec.params.min) || 25;
        const focused = daySessions.reduce((a, s) => a + (s.seconds_focused || 0), 0);
        return focused >= min * 60;
      }
      case 'session-before': {
        const time = spec.params && spec.params.time;
        if (!time) return false;
        const parts = time.split(':');
        const cutoff = Number(parts[0]) * 60 + Number(parts[1]);
        return daySessions.some(s => {
          const d = new Date(s.started_at);
          return PI.sessionSeconds(s) > 0 && (d.getHours() * 60 + d.getMinutes()) < cutoff;
        });
      }
      case 'unbroken-25':
        return daySessions.some(s =>
          window.JourneyMap && window.JourneyMap.hasUnbroken25(parseJsonQuiet(s.timeline_json)));
      case 'made-a-plan': {
        const todayKey = PI.localDayKey(PI.currentDate());
        if (dayKey === todayKey && ctx && ctx.todayPlan
            && PI.parsePlanEntries(ctx.todayPlan).length) return true;
        return workPeriods.some(p => {
          if (p.kind !== 'day' || p.period_key !== dayKey) return false;
          const r = parseJsonQuiet(p.plan_reality_json);
          return !!(r && r.has_plan);
        });
      }
      case 'did-daily-unwind':
        return workPeriods.some(p =>
          p.kind === 'day' && p.period_key === dayKey &&
          ((p.ai_recap || '') !== '' || (p.reflection || '') !== ''));
      default:
        return false;
    }
  }

  function describeCheck(spec) {
    if (!spec) return '';
    const p = spec.params || {};
    switch (spec.template) {
      case 'any-session': return 'Any focus session that day';
      case 'focus-minutes': return 'Focus at least ' + (p.min || 25) + ' minutes';
      case 'session-before': return 'Start a session before ' + (p.time || '10:00');
      case 'unbroken-25': return 'A 25-minute unbroken focus run';
      case 'made-a-plan': return 'Made a plan that day';
      case 'did-daily-unwind': return 'Did the daily unwind';
      default: return '';
    }
  }

  const WORK_WORDS = /\b(focus|focused|work|working|study|studying|deep|session|concentrat\w*)\b/;
  function guessCheckSpec(title) {
    const t = String(title || '').toLowerCase();
    if (!t.trim()) return null;

    if (/\bunbroken\b|without (a )?break|\bno breaks?\b/.test(t)) {
      return { template: 'unbroken-25', params: {} };
    }

    const dur = t.match(/(\d+(?:\.\d+)?)\s*(hours?|hrs?|h|minutes?|mins?|m)\b/);
    if (dur && WORK_WORDS.test(t)) {
      const n = parseFloat(dur[1]);
      const minutes = Math.round(dur[2].startsWith('h') ? n * 60 : n);
      return { template: 'focus-minutes', params: { min: Math.max(5, Math.min(240, minutes)) } };
    }

    const startWords = /\b(session|start|starting|begin|focus|work|study)\b/;
    if (/\bbefore noon\b/.test(t) && startWords.test(t)) {
      return { template: 'session-before', params: { time: '12:00' } };
    }
    const before = t.match(/\bbefore\s+(\d{1,2})(?::(\d{2}))?\s*(am|pm|a\.m\.|p\.m\.)?/);
    if (before && startWords.test(t)) {
      let hour = parseInt(before[1], 10);
      const minute = before[2] ? parseInt(before[2], 10) : 0;
      const meridiem = (before[3] || '').replace(/\./g, '');
      if (meridiem === 'pm' && hour < 12) hour += 12;
      if (meridiem === 'am' && hour === 12) hour = 0;
      if (hour <= 23 && minute <= 59) {
        const pad = n => String(n).padStart(2, '0');
        return { template: 'session-before', params: { time: pad(hour) + ':' + pad(minute) } };
      }
    }

    if (/\bplan\b|\bplanning\b/.test(t)) return { template: 'made-a-plan', params: {} };
    if (/\bunwind\b|\breflect\w*\b/.test(t)) return { template: 'did-daily-unwind', params: {} };
    if (/\b(a|one|any|1)\s+(\w+\s+)?session\b/.test(t) || /\bfocus (every|each) day\b/.test(t)) {
      return { template: 'any-session', params: {} };
    }
    return null;
  }

  function lastNDayKeys(n, now) {
    const PI = window.PlanningInsights;
    const base = now || PI.currentDate();
    const keys = [];
    for (let i = n - 1; i >= 0; i -= 1) {
      keys.push(PI.localDayKey(new Date(base.getFullYear(), base.getMonth(), base.getDate() - i)));
    }
    return keys;
  }

  function densityLabel(checkDaySet, now) {
    const count = lastNDayKeys(7, now).filter(k => checkDaySet.has(k)).length;
    return count + ' of the last 7 days';
  }

  async function detectAndSyncHabitChecks({ sessions, workPeriods, todayPlan, habits } = {}) {
    try {
      if (!window.PlanningInsights || typeof syncHabitChecks !== 'function') return;
      let list = habits;
      if (!list && typeof getHabits === 'function') list = await getHabits();
      list = (list || []).filter(h => h.status === 'active' && h.kind === 'auto');
      if (!list.length) return;
      const ctx = {
        sessions: sessions || [],
        workPeriods: workPeriods || [],
        todayPlan: todayPlan || null,
      };
      const keys = lastNDayKeys(60);
      const fresh = [];
      list.forEach(habit => {
        const have = new Set(habit.check_days || []);
        keys.forEach(dayKey => {
          if (dayKey < habit.created_day_key || have.has(dayKey)) return;
          if (verifyHabit(habit, dayKey, ctx)) fresh.push({ habit_id: habit.id, day_key: dayKey });
        });
      });
      if (fresh.length) await syncHabitChecks(fresh.slice(0, 200));
    } catch (e) {
    }
  }

  window.FocusHabits = {
    CATALOG,
    verifyHabit,
    describeCheck,
    guessCheckSpec,
    detectAndSyncHabitChecks,
    lastNDayKeys,
    densityLabel,
  };
})();
