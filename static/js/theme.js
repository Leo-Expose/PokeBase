// theme.js — Persist and apply theme + mode
const THEMES = ['default', 'gen4', 'future'];
const MODES  = ['light', 'dark'];
const THEME_LABELS = { 'default': 'Default', 'gen4': 'Gen 4', 'future': 'Future' };

function applyTheme(theme, mode) {
  document.documentElement.setAttribute('data-theme', theme);
  document.documentElement.setAttribute('data-mode', mode);
  localStorage.setItem('pb_theme', theme);
  localStorage.setItem('pb_mode', mode);

  // Update mode toggle button icon
  const modeBtn = document.getElementById('mode-toggle');
  if (modeBtn) {
    modeBtn.textContent = mode === 'dark' ? '☀️' : '🌙';
    modeBtn.title = mode === 'dark' ? 'Switch to light mode' : 'Switch to dark mode';
  }

  // Update theme button label
  const themeBtn = document.getElementById('theme-toggle');
  if (themeBtn) {
    themeBtn.title = `Theme: ${THEME_LABELS[theme] || theme}`;
  }
}

function initTheme() {
  const theme = localStorage.getItem('pb_theme') || 'default';
  const mode  = localStorage.getItem('pb_mode')  ||
    (window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  applyTheme(theme, mode);
}

function cycleTheme() {
  const current = localStorage.getItem('pb_theme') || 'default';
  const next = THEMES[(THEMES.indexOf(current) + 1) % THEMES.length];
  const mode = localStorage.getItem('pb_mode') || 'light';
  applyTheme(next, mode);
}

function toggleMode() {
  const theme = localStorage.getItem('pb_theme') || 'default';
  const current = localStorage.getItem('pb_mode') || 'light';
  applyTheme(theme, current === 'light' ? 'dark' : 'light');
}

// Run immediately to avoid flash
initTheme();
