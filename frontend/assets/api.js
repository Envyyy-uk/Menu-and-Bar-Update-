/* ==========================================================================
   Клієнт API.

   Механізму публікації з референсу тут немає взагалі: ні overrides.js, ні
   токена GitHub, ні чернеток, ні перечитування файлу повз кеш. Стан живе в
   Postgres, і його достатньо перепитати.

   Що лишилось із референсу — звичка не залежати від однієї вдалої відповіді:
   якщо сервер не відповів, показуємо останній відомий стан і кажемо про це.
   ========================================================================== */

const API = {
  base: '',
  pollMs: 20000,

  /** Токен столу з /t/{token} — QR веде саме сюди. Без нього меню лише читають. */
  tableToken() {
    const m = /^\/t\/([A-Za-z0-9_-]+)/.exec(location.pathname);
    return m ? m[1] : null;
  },

  async get(path, params) {
    const url = new URL(this.base + path, location.origin);
    Object.entries(params || {}).forEach(([k, v]) => {
      if (v !== undefined && v !== null && v !== '') url.searchParams.set(k, v);
    });
    const r = await fetch(url, { cache: 'no-store', credentials: 'same-origin' });
    if (!r.ok) {
      // Статус потрібен викликачу: без нього екран кухні на 401 показував
      // порожнечу замість форми входу — тобто рівно той тихий екран, якого
      // тут не має бути.
      const err = new Error(`${path}: ${r.status}`);
      err.status = r.status;
      throw err;
    }
    return r.json();
  },

  async send(method, path, body) {
    const r = await fetch(this.base + path, {
      method,
      headers: { 'Content-Type': 'application/json' },
      credentials: 'same-origin',
      body: body === undefined ? undefined : JSON.stringify(body)
    });
    const text = await r.text();
    const data = text ? JSON.parse(text) : null;
    if (!r.ok) {
      const err = new Error((data && data.detail) || `${path}: ${r.status}`);
      err.status = r.status;
      err.data = data;
      throw err;
    }
    return data;
  },

  post(path, body) { return this.send('POST', path, body); },
  patch(path, body) { return this.send('PATCH', path, body); },
  del(path) { return this.send('DELETE', path); }
};

/* -------------------------------------------------------------------------
   Меню: одна відповідь, з якої рендериться вся сторінка.

   Останній вдалий стан лишається в пам'яті. Обрив мережі не має очищати
   екран: гість дочитає склад страви й офлайн, просто з поміткою.
   ------------------------------------------------------------------------- */
const MenuStore = {
  data: null,
  ok: false,
  listeners: [],

  onChange(fn) { this.listeners.push(fn); },

  /** Відбиток стану без поля `now`: годинник тікає щохвилини, і без цього
      «щось змінилося» було б правдою завжди, а меню перемальовувалося б під
      пальцем у гостя. Наявність, що змінилася від часу, у відбиток входить. */
  fingerprint(data) {
    return JSON.stringify(data, (k, v) => (k === 'now' ? undefined : v));
  },

  async refresh() {
    const at = new URLSearchParams(location.search).get('at');
    try {
      const data = await API.get('/api/menu', { at });
      const changed = this.fingerprint(data) !== this.fingerprint(this.data);
      this.data = data;
      this.ok = true;
      this.listeners.forEach(fn => fn(this.data, { changed, online: true }));
      return true;
    } catch (e) {
      this.ok = false;
      this.listeners.forEach(fn => fn(this.data, { changed: false, online: false }));
      return false;
    }
  },

  /** Перепитуємо за таймером і щоразу, коли застосунок повертається на
      передній план — саме там найчастіше висить застарілий стан. */
  start() {
    this.refresh();
    setInterval(() => this.refresh(), API.pollMs);
    document.addEventListener('visibilitychange', () => {
      if (!document.hidden) this.refresh();
    });
    window.addEventListener('online', () => this.refresh());
  }
};
