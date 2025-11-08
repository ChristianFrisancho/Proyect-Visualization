// theme.js - tema con data-theme + evento themeChanged
(function(){
  const KEY = 'vis-theme';
  function apply(mode){
    const m = (mode === 'dark') ? 'dark' : 'light';
    document.documentElement.setAttribute('data-theme', m);
    localStorage.setItem(KEY, m);
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = (m === 'dark') ? 'Light' : 'Dark';
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: m }}));
  }
  // aplica el guardado si hiciera falta
  const saved = document.documentElement.getAttribute('data-theme') || localStorage.getItem(KEY) || 'light';
  apply(saved);

  window.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.textContent = (document.documentElement.getAttribute('data-theme') === 'dark') ? 'Light' : 'Dark';
    btn.addEventListener('click', () => {
      const now = document.documentElement.getAttribute('data-theme') || 'light';
      apply(now === 'dark' ? 'light' : 'dark');
    });
  });
})();
