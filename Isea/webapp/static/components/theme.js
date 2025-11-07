// theme.js - aplica el tema guardado y emite 'themeChanged'
(function(){
  const KEY = 'vis-theme';
  const apply = (mode) => {
    const isDark = mode === 'dark';
    document.documentElement.classList.toggle('dark', isDark);
    document.body.classList.toggle('dark', isDark);
    window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: isDark ? 'dark' : 'light' }}));
    const btn = document.getElementById('theme-toggle');
    if (btn) btn.textContent = isDark ? 'Light' : 'Dark';
  };

  const saved = localStorage.getItem(KEY);
  if (saved === 'dark') apply('dark');

  window.addEventListener('DOMContentLoaded', () => {
    const btn = document.getElementById('theme-toggle');
    if (!btn) return;
    btn.textContent = (document.body.classList.contains('dark') ? 'Light' : 'Dark');
    btn.addEventListener('click', () => {
      const next = document.body.classList.contains('dark') ? 'light' : 'dark';
      localStorage.setItem(KEY, next);
      apply(next);
    });
  });
})();
