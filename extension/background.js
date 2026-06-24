// Focus Buddy — Website Awareness extension (background service worker).
//
// What it does: when you switch tabs (or a tab finishes loading), it reads the
// active tab's URL and POSTs it to your locally-running Focus Buddy backend at
// 127.0.0.1:8000/activity. The tracker page later reads that URL and sends it to
// the AI so it can judge whether the site fits your task.
//
// Privacy notes:
//  - It only talks to 127.0.0.1 (your own machine) — never anywhere else.
//  - It skips Focus Buddy's own page and browser-internal pages (chrome://, etc.).
//  - If the backend isn't running, the POST just fails quietly (no-op).
//  - MV3 service workers sleep when idle; tab events wake them, so we don't need
//    any long-lived timer — we just report on each event.

const BACKEND = 'http://127.0.0.1:8000/activity';
const TRACKING_STATE = 'http://127.0.0.1:8000/tracking-state';

// URLs we never report: browser internals and our own app (any localhost page).
const SKIP_PREFIXES = ['chrome://', 'chrome-extension://', 'edge://', 'about:', 'devtools://', 'view-source:'];

function shouldSkip(url) {
  if (!url) return true;
  if (SKIP_PREFIXES.some((p) => url.startsWith(p))) return true;
  try {
    const host = new URL(url).hostname;
    // Don't report Focus Buddy itself (or any other local dev page).
    if (host === 'localhost' || host === '127.0.0.1') return true;
  } catch (e) {
    return true; // unparseable URL — skip it
  }
  return false;
}

// Drop the query string (?...) and hash (#...) so secrets that hide in URLs —
// tokens, search terms, document IDs, usernames — never leave the browser. We
// keep only origin + path, which still identifies the site/page; the page title
// carries the actual meaning for the AI.
function cleanUrl(raw) {
  try {
    const u = new URL(raw);
    return u.origin + u.pathname;
  } catch (e) {
    return null;
  }
}

// Ask the backend whether a tracker session is actively tracking (with website
// awareness on). We only report when it is — so pausing/closing the tracker, or
// turning the website toggle off, stops the extension from sending anything.
async function trackingActive() {
  try {
    const r = await fetch(TRACKING_STATE);
    if (!r.ok) return false;
    const d = await r.json();
    return !!d.active;
  } catch (e) {
    return false; // backend not running / unreachable — stay quiet
  }
}

async function report(tab) {
  if (!tab || shouldSkip(tab.url)) return;
  const url = cleanUrl(tab.url);
  if (!url) return;
  if (!(await trackingActive())) return;  // gate: only report while the tracker is running
  try {
    await fetch(BACKEND, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, title: tab.title || '' }),
    });
  } catch (e) {
    // Backend not running / unreachable — ignore. Focus Buddy still works camera-only.
  }
}

// Switched to a different tab.
chrome.tabs.onActivated.addListener(async (info) => {
  try {
    const tab = await chrome.tabs.get(info.tabId);
    report(tab);
  } catch (e) {}
});

// The active tab navigated / finished loading a new page.
//  - status === 'complete' covers normal full page loads.
//  - changeInfo.url covers in-page navigations on single-page sites (YouTube,
//    Gmail, etc.) that swap the URL via the history API without a reload.
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!tab.active) return;
  if (changeInfo.url || changeInfo.status === 'complete') {
    report(tab);
  }
});

// Switched browser windows (e.g. alt-tabbed back to the browser).
chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return; // left the browser entirely
  try {
    const [tab] = await chrome.tabs.query({ active: true, windowId });
    if (tab) report(tab);
  } catch (e) {}
});
