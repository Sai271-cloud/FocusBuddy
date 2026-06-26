# Focus Buddy

Focus Buddy is a browser-based productivity and reflection app. You create a task, start a focus
session, and the app tracks time in four states: Focused, Distracted, Uncertain, and Away. Finished
sessions feed analytics, daily/weekly unwind flows, and pattern memory.

## Current Shape

- `frontend/` is the real app UI: plain HTML, CSS, and JavaScript served over HTTP.
- `backend/` is the FastAPI API: SQLite storage locally, Postgres storage when hosted,
  task/session endpoints, analytics helpers, and Gemini proxy endpoints.
- `render.yaml` and `frontend/vercel.json` prepare the public judge demo deployment: Render runs
  the FastAPI API, and Vercel serves the static frontend.
- `extension/` is an unpacked Chrome/Edge MV3 extension that can report the current tab title and a
  stripped URL to the local backend while tracking is active.
- `promptlab/` is a prompt experimentation harness. It is useful for testing candidate coaching
  prompt behavior, but it is not automatically the same as production backend prompts.
- `v0-export/` is a Next.js/v0 design export sandbox, not the production app.

## Data Flow

- Webcam frames are sampled in the browser and sent through the backend to Gemini for focus
  analysis.
- The Gemini API key must stay on the backend in `.env`; never put it in frontend code.
- MediaPipe face metrics run locally in the browser and send semantic labels only, not raw landmark
  floats.
- Website awareness is opt-in. The extension reports the page title and a stripped URL to the
  backend, which keeps the latest activity in memory with a short TTL.
- SQLite stores tasks, sessions, work-period reflections/recaps, profile text, hourly focus rows,
  and qualitative pattern-memory observations during local development. The hosted judge demo stores
  the same app data in Render Postgres, split by demo workspace.
- Seeded judge demos use readable links (`/demo/early-morning`, `/demo/doomscroller`,
  `/demo/overplanner`, `/demo/night-owl`, `/demo/self-improver`) with sample data frozen around
  June 28, 2026. `/demo/new` is a blank per-browser sandbox.

## Run Locally

Start the backend from the project root:

```powershell
uvicorn backend.main:app --reload
```

The API runs at `http://127.0.0.1:8000`, and FastAPI docs are at
`http://127.0.0.1:8000/docs`.

Serve the frontend over HTTP from `frontend/`:

```powershell
python -m http.server 5500
```

Then open `http://localhost:5500`. Do not open the HTML with `file://`; webcam permissions and API
calls depend on an HTTP origin. If Python is not working on this machine, fix/recreate `.venv` or use
another static file server.

## Environment

Create a local `.env` for backend-only secrets:

```text
GEMINI_API_KEY=...
```

Do not commit `.env`.

For the hosted backend, Render provides `DATABASE_URL` from Postgres. Set these environment
variables in Render:

```text
GEMINI_API_KEY=...
FOCUS_BUDDY_CORS_ORIGINS=https://<your-vercel-project>.vercel.app
COACHING_MODEL=gemini-3.5-flash
```

After Render gives you the backend URL, update `frontend/js/config.js` if the service is not named
`focus-buddy-api`.

## Public Judge Demo

Once deployed, send judges named links like:

```text
https://<your-vercel-project>.vercel.app/demo/early-morning
https://<your-vercel-project>.vercel.app/demo/doomscroller
https://<your-vercel-project>.vercel.app/demo/overplanner
https://<your-vercel-project>.vercel.app/demo/night-owl
https://<your-vercel-project>.vercel.app/demo/self-improver
https://<your-vercel-project>.vercel.app/demo/new
```

The five named links auto-seed different personas with the week of June 22-27, 2026 already filled
with tasks, sessions, analytics, plans, daily unwinds, hourly focus, and pattern memory. The app's
demo clock is fixed to the morning of June 28, 2026 so judges can run a fresh session and daily
unwind. The Judge Demo panel includes a reset button for seeded personas and a clear-data button for
the blank sandbox.

## Hosting

The intended demo setup is:

- **Render** hosts the FastAPI backend and Postgres database from `render.yaml`.
- **Vercel** hosts the static frontend from `frontend/` and rewrites `/demo/:slug` to the app.
- The Gemini API key stays only in Render environment variables.

Deploy Render first, copy its backend URL, then deploy Vercel. If the backend URL differs from
`https://focus-buddy-api.onrender.com`, update `frontend/js/config.js` and redeploy Vercel. Finally,
set Render's `FOCUS_BUDDY_CORS_ORIGINS` to the exact Vercel origin.

## Browser Extension

Load `extension/` unpacked from `chrome://extensions` or `edge://extensions` with Developer Mode on.
The extension only reports activity while the backend says tracking is active.

## Checks

The shared project check is:

```powershell
.\tools\check.ps1
```

It checks memory sync, ignored generated folders, secret patterns, frontend secret leaks, and Python
syntax when a working Python is available.

## Agent Notes

Keep `AGENTS.md` and `CLAUDE.md` synchronized. When one changes, update the other in the same pass.
Durable project lessons belong in `docs/project-lessons.md`, or in the matching `.agents/skills/`
and `.claude/skills/` skill mirrors for task-specific lessons.
