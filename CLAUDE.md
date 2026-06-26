# Focus Buddy — Project Memory (CLAUDE.md)

> This is the project memory for Focus Buddy. Codex reads AGENTS.md, and Claude Code reads
> CLAUDE.md, at the start of sessions in this repo. Keep both files specific, up to date,
> and in sync as the project changes.

## About me
- I'm a **beginner coder**. Explain decisions in plain English before making big changes, and keep
  code readable enough that I can explain it out loud
- I prefer **simple, working solutions** over clever or over-engineered ones. When in doubt, do the
  smaller thing and tell me the tradeoff.

## How I like you to workthou
- Every single time you put something into the terminal please say ok reference my name first(My name is Sai). ex. "Hello Sai, -----"
- Before a big change, explain the plan and which files will change, then wait for my OK.
- **Don't overwrite or delete important files without explaining first.**
- Make small, focused changes. Don't refactor unrelated code or add dependencies without asking.
- When something breaks: reproduce it first, fix the root cause, then tell me what caused it.
- If you learn something I'll need again, record it per the self-improvement rule near the bottom
  of this file.
- When updating either `AGENTS.md` or `CLAUDE.md`, update the other file in the same change so both
  agents follow the same project memory. If a rule is intentionally tool-specific, label it clearly.
- After finishing a feature, debugging session, or review, remind Sai to ask for a handoff and run
  `/compact` before starting unrelated work.
- Don't assume — if a current fact (a model name, a price, an API) might have changed, check it.

## Guardrails — mistakes coding agents make
Coding agents (you included) have a few predictable failure modes. These rules exist to catch them —
follow them even when a faster path is tempting.

- **Stop after two failures; don't thrash.** If the same command, search, or fix fails twice, stop —
  don't keep trying variations on it. Tell me what you tried, what you expected, and what actually
  happened, then wait. Two failures of the same kind means ask a human, not try harder. Grinding
  through attempts on a wall just burns time and tokens.
- **Never fix by duplicating code.** Don't copy a block and tweak the copy to solve a problem. If
  you're about to duplicate logic, stop and either reuse the existing function or tell me why a
  shared one won't work — two near-identical blocks is a bug waiting to happen. Same for shallow
  patches: fix the actual cause, not just the visible symptom.
- **Be a real reviewer, not a cheerleader.** When I ask you to check or review your own work, don't
  default to "looks good" or "excellent." Actively look for what could break, list the weak spots,
  and flag anything you can't verify yourself — tell me where the code is *weakest*, not that it's
  great. For important changes I'll often review in a separate fresh session that has no memory of
  writing the code, because a clean read catches bugs self-review misses; help that by keeping
  changes small enough to review that way.

## Project overview
Focus Buddy is a web-based productivity + self-reflection app that estimates how much of a work
session a user is actually focused. The user makes a task, starts a session, and the app tracks
time in four states — **Focused, Distracted, Uncertain, Away** — then shows analytics so they learn
what distracts them.

- **Audience:** students and people building better focus habits.
- **Feel:** calm, polished, Sunsama-inspired (not a copy) — soft colors, compact task cards, a clean
  dashboard.

## Architecture at a glance
Two halves, split by concern:
- **Frontend (browser)** does everything real-time: webcam capture, the timer, charts, running
  totals, the live focus state, and light on-device CV labels that don't need a big model
  (face/presence/eyes/head direction now; posture later).
- **Backend (FastAPI)** is the data + AI layer: it stores tasks and finished sessions + their
  per-state totals, serves analytics, and **proxies the AI calls** — it sends the webcam frame, the
  task, and (opt-in) the active URL/title to Gemini and returns the focus state. Keeping the AI
  calls server-side is also where the API key stays (never in frontend code).

## Tech Stack
Grouped by **where it runs** — frontend (real-time UI + light on-device CV), backend (data + the
AI calls).

**Backend (Python)**
- **FastAPI** — the web framework serving the API (create tasks, save sessions, return analytics).
  Picked for being clean, beginner-friendly, and for its auto-generated `/docs` page (handy in a
  demo).
- **uvicorn** — the server that runs the FastAPI app: `uvicorn backend.main:app --reload`.
- **SQLAlchemy** — lets the code talk to the database from Python instead of raw SQL; it defines the
  data models (Task, FocusSession).
- **SQLite** — the database itself: a single file, zero setup. Right for the MVP; only consider
  Postgres later if hosted multi-user is ever needed.
- **Pydantic** — validates request/response data and powers the clean `/docs` (ships with FastAPI).

**Frontend (browser)**
- **Plain HTML / CSS / JavaScript** — no framework, no build step, so every line is explainable.
- **Tailwind CSS** (Play CDN during the MVP) — utility classes for the calm, polished look without a
  build step. Only genuinely custom styles go in `css/styles.css`.
- **Chart.js** (CDN) — the focus-breakdown chart and the analytics visuals.

**Computer vision**
- **Gemini (vision)** — the focus state itself comes from a Gemini call: the backend sends the
  sampled webcam frame + task (+ opt-in URL/title) and Gemini returns one of the four states. This
  is the core AI signal.
- **MediaPipe Tasks for Web** — Google's CV library running locally in the browser. Face Landmarker
  currently turns landmarks into semantic labels (eyes open/closed, head facing/away/down, face
  present). Pose Landmarker for the posture coach is planned for Phase 2. This part is genuinely
  on-device — no big model needed.
- **`getUserMedia`** — the browser API that turns on the webcam.



**Not a library — something I write**
- **FocusEngine** — one function that returns the app's focus state. In the current MVP it is
  intentionally thin: it wraps the Gemini focus call and returns one focus state. Later, this is
  where the app can add weighted scoring, override rules, time smoothing, website signals, posture,
  and other signals behind the same interface. Don't look for a package for this — it's my own code.

**Stack rules**
- Don't silently swap the stack. Moving to Next.js/React, Postgres/Supabase, etc. is a deliberate,
  large change — explain the tradeoffs and wait for my OK first.
- Don't add new dependencies or frameworks without asking.

## Folder structure  *(current — keep updated)*
This map should match what is actually in the repo. Filenames marked ✓ are referenced by the skills;
the rest are conventional and may change. **If files or folders are added, removed, renamed, or moved,
update this map in both `AGENTS.md` and `CLAUDE.md`. A map that describes the old structure is worse
than none, because it misleads.**

```
focus-buddy/
  AGENTS.md                  # Codex project memory; keep synced with CLAUDE.md
  CLAUDE.md                  # Claude Code project memory; keep synced with AGENTS.md
  README.MD                  # what it is, how to run, how it works
  requirements.txt           # Python dependencies for backend/local checks
  .agents/skills/            # Codex task-specific skills
  .codex/
    agents/                  # Codex custom read-only reviewer agents
    hooks.json               # Codex project hooks that call the shared agent hook scripts
  .claude/
    agents/                  # Claude Code project read-only reviewer subagents
    settings.json            # Claude Code project settings
    settings.local.json      # local Claude Code settings
    hooks/                   # local Claude Code safety/check hooks
    skills/                  # Claude Code task-specific skills
      privacy-guard/data-flow.md  # honest "what data goes where" reference (for demo Q&A)
  docs/
    agent-subagents.md       # when to use the project review agents in Claude and Codex
    project-lessons.md       # shared long-term lesson log for Codex + Claude Code
    session-handoff-2026-06-25-debug-fixes.md  # prior handoff for debug/UI fix work
    session-handoff-2026-06-26-planner-modal-current-plan.md  # latest handoff for planner modal/current-plan work
  tools/
    check.ps1                # manual project sanity check for agents and local setup
    serve.ps1                # starts backend + frontend for human-run browser smoke tests
    stop-serve.ps1           # stops only the helper-owned server PIDs
    agent-hooks/             # shared PowerShell hook scripts used by Claude Code + Codex
  tests/
    test_chunk_d_planning.py # backend unit coverage for plan-vs-reality, calibration, reschedule
  promptlab/                 # prompt testing harness; out/ is generated and ignored
  v0-export/                 # archived/reference generated UI export; ignored by default
  backend/
    main.py                  # ✓ FastAPI app + routes (thin handlers)
    schemas.py               # ✓ Pydantic request/response models
    crud.py                  # ✓ SQLAlchemy query helpers (one job each)
    models.py                # SQLAlchemy models: Task, FocusSession, UserProfile, Observation, HourlyFocus
    database.py              # DB connection/session setup (+ seeds the Observation starters)
    focus_buddy.db           # the SQLite file (created on first run)
  frontend/
    index.html               # homepage — task list + add a task
    tracker.html             # live session: timer, webcam, chart, totals
    analytics.html           # saved-session analytics
    plan.html                # Today's Plan — optional 4-phase planning wizard + schedule calendar
    css/
      styles.css             # ✓ only genuinely custom styles (Tailwind via CDN otherwise)
    js/
      api.js                 # ✓ all fetch() calls to the backend live here
      plan-calendar.js       # Today's Plan schedule calendar: placement, drag/resize, AI ghosts
      planning-insights.js   # shared plan helpers: local day bounds, plan parsing, focus goal/streak math
      session-replay.js      # builds replay UI from saved timeline_json + journal_json
      focus-engine.js        # the FocusEngine seam — wraps the Gemini focus call
      focus-detector.js      # webcam loop: samples a frame → Gemini; reads face-metrics + activity
      face-metrics.js        # on-device MediaPipe Face Landmarker → eye/head/presence LABELS
  extension/                 # Chrome/Edge MV3 extension — website-awareness signal
    manifest.json            # MV3 manifest (tabs permission, host_permissions → :8000)
    background.js            # reports active-tab URL to POST /activity
    README.md                # load-unpacked instructions
```

## Running it  *(current)*
Two processes — backend and frontend — on two ports. They're separate, which is exactly why
`CORSMiddleware` has to allow the frontend's origin (see the backend-endpoint / debug skills).

**Backend** (from the project root):

```
uvicorn backend.main:app --reload
```

Serves the API at `http://127.0.0.1:8000`, with interactive docs at `http://127.0.0.1:8000/docs`.

**Frontend** — serve it over http, don't just double-click the HTML. Opening it as a `file://` path
breaks two things: the webcam (`getUserMedia` needs a secure context — `localhost` counts, `file://`
doesn't) and the `fetch()` calls to the backend. Simplest option, since Python's already here, from
the `frontend/` folder:

```
python -m http.server 5500
```

Then open `http://localhost:5500`. (Port number is a suggestion — any free port is fine, as long as
the backend's CORS settings allow it.) This requires a working Python. If this machine says there is
no working Python, fix/recreate `.venv` or use another static file server, but still serve the
frontend over HTTP rather than opening the HTML as `file://`.

**Agent / smoke-test workflow**
- Default verification should be in-process, with no live server needed:

```
python -m unittest discover -s tests
```

  For ad-hoc API checks, prefer FastAPI `TestClient` in-process instead of opening a port, e.g.
  `python -c "from fastapi.testclient import TestClient; from backend.main import app; print(TestClient(app).get('/docs').status_code)"`.
- For a real browser smoke test, Sai runs `tools\serve.ps1` in his own terminal (or `! tools\serve.ps1`
  if the shell output should land in the session). The agent then confirms `http://127.0.0.1:8000/docs`
  is up and runs Playwright against `http://localhost:5500`. Sai runs `tools\stop-serve.ps1` afterward.
- Do not improvise `Start-Process` or background long-lived servers from inside the agent shell for
  browser smoke tests. Agent-launched server children can be reaped or blocked; use the helper run by
  a human instead.
- Leave unrelated dirty worktree changes untouched (for example, a pre-existing `backend/main.py`
  edit). Mention them and move on; that observation is not an error.

## Where I want to take it (direction)
A multi-feature tool, built in **phases where each phase is a working demo on its own**:
1. **Core MVP** — tasks, sessions, live timer, webcam preview, AI focus detection, live chart, save,
   basic analytics. (This works today.)
2. **Smart focus (the AI core)** — fuse multiple signals (webcam + task + opt-in website URL/title)
   into ONE focus decision via the FocusEngine seam, with Gemini doing the semantic judgment.
3. **AI debrief** — at the end of a session / the daily & weekly unwind, the AI reasons over the
   session data and gives specific, actionable coaching. (This is the demo headline.)
4. **Posture coach** — MediaPipe Pose, with our own trained classifier for good vs. bad posture.
5. **Planning + daily summaries** — a "today's plan" view and a recap from saved sessions.

### Build the FocusEngine seam from day one
Even though Phase 1 has only one signal (the webcam), build the seam now: the rest of the app asks a
single function "what's my focus state?" and never reads landmarks or model output directly. In
Phase 1 that function just wraps the Gemini focus call. Later phases add the website signal, posture,
and (post-hackathon) more signals *behind* that same function, so the UI never has to be rewritten to
add one. Don't "simplify" this away by wiring the model call straight into the UI — the seam is the point.

## Security & honest disclosure
Privacy is no longer the headline pitch, but two rules still hold — these are basic hygiene, not
positioning:
- **Keep API keys on the backend, never in frontend code; never commit `.env`.**
- **Be honest in the UI about what's sent where.** The app sends webcam frames + the task and
  (opt-in) the active URL/title to Gemini to detect focus. Say so plainly; don't claim data stays on
  the device.

## Platform limits (what a browser app can't do)
These are real limits of the browser — know them so you don't promise what the build can't do.
- A web page can only see activity **inside its own tab**. It cannot read system-wide keyboard,
  mouse, or which app/window is focused.
- The **browser build** therefore can't see other apps (VS Code, Figma, etc.) — only the active tab
  URL via the extension. Full system-wide awareness (mouse/keyboard counts, active app) needs a
  **desktop app (Electron/Tauri)**.
- **Desktop is the post-hackathon roadmap, not the 12-day build** — re-platforming under time
  pressure is the bigger risk; we pitch desktop as the next step and demo the working browser app.
- Also out of scope for the hackathon: user accounts/login, multi-device sync, social/leaderboard
  features, and a mobile app.

## Self-improvement rule
When you fix a bug, work out how part of this project actually behaves, or I correct you on
something, write the lesson down so it isn't lost when the chat ends. Put it where a future
session will actually look:

- **A task-specific lesson** (browser CV, a backend pattern, a privacy gotcha) → add it to the
  matching skill in both `.agents/skills/` and `.claude/skills/` when both exist — e.g. a
  webcam-loading fix goes in the browser-vision skill, an endpoint convention goes in the
  backend-endpoint skill.
- **A project-wide lesson** (a run command, a folder decision, something that spans areas) → add it
  at the bottom of the file where recent lessons header is

Write it as a specific instruction a future session can act on, not a vague reminder — e.g. "gate
the detection loop behind the MediaPipe ready-promise" beats "be careful with the webcam." If a fix
revealed something this file states wrongly, fix the file too.

## Recent lessons
# Project Lessons

Shared long-term lessons for Focus Buddy. Keep this file as the single project-wide lesson log for both Codex and Claude Code.

When adding a new project-wide lesson, add it under `## Recent lessons` with the newest lesson first. Keep the format specific enough that a future session can act on it.

## Recent lessons
Specific things learned while building — newest first. Empty until the first real one; don't pad it.

Format for each entry:
- **Lesson:** <the rule, as an instruction>
  **Why it matters:** <what broke, or what it prevents>
  **Where it applies:** <file or area, e.g. focus-detector.js>

- **Lesson:** For local verification, agents should default to in-process checks (`python -m unittest
  discover -s tests` or FastAPI `TestClient`) and only use live servers for browser-level smoke tests;
  when live servers are needed, Sai runs `tools\serve.ps1` from his own terminal and later stops
  helper-owned PIDs with `tools\stop-serve.ps1`. Agents must not improvise `Start-Process`
  background servers for smoke tests.
  **Why it matters:** background servers launched from an agent shell can be reaped, blocked, or
  broken by quoting/environment differences, which causes repeated false blockers before Playwright
  can verify the UI.
  **Where it applies:** `tools/{serve,stop-serve}.ps1`, `AGENTS.md`, `CLAUDE.md`, browser smoke tests,
  PowerShell verification.

- **Lesson:** Keep environment cleanup facts concrete: `.venv.broken-*` folders are old broken
  virtualenv backups and can be deleted after the active `.venv` is verified; the current intended
  venv uses Python 3.13. When testing JavaScript snippets from PowerShell, avoid fragile inline
  `node -e "..."` quoting for assertions; use PowerShell-native checks or a temporary script file
  instead. Keep `.gitattributes` as the repo-level fix for recurring LF-to-CRLF warnings rather
  than changing global Git config or renormalizing the whole repo casually.
  **Why it matters:** future sessions can otherwise misread backup folders as active Python
  problems, waste time on shell quoting failures that are not app bugs, or create noisy line-ending
  diffs while trying to silence Git warnings.
  **Where it applies:** `.venv*`, `.gitattributes`, PowerShell verification commands,
  `AGENTS.md`, `CLAUDE.md`.

- **Lesson:** Chunk D planning is one matched loop, not separate widgets: Today/tracker can highlight
  the recommended-first task as a suggestion, tracker sessions can carry a pre-session `intention`,
  daily unwind can save `plan_reality_json`, and estimate calibration/reschedule must reuse the same
  plan-vs-reality matching instead of inventing a second matcher. Keep the handoff suggestion-only:
  never auto-start, reorder, or force a task because it came from the plan.
  **Why it matters:** the plan -> work -> reflect loop only stays trustworthy if planned task IDs,
  actual sessions, intentions, and daily recaps use the same local-day boundaries; separate matching
  paths create conflicting scorecards and misleading calibration warnings.
  **Where it applies:** `backend/{models,schemas,crud,database,main}.py`,
  `frontend/{index,tracker,analytics,plan}.html`, `frontend/js/{api,planning-insights,plan-calendar}.js`.

- **Lesson:** In Today's Plan, keep schedule-placement changes and estimate changes separate all
  the way through the save path: pass a 5-minute snap marker for drag, AI-time, and keyboard-nudge
  moves; use 15-minute snapping only for Schedule and +/- stepper controls; and clear saved
  `advice_json` on autosave only when task/estimate/available-time changes make advice stale.
  Backend saved `plan_json` must validate each row through `PlanEntry` so saved plans and
  `/plan/advice` reject the same malformed entries.
  **Why it matters:** the wrapper around `PlanCalendar.normalizeScheduledMin` can silently re-snap
  5-minute moves to 15 minutes, stale AI ghost blocks can return after resize/estimate edits, and
  saved plans can otherwise accept data the direct advice API rejects.
  **Where it applies:** `frontend/{plan.html,js/plan-calendar.js}`, `backend/{schemas,main}.py`.

- **Lesson:** Treat Today's Plan AI advice as tied to the task/estimate/difficulty/available-time
  snapshot, but not to manual schedule placement: moving blocks leaves AI suggestions comparable and
  must preserve saved advice. Task, estimate, difficulty, or available-time edits make saved advice stale;
  save fresh `advice_json` only after regenerating through the visible Generate/Regenerate path, and send
  `advice_json: ""` only when clearing truly stale saved advice. Keep schedule placement logic in
  `frontend/js/plan-calendar.js`: clamp starts to the latest same-day slot, keep stepper moves snapped to
  15 minutes, keep drag moves snapped to 5 minutes, preserve scroll/focus across rerenders, and auto-save
  placement/resize changes with advice preserved. Planner load failures must show a backend-running error,
  not an empty "No tasks yet" state. Backend planner saves must validate `plan_json`, repair older
  `daily_plans` tables that lack `advice_json`, dedupe `/plan/advice` entries by `task_id`, reject payloads
  over the planner limit instead of silently slicing, reject advice totals over one day, pack late schedules
  earlier instead of clamping several blocks to `23:59`, and gate `general_advice` unless About-me or
  confirmed patterns provide a real basis.
  **Why it matters:** stale advice can silently return after edits, backend outages can look like an empty
  task list, old Chunk A databases can miss the advice column, and weak planner enforcement lets corrupt
  or misleading AI output get saved, and schedule edits should not erase useful AI comparisons.
  **Where it applies:** `frontend/{plan.html,js/plan-calendar.js}`, `backend/{database,schemas,main}.py`.

- **Lesson:** **"Today's Plan" (Phase 5) Chunk A is built** — an OPTIONAL `frontend/plan.html` 4-phase
  wizard (pick tasks → estimate+difficulty → AI-advice placeholder → confirm/save) on a new
  `daily_plans` table (`DailyPlan` model; `create_all` makes it, no migration). Routes: `GET
  /plan/{period_key}` returns **null/200 when absent, NEVER 404** (so `api.js`'s throw-on-non-200
  `requestJson` treats "no plan" as empty, not an error); `POST /plan` is a **preserve-on-None upsert**
  like `upsert_work_period` (`available_min`/`plan_json`/`advice_json` all Optional, so a plan-only and
  an advice-only save don't clobber each other); `DELETE /plan/{period_key}`. `period_key` is the
  **frontend-computed local YYYY-MM-DD**; a task appears **at most once per plan** (dedupe on add). The
  wizard is **opt-in and freely abandonable** (persistent ✕ + Escape → Today, "Not today" link, nothing
  saved until the explicit Save) — the landing-page redirect was DROPPED. Sliders + segmented difficulty
  styled in `styles.css` (`.fb-range`, `.seg`, `.budget-meter`); Plan is the first nav item on
  `index.html`+`analytics.html` only (NOT tracker.html — it has a session-only header). Chunk B is **built**: `POST /plan/advice` (planner-specific — cold-start fallback, sample-count
  gating, and deterministic schedule validation that dedupes, drops hallucinated tasks, and packs
  non-overlapping slots using the real estimates) returns `{summary, cold_start, scheduled[],
  over_plan_note, general_advice[]}`, shown as a manual Generate → visual timeline (each block shaded
  by that hour's `focus_pct`) and saved into `advice_json`; its data flow is disclosed in
  `privacy-guard/data-flow.md`. Chunk C (next) = plan-vs-reality (match by `task_id` within the local
  day). Verified A+B: crud/validation by unit + over-HTTP tests (preserve-on-None both ways; live
  Gemini advice with correct cold-start hardest-first scheduling), and Playwright wizard end-to-end
  (save, rehydrate/edit, clear, Generate→timeline), 0 real console errors (favicon aside).
  **Why it matters:** turns the dormant hourly profile + Pattern Memory into forward planning; the
  null-not-404, Optional-upsert, dedupe, and local-day rules were locked up front (from a Codex
  adversarial review) so Chunks B/C don't have to rewrite the data shape.
  **Where it applies:** `backend/{models,schemas,crud,main}.py`, `frontend/plan.html`,
  `frontend/js/api.js`, `frontend/css/styles.css`, `frontend/{index,analytics}.html`.

- **Lesson:** `frontend/js/session-replay.js` must NOT synthesize an `uncertain` state when a session
  has saved `seconds_*` totals but empty `timeline_json`/`journal_json` (legacy or partial-save rows).
  It now falls back to an **aggregate-only** bar built from the four second-counters (captioned
  "Aggregate only — no minute-by-minute timeline"), shows the empty-state only when even the counters
  are zero, and extends the first real state back to t=0 for the pre-first-event gap (instead of
  defaulting that gap to uncertain). Verified with a node harness (focused + empty arrays → a focused
  bar, NOT all-uncertain).
  **Why it matters:** the old code rendered a 100%-focused session as 100% Uncertain — a
  self-contradiction that misrepresents real data (caught by a Codex adversarial review).
  **Where it applies:** `frontend/js/session-replay.js`.

- **Lesson:** If `tools/check.ps1` says no working Python and `.venv\pyvenv.cfg` points at
  `AppData\Local\Python\pythoncore-3.14-64`, recreate `.venv` from a normal user install of Python
  3.13/3.12 and reinstall `requirements.txt`; do not try to repair the redirector venv in place.
  **Why it matters:** the old venv depended on an inaccessible Python install, so both
  `.venv\Scripts\python.exe` and `python` failed before checks could compile the backend.
  **Where it applies:** `.venv`, `requirements.txt`, `tools/check.ps1`.

- **Lesson:** Focus Buddy review agents live in the native project-agent format for each tool:
  Claude Code uses `.claude/agents/*.md` and Codex uses `.codex/agents/*.toml`. Keep these agents
  read-only by default and use them for review/audit findings, not implementation. `.agents/skills`
  and `.claude/skills` remain workflow guidance that agents or main sessions can read before
  reviewing a domain.
  **Why it matters:** skills and subagents solve different problems; mixing them up would make
  reviewers harder to invoke and easier to accidentally turn into editors.
  **Where it applies:** `.claude/agents/`, `.codex/agents/`, `.agents/skills/`,
  `.claude/skills/`, `docs/agent-subagents.md`, `tools/check.ps1`.

- **Lesson:** The three **coaching** prompts (`debrief_session`, `daily_unwind`, `weekly_unwind` in
  `backend/main.py`) were rebuilt through a rigorous `promptlab/` sweep (synthetic personas → real
  Gemini → independent evidence-trained grader subagents, iterated to convergence at "v12"). Two
  durable results were ported into `main.py`: **(1) the v12 prompt text** — its lead principle is
  SPECIFICITY ("catch a concrete moment in THIS person's data, then suggest a different move THERE";
  generic advice is the failure mode), plus a DOMINANT-problem lever menu (a site blocker is ONLY for a
  real repeated phone/scroll pattern — never the default for a fade, interruption, or self-corrector),
  few-shot EXAMPLES, and uncertain≠fatigue. **(2) Deterministic code enforcement**, because flash-lite
  only follows mechanical rules ~2/3 of the time: `_scrub`/`_scrub_response` strip banned openers and any
  echoed internal guide line (`_LEAK`); `_session_gated`/`_daily_gated`/`_weekly_flags` blank coaching
  fields on low-signal sessions/days/weeks; and the daily **honesty line** (`_daily_dominant_line`) and
  weekly **trend** (`_weekly_trend_line`) are COMPUTED IN CODE and injected as fact (the model is told
  "do NOT quote" them; the scrub removes echoes). Each coaching endpoint now does
  `_enforce_*(_parse_*(response.text), gctx)`. The dead `reflective_question` field was removed from
  `schemas.DebriefResponse`, `_parse_debrief`, and `tracker.html`. **Model seam:** coaching uses
  `COACHING_MODEL = os.getenv("COACHING_MODEL", "gemini-3.1-flash-lite")`, kept SEPARATE from
  `GEMINI_MODEL` (the per-sample `/focus/analyze` hot path and the `/learn` call stay flash-lite). On the
  free-tier key, **`gemini-3.1-pro-preview` 429s immediately (no free quota — needs billing)** and
  **`gemini-3.5-flash` is capped at ~20 requests/day** (and 503s under load), so flash-lite is the
  reliable default; set `COACHING_MODEL=gemini-3.1-pro-preview` in `.env` after enabling billing to
  upgrade all three with no code change. Verified at code level (compile, app import, 30 enforcement/
  gate/parser assertions). **STILL PENDING (was quota-blocked):** the live-Gemini end-to-end
  (Playwright) smoke test, and the `gemini-3.5-flash` worst-offender comparison — both deferred to a
  quota reset; `promptlab/` (incl. `compare_models.py`) is kept until that's done, then deleted.
  **Why it matters:** the coaching is the product's voice; this is the converged, evidence-grounded
  version with the rules that MUST hold enforced in code so a weaker model can't silently violate them,
  and a one-env-var path to a stronger model when billing allows.
  **Where it applies:** `backend/main.py` (the three coaching endpoints + the `_scrub`/gate/inject/
  `_enforce_*` block + `COACHING_MODEL`), `backend/schemas.py`, `frontend/tracker.html`, `promptlab/`.

- **Lesson:** Project skills must use an exact `SKILL.md` filename in both `.agents/skills/` and
  `.claude/skills/`; reference-only folders such as `privacy-guard` still need a small `SKILL.md`
  that points to their deeper docs. Keep generated/context-heavy folders such as `promptlab/out/`
  `.pnpm-store/`, and archived exports ignored, and use `tools/check.ps1` as the quick sanity check
  for skill discovery, mirrored memory, JSON config, Python syntax, and frontend secret scans. Folder
  maps in `AGENTS.md`/`CLAUDE.md` should describe files that exist today; planned files belong in
  roadmap text until they are created.
  **Why it matters:** nonstandard skill filenames are easy for Codex/Claude discovery to miss, and
  generated output plus stale maps waste context or send future agents looking for files that do not
  exist.
  **Where it applies:** `.agents/skills/`, `.claude/skills/`, `.gitignore`, `tools/check.ps1`.

- **Lesson:** Shared agent safety hooks live in `tools/agent-hooks/`; Claude Code calls them through
  thin wrappers in `.claude/hooks/` wired from `.claude/settings.local.json`, and Codex calls the
  same shared scripts from `.codex/hooks.json`. Keep them conservative: block destructive commands,
  likely secret leaks, surprise dependency installs, frontend key references, and AGENTS/CLAUDE drift;
  use cheap checks only. The backend syntax hook should run `python -m compileall -q backend` only
  when a usable Python is available, and skip cleanly if the local `.venv` is broken. The compact
  reminder is only a transcript-size heuristic: it starts around 50%, caps the displayed bucket at
  `95%+`, and must never pretend to know an exact model context reading.
  **Why it matters:** hooks can block Claude or Codex automatically, so false positives burn time and
  usage. This repo's current `.venv` points at an inaccessible Python 3.14 executable, which would
  have made every backend edit look like a hook failure unless the hook skipped safely.
  **Where it applies:** `.claude/settings.local.json`, `.claude/hooks/*.ps1`, `.codex/hooks.json`,
  `tools/agent-hooks/*.ps1`, `backend/`.

- **Lesson:** **Pattern Memory** has TWO parts, both updated by the best-effort
  `POST /sessions/{id}/learn` call (fired fire-and-forget from `tracker.html` after the debrief).
  **(a) Hourly focus profile** = a DETERMINISTIC 24-row `hourly_focus` table (one row per local clock
  hour 0-23, prebooted by `crud.seed_hourly_focus`), NOT AI. The frontend sends the session's **local
  `start_hour`/`end_hour`** (it computes them — backend stores UTC and does no tz math); the backend
  computes `session_pct = focused/total` and folds it into each hour the session touched via
  `crud.update_hourly_focus` (running average, midnight-wrap aware). This part runs **even if Gemini is
  down** (it's before the `_client` check). Shown as a green-tinted 24-cell grid in the About-me modal
  (`GET /hourly-focus`). **(b) Qualitative `observations`** = the AI affirm/reject/add loop:
  `Observation` model, pre-seeded (`crud.seed_observations`, only when empty) with NON-time hypotheses
  (drift/fade/recovery — time-of-day was intentionally removed since (a) handles it). Gemini returns
  `{affirm:[ids],reject:[ids],new:[...]}`; counts bump (`affirm/reject_observation`), ≤2 new/session
  (cap ~20 active), retire via the pure rule **`active = (rejections − affirmations) < 2`**.
  Confidence: `net ≥ 2` → "confirmed", else "emerging". The `new` prompt insists a pattern be
  genuinely DIFFERENT from existing ones AND focus-relevant (no rewordings). The call **never raises**
  (returns `{updated, hours_updated}`, zeros on failure) and is fully separate from the debrief, which
  is **unchanged** — I only extracted the shared `_session_summary()` helper (no duplicated code).
  Startup (`init_db` → `_init_pattern_memory`) seeds both tables, runs a one-time **cleanup** of the
  obsolete time-of-day seeds (`crud.cleanup_legacy_time_observations`, idempotent, deletes only the 3
  known seed strings), and **decays** notes untouched for 30+ days
  (`crud.decay_stale_observations` — moves net one step toward 0, re-stamps `updated_at`, re-applies
  the active rule so a confirmed note drifts to emerging and a retired one can revive). Viewer/delete + the hour grid live in the About-me
  modal (`settings-menu.js`, escaped via a local `escapeHtml`). Weekly unwind now reads the active
  observations and hourly focus profile along with About me and prior weekly recaps, so keep future
  pattern-memory changes compatible with that consumption path. Verified on fresh temp DBs end-to-end.
  **Why it matters:** measures time-of-focus exactly (cheap, reliable) while letting the AI handle the
  fuzzy qualitative patterns — without ever destabilizing the working debrief/save path.
  **Where it applies:** `backend/{models,schemas,crud,database,main}.py`,
  `frontend/js/{api,settings-menu}.js`, `frontend/tracker.html`.

- **Lesson:** **On-device MediaPipe face sensors** (`frontend/js/face-metrics.js`) run Face Landmarker
  locally (~4 fps via `setInterval`, loaded from jsdelivr `@mediapipe/tasks-vision@latest/+esm` behind
  a ready-promise) and turn landmarks into **smoothed semantic LABELS** (eyes open/closed via
  eye-aspect-ratio with a ~1.5s blink-rejecting window, head facing/away/down, face present). The
  detector reads `window.faceMetrics.getSensorLabels()` each sample and passes it as `sensors` →
  `getFocusState` → `analyzeFocus` → `/focus/analyze`; the backend folds it into the prompt as
  "On-device sensors (may be imperfect — trust the image if they conflict): …". **Send LABELS, not
  raw floats** — Gemini can't calibrate an EAR number; code does the thresholding. **Fail-safe:**
  `getSensorLabels()` returns `null` if MediaPipe can't load (verified: blocking the CDN → `sensors`
  null, app unchanged, no crash). Verified the labels steer the decision (eyes-closed+away →
  distracted, open+facing → focused). Gotchas: MediaPipe logs an INFO line via `console.error`
  ("Created TensorFlow Lite XNNPACK delegate") — benign; and curl on Windows mangles the `·`
  separator (UTF-8) — `fetch` sends it fine, so test the backend with Python, not curl.
  **Why it matters:** hardens the physical facts Gemini is weakest at (eyes/presence/gaze) without
  betting the core detection on a dependency.
  **Where it applies:** `frontend/js/{face-metrics,focus-detector,focus-engine,api}.js`,
  `frontend/tracker.html`, `backend/{schemas,main}.py`.

- **Lesson:** The dev **"Show AI reasoning"** toggle (`fb-show-reasoning`, Settings → Developer,
  default off) surfaces Gemini's per-sample reasoning on the tracker. It's **gated so the hot path is
  unchanged when off**: the detector reads the flag (`_explainOn()`) and passes `explain` through
  `getFocusState`→`analyzeFocus`→`/focus/analyze`; the backend only adds the `reason` field to the
  prompt + response **when `request.explain` is true** (otherwise the call returns `{state, note}`
  exactly as before — no extra tokens). `_parse_focus` now returns `(state, note, reason)` and still
  falls back to a bare state on bad JSON. The reason rides the sample via `onStateChange(state, note,
  reason)` → `setState` updates the `#ai-reason` panel (shown when the flag is on).
  **Why it matters:** dev-only visibility into *why* the AI picked a state + which signals it weighed,
  without making the production/demo detection call heavier.
  **Where it applies:** `backend/{schemas,main}.py`, `frontend/js/{api,focus-engine,focus-detector,settings-menu}.js`, `tracker.html`.

- **Lesson:** The opt-in **Pomodoro** timer (tracker hero toggle; `fb-pomo-enabled`/`fb-pomo-focus`/
  `fb-pomo-break`, bounds focus 10–55 / break 5–15) runs focus→break cycles by treating a **break as
  an automatic pause**: `startBreak()` calls `pauseDetection()` + each break tick adds `deltaSec*1000`
  to `pausedMs` (freezing `elapsedSeconds` so break time is excluded from focus stats), and
  `endBreak()` sets `phaseStartElapsed = elapsedSeconds`, resets `lastTickMs`, and `resumeDetection()`.
  Focus-block progress is measured in `elapsedSeconds` (so a manual pause also pauses the block).
  Guard the manual-resume handler with `if (!onBreak) resumeDetection()` so it doesn't un-pause the
  camera mid-break. Frontend-only; AI tuning of the durations is deferred to the future AI-Weekly-
  Unwind chunk. **Testing time-based logic:** use Playwright `page.clock.install()` + `fastForward`,
  and pass durations as **`"mm:ss"` strings** — a bare number is milliseconds (`fastForward(610)` =
  0.61s, not 610s).
  **Why it matters:** reusing the pause machinery means breaks correctly don't count against focus,
  with no backend/data changes; and the ms-vs-string gotcha silently no-ops time tests.
  **Where it applies:** `frontend/tracker.html` (`tick`, `startBreak`/`endBreak`, pomo wiring).

- **Lesson:** The **"About me"** profile is a single-row `user_profile` table (`UserProfile`, always
  id=1) holding one free-text `about` field, exposed via `GET`/`PUT /profile` and `crud.get_profile`
  (get-or-create) / `update_profile` (strips + caps at 1000 chars). It's injected into BOTH AI
  prompts via the shared `_about_block(db)` helper — so `analyze_focus` now takes a `db` dependency
  and reads it each sample (cheap single-row read). The editor is a modal built on demand in
  `settings-menu.js` (`openAboutModal`, reachable from the gear's "About you" → Edit), using
  `getProfile`/`saveProfile` in `api.js`. New table → created by `create_all`, no migration. Verified
  the context lands: a debrief correctly read an away period as "your 3pm break" and noted the
  "multi-monitor setup."
  **Why it matters:** gives Gemini standing context (setup, schedule, habits) so glancing at a 2nd
  monitor or an expected break isn't misread as distraction.
  **Where it applies:** `backend/{models,schemas,crud,main}.py`, `frontend/js/{api,settings-menu}.js`.

- **Lesson:** The focus-detection prompt must judge a website's relevance by **what the specific
  page is about (its title), NOT the site's general category**. The old wording ("an entertainment
  site supports 'distracted'") wrongly flagged a *typing-tutorial YouTube video* as distracted during
  a typing-practice task. The prompt now says task-related tutorials/articles/videos (even on
  YouTube) are 'focused' since looking them up is part of doing the task, and to lean on the webcam
  image when relevance is unclear. Because the extension strips the URL query, the **page title is
  the main relevance signal** — keep it in the prompt. Verified: "How to Type Faster" → focused,
  "Funny Cat Compilation" → distracted.
  **Why it matters:** the whole point of the website signal is intent-alignment; a site-category bias
  defeats it and frustrates the user.
  **Where it applies:** `backend/main.py` `analyze_focus` prompt (the `site` block).

- **Lesson:** `showToast(message)` and `confirmDialog(message)` in `notify.js` render `message` as
  innerHTML but now **escape it internally** (via a local `esc()`), so **callers pass RAW text** —
  do NOT pre-escape at the call site or you'll double-escape (you'd see `&amp;quot;`). (The toast
  `opts.icon` and the dialog button labels stay raw HTML — they're app-controlled.) A task named
  `<3 coding` is the test case; verified a `<img onerror>` payload renders as inert text.
  **Why it matters:** centralizing the escape in the helper means a forgetful caller can't introduce
  an injection/rendering bug; the previous "callers must escape" convention was fragile.
  **Where it applies:** `frontend/js/notify.js`; callers in `tracker.html` (`fireNudge`) and
  `index.html` (delete confirm) now pass raw text.

- **Lesson:** The **session journal** (`journal_json` column on `focus_sessions`, mirroring
  `timeline_json`) is a list of timestamped events that feeds the debrief. Division of labor: the
  **code** logs clean signals — focus-state changes (in `tracker.html setState(state, note)`) and
  tab/site switches (in `setActivity`, deduped by domain) — while the **model** supplies fuzzy color
  via a short per-sample `note`. To get the note, `/focus/analyze` now returns JSON `{state, note}`
  (note only when NOT focused); `_parse_focus` parses it defensively and **falls back to the old
  word-scan (`_parse_state`) on any failure**, so the core focus signal is never lost (note just
  becomes ''). The seam `getFocusState` now returns `{state, note}` (not a bare string) — its only
  caller is `focus-detector._sampleFrame`. The debrief formats the journal via `_format_journal`
  (capped at 50 lines) and grounds its patterns in it. New DBs get the column from `create_all`;
  existing DBs get it via an `ALTER TABLE ... ADD COLUMN journal_json` in `_repair_sqlite_schema`.
  **Why it matters:** gives the debrief site-level/narrative coaching ("you switch to Instagram every
  ~2 min") without hardcoding any site list, and without destabilizing the working focus detection.
  **Where it applies:** `backend/main.py` (`_parse_focus`, `_format_journal`, `/focus/analyze`,
  `debrief_session`), `backend/{models,schemas,crud,database}.py`, `frontend/js/{focus-engine,focus-detector}.js`,
  `frontend/tracker.html`.

- **Lesson:** The end-of-session AI debrief (`POST /sessions/{id}/debrief` → Gemini coaching JSON)
  is **best-effort and runs AFTER the save**: in tracker.html's End & Save handler, `await
  enqueueSessionSave(true)` must fully complete first, then the debrief modal opens — a debrief
  failure (502/503/timeout/network) only shows an error state, never risks the saved session, and
  every modal state has a Done/Escape that redirects to index.html (never strand the user). The
  endpoint parses the model's JSON with `_parse_debrief` (strips ```fences, coerces types, clamps
  lists, and on ANY error falls back to putting raw text in `summary` — never 500s on a parse miss).
  All-zero sessions return 422 and the frontend skips the call. The session debrief is
  **generated-and-shown, not persisted** (no session debrief DB column yet); daily and weekly unwind
  recaps are separate features and are persisted in `work_periods.ai_recap`.
  **Why it matters:** keeps a flaky AI call from ever losing a user's session or trapping them, and
  keeps malformed model output from breaking the endpoint/UI.
  **Where it applies:** `backend/main.py` (`debrief_session`, `_parse_debrief`, `_collapse_timeline`),
  `frontend/tracker.html` (the `#confirm-end` flow + `#debrief-overlay`), `frontend/js/api.js`.

- **Lesson:** A browser extension's requests carry an `Origin` of `chrome-extension://<id>`, which
  the localhost-only CORS regex rejects — so the extension's `fetch` fails **silently** (no app
  error). The backend's `allow_origin_regex` must include `chrome-extension://[a-p]+`. Also: the
  active-tab URL + page title are held in a module-level dict (`_latest_activity`) **in memory only, never SQLite**
  (it's transient state), and goes stale after `ACTIVITY_TTL` (30s) so a closed browser
  doesn't leave a stale URL in use. The extension lives in `extension/`, loaded unpacked
  (`chrome://extensions` → Developer mode → Load unpacked); no Web Store publishing needed.
  **Why it matters:** without the CORS fix the whole website-awareness feature is dead on arrival
  with no visible error; persisting URLs would be needless data-at-rest with no benefit.
  **Where it applies:** `backend/main.py` (CORS, `/activity`, the `/focus/analyze` prompt), `extension/`.

- **Lesson:** The three coaching prompts (`debrief_session`, `daily_unwind`, `weekly_unwind` in
  `main.py`) were re-engineered with focus-psychology principles: **autonomy-supportive voice** ("you
  might", not "you should" — SDT), **lead with the win** (positive reinforcement before any friction),
  **ground every claim in a datum + interpretation** (no number-parroting), **implementation-intention**
  phrasing for actions ("When/after <cue>, you <action>" — addressed to "you", never "I will"), depth/
  flow language, and a daily **shutdown question** (Newport detachment ritual). New response fields were
  added (defaults `''`, parsers extended defensively): debrief `win`+`next_action`; daily
  `win`+`next_action`+`shutdown_question`; weekly `next_week_focus`. **Field-plumbing gotcha:** the
  daily/weekly **`generate*Ai` functions in `analytics.html` build `unwind.aiRecap` by copying named
  fields from the response** — when you add a response field you MUST add it there too or the UI
  silently drops it (caught in testing: recap rendered with no Win). The session debrief is immune
  because `renderDebrief` consumes the raw API response directly. Verified across synthetic profiles
  (high-focus, micro-distraction, lots-uncertain, improvement/slip days, problem/clean weeks): outputs
  are concrete, autonomy-supportive, data-grounded; gating + clamps + 422 + defensive fallback all
  intact. Transient Gemini 502s happen — the unwind UIs already show an error state with retry.
  **Why it matters:** the coaching is the product's voice; research-backed framing makes it land
  without lecturing or causing burnout.
  **Where it applies:** `backend/{schemas,main}.py`, `frontend/tracker.html`, `frontend/analytics.html`.

- **Lesson:** The **AI Weekly Unwind** (`POST /unwind/weekly`) adds a 4th step to the weekly unwind
  modal (overview → day-by-day → **AI insights** → reflection; daily already had its AI step). The
  weekly day-by-day is now a **mini-bar visual** (best day highlighted). The endpoint reasons over the
  week using the **frontend-sent per-day data with each day's saved daily `ai_recap` folded in**
  (raw-stats fallback for un-unwound days), plus `hourly_focus`, active `observations` (read-only),
  About me, and **prior weekly `work_periods` for the trend** (backend reads them — they're already
  keyed by local Monday, so no tz math). Returns `{summary, theme, insights[], improvements[],
  pomodoro{recommend,focus_min,break_min,why}}`; `_parse_weekly_unwind` **clamps the Pomodoro to
  10–55 / 5–15**. **Gating gotcha:** the prompt must judge problems from **THIS week's data only** —
  without that, the model pulls "improvements"/pomodoro changes from the remembered observation priors
  even on a clean week (verified fix: clean week → `improvements:[]`, `recommend:false`; problem week →
  populated). The recap is saved to `work_periods.ai_recap` for `kind='week'` (reuses the daily
  column + preserve-on-None upsert). **Pomodoro popup** (`openPomoSuggest`, built in JS, sits
  fixed beside the unwind modal, pomofocus.io-style steppers): **auto-opens only when
  `pomodoro.recommend`** on a fresh generate; on reopen it does NOT auto-open — a "Tune my Pomodoro →"
  button does. Apply writes `fb-pomo-focus`/`fb-pomo-break` + `fb-pomo-enabled='on'` (the keys
  `tracker.html` reads). The weekly AI step reuses the daily machinery via a kind dispatcher
  (`generateUnwindAi`, `unwindStepKeys('week')` now 4 keys). The "people change" framing is in the
  prompt (weight recent weeks; priors can be overridden) — fulfills memory
  [[weekly-unwind-people-change]].
  **Why it matters:** the headline feature — turns the whole week's data + the Pattern Memory into
  narrative coaching and an actionable, user-confirmed Pomodoro change.
  **Where it applies:** `backend/{schemas,main}.py`, `frontend/js/api.js`, `frontend/analytics.html`.

- **Lesson:** The **AI Daily Unwind** adds an AI coaching step to the existing daily unwind modal
  (`analytics.html`), which was previously manual-only (donut → by-task → write-your-own reflection).
  Daily is now **4 steps** (donut → by-task → **AI insights** → reflection); weekly is **unchanged at
  3**. The step machinery was refactored from hardcoded numeric indices to a per-kind key list
  (`unwindStepKeys(kind)`) driving the dots/body/Next — when adding steps, edit that list, not scattered
  `step === 2` checks. The AI step is a **manual "Generate" button** (→ `POST /unwind/daily`), shows
  summary + "today vs your patterns" + advice (above an **app-rendered stats strip** — focus % + the
  per-state breakdown via the existing `legendRows(sum)` + total tracked, exact numbers not the
  model's, shown even before Generate), and has a **Regenerate**. It's **saved** in a new
  `work_periods.ai_recap` column as a JSON string (parsed defensively on reopen → bad JSON falls back to
  the Generate button). **Persistence gotcha:** the recap and the user's reflection share one
  `work_periods` row but are saved by two different paths, so `WorkPeriodCreate.reflection`/`.ai_recap`
  are **Optional and `crud.upsert_work_period` only overwrites each when not None** ('' clears) — this is
  what keeps the AI-save from wiping the reflection and vice-versa. The endpoint reads `hourly_focus` +
  active `observations` (read-only — `/learn` already updates them) + About me, and the frontend sends
  today's `session_ids` + a 14-day `recent_avg_focus_pct`; it 422s under ~120s tracked (frontend shows a
  friendly note). New column on the existing table → `ALTER TABLE work_periods ADD COLUMN ai_recap` in
  `_repair_sqlite_schema`. Verified end-to-end (incl. that a day breaking the "drifts early" pattern is
  called out, and that reflection+recap coexist). Weekly AI unwind is the next chunk (see
  [[weekly-unwind-people-change]]).
  **Why it matters:** turns the dormant Pattern Memory + hourly profile into actual day-level coaching
  without destabilizing the working manual unwind or the per-session debrief.
  **Where it applies:** `backend/{models,schemas,crud,database,main}.py`, `frontend/js/api.js`,
  `frontend/analytics.html`.

- **Lesson:** The extension **only reports while a tracker session is actively tracking** (with the
  website toggle on), via a backend **gate**: `_tracking_state` (in-memory, `TRACKING_TTL` **90s**). The
  tracker **heartbeats** `POST /tracking-state {active}` every 20s where `active = sessionId &&
  !isPaused && !onBreak && websiteTrackingOn()`, and pushes it immediately on pause/resume/break/stop;
  the extension calls `GET /tracking-state` before every report and stays silent if false; and BOTH
  `POST /activity` (write) and `GET /activity` (read) are **gated** — write ignored and read returns
  null whenever the gate is closed (toggle honored authoritatively). On gate-close, `_latest_activity`
  is **cleared immediately** so no URL lingers in the 30s `ACTIVITY_TTL` window.
  Gotchas baked in: (1) close the gate on **`pagehide` only, NOT `visibilitychange`** — a plain
  tab-switch must keep it open so the extension can report the tab the user switched to (the whole
  point). (2) On End&Save, `stopDetection()` runs but the tracker's `sessionId` is still set, so send
  `setTrackingState(false)` **explicitly** there, not via `trackingGateOn()`. (3) **TTL must exceed
  Chrome's ~60s background-tab timer throttle** — a hidden tracker tab's heartbeat slows down, so a
  short TTL (the original 40s) would false-close the gate while the user works in another tab; 90s + the
  immediate explicit closes covers both. The TTL is now ONLY a backstop for a true browser crash (and
  the extension dies with the browser in a crash, so the practical exposure is just a brief
  post-restart window). Verified end-to-end (Playwright + fake camera): start→true, pause→false,
  resume→true, toggle-off→stays false, `/activity` dropped + cleared while closed.
  **Why it matters:** stops the extension leaking your active-tab URL to the local backend when you're
  not actually tracking, makes the website toggle real (it used to only gate the tracker's read), and
  avoids a throttling bug that would silently kill website awareness during long multi-tab work.
  **Where it applies:** `backend/{main,schemas}.py`, `extension/background.js`,
  `frontend/js/api.js`, `frontend/tracker.html`.

- **Lesson:** Website awareness is **opt-in**: gated by `localStorage['fb-website-tracking']` (default
  off), set from the settings gear. The shared settings menu is now available on the main app pages,
  including `tracker.html`. The tracker reads the flag each sample; only when on does `focus-detector` call
  `GET /activity` and pass the URL into `getFocusState(...,currentUrl)` → the same Gemini call. The
  seam is unchanged (UI still only asks "what's my focus state?").
  **Why it matters:** keeps the website signal honest — opt-in and disclosed, off by default — while
  avoiding stale guidance about where the toggle can be changed.
  **Where it applies:** `frontend/js/settings-menu.js`, `focus-detector.js`, `focus-engine.js`, `tracker.html`.

- **Lesson:** After editing any `backend/` file, the running `uvicorn --reload` will NOT pick up
  the change — restart the server manually (stop it, rerun `uvicorn backend.main:app --reload`).
  Claude can't kill a server started in the user's own terminal (different session), so to
  self-verify backend changes, run a second instance on another port
  (`python -m uvicorn backend.main:app --port 8001`) and test against that.
  **Why it matters:** the project lives under OneDrive, whose virtual filesystem doesn't emit the
  file-change events `watchfiles` needs, so `--reload` silently serves stale code (new routes 404).
  **Where it applies:** every backend change; the whole `backend/` folder.

- **Lesson:** A brand-new SQLAlchemy table needs no migration code — `init_db()`'s
  `Base.metadata.create_all()` creates it on startup. `_repair_sqlite_schema()` is only for adding
  columns to *existing* tables. New persisted state can be a new table via model → schema → crud →
  route, with nothing added to `database.py`.
  **Why it matters:** avoids writing unnecessary/duplicate migration logic.
  **Where it applies:** `backend/models.py`, `backend/database.py` (the `work_periods` table).

- **Lesson:** Analytics group sessions by **local** day/week, never UTC — use
  `getFullYear/Month/Date` and a Monday-based `getDay()` offset. Day `period_key` is local
  `YYYY-MM-DD`; week `period_key` is that week's Monday. Build `Date` from a key with
  `new Date(y, m-1, d)`, NOT `new Date('YYYY-MM-DD')` (which parses as UTC and can shift the day).
  **Why it matters:** a UTC slip puts a session on the wrong day/week and misplaces calendar blocks.
  **Where it applies:** `frontend/analytics.html`, `frontend/index.html` calendar.

- **Lesson:** When a CSS/JS change "doesn't show up," it's almost always **browser cache**, not a
  failed edit. `python -m http.server` sends no `Cache-Control`, so browsers serve a stale
  `styles.css`/`*.js` on a normal refresh. Before concluding a change didn't work: (1) `curl
  http://localhost:5500/css/styles.css | grep <token>` to confirm the server sends the new value,
  then (2) tell the user to **hard-refresh (Ctrl+Shift+R / Ctrl+F5)**. When self-verifying in
  Playwright, navigate with a cache-buster (`...?cb=<timestamp>`) and reload after editing CSS — an
  already-open page keeps the old stylesheet in memory.
  **Why it matters:** wastes time chasing a non-existent code bug when the file is already correct.
  **Where it applies:** any `frontend/css` or `frontend/js` edit; verification workflow.

## About this file
This is the project memory, read automatically at the start of every session in this repo. The
`.claude/skills/` folder holds task-specific skills (building features, browser CV, the FocusEngine,
demo prep, the data-flow reference, etc.) that load when relevant. Keep this file current — a stale overview
that describes the old approach is worse than none, because it misleads.
