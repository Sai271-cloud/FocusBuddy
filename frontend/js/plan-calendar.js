(function () {
  const HOUR_HEIGHT = 52;
  const DAY_MIN = 24 * 60;
  const STEP = 15;
  const DRAG_SNAP = 5;
  const DEFAULT_PLACE = 9 * 60;
  const MIN_ESTIMATE = 10;
  const MAX_ESTIMATE = 120;

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
  function clampStart(e, m, snap = STEP) {
    let next = clamp(snapTo(m, snap), 0, latestSnappedStart(e, snap));
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
    const onUpdate = (opts && opts.onUpdate) || null;
    const legacyChange = (opts && opts.onChange) || function () {};
    const applyPatch = (taskId, patch) => {
      if (onUpdate) onUpdate(taskId, patch);
      else legacyChange(taskId, Object.prototype.hasOwnProperty.call(patch, 'scheduled_min') ? patch.scheduled_min : null);
    };
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
              : active.classList.contains('plan-step') ? 'step'
                : '',
        }
      : null;

    const controls = entries.map(e => {
      const start = isPlaced(e) ? clampStart(e, e.scheduled_min, DRAG_SNAP) : null;
      const atStart = start === 0;
      const atEnd = start !== null && start >= latestSnappedStart(e);
      const difficulty = e.difficulty || 'medium';
      const timeControls = isPlaced(e)
        ? `<div class="plan-time-controls">
             <span class="plan-list-time">${fmtClock(start)}</span>
             <button type="button" class="plan-step ${atStart ? 'is-disabled' : ''}" data-act="minus" data-id="${e.task_id}" aria-disabled="${atStart}" ${atStart ? 'disabled' : ''} aria-label="Move ${esc(e.name)} 15 minutes earlier">−</button>
             <button type="button" class="plan-step ${atEnd ? 'is-disabled' : ''}" data-act="plus" data-id="${e.task_id}" aria-disabled="${atEnd}" ${atEnd ? 'disabled' : ''} aria-label="Move ${esc(e.name)} 15 minutes later">+</button>
             <button type="button" class="plan-step" data-act="off" data-id="${e.task_id}" aria-label="Unschedule ${esc(e.name)}">×</button>
           </div>`
        : `<div class="plan-time-controls"><button type="button" class="btn-ghost text-xs plan-place" data-id="${e.task_id}">Schedule</button></div>`;
      return `
        <div class="plan-list-row ${isPlaced(e) ? 'is-placed' : 'is-tray'}">
          <div class="plan-list-main">
            <button type="button" class="plan-tray-chip ${difficulty}" draggable="true" data-id="${e.task_id}" aria-label="${isPlaced(e) ? 'Drag or focus' : 'Drag'} ${esc(e.name)}">
              <span class="plan-list-name" title="${esc(e.name)}">${esc(e.name)}</span>
              <span class="plan-list-est">${e.estimate_min || 0}m · ${esc(difficulty)}</span>
            </button>
          </div>
          <div class="plan-list-ctrls">${timeControls}</div>
        </div>`;
    }).join('');

    let hourRows = '';
    for (let h = 0; h < 24; h++) {
      const workClass = h >= 7 && h < 22 ? 'is-work-hour' : 'is-off-hour';
      hourRows += `<div class="plan-cal-row ${workClass}" style="top:${h * HOUR_HEIGHT}px;" data-hour="${h}"><span class="cal-hour-label">${hourLabel(h)}</span></div>`;
    }

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

    root.innerHTML = `
      <div class="plan-sched">
        <div class="plan-list">${controls}${trayNote}</div>
        <div class="plan-cal" id="plan-cal-scroll">
          ${overlapHint}
          <div class="plan-cal-grid" style="height:${24 * HOUR_HEIGHT}px">
            ${hourRows}
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
                : activeRef.kind === 'step'
                  ? `.plan-step[data-id="${activeRef.id}"][data-act="${activeRef.act}"]`
                  : '';
      if (selector) {
        const nextFocus = root.querySelector(selector);
        if (nextFocus) nextFocus.focus({ preventScroll: true });
      }
    }

    const find = id => entries.find(x => x.task_id === id);
    const grid = root.querySelector('.plan-cal-grid');
    const preview = root.querySelector('.plan-drop-preview');

    function minuteFromPointer(evt, entry, snap = DRAG_SNAP) {
      if (!grid) return 0;
      const rect = grid.getBoundingClientRect();
      const raw = (evt.clientY - rect.top) / HOUR_HEIGHT * 60;
      return clampStart(entry, raw, snap);
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
    function hideDropPreview() {
      if (preview) preview.style.display = 'none';
    }
    function clearDragState() {
      hideDropPreview();
      root.querySelectorAll('.is-dragging').forEach(n => n.classList.remove('is-dragging'));
    }
    function pointerOverCalendar(evt) {
      const calRect = scroller ? scroller.getBoundingClientRect() : null;
      return !!(calRect &&
        evt.clientX >= calRect.left &&
        evt.clientX <= calRect.right &&
        evt.clientY >= calRect.top &&
        evt.clientY <= calRect.bottom);
    }
    function autoScroll(evt) {
      if (!scroller) return;
      const rect = scroller.getBoundingClientRect();
      if (evt.clientY < rect.top + 36) scroller.scrollTop = Math.max(0, scroller.scrollTop - 18);
      if (evt.clientY > rect.bottom - 36) scroller.scrollTop += 18;
    }
    function createDragFloat(entry, sourceRect) {
      const diff = ['easy', 'medium', 'hard'].includes(entry.difficulty) ? entry.difficulty : 'medium';
      const width = Math.min(260, Math.max(180, sourceRect ? sourceRect.width : 210));
      const height = Math.max(32, durationOf(entry) / 60 * HOUR_HEIGHT);
      const node = document.createElement('div');
      node.className = `plan-drag-float ${diff}`;
      node.style.width = `${width}px`;
      node.style.height = `${height}px`;
      node.innerHTML = `
        <span class="plan-drag-float-name">${esc(entry.name)}</span>
        <span class="plan-drag-float-time">${durationOf(entry)}m</span>`;
      document.body.appendChild(node);
      return node;
    }
    function moveDragFloat(node, evt) {
      if (!node) return;
      node.style.transform = `translate3d(${evt.clientX + 14}px, ${evt.clientY + 12}px, 0)`;
    }
    function setDragFloatTime(node, entry, startMin) {
      if (!node) return;
      const time = node.querySelector('.plan-drag-float-time');
      if (!time) return;
      time.textContent = Number.isFinite(startMin)
        ? `${fmtClock(startMin)} · ${durationOf(entry)}m`
        : `${durationOf(entry)}m`;
    }
    function removeDragFloat(node) {
      if (node && node.parentNode) node.parentNode.removeChild(node);
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
      const floatNode = mode === 'move' ? createDragFloat(entry, target.getBoundingClientRect()) : null;
      const move = moveEvt => {
        autoScroll(moveEvt);
        if (dragState.mode === 'resize') {
          const start = Number.isFinite(original.scheduled_min) ? original.scheduled_min : DEFAULT_PLACE;
          dragState.latestLength = resizeLengthFromPointer(moveEvt, start);
          showPreview(start, dragState.latestLength);
        } else {
          const overCalendar = pointerOverCalendar(moveEvt);
          dragState.latestMin = overCalendar ? minuteFromPointer(moveEvt, entry) : dragState.latestMin;
          setDragFloatTime(floatNode, entry, overCalendar ? dragState.latestMin : null);
          moveDragFloat(floatNode, moveEvt);
          if (overCalendar) showPreview(dragState.latestMin, durationOf(entry));
          else hideDropPreview();
        }
      };
      const up = upEvt => {
        document.removeEventListener('pointermove', move);
        document.removeEventListener('pointerup', up);
        document.removeEventListener('pointercancel', cancel);
        clearDragState();
        removeDragFloat(floatNode);
        const overCalendar = pointerOverCalendar(upEvt);
        if (dragState.mode === 'resize') {
          applyPatch(entry.task_id, { estimate_min: dragState.latestLength });
          return;
        }
        if (!overCalendar && original.scheduled_min !== null) {
          applyPatch(entry.task_id, { scheduled_min: null, _snap: DRAG_SNAP });
          return;
        }
        if (overCalendar) applyPatch(entry.task_id, { scheduled_min: minuteFromPointer(upEvt, entry), _snap: DRAG_SNAP });
      };
      const cancel = () => {
        document.removeEventListener('pointermove', move);
        document.removeEventListener('pointerup', up);
        document.removeEventListener('pointercancel', cancel);
        clearDragState();
        removeDragFloat(floatNode);
      };
      document.addEventListener('pointermove', move);
      document.addEventListener('pointerup', up);
      document.addEventListener('pointercancel', cancel);
      move(evt);
    }

    root.querySelectorAll('.plan-step, .plan-block-unschedule').forEach(btn => {
      btn.addEventListener('click', evt => {
        evt.stopPropagation();
        const act = btn.dataset.act;
        const id = parseInt(btn.dataset.id, 10);
        const e = find(id);
        if (!e) return;
        if (act === 'off') { applyPatch(id, { scheduled_min: null }); return; }
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
          applyPatch(e.task_id, { scheduled_min: clampStart(e, (e.scheduled_min || 0) + delta, DRAG_SNAP), _snap: DRAG_SNAP });
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
        if (evt.target.closest && evt.target.closest('.plan-cal-block, button')) return;
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
