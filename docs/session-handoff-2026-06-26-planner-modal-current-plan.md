# Session Handoff - Planner Add-Task Popup + Current Plan View

## Where it started
Sai asked to implement a previous agent's plan for two planner improvements: replace the inline Plan add-task form with a roomier popup that includes description, and reopen saved plans into a current-plan dashboard instead of forcing the wizard. The work stayed frontend-only because the backend task API already supports `createTask(name, description)`.

The session also covered local environment questions: why `.venv.broken-20260623-195918` exists, what the RED checks meant, and what environment issues are currently known.

## Decisions locked + what shipped
- Plan step 1 no longer renders the inline `#inline-add` form; it now shows an `Add task` button that opens a modal - `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\plan.html`.
- The modal collects task name and description, calls `createTask(name, description)`, auto-selects the created task for the daily plan, closes, and returns focus to the planner - `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\plan.html`.
- Saved plans now render a `Current plan` dashboard on load and after `Save plan`, with task rows, scheduled/unscheduled status, estimate, difficulty, planned-time summary, available-time budget, and actions for `Edit tasks`, `Edit estimates`, `Edit schedule`, `Clear plan`, and `Go to Today` - `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\plan.html`.
- Edit actions jump back into the existing wizard steps without clearing entries: tasks -> step 0, estimates -> step 1, schedule -> step 2 - `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\plan.html`.
- Existing planner advice/autosave rules were preserved: schedule placement uses the existing calendar path and does not make advice stale; task selection, estimates, difficulty, and available-time edits still call the existing dirty/stale paths - `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\plan.html`.
- Added compact styles for the add-task modal, pick-step header, current-plan stats/list/actions, and responsive fallbacks - `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\css\styles.css`.
- Confirmed `.venv.broken-20260623-195918` is an old renamed broken virtual environment pointing at `C:\Users\saite\AppData\Local\Python\pythoncore-3.14-64\python.exe`; the current `.venv` points at Python 3.13 under `C:\Users\saite\AppData\Local\Programs\Python\Python313\python.exe`.

## Key files for next session
- `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\plan.html` - main behavior change; read the inline script sections around modal helpers, `currentPlanBody()`, `render()`, `bindCurrentPlan()`, and `savePlanNow()`.
- `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\css\styles.css` - modal/current-plan styling lives in the Today's Plan section.
- `C:\Users\saite\OneDrive\Desktop\Focus App\frontend\js\api.js` - unchanged by this task, but confirms `createTask(name, description = '')` already exists.
- Plan file: none; the implementation plan was supplied in chat under the title `Planner Add-Task Popup + Current Plan View`.
- Memory files touched: `C:\Users\saite\OneDrive\Desktop\Focus App\AGENTS.md`, `C:\Users\saite\OneDrive\Desktop\Focus App\CLAUDE.md` to add this handoff file to the docs map.

## Running state
- Background processes: none started by this agent.
- Dev servers / ports: `http://127.0.0.1:8000/docs` and `http://127.0.0.1:5500/plan.html` were already reachable during verification; this agent did not start or stop those servers.
- Open worktrees / branches: normal checkout at `C:\Users\saite\OneDrive\Desktop\Focus App`, branch `main`, already ahead of `origin/main` by one commit when checked. The working tree had many pre-existing modified files; do not revert unrelated changes.

## Verification - how to confirm things still work
- `node --check frontend\js\api.js` - expected exit `0`.
- `node --check frontend\js\plan-calendar.js` - expected exit `0`.
- `node -e "const fs=require('fs'); const html=fs.readFileSync('frontend/plan.html','utf8'); const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]); scripts.forEach(script=>new Function(script)); console.log('inline scripts syntax ok: '+scripts.length);"` - expected output `inline scripts syntax ok: 1`.
- PowerShell planner contract check: read `frontend\plan.html` and assert no `id="inline-add"`, modal/name/description fields exist, `createTask(name, description)` exists, `state.view = 'current'` transitions exist, `currentPlanBody` exists, and current-plan edit/clear actions exist - expected output `planner contract ok`.
- `git diff --check -- frontend/plan.html frontend/css/styles.css frontend/js/api.js frontend/js/plan-calendar.js` - expected exit `0`; CRLF warnings may appear on Windows.
- Browser smoke still needed manually: open `http://localhost:5500/plan.html`, add a task with a description from the modal, confirm it appears selected, save a plan, reload Plan, confirm Current plan appears, and test `Edit tasks`, `Edit estimates`, `Edit schedule`, and `Clear plan`.

## Deferred + open questions
- Deferred: in-app browser smoke test - blocked because the browser plugin folder exists but is missing `scripts/browser-client.mjs` at `C:\Users\saite\.codex\plugins\cache\openai-bundled\browser\26.616.51431\scripts\browser-client.mjs`.
- Deferred: installing `rg` - not required for the feature, but `rg` is unavailable in this shell, so future searches fall back to PowerShell `Select-String` / `Get-ChildItem`.
- Deferred: deleting `.venv.broken-20260623-195918` - it appears safe to remove once Sai confirms the current `.venv` works, but it was not deleted.
- Open: whether to do a fresh-session review before committing, because the repo is on `main` with a dirty working tree and unrelated pre-existing changes.

## Pick up here
Start with a fresh review of `frontend\plan.html` and `frontend\css\styles.css`, then run the manual browser smoke test for the Plan modal/current-plan flow. If that passes, decide whether to commit just this planner change or review the broader dirty tree first.
