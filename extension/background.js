
const BACKEND = 'http://127.0.0.1:8000/activity';
const TRACKING_STATE = 'http://127.0.0.1:8000/tracking-state';

const SKIP_PREFIXES = ['chrome://', 'chrome-extension://', 'edge://', 'about:', 'devtools://', 'view-source:'];

function shouldSkip(url) {
  if (!url) return true;
  if (SKIP_PREFIXES.some((p) => url.startsWith(p))) return true;
  try {
    const host = new URL(url).hostname;
    if (host === 'localhost' || host === '127.0.0.1') return true;
  } catch (e) {
    return true;
  }
  return false;
}

function cleanUrl(raw) {
  try {
    const u = new URL(raw);
    return u.origin + u.pathname;
  } catch (e) {
    return null;
  }
}

async function trackingActive() {
  try {
    const r = await fetch(TRACKING_STATE);
    if (!r.ok) return false;
    const d = await r.json();
    return !!d.active;
  } catch (e) {
    return false;
  }
}

async function report(tab) {
  if (!tab || shouldSkip(tab.url)) return;
  const url = cleanUrl(tab.url);
  if (!url) return;
  if (!(await trackingActive())) return;
  try {
    await fetch(BACKEND, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: url, title: tab.title || '' }),
    });
  } catch (e) {
  }
}

chrome.tabs.onActivated.addListener(async (info) => {
  try {
    const tab = await chrome.tabs.get(info.tabId);
    report(tab);
  } catch (e) {}
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
  if (!tab.active) return;
  if (changeInfo.url || changeInfo.status === 'complete') {
    report(tab);
  }
});

chrome.windows.onFocusChanged.addListener(async (windowId) => {
  if (windowId === chrome.windows.WINDOW_ID_NONE) return;
  try {
    const [tab] = await chrome.tabs.query({ active: true, windowId });
    if (tab) report(tab);
  } catch (e) {}
});
