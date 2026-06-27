(function () {
  var host = window.location.hostname;
  var local = !host || host === 'localhost' || host === '127.0.0.1';
  if (local || window.FOCUS_BUDDY_API) return;

  // Hosted Vercel uses the same origin for the static pages and FastAPI function.
  // API keys still live on the backend; this is only the public API base.
  window.FOCUS_BUDDY_API = '';
})();
