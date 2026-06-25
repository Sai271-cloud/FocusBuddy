// Shared planner insight helpers for Today, Tracker, Plan, and Analytics.
// These are deterministic browser-side helpers; they do not call the AI.
(function () {
  const GOAL_KEY = 'fb-daily-focus-goal';
  const DEFAULT_GOAL_MIN = 60;

  function pad(n) {
    return String(n).padStart(2, '0');
  }

  function localDayKey(date = new Date()) {
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}`;
  }

  function dateFromKey(key) {
    const parts = String(key || '').split('-').map(Number);
    if (parts.length !== 3 || parts.some(n => !Number.isFinite(n))) return new Date();
    return new Date(parts[0], parts[1] - 1, parts[2]);
  }

  function isoWithLocalOffset(date) {
    const offsetMin = -date.getTimezoneOffset();
    const sign = offsetMin >= 0 ? '+' : '-';
    const abs = Math.abs(offsetMin);
    const off = `${sign}${pad(Math.floor(abs / 60))}:${pad(abs % 60)}`;
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
      `T${pad(date.getHours())}:${pad(date.getMinutes())}:${pad(date.getSeconds())}${off}`;
  }

  function dayBounds(key = localDayKey()) {
    const start = dateFromKey(key);
    const end = new Date(start.getFullYear(), start.getMonth(), start.getDate() + 1);
    return { day_start: isoWithLocalOffset(start), day_end: isoWithLocalOffset(end) };
  }

  function parseJson(value, fallback) {
    try {
      const parsed = JSON.parse(value || '');
      return parsed == null ? fallback : parsed;
    } catch {
      return fallback;
    }
  }

  function parsePlanEntries(plan) {
    const raw = parseJson(plan && plan.plan_json, []);
    if (!Array.isArray(raw)) return [];
    const seen = new Set();
    const out = [];
    raw.forEach((item, index) => {
      if (!item || !Number.isFinite(Number(item.task_id)) || seen.has(Number(item.task_id))) return;
      seen.add(Number(item.task_id));
      out.push({
        task_id: Number(item.task_id),
        name: item.name || '',
        estimate_min: Math.max(0, Number(item.estimate_min) || 0),
        difficulty: ['easy', 'medium', 'hard'].includes(item.difficulty) ? item.difficulty : 'medium',
        scheduled_min: Number.isInteger(item.scheduled_min) ? item.scheduled_min : null,
        order: index,
      });
    });
    return out;
  }

  function parseAdvice(plan) {
    const parsed = parseJson(plan && plan.advice_json, null);
    return parsed && Array.isArray(parsed.scheduled) ? parsed : null;
  }

  function adviceStarts(plan) {
    const advice = parseAdvice(plan);
    const out = new Map();
    (advice && advice.scheduled || []).forEach(block => {
      const id = Number(block && block.task_id);
      if (!Number.isFinite(id) || out.has(id)) return;
      out.set(id, (Number(block.start_hour) || 0) * 60 + (Number(block.start_min) || 0));
    });
    return out;
  }

  function recommendedPlanEntry(plan, tasks = [], reality = null) {
    const entries = parsePlanEntries(plan);
    if (!entries.length) return null;
    const activeIds = new Set((tasks || []).filter(t => !t.completed).map(t => Number(t.id)));
    const actualByTask = new Map();
    (reality && Array.isArray(reality.rows) ? reality.rows : []).forEach(row => {
      actualByTask.set(Number(row.task_id), Number(row.actual_total_min) || 0);
    });
    const starts = adviceStarts(plan);
    const candidates = entries.filter(entry => {
      if (activeIds.size && !activeIds.has(entry.task_id)) return false;
      const actual = actualByTask.get(entry.task_id) || 0;
      return !entry.estimate_min || actual < entry.estimate_min;
    });
    candidates.sort((a, b) => {
      const aStart = Number.isInteger(a.scheduled_min) ? a.scheduled_min : (starts.get(a.task_id) ?? 2000 + a.order);
      const bStart = Number.isInteger(b.scheduled_min) ? b.scheduled_min : (starts.get(b.task_id) ?? 2000 + b.order);
      return aStart - bStart || a.order - b.order;
    });
    return candidates[0] || null;
  }

  function sessionSeconds(session) {
    return (session.seconds_focused || 0) + (session.seconds_distracted || 0) +
      (session.seconds_uncertain || 0) + (session.seconds_away || 0);
  }

  function sessionsForDay(sessions, key) {
    return (sessions || []).filter(s => localDayKey(new Date(s.started_at)) === key);
  }

  function focusGoalMin() {
    const saved = Number(localStorage.getItem(GOAL_KEY));
    if (Number.isFinite(saved) && saved >= 0) return saved;
    return DEFAULT_GOAL_MIN;
  }

  function setFocusGoalMin(minutes) {
    localStorage.setItem(GOAL_KEY, String(Math.max(0, Number(minutes) || 0)));
  }

  function focusGoalProgress(sessions, key = localDayKey(), goalMin = focusGoalMin()) {
    const focusedMin = Math.round(
      sessionsForDay(sessions, key).reduce((sum, s) => sum + (s.seconds_focused || 0), 0) / 60
    );
    return {
      key,
      goal_min: goalMin,
      focused_min: focusedMin,
      pct: goalMin > 0 ? Math.min(100, Math.round(focusedMin / goalMin * 100)) : 0,
      met: goalMin > 0 && focusedMin >= goalMin,
    };
  }

  function focusStreak(sessions, goalMin = focusGoalMin(), todayKey = localDayKey()) {
    if (goalMin <= 0) return { count: 0, includes_today: false };
    let count = 0;
    let d = dateFromKey(todayKey);
    let includesToday = false;
    for (let i = 0; i < 60; i += 1) {
      const key = localDayKey(d);
      const progress = focusGoalProgress(sessions, key, goalMin);
      if (!progress.met) break;
      if (i === 0) includesToday = true;
      count += 1;
      d = new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1);
    }
    if (!includesToday) {
      d = new Date(dateFromKey(todayKey).getFullYear(), dateFromKey(todayKey).getMonth(), dateFromKey(todayKey).getDate() - 1);
      for (let i = 0; i < 60; i += 1) {
        const key = localDayKey(d);
        const progress = focusGoalProgress(sessions, key, goalMin);
        if (!progress.met) break;
        count += 1;
        d = new Date(d.getFullYear(), d.getMonth(), d.getDate() - 1);
      }
    }
    return { count, includes_today: includesToday };
  }

  window.PlanningInsights = {
    localDayKey,
    dateFromKey,
    isoWithLocalOffset,
    dayBounds,
    parsePlanEntries,
    parseAdvice,
    recommendedPlanEntry,
    sessionSeconds,
    sessionsForDay,
    focusGoalMin,
    setFocusGoalMin,
    focusGoalProgress,
    focusStreak,
  };
})();
