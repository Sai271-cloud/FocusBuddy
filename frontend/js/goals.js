// Goals v1 (deadline goals with task links). Pure display helpers shared by
// goals.html and the Today strip so neither page duplicates the math:
//  - goalTaskIds / goalFocusSeconds: derive links + measured progress from the
//    tasks and sessions the pages already fetch (TaskOut carries goal_id)
//  - daysLeftLabel: calm deadline wording — a passed date reads "past its date —
//    still open", never "overdue" (the anti-shame rule)
//  - formatHM: seconds → "6h 20m"
// All "today" math goes through PlanningInsights.currentDate/localDayKey so the
// demo frozen clock rides along; never call new Date() here.
(function () {
  'use strict';

  function goalTaskIds(tasks, goalId) {
    return (tasks || []).filter((t) => t.goal_id === goalId).map((t) => t.id);
  }

  function goalFocusSeconds(sessions, tasks, goalId) {
    const ids = new Set(goalTaskIds(tasks, goalId));
    let total = 0;
    for (const s of sessions || []) {
      if (ids.has(s.task_id)) total += s.seconds_focused || 0;
    }
    return total;
  }

  // Local day keys (YYYY-MM-DD) on which any attached task got focused time —
  // feeds the goals page's recent-activity dots. Day bucketing is local via
  // PlanningInsights so the demo frozen clock stays consistent.
  function goalWorkedDayKeys(sessions, tasks, goalId) {
    const ids = new Set(goalTaskIds(tasks, goalId));
    const days = new Set();
    for (const s of sessions || []) {
      if (ids.has(s.task_id) && (s.seconds_focused || 0) > 0) {
        days.add(window.PlanningInsights.localDayKey(new Date(s.started_at)));
      }
    }
    return days;
  }

  function daysBetween(fromKey, toKey) {
    const parse = (key) => {
      const parts = String(key || '').split('-').map(Number);
      if (parts.length !== 3 || parts.some(isNaN)) return null;
      return Date.UTC(parts[0], parts[1] - 1, parts[2]);
    };
    const from = parse(fromKey);
    const to = parse(toKey);
    if (from === null || to === null) return null;
    return Math.round((to - from) / 86400000);
  }

  function targetPretty(dayKey) {
    const parts = String(dayKey || '').split('-').map(Number);
    const d = new Date(parts[0], parts[1] - 1, parts[2]);
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  function daysLeftLabel(goal, todayKey) {
    const days = daysBetween(todayKey, goal.target_day_key);
    if (days === null) return '';
    if (days > 1) return days + ' days left';
    if (days === 1) return '1 day left';
    if (days === 0) return 'due today';
    return 'past its date — still open';
  }

  function formatHM(seconds) {
    const minutes = Math.max(0, Math.floor((seconds || 0) / 60));
    if (minutes >= 60) {
      const h = Math.floor(minutes / 60);
      const m = minutes % 60;
      return m ? h + 'h ' + m + 'm' : h + 'h';
    }
    return minutes + 'm';
  }

  window.FocusGoals = {
    goalTaskIds,
    goalFocusSeconds,
    goalWorkedDayKeys,
    daysLeftLabel,
    targetPretty,
    formatHM,
  };
})();
