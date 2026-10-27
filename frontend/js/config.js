(function () {
  var host = window.location.hostname;
  var local = !host || host === 'localhost' || host === '127.0.0.1';
  if (local || window.FOCUS_BUDDY_API) return;

  window.FOCUS_BUDDY_API = '';

  window.va = window.va || function () { (window.vaq = window.vaq || []).push(arguments); };
  var analytics = document.createElement('script');
  analytics.defer = true;
  analytics.src = '/_vercel/insights/script.js';
  document.head.appendChild(analytics);
})();
