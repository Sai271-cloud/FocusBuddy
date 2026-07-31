// Habit tracker v1 (coaching-seeded habits). Three jobs, all reward-layer:
//  - CATALOG: the starter habits anyone can adopt before their first weekly unwind
//  - verifyHabit: pure check "was this auto habit completed on this local day?"
//  - detectAndSyncHabitChecks: fire-and-forget sync of verified days to the
//    backend's insert-only habit_checks store (no toast BY DESIGN — an auto tick
//    quietly appears; announcing it would turn a calm record into a reward ping).
// The backend never does timezone math: this file owns the local-day reasoning,
// like journey-map.js does for landmarks.
(function () {
  'use strict';

  // Starter catalog. `check` mirrors the backend's crud.HABIT_TEMPLATES specs;
  // adopting stringifies it into the habit's check_json.
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

  // Pure: was `habit` completed on `dayKey`, judged from ctx = {sessions,
  // workPeriods, todayPlan}? Manual habits always return false here — only the
  // user's tick can complete those.
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
        // Today's live plan counts before any reality row exists; past days use
        // the saved plan-vs-reality record (same predicate as the landmark).
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

  // The last n local day keys, oldest → today (demo-clock aware via currentDate).
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

  // Fire-and-forget (the detectAndSyncLandmarks contract): verify every active
  // auto habit over the recent window and store any missing days. Never throws,
  // never toasts. Scans at most 60 days back and never before the habit's
  // adoption day, so history stays honest and the payload stays bounded.
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
      // Habits are a reward layer — a failure here must never touch the caller.
    }
  }

  window.FocusHabits = {
    CATALOG,
    verifyHabit,
    detectAndSyncHabitChecks,
    lastNDayKeys,
    densityLabel,
  };
})();
