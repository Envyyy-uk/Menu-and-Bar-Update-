/* ==========================================================================
   Екран кухні та бару.

   Одна справа, великі кнопки, без навігації. Це окрема поверхня від панелі
   навмисно: там роблять усе інше, тут — приймають і віддають.

   Головна фіча тут не список, а **індикатор зв'язку**. Тихий застарілий
   список неприпустимий: кухня спокійно працюватиме, поки замовлення падають
   у порожнечу. Тому тиша від сервера понад 10 секунд — червоний
   повноекранний банер і безперервний звук.

   Після відновлення зв'язку стан перезавантажується з сервера цілком, а не
   догравається подіями: пропущена подія інакше тихо лишила б екран
   застарілим.
   ========================================================================== */

let LANG = getLang();
let STATION = new URLSearchParams(location.search).get('station') === 'bar' ? 'bar' : 'kitchen';
let ORDERS = [];
let LATE = new Set();
let SOCKET = null;
let LAST_SEEN = 0;
let ALARM = false;
let MUTED = false;
let KNOWN = new Set();      // номери, які вже бачили — щоб дзвеніти лише на нових
let BOOTED = false;

const SILENCE_MS = 10000;   // після цього мовчання зв'язок вважається втраченим
const POLL_MS = 3000;       // fallback, коли WebSocket не піднявся

/* --------------------------------------------------------------- звук --- */
let audio = null;

function beep(pattern) {
  if (MUTED) return;
  try {
    audio = audio || new (window.AudioContext || window.webkitAudioContext)();
    if (audio.state === 'suspended') audio.resume();
    pattern.forEach(([freq, at, len]) => {
      const osc = audio.createOscillator();
      const gain = audio.createGain();
      osc.type = 'square';
      osc.frequency.value = freq;
      gain.gain.value = 0.06;
      osc.connect(gain).connect(audio.destination);
      osc.start(audio.currentTime + at);
      osc.stop(audio.currentTime + at + len);
    });
  } catch (e) { /* браузер без звуку — банер однаково лишається */ }
}

const soundNewOrder = () => beep([[880, 0, 0.12], [1320, 0.15, 0.18]]);
const soundAlarm = () => beep([[440, 0, 0.25], [330, 0.3, 0.25]]);

let alarmTimer = null;

function setAlarm(on) {
  if (on === ALARM) return;
  ALARM = on;
  document.body.classList.toggle('alarm', on);
  const banner = document.getElementById('offline');
  banner.hidden = !on;
  if (on) {
    soundAlarm();
    // Безперервно, а не один раз: у кухні зайняті руки, і один сигнал
    // губиться в шумі.
    alarmTimer = setInterval(soundAlarm, 1500);
  } else if (alarmTimer) {
    clearInterval(alarmTimer);
    alarmTimer = null;
  }
}

/* --------------------------------------------------------------- дані --- */
async function reload() {
  const [queue, alerts] = await Promise.all([
    API.get('/api/orders', { station: STATION }),
    API.get('/api/orders/alerts')
  ]);
  const fresh = queue.filter(o => o.status !== 'served');
  LATE = new Set(alerts.map(a => a.number));

  // Ключ — сама марка: у замовленні їх кілька, і кожна приходить своєю чергою
  if (BOOTED) {
    const arrived = fresh.filter(o => !KNOWN.has(o.id));
    if (arrived.length) soundNewOrder();
    arrived.forEach(o => o.fresh = true);
  }
  KNOWN = new Set(fresh.map(o => o.id));
  ORDERS = fresh;
  BOOTED = true;
  render();
}

/* -------------------------------------------------------------- екран --- */
/**
 * Картка — це **марка**: одна станція, один курс. Кухня натискає своє, бар —
 * своє, і одне одному вони не заважають.
 */
function card(order) {
  const blocked = order.blocked_by_course !== null && order.blocked_by_course !== undefined;
  const box = el('article', 'kcard' + (order.fresh ? ' fresh' : '') +
    (LATE.has(order.number) ? ' late' : '') + (blocked ? ' held' : ''));

  const head = el('div', 'kcard-head');
  head.appendChild(el('span', 'knum', `№${esc(order.number)}`));
  head.appendChild(el('span', 'ktable', `${esc(t('k.table', LANG))} ${esc(order.table || '—')}`));
  if (order.course !== undefined) {
    head.appendChild(el('span', 'kcourse', esc(t('k.course.' + order.course, LANG))));
  }
  head.appendChild(el('span', 'kage', waited(order)));
  box.appendChild(head);

  if (LATE.has(order.number)) box.appendChild(el('p', 'klate', esc(t('k.late', LANG))));
  if (blocked) box.appendChild(el('p', 'kheld', esc(t('k.blocked', LANG))));

  const list = el('ul', 'kitems');
  order.items.forEach(i => {
    const li = el('li');
    li.innerHTML = `<b>${i.qty}×</b> ${esc(i.name)}`;
    list.appendChild(li);
  });
  box.appendChild(list);

  if (order.note) box.appendChild(el('p', 'knote', esc(order.note)));

  const next = { paid: 'accepted', accepted: 'ready', ready: 'served' }[order.status];
  if (next) {
    const label = { accepted: 'k.accept', ready: 'k.ready', served: 'k.served' }[next];
    const b = el('button', 'kbtn ' + next, esc(t(label, LANG)));
    b.type = 'button';
    // Заблокований курс видно, але не натискається — сервер однаково відмовить
    b.disabled = blocked;
    b.addEventListener('click', async () => {
      b.disabled = true;
      try {
        await API.post(`/api/orders/tickets/${order.id}/status?target=${next}`);
        await reload();
      } catch (e) {
        b.disabled = blocked;
      }
    });
    box.appendChild(b);
  }
  return box;
}

function waited(order) {
  const since = order.paid_at ? new Date(order.paid_at) : new Date(order.created_at);
  const mins = Math.max(0, Math.floor((Date.now() - since.getTime()) / 60000));
  return `${mins} ${t('k.waiting', LANG)}`;
}

function render() {
  document.getElementById('station-name').textContent =
    t(STATION === 'bar' ? 'k.bar' : 'k.title', LANG);
  const mount = document.getElementById('board');
  mount.innerHTML = '';
  if (!ORDERS.length) {
    mount.appendChild(el('p', 'kempty', esc(t('k.empty', LANG))));
    return;
  }
  ORDERS.forEach(o => mount.appendChild(card(o)));
}

/* ------------------------------------------------------------ зв'язок --- */
function connect() {
  if (SOCKET && (SOCKET.readyState === 0 || SOCKET.readyState === 1)) return;
  const proto = location.protocol === 'https:' ? 'wss' : 'ws';
  try {
    SOCKET = new WebSocket(`${proto}://${location.host}/ws/kitchen?station=${STATION}`);
  } catch (e) {
    return;
  }

  SOCKET.addEventListener('open', () => { LAST_SEEN = Date.now(); });
  SOCKET.addEventListener('message', ev => {
    LAST_SEEN = Date.now();
    let event = {};
    try { event = JSON.parse(ev.data); } catch (e) { return; }
    if (event.type === 'ping' || event.type === 'hello') return;
    // Подія — це сигнал «щось змінилося». Стан беремо з сервера цілком.
    reload().catch(() => { /* наступний ping усе одно приведе сюди */ });
  });
  SOCKET.addEventListener('close', ev => {
    if (ev.code === 1008) { renderLogin(); return; }
    SOCKET = null;
  });
  SOCKET.addEventListener('error', () => { /* watchdog розбереться */ });
}

/** Тиша — це теж повідомлення. Кожну секунду міряємо, скільки її вже. */
function watchdog() {
  const silent = Date.now() - LAST_SEEN;
  setAlarm(silent > SILENCE_MS);
  const dot = document.getElementById('link');
  dot.className = 'netdot' + (silent > SILENCE_MS ? ' bad' : ' ok');
  dot.title = `${t('k.online', LANG)} · ${Math.round(silent / 1000)}s`;

  if (!SOCKET || SOCKET.readyState > 1) connect();
}

/** Fallback: якщо сокет не піднявся, працюємо опитуванням — краще повільно,
    ніж наосліп. Відповідь сервера теж рахується за ознаку життя. */
async function poll() {
  if (SOCKET && SOCKET.readyState === 1) return;
  try {
    await reload();
    LAST_SEEN = Date.now();
  } catch (e) { /* мовчимо: watchdog уже кричить */ }
}

/* --------------------------------------------------------------- вхід --- */
function renderLogin() {
  document.getElementById('board').innerHTML = '';
  const box = el('div', 'login');
  const form = el('form', 'stack');
  const pin = el('input');
  pin.type = 'password'; pin.inputMode = 'numeric'; pin.placeholder = 'PIN'; pin.maxLength = 12;
  const go = el('button', 'primary', esc(t('k.enter', LANG))); go.type = 'submit';
  form.append(pin, go);
  form.addEventListener('submit', async ev => {
    ev.preventDefault();
    try {
      await API.post('/api/auth/pin', { pin: pin.value });
      location.reload();
    } catch (e) {
      form.appendChild(el('p', 'klate', esc(e.message)));
    }
  });
  box.appendChild(form);
  document.getElementById('board').appendChild(box);
}

/* --------------------------------------------------------------- старт -- */
async function initKitchen() {
  applyTheme('dark');            // планшет на кухні, а не вітрина
  document.querySelectorAll('[data-i18n]').forEach(n => { n.innerHTML = t(n.dataset.i18n, LANG); });

  const mute = document.getElementById('mute');
  mute.textContent = t('k.mute', LANG);
  mute.addEventListener('click', () => {
    MUTED = !MUTED;
    mute.textContent = t(MUTED ? 'k.unmute' : 'k.mute', LANG);
    mute.classList.toggle('off', MUTED);
    if (!MUTED) beep([[880, 0, 0.08]]);   // заразом розблоковує звук у браузері
  });

  const swap = document.getElementById('swap');
  swap.addEventListener('click', () => {
    STATION = STATION === 'bar' ? 'kitchen' : 'bar';
    const url = new URL(location.href);
    url.searchParams.set('station', STATION);
    history.replaceState(null, '', url);
    KNOWN = new Set();
    BOOTED = false;
    reload().catch(() => {});
  });

  try {
    await reload();
  } catch (e) {
    if (e.status === 401) { renderLogin(); return; }
  }

  connect();
  LAST_SEEN = Date.now();
  setInterval(watchdog, 1000);
  setInterval(poll, POLL_MS);
  setInterval(render, 30000);    // час очікування на картках має йти сам

  // Планшет не має гаснути посеред сервісу
  if ('wakeLock' in navigator) {
    const hold = () => navigator.wakeLock.request('screen').catch(() => {});
    hold();
    document.addEventListener('visibilitychange', () => { if (!document.hidden) hold(); });
  }
}
