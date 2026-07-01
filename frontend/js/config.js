(function () {
  var host = window.location.hostname;
  var local = !host || host === 'localhost' || host === '127.0.0.1';
  if (local || window.FOCUS_BUDDY_API) return;

  window.FOCUS_BUDDY_API = '';
})();
