(function () {
  function resolveTheme() {
    var saved = null;
    try { saved = localStorage.getItem('fb-theme'); } catch (e) {}
    if (saved === 'dark' || saved === 'light') return saved;
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
  }

  applyTheme(resolveTheme());

  window.getTheme = function () {
    return document.documentElement.dataset.theme || 'light';
  };
  window.setTheme = function (theme) {
    try { localStorage.setItem('fb-theme', theme); } catch (e) {}
    applyTheme(theme);
  };
})();
