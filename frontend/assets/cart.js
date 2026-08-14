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

  // Повернення зі Stripe: /t/{token}?order={id}. Саме по собі воно нічого не
  // підтверджує — статус усе одно питаємо в сервера, а туди його поставить
  // вебхук.
  const back = new URLSearchParams(location.search).get('order');
  if (back && ORDER && ORDER.id !== back) ORDER = null;
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

/* Рядок кошика більше не дорівнює позиції меню: два мохіто різних смаків —
   це два рядки. Тому ключ рядка складений із ключа позиції й обраних
   варіантів. Групи сортуємо, щоб той самий вибір завжди давав той самий
   ключ, у якому б порядку його не зробили. */
function lineKey(key, options) {
  const parts = Object.keys(options || {}).sort().map(g => `${g}=${options[g]}`);
  return parts.length ? key + '|' + parts.join(';') : key;
}

function parseLine(line) {
  const [key, tail] = String(line).split('|');
  const options = {};
  if (tail) tail.split(';').forEach(pair => {
    const [g, c] = pair.split('=');
    if (g) options[g] = c;
  });
  return { key, options };
}

/** Ціна з урахуванням варіантів. Сервер рахує це саме ще раз — тут лише
    щоб гість бачив підсумок до оплати. */
function linePrice(item, options) {
  let price = item.price_pence;
  let add = 0;
  (item.options || []).forEach(group => {
    const picked = (options || {})[group.key];
    const choice = (group.choices || []).find(x => x.key === picked);
    if (!choice) return;
    if (choice.price_pence !== undefined && choice.price_pence !== null) price = choice.price_pence;
    add += choice.add_pence || 0;
  });
  return price + add;
}

/** Назви обраних варіантів — те саме, що потім побачить бармен на марці. */
function optionNames(item, options) {
  return (item.options || []).map(group => {
    const choice = (group.choices || []).find(x => x.key === (options || {})[group.key]);
    return choice ? choice.name : null;
  }).filter(Boolean);
}

function cartTotal(data) {
  return Object.entries(CART).reduce((sum, [line, qty]) => {
    const { key, options } = parseLine(line);
    const item = data.items.find(i => i.key === key);
    return sum + (item ? linePrice(item, options) * qty : 0);
  }, 0);
}

/** Скільки цієї позиції в кошику разом, усіма варіантами. Саме це число
    показує картка в меню. */
function qtyOf(itemKey) {
  return Object.entries(CART).reduce(
    (n, [line, qty]) => n + (parseLine(line).key === itemKey ? qty : 0), 0);
}

/* ------------------------------------------------------- вибір варіанта -- */
/** Аркуш вибору: «яке саме мохіто», «50 мл чи пляшка».

    Відкривається лише для позицій із варіантами. Пропустити вибір не можна —
    «Мохіто» без смаку це не замовлення, а загадка для бармена, тож кнопка
    лишається неактивною, поки не обрано все. */
function openOptions(item, data) {
  document.querySelectorAll('.sheet').forEach(n => n.remove());
  const sheet = el('div', 'sheet');
  const box = el('div', 'sheet-box opt-box');
  sheet.appendChild(box);

  box.appendChild(el('h2', null, esc(item.name)));
  const picked = {};

  const price = el('p', 'opt-price');
  const add = el('button', 'primary wide', esc(t('cart.add', LANG)));
  add.type = 'button';

  const sync = () => {
    const all = (item.options || []).every(g => picked[g.key]);
    add.disabled = !all;
    price.textContent = money(linePrice(item, picked), data.venue.currency, LANG);
  };

  (item.options || []).forEach(group => {
    box.appendChild(el('p', 'opt-label', esc(t(group.label, LANG))));
    const row = el('div', 'opt-row');
    group.choices.forEach(choice => {
      const b = el('button', 'opt-btn', esc(choice.name));
      b.type = 'button';
      b.addEventListener('click', () => {
        picked[group.key] = choice.key;
        row.querySelectorAll('.opt-btn').forEach(x => x.classList.toggle('on', x === b));
        sync();
      });
      row.appendChild(b);
    });
    box.appendChild(row);
  });

  box.append(price, add);
  add.addEventListener('click', () => {
    const line = lineKey(item.key, picked);
    CART[line] = (CART[line] || 0) + 1;
    saveCart();
    sheet.remove();
    refreshCart(data);
  });

  const close = el('button', 'wide', esc(t('cart.close', LANG)));
  close.type = 'button';
  close.addEventListener('click', () => sheet.remove());
  box.appendChild(close);

  sync();
  sheet.addEventListener('click', ev => { if (ev.target === sheet) sheet.remove(); });
  document.body.appendChild(sheet);
}

/* ---------------------------------------------------- кнопки на картках -- */
function orderControls(item, data) {
  const slot = el('div', 'order-line');
  const qty = qtyOf(item.key);
  const hasOptions = (item.options || []).length > 0;

  // Позиція з варіантами завжди веде через аркуш вибору: «+» на картці не
  // знає, яке саме мохіто додавати другим.
  if (!qty || hasOptions) {
    const addBtn = el('button', 'add-btn', esc(hasOptions ? t('cart.choose', LANG) : t('cart.add', LANG)));
    addBtn.type = 'button';
    addBtn.addEventListener('click', () => {
      if (hasOptions) return openOptions(item, data);
      CART[item.key] = 1;
      saveCart();
      refreshCart(data);
    });
    if (qty) slot.appendChild(el('span', 'qty', String(qty)));
    slot.appendChild(addBtn);
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
  Object.keys(CART).forEach(line => {
    const item = data.items.find(i => i.key === parseLine(line).key);
    if (!item || !item.orderable || !(item.available || {}).open) delete CART[line];
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

/** Рядок кошика: кількість і видалення прямо тут.

    Керування має бути там, де гість дивиться на підсумок. Відправляти його
    шукати ту саму картку в меню, щоб прибрати одну позицію, — це змусити
    прокрутити півменю з відкритим кошиком. */
function cartLine(key, qty, data, redraw) {
  const { key: itemKey, options } = parseLine(key);
  const item = data.items.find(i => i.key === itemKey);
  const li = el('li');
  if (!item) {
    // Позиція зникла з меню, поки кошик лежав відкритим — прибираємо мовчки.
    delete CART[key];
    saveCart();
    return null;
  }

  const info = el('div', 'cart-info');
  // Обраний варіант поруч із назвою: без нього два рядки «Mojito» виглядають
  // як помилка кошика, а не як два різні напої.
  const chosen = optionNames(item, options);
  info.appendChild(el('span', 'cart-name',
    esc(item.name) + (chosen.length ? ` <span class="cart-opt">· ${esc(chosen.join(' · '))}</span>` : '')));
  info.appendChild(el('span', 'cart-price',
    esc(money(linePrice(item, options) * qty, data.venue.currency, LANG))));

  const controls = el('div', 'order-line');
  const minus = el('button', 'qty-btn', '−');
  minus.type = 'button';
  minus.setAttribute('aria-label', `− ${item.name} ${chosen.join(' ')}`);
  minus.addEventListener('click', () => {
    CART[key] = qty - 1;
    if (CART[key] <= 0) delete CART[key];
    saveCart();
    redraw();
  });

  const plus = el('button', 'qty-btn', '+');
  plus.type = 'button';
  plus.setAttribute('aria-label', `+ ${item.name} ${chosen.join(' ')}`);
  plus.addEventListener('click', () => { CART[key] = qty + 1; saveCart(); redraw(); });

  const drop = el('button', 'drop-btn', '×');
  drop.type = 'button';
  drop.title = t('cart.remove', LANG);
  drop.setAttribute('aria-label', `${t('cart.remove', LANG)}: ${item.name} ${chosen.join(' ')}`);
  drop.addEventListener('click', () => { delete CART[key]; saveCart(); redraw(); });

  controls.append(minus, el('span', 'qty', String(qty)), plus, drop);
  li.append(info, controls);
  return li;
}

function openCart(data) {
  document.querySelectorAll('.sheet').forEach(n => n.remove());
  const sheet = el('div', 'sheet');
  const box = el('div', 'sheet-box');
  sheet.appendChild(box);

  // Побажання переживають перемальовування списку: гість міг написати їх
  // до того, як передумав щодо однієї позиції.
  let noteText = '';

  const draw = () => {
    box.innerHTML = '';
    box.appendChild(el('h2', null, esc(t('cart.title', LANG))));

    if (!cartCount()) {
      box.appendChild(el('p', 'hint', esc(t('cart.empty', LANG))));
    } else {
      const list = el('ul', 'cart-list');
      Object.entries(CART).forEach(([key, qty]) => {
        const li = cartLine(key, qty, data, draw);
        if (li) list.appendChild(li);
      });
      box.appendChild(list);
      box.appendChild(el('p', 'cart-total',
        `${esc(t('cart.total', LANG))}: <b>${esc(money(cartTotal(data), data.venue.currency, LANG))}</b>`));

      const note = el('textarea', 'note');
      note.placeholder = t('cart.note', LANG);
      note.rows = 2;
      note.value = noteText;
      note.addEventListener('input', () => { noteText = note.value; });
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

    // Картки в меню й панель унизу мають показувати те саме, що й кошик
    refreshCart(data);
  };

  draw();

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
    items: Object.entries(CART).map(([line, qty]) => {
      const { key, options } = parseLine(line);
      return { key, qty, options };
    }),
    note: note || null
  };

  try {
    const order = await API.post('/api/orders', payload);
    const checkout = await API.post(
      `/api/orders/${order.id}/checkout?client_token=${encodeURIComponent(payload.client_token)}`);

    if (checkout && checkout.mode === 'stripe') {
      // Гість лишається тут: гаманці й картка — в наступному аркуші.
      // Замовлення стане `paid` від вебхука, а не від того, що Stripe.js
      // відповів «успіх»: гість може згорнути вкладку рівно між списанням
      // і відповіддю, і замовлення все одно має дійти до кухні.
      ORDER = { id: order.id, client_token: payload.client_token, number: order.number, status: order.status };
      CART = {};
      resetToken();
      saveCart();
      document.querySelectorAll('.sheet').forEach(n => n.remove());
      MenuStore.refresh();
      refreshCart(data);
      openPaymentSheet(checkout, data, () => pollOrder(data));
      return;
    }

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
