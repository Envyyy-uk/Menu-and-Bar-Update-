/* ==========================================================================
   Дрібні елементи, потрібні і меню, і панелі, і екрану кухні.
   ========================================================================== */

const el = (tag, cls, html) => {
  const n = document.createElement(tag);
  if (cls) n.className = cls;
  if (html !== undefined) n.innerHTML = html;
  return n;
};

const esc = s => String(s == null ? '' : s)
  .replace(/[&<>"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[c]));

const cap = s => (s ? s.charAt(0).toUpperCase() + s.slice(1) : '');

/* --------------------------------------------------------- кнопка «нагору» */
const TOP_BTN_AFTER = 600;           // px прокрутки, після яких кнопка потрібна

function buildTopButton() {
  if (document.querySelector('.topbtn')) return;
  const b = el('button', 'topbtn', '↑');
  b.type = 'button';
  b.addEventListener('click', () => {
    // плавність приємна, але не тим, хто просив її вимкнути
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    window.scrollTo({ top: 0, behavior: reduce ? 'auto' : 'smooth' });
  });
  document.body.appendChild(b);

  const toggle = () => b.classList.toggle('on', window.scrollY > TOP_BTN_AFTER);
  toggle();
  window.addEventListener('scroll', toggle, { passive: true });
}

function labelTopButton(lang) {
  const b = document.querySelector('.topbtn');
  if (!b) return;
  const text = t('ui.top', lang);
  b.title = text;
  b.setAttribute('aria-label', text);
}

/* ------------------------------------------------------------------ тема -- */
const THEMES = ['auto', 'light', 'dark'];
const THEME_KEY = 'menu-theme';

function getTheme() {
  try {
    const saved = localStorage.getItem(THEME_KEY);
    if (THEMES.includes(saved)) return saved;
  } catch (e) { /* приватний режим */ }
  return 'auto';
}

function applyTheme(mode) {
  if (mode === 'auto') document.documentElement.removeAttribute('data-theme');
  else document.documentElement.dataset.theme = mode;
  try { localStorage.setItem(THEME_KEY, mode); } catch (e) { /* ігноруємо */ }
}

/* ----------------------------------------------- перемикачі мови й теми --- */
function buildSwitches(host, onLangChange) {
  const langs = el('div', 'langswitch');
  langs.setAttribute('role', 'group');
  langs.setAttribute('aria-label', t('lang.label'));
  LANGS.forEach(l => {
    const b = el('button', 'langbtn', l.short);
    b.type = 'button';
    b.title = l.label;
    b.dataset.lang = l.code;
    b.addEventListener('click', () => {
      setLang(l.code);
      onLangChange(l.code);
    });
    langs.appendChild(b);
  });

  const themes = el('div', 'themeswitch');
  themes.setAttribute('role', 'group');
  themes.setAttribute('aria-label', t('theme.label'));
  let current = getTheme();
  THEMES.forEach(mode => {
    const b = el('button', 'themebtn' + (mode === current ? ' on' : ''), t('theme.' + mode));
    b.type = 'button';
    b.dataset.theme = mode;
    b.addEventListener('click', () => {
      current = mode;
      applyTheme(mode);
      themes.querySelectorAll('.themebtn').forEach(x => x.classList.toggle('on', x.dataset.theme === mode));
    });
    themes.appendChild(b);
  });

  host.append(langs, themes);
}

/** Підписи перемикачів після зміни мови */
function refreshSwitches(lang) {
  document.querySelectorAll('.langbtn').forEach(b => b.classList.toggle('on', b.dataset.lang === lang));
  document.querySelectorAll('.themebtn').forEach(b => { b.textContent = t('theme.' + b.dataset.theme, lang); });
  labelTopButton(lang);
}
