// Dark/light theme. Loaded FIRST in <head> on every page so the theme is applied
// before the page paints — that prevents a flash of the light theme on load.
(function () {
  function resolveTheme() {
    var saved = null;
    try { saved = localStorage.getItem('fb-theme'); } catch (e) {}
    if (saved === 'dark' || saved === 'light') return saved;
    // No saved choice yet → follow the OS preference.
    var prefersDark = window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches;
    return prefersDark ? 'dark' : 'light';
  }

  function applyTheme(theme) {
    document.documentElement.dataset.theme = theme;
  }

  // Apply immediately (this runs while <head> parses, before <body> renders).
  applyTheme(resolveTheme());

  // Expose helpers for the settings page.
  window.getTheme = function () {
    return document.documentElement.dataset.theme || 'light';
  };
  window.setTheme = function (theme) {
    try { localStorage.setItem('fb-theme', theme); } catch (e) {}
    applyTheme(theme);
  };
})();
