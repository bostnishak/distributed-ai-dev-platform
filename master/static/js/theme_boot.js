// Apply saved theme/preferences before first paint without inline script (HDR-04 CSP).
(function initThemeBeforePaint() {
  try {
    const ls = window['localStorage'];
    const prefs = JSON.parse((ls && ls['getItem']('cm6453_prefs')) || '{}');
    const root = document.documentElement;
    let theme = prefs.theme || 'system';
    if (theme === 'system') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    const reduced = Boolean(prefs.reduce_motion) || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    root.dataset.theme = theme;
    root.dataset.accent = prefs.accent || 'indigo';
    root.dataset.font = prefs.font_size || 'medium';
    root.dataset.density = prefs.density || 'comfortable';
    root.dataset.motion = reduced ? 'reduced' : 'normal';
  } catch { /* defaults apply */ }
}());
