# Running Focus Buddy locally — setup guide

This guide gets Focus Buddy running on your own machine from scratch. It takes about 5–10 minutes.

There is **no database to install** and **nothing to deploy**: locally the app stores everything in a
small SQLite file it creates for you. You only need Python, a free Gemini API key, and a webcam.

> Prefer not to install anything? A hosted demo with sample data is available at the links the team
> shared (`/demo/...`). This guide is for running the real app on your own computer.

---

## 1. What you need first

| Requirement | Notes |
|---|---|
| **Python 3.13** (3.12 also works) | Download from [python.org](https://www.python.org/downloads/). On Windows, tick **"Add Python to PATH"** in the installer. |
| **Git** | To clone the repo ([git-scm.com](https://git-scm.com/downloads)). Or download the repo as a ZIP from GitHub and unzip it. |
| **A Gemini API key** | Free from [Google AI Studio](https://aistudio.google.com/apikey). The AI focus detection and coaching need it. |
| **A webcam** | The app watches the webcam to judge focus. A built-in laptop camera is fine. |
| **Chrome or Edge** | Needed only if you also want the optional website-awareness extension (Step 7). |

Check Python is installed by opening a terminal and running:

```
python --version
```

You should see `Python 3.13.x` (or `3.12.x`). If the command isn't found, reinstall Python and make
sure it's added to PATH.

---

## 2. Get the code

```
git clone https://github.com/Sai271-cloud/FocusBuddy.git
cd FocusBuddy
```

(If you downloaded the ZIP instead, unzip it and `cd` into the unzipped folder.)

All commands below are run **from this project folder** unless it says otherwise.

---

## 3. Install the Python dependencies

Create a virtual environment (a private, project-local Python) and install the packages:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

**macOS / Linux:**
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

After activating, your prompt shows `(.venv)` at the start. If PowerShell blocks the activate script
with an execution-policy error, run this once and try again:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```

---

## 4. Add your Gemini API key

The key must live on the backend only — never in the frontend. Create a file named `.env` in the
project root with this one line:

```
GEMINI_API_KEY=your_key_here
```

Replace `your_key_here` with the key from Google AI Studio. Do **not** commit this file (it's already
gitignored).

> Without a key the app still loads and the timer runs, but the AI focus calls return a 503 error
> instead of a focus state.

---

## 5. Start the backend (Terminal 1)

From the **project root**, with the venv activated:

```
uvicorn backend.main:app --reload
```

- API runs at `http://127.0.0.1:8000`
- Interactive API docs: `http://127.0.0.1:8000/docs`
- It creates a local `focus_buddy.db` SQLite file automatically on first run.

Leave this terminal running.

---

## 6. Start the frontend (Terminal 2)

Open a **second** terminal. The frontend is served from the **`frontend/` folder** — this matters,
see troubleshooting below.

```
cd frontend
python -m http.server 5500
```

Then open **`http://localhost:5500`** in Chrome or Edge. Allow camera access when prompted.

> Serve it over `http://` like this — don't double-click the HTML file. Opening it as a `file://`
> path breaks both the webcam and the connection to the backend.

That's it — make a task, start a session, and the app tracks your focus.

---

## 7. (Optional) The website-awareness browser extension

This lets the app also factor in *which website* you're on (e.g. a tutorial that fits your task vs. an
unrelated video). It talks only to your local backend on `127.0.0.1:8000`.

1. Open `chrome://extensions` (or `edge://extensions`).
2. Turn on **Developer mode** (top-right).
3. Click **Load unpacked** and select the `extension/` folder in this repo.
4. With the backend running, open Focus Buddy → Settings (gear) → turn **Website awareness** on
   (it's off by default).

To remove it, click **Remove** on the extension card. The app keeps working camera-only without it.

---

## Troubleshooting

**`GET /index.html 404 (File not found)`**
You started the frontend server from the wrong folder. `python -m http.server` serves whatever folder
you launched it from, and `index.html` lives in `frontend/`. Stop the server (Ctrl+C), then
`cd frontend` and run `python -m http.server 5500` again.

**The page loads but nothing happens / fetch errors in the console**
The backend isn't running. Start it in its own terminal from the project root:
`uvicorn backend.main:app --reload`. The two servers run at the same time in two terminals.

**Focus state shows an error / 503**
Your `GEMINI_API_KEY` isn't set or is wrong. Check the `.env` file is in the project root, the key is
valid, and restart the backend after editing `.env`.

**Camera is blocked or not found**
Allow camera access for `localhost` in the browser's site settings and reload. Webcam access needs an
`http://localhost` (or `https`) origin — it won't work from a `file://` page.

**`python` isn't recognized**
Reinstall Python with "Add to PATH" checked, or try `py` instead of `python` on Windows / `python3` on
macOS/Linux.

**PowerShell won't run the venv activate script**
Run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` once, then activate again.

---

## What runs where (honest data flow)

- The webcam frame is sampled in your browser and sent **through your local backend** to Gemini, which
  returns one focus state. The API key stays on the backend.
- Light face signals (eyes open/closed, head direction) run **on-device** in the browser via MediaPipe
  and send only simple labels, never raw camera data.
- Everything you create (tasks, sessions, reflections) is stored in the local `focus_buddy.db` SQLite
  file on your machine.
