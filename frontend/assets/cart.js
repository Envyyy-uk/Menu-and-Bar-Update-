/* ==========================================================================
   Кошик і замовлення.

   Ідемпотентність тримається на `client_token`: він генерується один раз на
   кошик і не міняється, поки замовлення не пішло. Тому подвійний тап і
   повтор після обриву мережі дають те саме замовлення, а не два.

   Токен зберігається в `sessionStorage`: гість може перезавантажити
   сторінку посеред оплати — і кнопка «Замовити» не створить дубль.
   ========================================================================== */

const CART_KEY = 'cart';
const TOKEN_KEY = 'cart-token';
const ORDER_KEY = 'order';

let CART = {};        // key → qty
let ORDER = null;     // { id, client_token } активного замовлення
let SENDING = false;

function loadCart() {
  try {
    CART = JSON.parse(sessionStorage.getItem(CART_KEY) || '{}');
    ORDER = JSON.parse(sessionStorage.getItem(ORDER_KEY) || 'null');
  } catch (e) { CART = {}; ORDER = null; }
}

function saveCart() {
  try {
    sessionStorage.setItem(CART_KEY, JSON.stringify(CART));
    if (ORDER) sessionStorage.setItem(ORDER_KEY, JSON.stringify(ORDER));
    else sessionStorage.removeItem(ORDER_KEY);
  } catch (e) { /* приватний режим — кошик просто не переживе перезавантаження */ }
}

/** Один токен на кошик. Новий з'являється лише коли попереднє замовлення
    вже пішло — інакше повтор перестав би бути повтором. */
function clientToken() {
  try {
    let tok = sessionStorage.getItem(TOKEN_KEY);
    if (!tok) {
      tok = 'ct-' + (crypto.randomUUID ? crypto.randomUUID() : Date.now() + '-' + Math.random());
      sessionStorage.setItem(TOKEN_KEY, tok);
    }
    return tok;
  } catch (e) {
    return 'ct-' + Date.now() + '-' + Math.random();
  }
}

function resetToken() {
  try { sessionStorage.removeItem(TOKEN_KEY); } catch (e) { /* ігноруємо */ }
}

const cartCount = () => Object.values(CART).reduce((a, b) => a + b, 0);

function cartTotal(data) {
  return Object.entries(CART).reduce((sum, [key, qty]) => {
    const item = data.items.find(i => i.key === key);
    return sum + (item ? item.price_pence * qty : 0);
  }, 0);
}

/* ---------------------------------------------------- кнопки на картках -- */
function orderControls(item, data) {
  const slot = el('div', 'order-line');
  const qty = CART[item.key] || 0;

  if (!qty) {
    const add = el('button', 'add-btn', esc(t('cart.add', LANG)));
    add.type = 'button';
    add.addEventListener('click', () => { CART[item.key] = 1; saveCart(); refreshCart(data); });
    slot.appendChild(add);
    return slot;
  }

  const minus = el('button', 'qty-btn', '−');
  minus.type = 'button';
  minus.setAttribute('aria-label', '−');
  minus.addEventListener('click', () => {
    CART[item.key] = qty - 1;
    if (CART[item.key] <= 0) delete CART[item.key];
    saveCart(); refreshCart(data);
  });
  const plus = el('button', 'qty-btn', '+');
  plus.type = 'button';
  plus.setAttribute('aria-label', '+');
  plus.addEventListener('click', () => { CART[item.key] = qty + 1; saveCart(); refreshCart(data); });

  slot.append(minus, el('span', 'qty', String(qty)), plus);
  return slot;
}

/** Викликається з menu.js після кожного рендеру меню. */
function onMenuRendered(data) {
  loadCart();
  // Позиція могла зникнути з меню, поки кошик лежав відкритим.
  Object.keys(CART).forEach(key => {
    const item = data.items.find(i => i.key === key);
    if (!item || !item.orderable || !(item.available || {}).open) delete CART[key];
  });

  document.querySelectorAll('.order-slot').forEach(slot => {
    const item = data.items.find(i => i.key === slot.dataset.itemKey);
    slot.innerHTML = '';
    if (!item || !TABLE) return;                       // без QR столу не замовляють
    if (!item.orderable || !(item.available || {}).open) return;
    slot.appendChild(orderControls(item, data));
  });

  refreshCart(data);
  if (ORDER) pollOrder(data);
}

/* ------------------------------------------------------------- панель --- */
function refreshCart(data) {
  document.querySelectorAll('.order-slot').forEach(slot => {
    const item = data.items.find(i => i.key === slot.dataset.itemKey);
    if (!item || !TABLE || !item.orderable || !(item.available || {}).open) return;
    slot.innerHTML = '';
    slot.appendChild(orderControls(item, data));
  });

  let bar = document.getElementById('cartbar');
  if (!bar) {
    bar = el('div', 'cartbar');
    bar.id = 'cartbar';
    document.body.appendChild(bar);
  }
  const count = cartCount();
  bar.hidden = !TABLE || (!count && !ORDER);
  bar.innerHTML = '';

  if (ORDER) {
    bar.appendChild(el('span', 'cart-sum',
      `${esc(t('order.number', LANG))}${esc(ORDER.number || '')} · ${esc(t('order.st.' + (ORDER.status || 'paid'), LANG))}`));
    const again = el('button', 'primary', esc(t('order.new', LANG)));
    again.type = 'button';
    again.addEventListener('click', () => {
      ORDER = null; CART = {}; resetToken(); saveCart(); refreshCart(data);
    });
    bar.appendChild(again);
    return;
  }

  bar.appendChild(el('span', 'cart-sum',
    `${count} · ${esc(money(cartTotal(data), data.venue.currency, LANG))}`));
  const open = el('button', 'primary', esc(t('cart.title', LANG)));
  open.type = 'button';
  open.addEventListener('click', () => openCart(data));
  bar.appendChild(open);
}

function openCart(data) {
  document.querySelectorAll('.sheet').forEach(n => n.remove());
  const sheet = el('div', 'sheet');
  const box = el('div', 'sheet-box');
  box.appendChild(el('h2', null, esc(t('cart.title', LANG))));

  if (!cartCount()) {
    box.appendChild(el('p', 'hint', esc(t('cart.empty', LANG))));
  } else {
    const list = el('ul', 'cart-list');
    Object.entries(CART).forEach(([key, qty]) => {
      const item = data.items.find(i => i.key === key);
      if (!item) return;
      const li = el('li');
      li.innerHTML = `<span>${esc(item.name)} × ${qty}</span>` +
        `<span>${esc(money(item.price_pence * qty, data.venue.currency, LANG))}</span>`;
      list.appendChild(li);
    });
    box.appendChild(list);
    box.appendChild(el('p', 'cart-total',
      `${esc(t('cart.total', LANG))}: <b>${esc(money(cartTotal(data), data.venue.currency, LANG))}</b>`));

    const note = el('textarea', 'note');
    note.placeholder = t('cart.note', LANG);
    note.rows = 2;
    box.appendChild(note);

    const send = el('button', 'primary wide', esc(t('cart.send', LANG)));
    send.type = 'button';
    send.addEventListener('click', () => submitOrder(data, note.value, send, box));
    box.appendChild(send);
  }

  const close = el('button', 'wide', esc(t('cart.close', LANG)));
  close.type = 'button';
  close.addEventListener('click', () => sheet.remove());
  box.appendChild(close);

  sheet.appendChild(box);
  sheet.addEventListener('click', ev => { if (ev.target === sheet) sheet.remove(); });
  document.body.appendChild(sheet);
}

/* ---------------------------------------------------------- надсилання -- */
async function submitOrder(data, note, button, box) {
  // Друга сторона захисту від подвійного тапу: перша — client_token на сервері
  if (SENDING) return;
  SENDING = true;
  button.disabled = true;
  button.textContent = t('cart.sending', LANG);

  const payload = {
    table_token: API.tableToken(),
    client_token: clientToken(),
    items: Object.entries(CART).map(([key, qty]) => ({ key, qty })),
    note: note || null
  };

  try {
    const order = await API.post('/api/orders', payload);
    await API.post(`/api/orders/${order.id}/checkout?client_token=${encodeURIComponent(payload.client_token)}`);
    let final = order;
    if (order.payment_mode === 'offline') {
      // Режим без Stripe: фейковий сервіс із розділу 15, замовлення на нуль
      // фунтів. З увімкненим Stripe цей крок робить вебхук, а не браузер.
      final = await API.post(
        `/api/orders/${order.id}/confirm-offline?client_token=${encodeURIComponent(payload.client_token)}`);
    }
    ORDER = { id: order.id, client_token: payload.client_token, number: final.number, status: final.status };
    CART = {};
    resetToken();
    saveCart();
    document.querySelectorAll('.sheet').forEach(n => n.remove());
    MenuStore.refresh();
    refreshCart(data);
  } catch (e) {
    const dropped = e.data && e.data.detail && e.data.detail.unavailable;
    if (dropped) {
      showDropped(data, dropped, box);
    } else {
      box.appendChild(el('p', 'warn', esc(`${t('net.failed', LANG)} ${e.message}`)));
    }
  } finally {
    SENDING = false;
    button.disabled = false;
    button.textContent = t('cart.send', LANG);
  }
}

/** Позиція випала, поки гість тримав її в кошику. Оплата не пройшла — гість
    бачить, що саме, і може підтвердити решту. */
function showDropped(data, dropped, box) {
  const note = el('div', 'dropped');
  note.appendChild(el('p', null, esc(t('cart.dropped', LANG))));
  const ul = el('ul');
  dropped.forEach(d => {
    delete CART[d.key];
    ul.appendChild(el('li', null, esc(d.name || d.key)));
  });
  note.appendChild(ul);
  saveCart();

  if (cartCount()) {
    const rest = el('button', 'primary wide', esc(t('cart.confirmRest', LANG)));
    rest.type = 'button';
    rest.addEventListener('click', () => {
      document.querySelectorAll('.sheet').forEach(n => n.remove());
      openCart(data);
    });
    note.appendChild(rest);
  }
  box.appendChild(note);
}

/* ------------------------------------------------------ статус для гостя - */
let orderTimer = null;

function pollOrder(data) {
  if (orderTimer) clearInterval(orderTimer);
  const tick = async () => {
    if (!ORDER) return;
    try {
      const fresh = await API.get(
        `/api/orders/${ORDER.id}`, { client_token: ORDER.client_token });
      ORDER.status = fresh.status;
      ORDER.number = fresh.number;
      saveCart();
      refreshCart(data);
      if (fresh.status === 'served') { clearInterval(orderTimer); orderTimer = null; }
    } catch (e) { /* мовчки: наступна спроба через 10 секунд */ }
  };
  tick();
  orderTimer = setInterval(tick, 10000);
}
