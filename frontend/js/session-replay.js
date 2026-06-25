(function () {
  const VALID_STATES = new Set(['focused', 'distracted', 'uncertain', 'away']);
  const LABELS = {
    focused: 'Focused',
    distracted: 'Distracted',
    uncertain: 'Uncertain',
    away: 'Away',
  };
  const COLORS = {
    focused: 'var(--sage)',
    distracted: 'var(--terracotta)',
    uncertain: 'var(--ochre)',
    away: 'var(--text-muted)',
  };

  function esc(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  function parseList(raw) {
    if (Array.isArray(raw)) return raw;
    if (typeof raw !== 'string' || raw.trim() === '') return [];
    try {
      const parsed = JSON.parse(raw);
      return Array.isArray(parsed) ? parsed : [];
    } catch {
      return [];
    }
  }

  function seconds(n) {
    const value = Number(n);
    return Number.isFinite(value) && value > 0 ? value : 0;
  }

  function totalSeconds(session, journal, timeline) {
    const saved =
      seconds(session.seconds_focused) +
      seconds(session.seconds_distracted) +
      seconds(session.seconds_uncertain) +
      seconds(session.seconds_away);
    if (saved > 0) return Math.round(saved);

    const journalMax = journal.reduce((max, e) => Math.max(max, seconds(e.t)), 0);
    const timelineMax = timeline.reduce((max, e) => Math.max(max, seconds(e.minute) * 60 + 60), 0);
    return Math.round(Math.max(journalMax, timelineMax));
  }

  function formatDuration(total) {
    total = Math.max(0, Math.round(total || 0));
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${s}s`;
    return `${s}s`;
  }

  function formatStamp(total) {
    total = Math.max(0, Math.round(total || 0));
    const m = Math.floor(total / 60);
    const s = total % 60;
    return `${m}:${String(s).padStart(2, '0')}`;
  }

  function normalizeStateEvents(journal, timeline, total) {
    let events = journal
      .filter(e => e && e.type === 'state' && VALID_STATES.has(e.state))
      .map(e => ({ t: Math.max(0, Math.min(total, seconds(e.t))), state: e.state }));

    if (!events.length) {
      events = timeline
        .filter(e => e && VALID_STATES.has(e.state))
        .map(e => ({ t: Math.max(0, Math.min(total, seconds(e.minute) * 60)), state: e.state }));
    }

    events.sort((a, b) => a.t - b.t);
    // No synthetic 'uncertain' when there were zero recorded state events — that would
    // misrepresent a session with saved totals but no per-state timeline. The caller falls
    // back to an aggregate-only view instead.
    if (!events.length) return [];
    // Extend the first real state back to t=0 (the pre-first-event gap is unknown; assume the
    // first known state held) rather than defaulting that gap to 'uncertain'.
    if (events[0].t > 0) events.unshift({ t: 0, state: events[0].state });

    const compact = [];
    for (const event of events) {
      const prev = compact[compact.length - 1];
      if (prev && prev.state === event.state) continue;
      compact.push(event);
    }
    return compact;
  }

  function aggregateSegments(session) {
    // No per-state timeline was recorded — build a proportional bar from the saved per-state
    // second counters, so we show the real focused/distracted split instead of one fake block.
    const order = ['focused', 'distracted', 'uncertain', 'away'];
    let cursor = 0;
    const segs = [];
    for (const state of order) {
      const dur = seconds(session[`seconds_${state}`]);
      if (dur <= 0) continue;
      segs.push({ state, start: cursor, end: cursor + dur, duration: dur });
      cursor += dur;
    }
    return segs;
  }

  function buildSegments(session) {
    const timeline = parseList(session.timeline_json);
    const journal = parseList(session.journal_json);
    const total = totalSeconds(session, journal, timeline);
    const events = normalizeStateEvents(journal, timeline, total);
    let segments = [];
    let aggregateOnly = false;

    if (events.length) {
      for (let i = 0; i < events.length; i += 1) {
        const start = events[i].t;
        const end = i + 1 < events.length ? events[i + 1].t : total;
        if (end > start) {
          segments.push({ state: events[i].state, start, end, duration: end - start });
        }
      }
    } else {
      // No recorded state events: fall back to an honest aggregate-only bar (or, if even the
      // counters are zero, an empty timeline rendered by renderTimeline).
      segments = aggregateSegments(session);
      aggregateOnly = segments.length > 0;
    }

    return { total, timeline, journal, segments, aggregateOnly };
  }

  function bestFocusStretch(segments) {
    return segments
      .filter(s => s.state === 'focused')
      .reduce((best, seg) => (!best || seg.duration > best.duration ? seg : best), null);
  }

  function renderTimeline(segments, total, aggregateOnly) {
    if (!segments.length || total <= 0) {
      return '<p class="text-sm" style="color:var(--text-muted);margin:8px 0 0">No state timeline was recorded for this session.</p>';
    }

    const bars = segments.map(seg => `
      <div
        title="${esc(LABELS[seg.state])}: ${esc(formatDuration(seg.duration))}"
        style="flex:${Math.max(1, seg.duration)} 1 0;min-width:5px;background:${COLORS[seg.state]};"
        aria-label="${esc(LABELS[seg.state])} for ${esc(formatDuration(seg.duration))}">
      </div>`).join('');

    // With a real timeline the legend marks when each state began. In the aggregate-only
    // fallback the start times aren't real clock moments, so show each state's total instead.
    const legend = aggregateOnly
      ? segments.map(seg => `
        <span style="display:inline-flex;align-items:center;gap:5px;color:var(--text-muted);font-size:0.72rem">
          <span style="width:7px;height:7px;border-radius:99px;background:${COLORS[seg.state]}"></span>
          ${LABELS[seg.state]} ${formatDuration(seg.duration)}
        </span>`).join('')
      : segments.slice(0, 6).map(seg => `
        <span style="display:inline-flex;align-items:center;gap:5px;color:var(--text-muted);font-size:0.72rem">
          <span style="width:7px;height:7px;border-radius:99px;background:${COLORS[seg.state]}"></span>
          ${formatStamp(seg.start)} ${LABELS[seg.state]}
        </span>`).join('');
    const more = (!aggregateOnly && segments.length > 6)
      ? `<span style="color:var(--text-faint);font-size:0.72rem">+${segments.length - 6} more</span>`
      : '';
    const note = aggregateOnly
      ? '<p class="text-xs" style="color:var(--text-faint);margin:7px 0 0">Aggregate only — no minute-by-minute timeline was recorded for this session.</p>'
      : '';

    return `
      <div style="margin-top:10px">
        <div style="height:12px;display:flex;overflow:hidden;border-radius:99px;background:var(--surface-2)" role="img" aria-label="${aggregateOnly ? 'Aggregate focus breakdown' : 'Session state timeline'}">
          ${bars}
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:8px 12px;margin-top:8px">
          ${legend}${more}
        </div>
        ${note}
      </div>`;
  }

  function renderSites(journal) {
    const sites = journal.filter(e => e && e.type === 'site' && (e.site || e.title));
    if (!sites.length) {
      return '<p class="text-xs" style="color:var(--text-faint);margin:6px 0 0">No site switches were recorded.</p>';
    }
    const visible = sites.slice(0, 5).map(e => {
      const title = e.title ? `${esc(e.title)} ` : '';
      const site = e.site ? `<span style="color:var(--text-faint)">(${esc(e.site)})</span>` : '';
      return `<li style="margin:5px 0;line-height:1.35"><span style="color:var(--text-faint);font-variant-numeric:tabular-nums">${formatStamp(e.t)}</span> ${title}${site}</li>`;
    }).join('');
    const more = sites.length > 5 ? `<li style="margin:5px 0;color:var(--text-faint)">+${sites.length - 5} more site switches</li>` : '';
    return `<ul style="margin:6px 0 0;padding-left:16px;color:var(--text);font-size:0.78rem">${visible}${more}</ul>`;
  }

  function renderNotes(journal) {
    const notes = journal.filter(e => e && e.type === 'note' && e.note);
    if (!notes.length) {
      return '<p class="text-xs" style="color:var(--text-faint);margin:6px 0 0">No distraction notes were recorded.</p>';
    }
    const visible = notes.slice(0, 5).map(e =>
      `<li style="margin:5px 0;line-height:1.35"><span style="color:var(--text-faint);font-variant-numeric:tabular-nums">${formatStamp(e.t)}</span> ${esc(e.note)}</li>`
    ).join('');
    const more = notes.length > 5 ? `<li style="margin:5px 0;color:var(--text-faint)">+${notes.length - 5} more notes</li>` : '';
    return `<ul style="margin:6px 0 0;padding-left:16px;color:var(--text);font-size:0.78rem">${visible}${more}</ul>`;
  }

  function renderBest(best) {
    if (!best) {
      return '<p class="text-sm" style="color:var(--text-muted);margin:6px 0 0">No focused stretch was recorded yet.</p>';
    }
    return `
      <p style="color:var(--text);font-weight:600;margin:5px 0 1px">${formatDuration(best.duration)}</p>
      <p class="text-xs" style="color:var(--text-faint);margin:0">${formatStamp(best.start)} to ${formatStamp(best.end)}</p>`;
  }

  function renderPanel(label, body) {
    return `
      <div style="border:1px solid var(--border);border-radius:8px;padding:10px;background:var(--surface-2)">
        <p class="section-label" style="margin:0">${esc(label)}</p>
        ${body}
      </div>`;
  }

  function render(session, opts = {}) {
    const { total, journal, segments, aggregateOnly } = buildSegments(session || {});
    const best = aggregateOnly ? null : bestFocusStretch(segments);
    const taskName = session && session.task_name ? session.task_name : 'this session';
    const summary = total > 0
      ? `${formatDuration(total)} tracked`
      : 'Replay data is limited';

    return `
      <section class="session-replay" aria-label="Session replay" style="${opts.marginTop ? `margin-top:${opts.marginTop}` : ''}">
        <div style="display:flex;align-items:flex-start;justify-content:space-between;gap:12px">
          <div>
            <p class="section-label" style="margin:0 0 2px">Session replay</p>
            <h3 class="serif" style="font-size:1rem;font-weight:600;color:var(--text);margin:0">${esc(taskName)}</h3>
            <p class="text-xs" style="color:var(--text-faint);margin:3px 0 0">${summary}</p>
          </div>
        </div>
        ${renderTimeline(segments, total, aggregateOnly)}
        <div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px;margin-top:12px">
          ${renderPanel('Best focus stretch', renderBest(best))}
          ${renderPanel('Sites opened', renderSites(journal))}
          ${renderPanel('Distraction notes', renderNotes(journal))}
        </div>
      </section>`;
  }

  window.FocusSessionReplay = {
    render,
    _buildSegments: buildSegments,
  };
})();
