// Plan calendar — renders the Schedule step's task tray + day calendar.
//
// API: PlanCalendar.render(rootEl, {
//   entries, hourly, aiSuggest, onUpdate, onChange
// })
//   entries  : [{ task_id, name, estimate_min, difficulty, scheduled_min? }]
//   hourly   : Map(hour -> { focus_pct, sessions }) for hour shading
//   aiSuggest: optional PlanAdviceResponse with scheduled[] ghost blocks
//   suggestLabel: optional label for ghost suggestions (default "AI")
//   onUpdate : (taskId, patch) => void, e.g. { scheduled_min: 540 }
//   onChange : legacy fallback, (taskId, scheduledMin | null) => void
(function () {
  const HOUR_HEIGHT = 52;
  const DAY_MIN = 24 * 60;
  const STEP = 15;
  const DRAG_SNAP = 5;
  const DEFAULT_PLACE = 9 * 60;
  const MIN_ESTIMATE = 10;
  const MAX_ESTIMATE = 120;
  const AI_MAGNET_MIN = 10;

  function esc(s) {
    return String(s == null ? '' : s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;').replace(/'/g, '&#039;');
  }

  function durationOf(e) {
    const mins = Number(e && e.estimate_min);
    return Number.isFinite(mins) && mins > 0 ? mins : 5;
  }
  function latestStart(e) { return Math.max(0, DAY_MIN - durationOf(e)); }
  function snapTo(m, snap) { return Math.round(m / snap) * snap; }
  function snapDown(m, snap) { return Math.floor(m / snap) * snap; }
  function clamp(min, lo, hi) { return Math.max(lo, Math.min(hi, min)); }
  function latestSnappedStart(e, snap = STEP) { return snapDown(latestStart(e), snap); }
  function clampStart(e, m, snap = STEP, magnets = []) {
    let next = clamp(snapTo(m, snap), 0, latestSnappedStart(e, snap));
    for (const magnet of magnets) {
      if (Math.abs(next - magnet) <= AI_MAGNET_MIN) return clamp(magnet, 0, latestStart(e));
    }
    return next;
  }
  function clampEstimate(mins) {
    return clamp(snapTo(Number(mins) || MIN_ESTIMATE, DRAG_SNAP), MIN_ESTIMATE, MAX_ESTIMATE);
  }
  function isPlaced(e) { return Number.isFinite(e.scheduled_min); }

  function fmtClock(min) {
    min = ((min % DAY_MIN) + DAY_MIN) % DAY_MIN;
    const h = Math.floor(min / 60), m = min % 60;
    const ap = h < 12 ? 'am' : 'pm';
    let hr = h % 12; if (hr === 0) hr = 12;
    return `${hr}:${String(m).padStart(2, '0')}${ap}`;
  }
  function hourLabel(h) {
    const ap = h < 12 ? 'AM' : 'PM';
    let hr = h % 12; if (hr === 0) hr = 12;
    return `${hr} ${ap}`;
  }

  function rangesOverlap(aStart, aLen, bStart, bLen) {
    return aStart < bStart + bLen && bStart < aStart + aLen;
  }
  function slotOpen(entries, entry, start) {
    const len = durationOf(entry);
    return !entries.some(other =>
      other.task_id !== entry.task_id &&
      isPlaced(other) &&
      rangesOverlap(start, len, clampStart(other, other.scheduled_min), durationOf(other))
    );
  }
  function nextOpenSlot(entries, entry, from = DEFAULT_PLACE) {
    const latest = latestSnappedStart(entry);
    for (let start = Math.min(from, latest); start <= latest; start += STEP) {
      if (slotOpen(entries, entry, start)) return start;
    }
    for (let start = 0; start < Math.min(from, latest + STEP); start += STEP) {
      if (slotOpen(entries, entry, start)) return start;
    }
    return clampStart(entry, from);
  }

  function suggestionMap(aiSuggest) {
    const out = new Map();
    const scheduled = aiSuggest && Array.isArray(aiSuggest.scheduled) ? aiSuggest.scheduled : [];
    scheduled.forEach(b => {
      if (!b || !Number.isFinite(Number(b.task_id))) return;
      const start = (Number(b.start_hour) || 0) * 60 + (Number(b.start_min) || 0);
      out.set(Number(b.task_id), {
        task_id: Number(b.task_id),
        start_minute: clampStart({ estimate_min: Number(b.length_min) || 5 }, start, DRAG_SNAP),
        length_min: Number(b.length_min) || 0,
        reason: typeof b.reason === 'string' ? b.reason.trim() : '',
      });
    });
    return out;
  }

  function layoutPlaced(entries) {
    const blocks = entries.filter(isPlaced).map(e => {
      const start = clampStart(e, e.scheduled_min, DRAG_SNAP);
      const length = durationOf(e);
      return { entry: e, start, end: start + length, length, lane: 0, laneCount: 1 };
    }).sort((a, b) => a.start - b.start || a.end - b.end || a.entry.task_id - b.entry.task_id);

    const groups = [];
    let group = null;
    blocks.forEach(block => {
      if (!group || block.start >= group.end) {
        group = { end: block.end, blocks: [block] };
        groups.push(group);
      } else {
        group.blocks.push(block);
        group.end = Math.max(group.end, block.end);
      }
    });

    groups.forEach(g => {
      const laneEnds = [];
      g.blocks.forEach(block => {
        let lane = 0;
        while (laneEnds[lane] > block.start) lane++;
        laneEnds[lane] = block.end;
        block.lane = lane;
      });
      const laneCount = Math.max(1, laneEnds.length);
      g.blocks.forEach(block => { block.laneCount = laneCount; });
    });
    return blocks;
  }

  function blockVars(lane, laneCount) {
    const leftPct = (lane / laneCount) * 100;
    const leftPx = (lane / laneCount) * 60;
    const widthPct = 100 / laneCount;
    const widthPx = (60 / laneCount) + 4;
    return `--lane-left:${leftPct}%;--lane-left-px:${leftPx}px;--lane-width:${widthPct}%;--lane-width-px:${widthPx}px;`;
  }

  function render(root, opts) {
    const entries = (opts && opts.entries) || [];
    const hourly = (opts && opts.hourly) || new Map();
    const aiSuggest = (opts && opts.aiSuggest) || null;
    const suggestLabel = (opts && opts.suggestLabel) || 'AI';
    const suggestUseLabel = (opts && opts.suggestUseLabel) || `Use ${suggestLabel}`;
    const suggestAllLabel = (opts && opts.suggestAllLabel) || `Apply all ${suggestLabel} times`;
    const onUpdate = (opts && opts.onUpdate) || null;
    const onDismissAi = (opts && opts.onDismissAi) || null;
    const legacyChange = (opts && opts.onChange) || function () {};
    const applyPatch = (taskId, patch) => {
      if (onUpdate) onUpdate(taskId, patch);
      else legacyChange(taskId, Object.prototype.hasOwnProperty.call(patch, 'scheduled_min') ? patch.scheduled_min : null);
    };
    const suggestions = suggestionMap(aiSuggest);
    const dismissedAi = new Set((opts && opts.dismissedAi) || []);
    dismissedAi.forEach(id => suggestions.delete(Number(id)));
    const aiMagnets = [...suggestions.values()].map(s => s.start_minute);
    const prevScroller = root.querySelector('#plan-cal-scroll');
    const prevScrollTop = prevScroller ? prevScroller.scrollTop : null;
    const active = document.activeElement && root.contains(document.activeElement) ? document.activeElement : null;
    const activeRef = active && active.dataset && active.dataset.id
      ? {
          id: active.dataset.id,
          act: active.dataset.act || '',
          kind: active.classList.contains('plan-cal-block') ? 'block'
            : active.classList.contains('plan-tray-chip') ? 'tray'
            : active.classList.contains('plan-place') ? 'place'
              : active.classList.contains('plan-ai-use') ? 'ai'
                : active.classList.contains('plan-ai-dismiss') ? 'ai-dismiss'
                  : active.classList.contains('plan-step') ? 'step'
                    : '',
        }
      : null;

    const controls = entries.map(e => {
      const suggestion = suggestions.get(e.task_id);
      const start = isPlaced(e) ? clampStart(e, e.scheduled_min, DRAG_SNAP) : null;
      const atStart = start === 0;
      const atEnd = start !== null && start >= latestSnappedStart(e);
      const difficulty = e.difficulty || 'medium';
      const aiControls = suggestion
        ? `<button type="button" class="plan-ai-use" data-act="ai-one" data-id="${e.task_id}" title="${esc(suggestion.reason || suggestUseLabel)}">${esc(suggestUseLabel)}</button>
           <button type="button" class="plan-ai-dismiss" data-act="ai-dismiss" data-id="${e.task_id}" title="Hide this suggestion">Skip</button>`
        : '';
      const ctrls = isPlaced(e)
        ? `<span class="plan-list-time">${fmtClock(start)}</span>
           <button type="button" class="plan-step ${atStart ? 'is-disabled' : ''}" data-act="minus" data-id="${e.task_id}" aria-disabled="${atStart}" ${atStart ? 'disabled' : ''} aria-label="Move ${esc(e.name)} 15 minutes earlier">−</button>
           <button type="button" class="plan-step ${atEnd ? 'is-disabled' : ''}" data-act="plus" data-id="${e.task_id}" aria-disabled="${atEnd}" ${atEnd ? 'disabled' : ''} aria-label="Move ${esc(e.name)} 15 minutes later">+</button>
           <button type="button" class="plan-step" data-act="off" data-id="${e.task_id}" aria-label="Unschedule ${esc(e.name)}">×</button>
           ${aiControls}`
        : `<button type="button" class="btn-ghost text-xs plan-place" data-id="${e.task_id}">Schedule</button>${aiControls}`;
      return `
        <div class="plan-list-row ${isPlaced(e) ? 'is-placed' : 'is-tray'}">
          <button type="button" class="plan-tray-chip ${difficulty}" draggable="true" data-id="${e.task_id}" aria-label="${isPlaced(e) ? 'Drag or focus' : 'Drag'} ${esc(e.name)}">
            <span class="plan-list-name" title="${esc(e.name)}">${esc(e.name)}</span>
            <span class="plan-list-est">${e.estimate_min || 0}m · ${esc(difficulty)}</span>
          </button>
          <div class="plan-list-ctrls">${ctrls}</div>
        </div>
        ${suggestion && suggestion.reason ? `<p class="plan-ai-reason">${esc(e.name)}: ${esc(suggestion.reason)}</p>` : ''}`;
    }).join('');

    let hourRows = '';
    for (let h = 0; h < 24; h++) {
      const hf = hourly.get(h);
      const has = hf && hf.sessions > 0;
      const pct = has ? Math.round(hf.focus_pct) : null;
      const tint = has ? `background:color-mix(in srgb, var(--sage-soft) ${pct}%, transparent);` : '';
      const workClass = h >= 7 && h < 22 ? 'is-work-hour' : 'is-off-hour';
      hourRows += `<div class="plan-cal-row ${workClass}" style="top:${h * HOUR_HEIGHT}px;${tint}" data-hour="${h}"><span class="cal-hour-label">${hourLabel(h)}</span></div>`;
    }

    const ghostBlocks = [...suggestions.values()].map(s => {
      const entry = entries.find(e => e.task_id === s.task_id);
      if (!entry) return '';
      const top = s.start_minute / 60 * HOUR_HEIGHT;
      const height = Math.max(24, durationOf(entry) / 60 * HOUR_HEIGHT);
      return `
        <div class="plan-cal-ghost" style="top:${top}px;height:${height}px" title="${esc(entry.name)} AI suggestion · ${fmtClock(s.start_minute)}${s.reason ? ' · ' + esc(s.reason) : ''}">
          <span>${esc(suggestLabel)} · ${esc(entry.name)}</span>
          <span>${fmtClock(s.start_minute)}</span>
        </div>`;
    }).join('');

    const placed = layoutPlaced(entries);
    const blocks = placed.map(b => {
      const e = b.entry;
      const top = b.start / 60 * HOUR_HEIGHT;
      const height = Math.max(24, b.length / 60 * HOUR_HEIGHT);
      const end = b.start + b.length;
      const diff = e.difficulty || 'medium';
      return `
        <div class="plan-cal-block ${esc(diff)}" tabindex="0" data-id="${e.task_id}" style="top:${top}px;height:${height}px;${blockVars(b.lane, b.laneCount)}" title="${esc(e.name)} · ${fmtClock(b.start)}–${fmtClock(end)}">
          <span class="plan-cal-block-name">${esc(e.name)}</span>
          <span class="plan-cal-block-time">${fmtClock(b.start)}</span>
          <button type="button" class="plan-block-unschedule" data-act="off" data-id="${e.task_id}" aria-label="Unschedule ${esc(e.name)}">×</button>
          <span class="plan-resize-grip" data-id="${e.task_id}" role="separator" aria-label="Resize ${esc(e.name)}"></span>
        </div>`;
    }).join('');

    const now = new Date();
    const nowMin = now.getHours() * 60 + now.getMinutes();
    const nowTop = nowMin / 60 * HOUR_HEIGHT;
    const unplacedCount = entries.filter(e => !isPlaced(e)).length;
    const trayNote = unplacedCount
      ? `<p class="text-xs" style="color:var(--text-faint);margin:8px 0 0">${unplacedCount} task${unplacedCount === 1 ? '' : 's'} not yet placed.</p>`
      : '';
    const overlapHint = placed.some(b => b.laneCount > 1)
      ? `<p class="plan-overlap-hint">Overlaps shown side by side. Saving is allowed.</p>`
      : '';
    const aiActions = suggestions.size
      ? `<div class="plan-ai-actions"><button type="button" class="btn-ghost text-xs" data-act="ai-all">${esc(suggestAllLabel)}</button></div>`
      : '';

    root.innerHTML = `
      <div class="plan-sched">
        <div class="plan-list">${controls}${aiActions}${trayNote}</div>
        <div class="plan-cal" id="plan-cal-scroll">
          ${overlapHint}
          <div class="plan-cal-grid" style="height:${24 * HOUR_HEIGHT}px">
            ${hourRows}
            ${ghostBlocks}
            <div class="plan-cal-now" style="top:${nowTop}px" aria-hidden="true"></div>
            <div class="plan-drop-preview" aria-hidden="true"></div>
            ${blocks}
          </div>
        </div>
      </div>`;

    const scroller = root.querySelector('#plan-cal-scroll');
    if (scroller) {
      if (prevScrollTop == null) {
        scroller.scrollTop = Math.max(0, Math.min(nowTop - 120, 7 * HOUR_HEIGHT));
      } else {
        scroller.scrollTop = prevScrollTop;
      }
    }
    if (activeRef && activeRef.id) {
      const selector = activeRef.kind === 'block'
        ? `.plan-cal-block[data-id="${activeRef.id}"]`
        : activeRef.kind === 'tray'
          ? `.plan-tray-chip[data-id="${activeRef.id}"]`
          : activeRef.kind === 'place'
            ? `.plan-place[data-id="${activeRef.id}"]`
            : activeRef.kind === 'ai'
              ? `.plan-ai-use[data-id="${activeRef.id}"]`
              : activeRef.kind === 'ai-dismiss'
                ? `.plan-ai-dismiss[data-id="${activeRef.id}"]`
                : activeRef.kind === 'step'
                  ? `.plan-step[data-id="${activeRef.id}"][data-act="${activeRef.act}"]`
                  : '';
      if (selector) {
        const nextFocus = root.querySelector(selector);
        if (nextFocus) nextFocus.focus({ preventScroll: true });
      }
    }

    const find = id => entries.find(x => x.task_id === id);
    const magnetsFor = id => aiMagnets.concat((opts && opts.magnets && opts.magnets[id]) || []);
    const grid = root.querySelector('.plan-cal-grid');
    const preview = root.querySelector('.plan-drop-preview');

    function minuteFromPointer(evt, entry, snap = DRAG_SNAP) {
      if (!grid) return 0;
      const rect = grid.getBoundingClientRect();
      const raw = (evt.clientY - rect.top) / HOUR_HEIGHT * 60;
      return clampStart(entry, raw, snap, magnetsFor(entry.task_id));
    }
    function resizeLengthFromPointer(evt, start) {
      if (!grid) return MIN_ESTIMATE;
      const rect = grid.getBoundingClientRect();
      const rawEnd = (evt.clientY - rect.top) / HOUR_HEIGHT * 60;
      return clampEstimate(rawEnd - start);
    }
    function showPreview(topMin, lengthMin) {
      if (!preview) return;
      preview.style.display = 'block';
      preview.style.top = `${topMin / 60 * HOUR_HEIGHT}px`;
      preview.style.height = `${Math.max(24, lengthMin / 60 * HOUR_HEIGHT)}px`;
    }
    function hidePreview() {
      if (preview) preview.style.display = 'none';
      root.querySelectorAll('.is-dragging').forEach(n => n.classList.remove('is-dragging'));
    }
    function autoScroll(evt) {
      if (!scroller) return;
      const rect = scroller.getBoundingClientRect();
      if (evt.clientY < rect.top + 36) scroller.scrollTop = Math.max(0, scroller.scrollTop - 18);
      if (evt.clientY > rect.bottom - 36) scroller.scrollTop += 18;
    }

    function startDrag(evt, entry, mode, startMin) {
      evt.preventDefault();
      const target = evt.currentTarget;
      if (target.setPointerCapture && evt.pointerId != null) target.setPointerCapture(evt.pointerId);
      target.classList.add('is-dragging');
      const original = {
        scheduled_min: Number.isFinite(entry.scheduled_min) ? entry.scheduled_min : null,
        estimate_min: entry.estimate_min,
      };
      const initialMin = Number.isFinite(startMin)
        ? startMin
        : (Number.isFinite(original.scheduled_min) ? original.scheduled_min : DEFAULT_PLACE);
      const dragState = { mode, entry, latestMin: initialMin, latestLength: entry.estimate_min };
      const move = moveEvt => {
        autoScroll(moveEvt);
        if (dragState.mode === 'resize') {
          const start = Number.isFinite(original.scheduled_min) ? original.scheduled_min : DEFAULT_PLACE;
          dragState.latestLength = resizeLengthFromPointer(moveEvt, start);
          showPreview(start, dragState.latestLength);
        } else {
          dragState.latestMin = minuteFromPointer(moveEvt, entry);
          showPreview(dragState.latestMin, durationOf(entry));
        }
      };
      const up = upEvt => {
        document.removeEventListener('pointermove', move);
        document.removeEventListener('pointerup', up);
        hidePreview();
        const calRect = scroller ? scroller.getBoundingClientRect() : null;
        const overCalendar = calRect && upEvt.clientX >= calRect.left && upEvt.clientX <= calRect.right && upEvt.clientY >= calRect.top && upEvt.clientY <= calRect.bottom;
        if (dragState.mode === 'resize') {
          applyPatch(entry.task_id, { estimate_min: dragState.latestLength });
          return;
        }
        if (!overCalendar && original.scheduled_min !== null) {
          applyPatch(entry.task_id, { scheduled_min: null, _snap: DRAG_SNAP });
          return;
        }
        if (overCalendar) applyPatch(entry.task_id, { scheduled_min: dragState.latestMin, _snap: DRAG_SNAP });
      };
      document.addEventListener('pointermove', move);
      document.addEventListener('pointerup', up);
      move(evt);
    }

    root.querySelectorAll('.plan-step, .plan-block-unschedule, .plan-ai-use, .plan-ai-dismiss, [data-act="ai-all"]').forEach(btn => {
      btn.addEventListener('click', evt => {
        evt.stopPropagation();
        const act = btn.dataset.act;
        if (act === 'ai-all') {
          suggestions.forEach(s => applyPatch(s.task_id, { scheduled_min: s.start_minute, _snap: DRAG_SNAP }));
          return;
        }
        const id = parseInt(btn.dataset.id, 10);
        const e = find(id);
        if (!e) return;
        if (act === 'off') { applyPatch(id, { scheduled_min: null }); return; }
        if (act === 'ai-one') {
          const s = suggestions.get(id);
          if (s) applyPatch(id, { scheduled_min: s.start_minute, _snap: DRAG_SNAP });
          return;
        }
        if (act === 'ai-dismiss') {
          if (onDismissAi) onDismissAi(id);
          return;
        }
        const delta = act === 'plus' ? STEP : -STEP;
        const next = clampStart(e, (e.scheduled_min || 0) + delta, STEP);
        if (next === clampStart(e, e.scheduled_min || 0, STEP)) return;
        applyPatch(id, { scheduled_min: next });
      });
    });

    root.querySelectorAll('.plan-place').forEach(btn => {
      btn.addEventListener('click', evt => {
        evt.stopPropagation();
        const id = parseInt(btn.dataset.id, 10);
        const e = find(id);
        if (e) applyPatch(id, { scheduled_min: nextOpenSlot(entries, e), _snap: STEP });
      });
    });

    root.querySelectorAll('.plan-tray-chip').forEach(chip => {
      chip.addEventListener('pointerdown', evt => {
        const e = find(parseInt(chip.dataset.id, 10));
        if (e) startDrag(evt, e, 'move', Number.isFinite(e.scheduled_min) ? e.scheduled_min : DEFAULT_PLACE);
      });
      chip.addEventListener('keydown', evt => {
        const e = find(parseInt(chip.dataset.id, 10));
        if (!e) return;
        if (evt.key === 'Enter' || evt.key === ' ') {
          evt.preventDefault();
          applyPatch(e.task_id, { scheduled_min: isPlaced(e) ? e.scheduled_min : nextOpenSlot(entries, e), _snap: isPlaced(e) ? DRAG_SNAP : STEP });
        }
      });
    });

    root.querySelectorAll('.plan-cal-block').forEach(block => {
      block.addEventListener('pointerdown', evt => {
        if (evt.target && evt.target.closest && evt.target.closest('button, .plan-resize-grip')) return;
        const e = find(parseInt(block.dataset.id, 10));
        if (e) startDrag(evt, e, 'move', e.scheduled_min);
      });
      block.addEventListener('keydown', evt => {
        const e = find(parseInt(block.dataset.id, 10));
        if (!e) return;
        if (evt.key === 'ArrowUp' || evt.key === 'ArrowDown') {
          evt.preventDefault();
          const delta = evt.key === 'ArrowDown' ? DRAG_SNAP : -DRAG_SNAP;
          applyPatch(e.task_id, { scheduled_min: clampStart(e, (e.scheduled_min || 0) + delta, DRAG_SNAP, magnetsFor(e.task_id)), _snap: DRAG_SNAP });
        } else if (evt.key === 'Delete' || evt.key === 'Backspace') {
          evt.preventDefault();
          applyPatch(e.task_id, { scheduled_min: null, _snap: DRAG_SNAP });
        }
      });
    });

    root.querySelectorAll('.plan-resize-grip').forEach(grip => {
      grip.addEventListener('pointerdown', evt => {
        evt.stopPropagation();
        const e = find(parseInt(grip.dataset.id, 10));
        if (e && isPlaced(e)) startDrag(evt, e, 'resize', e.scheduled_min);
      });
    });

    if (grid) {
      grid.addEventListener('click', evt => {
        if (evt.target.closest && evt.target.closest('.plan-cal-block, .plan-cal-ghost, button')) return;
        const first = entries.find(e => !isPlaced(e));
        if (!first) return;
        applyPatch(first.task_id, { scheduled_min: minuteFromPointer(evt, first, STEP) });
      });
    }
  }

  window.PlanCalendar = {
    render,
    _fmtClock: fmtClock,
    normalizeScheduledMin: clampStart,
    _clampEstimate: clampEstimate,
  };
})();
