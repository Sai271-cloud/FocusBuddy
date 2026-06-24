# Focus Buddy — Website Awareness extension

A tiny Chrome/Edge extension that tells your **locally-running** Focus Buddy app which website
you're currently on, so the AI can judge whether the site fits your task (e.g. an ML video while
you're doing an ML project = focused; an unrelated video = drifting).

It only ever sends data to `127.0.0.1:8000` (your own machine). It skips Focus Buddy's own page
and browser-internal pages, and it **strips the query string and hash** from every URL (so tokens,
search terms, and document IDs stay in your browser — only the domain + path and the page title are
sent). You also have to turn on **Website awareness** in Focus Buddy's settings for any of this to
be used — by default the app ignores it.

## Install (no Chrome Web Store needed)

1. Open `chrome://extensions` (or `edge://extensions`).
2. Turn on **Developer mode** (top-right toggle).
3. Click **Load unpacked** and select this `extension/` folder.
4. Make sure the Focus Buddy backend is running (`uvicorn backend.main:app --reload`).
5. In Focus Buddy → Settings (gear) → **Website awareness**, flip the toggle on.

That's it. Switch tabs while a session is running and Focus Buddy will factor in where you are.

## Remove it

On `chrome://extensions`, click **Remove** on the Focus Buddy card. Nothing is left behind — the
app keeps working camera-only.
