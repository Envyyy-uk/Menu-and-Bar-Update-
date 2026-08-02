/* ==========================================================================
   Адмін-панель.

   Чого тут свідомо немає, на відміну від референсу: усього механізму
   публікації. Ні `overrides.js`, ні токена GitHub у localStorage, ні
   чернеток, ні банера «незбережена чернетка», ні «скинути чернетку».
   Зміна стану — це запис у Postgres, гість бачить її наступним опитуванням.
   Сервер тут не додає складності, а прибирає найбільший її шматок.

   Панель розрахована на телефон: керування вгорі й липке при прокрутці,
   кнопки станів на всю ширину рядка.
   ========================================================================== */

let LANG = getLang();
let ME = null;
let TAB = 'orders';   // черга — перше, заради чого відкривають панель у зміну
let ITEM_QUERY = '';
let ORDERS_TIMER = null;

const DATA = {
  items: [], sections: [], schedules: [], tables: [], users: [], devices: [], audit: [],
  orders: [], alerts: [], stripe: null, menu: null
};

const STATES = ['auto', 'on', 'off', 'soon'];
const may = p => !!(ME && ME.permissions.includes(p));

/* ----------------------------------------------------------- службове --- */
function flash(node, text, ok = true) {
  const tag = el('span', 'flash' + (ok ? '' : ' bad'), esc(text));
  node.appendChild(tag);
  setTimeout(() => tag.remove(), 1800);
}

async function guard(node, fn) {
  try {
    const out = await fn();
    if (node) flash(node, t('a.saved', LANG));
    return out;
  } catch (e) {
    if (e.status === 401) return renderLogin();
    if (node) flash(node, `${t('a.error', LANG)}: ${e.message}`, false);
    else alert(`${t('a.error', LANG)}: ${e.message}`);
    return null;
  }
}

/* --------------------------------------------------------------- вхід --- */
function renderLogin() {
  ME = null;
  const root = document.getElementById('app');
  root.innerHTML = '';
  const box = el('div', 'login');
  box.appendChild(el('h2', null, esc(t('a.login', LANG))));

  const form = el('form', 'stack');
  const email = el('input'); email.type = 'email'; email.placeholder = t('a.email', LANG); email.autocomplete = 'username';
  const pass = el('input'); pass.type = 'password'; pass.placeholder = t('a.password', LANG); pass.autocomplete = 'current-password';
  const submit = el('button', 'primary', esc(t('a.byPassword', LANG))); submit.type = 'submit';
  form.append(email, pass, submit);
  form.addEventListener('submit', async ev => {
    ev.preventDefault();
    await guard(box, async () => {
      ME = await API.post('/api/auth/login', { email: email.value, password: pass.value });
      await boot();
    });
  });
  box.appendChild(form);

  const pinForm = el('form', 'stack');
  const pin = el('input');
  pin.type = 'password'; pin.inputMode = 'numeric'; pin.autocomplete = 'one-time-code';
  pin.placeholder = t('a.pin', LANG); pin.maxLength = 12;
  const pinBtn = el('button', null, esc(t('a.byPin', LANG))); pinBtn.type = 'submit';
  pinForm.append(pin, pinBtn);
  pinForm.addEventListener('submit', async ev => {
    ev.preventDefault();
    await guard(box, async () => {
      ME = await API.post('/api/auth/pin', { pin: pin.value });
      await boot();
    });
  });
  box.append(el('p', 'hint', esc(t('a.pinHint', LANG))), pinForm);

  root.appendChild(box);
}

/* -------------------------------------------------------------- шапка --- */
function renderHeader() {
  const host = document.getElementById('who');
  host.innerHTML = '';
  if (!ME) return;
  host.appendChild(el('span', null, `${esc(ME.name)} · ${esc(ME.role)}`));
  const out = el('button', 'link', esc(t('a.logout', LANG)));
  out.type = 'button';
  out.addEventListener('click', async () => {
    await API.post('/api/auth/logout');
    renderLogin();
  });
  host.appendChild(out);
}

function tickClock() {
  const node = document.getElementById('clock');
  if (!node || !DATA.menu) return;
  node.textContent = `${venueClock(DATA.menu.venue.timezone, LANG)} · ${t('a.venueTime', LANG)}`;
}

/* ------------------------------------------------------------ вкладки --- */
function tabsFor() {
  const list = [['orders', 'a.tab.orders'], ['items', 'a.tab.items'], ['sections', 'a.tab.sections']];
  if (may('schedules.edit')) list.push(['schedules', 'a.tab.schedules']);
  if (may('tables.manage')) list.push(['tables', 'a.tab.tables']);
  if (may('users.create')) list.push(['users', 'a.tab.users']);
  if (may('audit.view')) list.push(['audit', 'a.tab.audit']);
  return list;
}

function renderTabs() {
  const host = document.getElementById('tabs');
  host.innerHTML = '';
  const nav = el('nav', 'tabs');
  tabsFor().forEach(([key, label]) => {
    const b = el('button', 'tab' + (key === TAB ? ' on' : ''), esc(t(label, LANG)));
    b.type = 'button';
    b.addEventListener('click', () => { TAB = key; renderTabs(); renderBody(); });
    nav.appendChild(b);
  });
  host.appendChild(nav);
}

/* -------------------------------------------------------- стани позиції - */
function stateButtons(current, onPick) {
  const box = el('div', 'states');
  STATES.forEach(s => {
    const b = el('button', 'sbtn s-' + s + (s === current ? ' on' : ''), esc(t('a.state.' + s, LANG)));
    b.type = 'button';
    b.addEventListener('click', () => onPick(s, box));
    box.appendChild(b);
  });
  return box;
}

function scheduleSelect(current) {
  const sel = el('select');
  const none = el('option', null, esc(t('a.noSchedule', LANG)));
  none.value = '';
  sel.appendChild(none);
  DATA.schedules.forEach(s => {
    const o = el('option', null, esc(s.label || s.key));
    o.value = s.key;
    if (s.key === current) o.selected = true;
    sel.appendChild(o);
  });
  return sel;
}

/* ------------------------------------------------------------ позиції --- */
function renderItems(mount) {
  const bar = el('div', 'rowbar');
  const search = el('input', 'search');
  search.type = 'search';
  search.placeholder = t('a.search', LANG);
  search.value = ITEM_QUERY;
  search.addEventListener('input', () => {
    ITEM_QUERY = search.value.toLowerCase();
    mount.querySelectorAll('.arow').forEach(r => {
      r.style.display = r.dataset.search.includes(ITEM_QUERY) ? '' : 'none';
    });
  });
  bar.appendChild(search);
  mount.appendChild(bar);

  const live = {};
  (DATA.menu ? DATA.menu.items : []).forEach(i => { live[i.key] = i.available; });

  DATA.items.forEach(item => {
    const row = el('div', 'arow');
    row.dataset.search = (item.name + ' ' + item.key).toLowerCase();

    const head = el('div', 'arow-head');
    head.appendChild(el('b', null, esc(item.name)));
    const av = live[item.key];
    if (av) {
      head.appendChild(el('span', 'pill ' + (av.open ? 'ok' : 'off'),
        esc(av.open ? t('a.openNow', LANG) : t('a.closedNow', LANG))));
    }
    row.appendChild(head);

    // 86 і стани доступні всім, включно із залом — це і є щоденна робота
    row.appendChild(stateButtons(item.state, async (state, box) => {
      const saved = await guard(row, () => API.patch(`/api/admin/items/${item.id}`, { state }));
      if (!saved) return;
      item.state = state;
      box.querySelectorAll('.sbtn').forEach(b => b.classList.toggle('on', b.textContent === t('a.state.' + state, LANG)));
      refreshLive();
    }));

    const fields = el('div', 'fields');

    if (item.state === 'soon') {
      const opens = el('input');
      opens.type = 'datetime-local';
      opens.value = item.opens_at || '';
      opens.addEventListener('change', () => guard(row, async () => {
        await API.patch(`/api/admin/items/${item.id}`, { opens_at: opens.value ? opens.value.slice(0, 16) : null });
        item.opens_at = opens.value.slice(0, 16);
        refreshLive();
      }));
      fields.append(el('label', null, esc(t('a.opensAt', LANG))), opens);
    }

    const sched = scheduleSelect(item.schedule_key);
    sched.addEventListener('change', () => guard(row, async () => {
      await API.patch(`/api/admin/items/${item.id}`, { schedule_key: sched.value || null });
      item.schedule_key = sched.value || null;
      refreshLive();
    }));
    fields.append(el('label', null, esc(t('a.schedule', LANG))), sched);

    if (may('items.edit')) {
      const price = el('input');
      price.type = 'number'; price.min = '0'; price.step = '0.05';
      price.value = (item.price_pence / 100).toFixed(2);
      price.addEventListener('change', () => guard(row, async () => {
        const pence = Math.round(parseFloat(price.value || '0') * 100);
        await API.patch(`/api/admin/items/${item.id}`, { price_pence: pence });
        item.price_pence = pence;
      }));
      fields.append(el('label', null, esc(t('a.price', LANG))), price);

      const station = el('select');
      [['kitchen', 'a.kitchen'], ['bar', 'a.bar']].forEach(([v, k]) => {
        const o = el('option', null, esc(t(k, LANG)));
        o.value = v;
        if (v === item.station) o.selected = true;
        station.appendChild(o);
      });
      station.addEventListener('change', () => guard(row, async () => {
        await API.patch(`/api/admin/items/${item.id}`, { station: station.value });
        item.station = station.value;
      }));
      fields.append(el('label', null, esc(t('a.station', LANG))), station);

      // Курс подачі: напої йдуть одразу, решта — по черзі
      const course = el('select');
      [0, 1, 2, 3].forEach(c => {
        const o = el('option', null, esc(t('a.course.' + c, LANG)));
        o.value = String(c);
        if (c === item.course) o.selected = true;
        course.appendChild(o);
      });
      course.addEventListener('change', () => guard(row, async () => {
        await API.patch(`/api/admin/items/${item.id}`, { course: Number(course.value) });
        item.course = Number(course.value);
      }));
      fields.append(el('label', null, esc(t('a.course', LANG))), course);
    } else {
      // Ціну зал бачить, але не редагує. Ховати її було б брехнею: вона
      // однаково є в меню гостя.
      fields.append(el('label', null, esc(t('a.price', LANG))),
        el('span', 'ro', esc(money(item.price_pence, DATA.menu ? DATA.menu.venue.currency : 'GBP', LANG))));
    }

    row.appendChild(fields);
    mount.appendChild(row);
  });
}

/* ------------------------------------------------------------ розділи --- */
function renderSections(mount) {
  DATA.sections.forEach(sec => {
    const row = el('div', 'arow');
    row.appendChild(el('div', 'arow-head', `<b>${esc(pick(sec.names, LANG) || sec.key)}</b>`));
    row.appendChild(stateButtons(sec.state, async (state, box) => {
      const ok = await guard(row, () => API.patch(`/api/admin/sections/${sec.id}`, { state }));
      if (!ok) return;
      sec.state = state;
      box.querySelectorAll('.sbtn').forEach(b => b.classList.toggle('on', b.textContent === t('a.state.' + state, LANG)));
      refreshLive();
    }));
    const fields = el('div', 'fields');
    const sched = scheduleSelect(sec.schedule_key);
    sched.addEventListener('change', () => guard(row, async () => {
      await API.patch(`/api/admin/sections/${sec.id}`, { schedule_key: sched.value || null });
      sec.schedule_key = sched.value || null;
      refreshLive();
    }));
    fields.append(el('label', null, esc(t('a.schedule', LANG))), sched);
    row.appendChild(fields);
    mount.appendChild(row);
  });
}

/* ---------------------------------------------------------- розклади ---- */
function renderSchedules(mount) {
  const dayNames = t('sched.days', LANG).split(',');

  DATA.schedules.forEach(s => {
    const row = el('div', 'arow');
    row.appendChild(el('div', 'arow-head', `<b>${esc(s.label || s.key)}</b><span class="ro">${esc(s.key)}</span>`));
    const ranges = JSON.parse(JSON.stringify(s.ranges || []));
    const list = el('div', 'ranges');

    const draw = () => {
      list.innerHTML = '';
      ranges.forEach((r, idx) => {
        const box = el('div', 'range');
        const days = el('div', 'days');
        // тиждень читаємо з понеділка, а не з неділі
        [1, 2, 3, 4, 5, 6, 0].forEach(d => {
          const b = el('button', 'dbtn' + (r.days.includes(d) ? ' on' : ''), esc(dayNames[d]));
          b.type = 'button';
          b.addEventListener('click', () => {
            r.days = r.days.includes(d) ? r.days.filter(x => x !== d) : [...r.days, d];
            draw();
          });
          days.appendChild(b);
        });
        const from = el('input'); from.type = 'time'; from.value = r.from;
        from.addEventListener('change', () => { r.from = from.value; });
        const to = el('input'); to.type = 'time'; to.value = r.to;
        to.addEventListener('change', () => { r.to = to.value; });
        const drop = el('button', 'link', '×');
        drop.type = 'button';
        drop.addEventListener('click', () => { ranges.splice(idx, 1); draw(); });
        box.append(days, from, el('span', null, '–'), to, drop);
        list.appendChild(box);
      });
    };
    draw();
    row.appendChild(list);
    row.appendChild(el('p', 'hint', esc(t('a.sched.midnight', LANG))));

    const add = el('button', null, esc(t('a.sched.addRange', LANG)));
    add.type = 'button';
    add.addEventListener('click', () => { ranges.push({ days: [1, 2, 3, 4, 5], from: '12:00', to: '17:30' }); draw(); });

    const save = el('button', 'primary', esc(t('a.save', LANG)));
    save.type = 'button';
    save.addEventListener('click', () => guard(row, async () => {
      const out = await API.patch(`/api/admin/schedules/${s.id}`, { ranges });
      s.ranges = out.ranges;
      refreshLive();
    }));

    const drop = el('button', 'danger', esc(t('a.delete', LANG)));
    drop.type = 'button';
    drop.addEventListener('click', () => {
      if (!confirm(t('a.confirm', LANG))) return;
      guard(row, async () => {
        await API.del(`/api/admin/schedules/${s.id}`);
        await reload();
      });
    });

    row.appendChild(el('div', 'actions')).append(add, save, drop);
    mount.appendChild(row);
  });

  const form = el('form', 'arow stack');
  form.appendChild(el('b', null, esc(t('a.sched.new', LANG))));
  const key = el('input'); key.placeholder = t('a.sched.key', LANG); key.required = true;
  const label = el('input'); label.placeholder = t('a.users.name', LANG);
  const btn = el('button', 'primary', esc(t('a.add', LANG))); btn.type = 'submit';
  form.append(key, label, btn);
  form.addEventListener('submit', ev => {
    ev.preventDefault();
    guard(form, async () => {
      await API.post('/api/admin/schedules', {
        key: key.value.trim(), label: label.value.trim(),
        ranges: [{ days: [1, 2, 3, 4, 5], from: '12:00', to: '17:30' }]
      });
      await reload();
    });
  });
  mount.appendChild(form);
}

/* ------------------------------------------------------------- столи ---- */
function renderTables(mount) {
  DATA.tables.forEach(tb => {
    const row = el('div', 'arow');
    row.appendChild(el('div', 'arow-head', `<b>${esc(tb.label)}</b>`));
    row.appendChild(el('p', 'ro url', esc(tb.url)));

    const img = el('img', 'qr');
    img.alt = `QR ${tb.label}`;
    img.loading = 'lazy';
    img.src = `/api/admin/tables/${tb.id}/qr.png?v=${encodeURIComponent(tb.token_rotated_at || '')}`;
    row.appendChild(img);

    const actions = el('div', 'actions');

    const print = el('button', null, esc(t('a.tables.print', LANG)));
    print.type = 'button';
    print.addEventListener('click', () => printQr(tb, img.src));

    const rotate = el('button', 'danger', esc(t('a.tables.rotate', LANG)));
    rotate.type = 'button';
    rotate.addEventListener('click', () => {
      if (!confirm(t('a.tables.rotateWarn', LANG) + '\n' + t('a.confirm', LANG))) return;
      guard(row, async () => {
        const out = await API.post(`/api/admin/tables/${tb.id}/rotate`);
        tb.url = out.url;
        tb.token_rotated_at = out.token_rotated_at;
        row.querySelector('.url').textContent = out.url;
        img.src = `/api/admin/tables/${tb.id}/qr.png?v=${encodeURIComponent(out.token_rotated_at)}`;
      });
    });

    const active = el('label', 'check');
    active.innerHTML = `<input type="checkbox"${tb.active ? ' checked' : ''}> ${esc(t('a.tables.active', LANG))}`;
    active.querySelector('input').addEventListener('change', ev => guard(row, async () => {
      await API.patch(`/api/admin/tables/${tb.id}`, { active: ev.target.checked });
      tb.active = ev.target.checked;
    }));

    actions.append(print, rotate, active);
    row.appendChild(actions);
    mount.appendChild(row);
  });

  const form = el('form', 'arow stack');
  form.appendChild(el('b', null, esc(t('a.tables.new', LANG))));
  const label = el('input'); label.placeholder = 'Bar 4'; label.required = true;
  const btn = el('button', 'primary', esc(t('a.add', LANG))); btn.type = 'submit';
  form.append(label, btn);
  form.addEventListener('submit', ev => {
    ev.preventDefault();
    guard(form, async () => {
      await API.post('/api/admin/tables', { label: label.value.trim() });
      await reload();
    });
  });
  mount.appendChild(form);
}

/**
 * Друк наліпки зі свого ж вікна.
 *
 * Свідомо без `window.open`: нове вікно блокує і Safari на телефоні, і будь-який
 * вбудований фрейм — кнопка тоді просто мовчить. Замість цього кладемо наліпку
 * в приховану область і друкуємо поточну сторінку; решту ховає `@media print`.
 */
function printQr(table, src) {
  let area = document.getElementById('printarea');
  if (!area) {
    area = el('div', null);
    area.id = 'printarea';
    document.body.appendChild(area);
  }
  area.innerHTML =
    `<h1>${esc(table.label)}</h1>` +
    (src ? `<img src="${esc(src)}" alt="QR ${esc(table.label)}">` : '') +
    `<p class="url">${esc(table.url)}</p>` +
    `<p class="hint">${esc(t('a.tables.printHint', LANG))}</p>`;

  const done = () => { area.innerHTML = ''; window.removeEventListener('afterprint', done); };
  window.addEventListener('afterprint', done);

  const img = area.querySelector('img');
  // Картинку треба дочекатися: інакше на аркуш піде порожнє місце
  if (img && !img.complete) {
    img.addEventListener('load', () => window.print());
    img.addEventListener('error', () => window.print());
  } else {
    window.print();
  }
}

/* -------------------------------------------------------------- люди ---- */
const ROLE_ORDER = ['owner', 'head_manager', 'manager', 'staff'];

function renderUsers(mount) {
  DATA.users.forEach(u => {
    const row = el('div', 'arow');
    row.appendChild(el('div', 'arow-head',
      `<b>${esc(u.name)}</b><span class="pill">${esc(u.role)}</span>` +
      (u.active ? '' : `<span class="pill off">${esc(t('a.state.off', LANG))}</span>`)));
    if (u.email) row.appendChild(el('p', 'ro', esc(u.email)));

    const actions = el('div', 'actions');
    const pin = el('button', null, esc(u.has_pin ? t('a.users.resetPin', LANG) : t('a.users.withPin', LANG)));
    pin.type = 'button';
    pin.addEventListener('click', () => guard(row, async () => {
      const out = await API.post(`/api/admin/users/${u.id}/pin`);
      u.has_pin = true;
      // PIN показується один раз — далі в базі лише хеш
      row.appendChild(el('p', 'pin-once', `${esc(t('a.users.pinOnce', LANG))} <b>${esc(out.pin)}</b>`));
    }));
    actions.appendChild(pin);

    const toggle = el('button', u.active ? 'danger' : '', esc(u.active ? t('a.state.off', LANG) : t('a.state.on', LANG)));
    toggle.type = 'button';
    toggle.addEventListener('click', () => guard(row, async () => {
      await API.patch(`/api/admin/users/${u.id}`, { active: !u.active });
      await reload();
    }));
    actions.appendChild(toggle);

    row.appendChild(actions);
    mount.appendChild(row);
  });

  const form = el('form', 'arow stack');
  form.appendChild(el('b', null, esc(t('a.users.new', LANG))));
  const name = el('input'); name.placeholder = t('a.users.name', LANG); name.required = true;
  const role = el('select');
  // Ролі, вищі або рівні власній, у списку не з'являються взагалі
  ROLE_ORDER.filter(r => ROLE_ORDER.indexOf(r) > ROLE_ORDER.indexOf(ME.role)).forEach(r => {
    const o = el('option', null, r); o.value = r; role.appendChild(o);
  });
  const email = el('input'); email.type = 'email'; email.placeholder = t('a.email', LANG);
  const pass = el('input'); pass.type = 'password'; pass.placeholder = t('a.password', LANG);
  const withPin = el('label', 'check');
  withPin.innerHTML = `<input type="checkbox"> ${esc(t('a.users.withPin', LANG))}`;
  const btn = el('button', 'primary', esc(t('a.add', LANG))); btn.type = 'submit';
  form.append(name, role, email, pass, withPin, btn);
  form.addEventListener('submit', ev => {
    ev.preventDefault();
    guard(form, async () => {
      const out = await API.post('/api/admin/users', {
        name: name.value.trim(),
        role: role.value,
        email: email.value.trim() || null,
        password: pass.value || null,
        with_pin: withPin.querySelector('input').checked
      });
      if (out.pin) alert(`${t('a.users.pinOnce', LANG)}\n\n${out.pin}`);
      await reload();
    });
  });
  mount.appendChild(form);

  // --- пристрої
  const box = el('div', 'arow');
  box.appendChild(el('b', null, esc(t('a.devices', LANG))));
  DATA.devices.forEach(d => {
    const line = el('p', 'ro', `${esc(d.label)} — ${d.active ? '✓' : '×'}`);
    const b = el('button', 'link', esc(d.active ? t('a.state.off', LANG) : t('a.state.on', LANG)));
    b.type = 'button';
    b.addEventListener('click', () => guard(box, async () => {
      await API.patch(`/api/admin/devices/${d.id}`, { active: !d.active });
      await reload();
    }));
    line.appendChild(b);
    box.appendChild(line);
  });
  box.appendChild(el('p', 'hint', esc(t('a.devices.hint', LANG))));
  const reg = el('button', 'primary', esc(t('a.devices.new', LANG)));
  reg.type = 'button';
  reg.addEventListener('click', () => guard(box, async () => {
    await API.post('/api/admin/devices', { label: `Device ${new Date().toISOString().slice(0, 16)}` });
    await reload();
  }));
  box.appendChild(reg);
  mount.appendChild(box);
}

/* -------------------------------------------------------- замовлення ---- */
function renderOrders(mount) {
  if (may('stripe.manage') && DATA.stripe) {
    const card = el('div', 'arow');
    card.appendChild(el('b', null, esc(t('a.stripe', LANG))));
    const s = DATA.stripe;
    if (!s.enabled) {
      card.appendChild(el('p', 'warn', esc(t('a.stripe.offline', LANG))));
    } else {
      card.appendChild(el('p', 'ro',
        esc(s.charges_enabled ? t('a.stripe.ok', LANG) : t('a.stripe.pending', LANG))));
    }
    if (!s.enabled || !s.charges_enabled) {
      const connect = el('button', 'primary', esc(t('a.stripe.connect', LANG)));
      connect.type = 'button';
      connect.addEventListener('click', () => guard(card, async () => {
        const out = await API.post('/api/admin/stripe/connect');
        location.href = out.url;
      }));
      card.appendChild(connect);
    }
    mount.appendChild(card);
  }

  const lateIds = new Set(DATA.alerts.map(a => a.id));
  if (!DATA.orders.length) {
    mount.appendChild(el('p', 'hint', esc(t('a.orders.empty', LANG))));
    return;
  }

  DATA.orders.forEach(order => {
    const row = el('div', 'arow' + (lateIds.has(order.id) ? ' late' : ''));
    const head = el('div', 'arow-head');
    head.appendChild(el('b', null, `№${esc(order.number)} · ${esc(order.table || '—')}`));
    head.appendChild(el('span', 'pill', esc(t('order.st.' + order.status, LANG))));
    head.appendChild(el('span', 'pill',
      esc(money(order.total_pence, DATA.menu.venue.currency, LANG))));
    row.appendChild(head);

    // Оплачено й досі не прийнято — це той самий алерт, який кричить на кухні
    if (lateIds.has(order.id)) row.appendChild(el('p', 'warn', esc(t('a.orders.late', LANG))));

    const list = el('ul', 'ing');
    order.items.forEach(i => list.appendChild(el('li', null,
      `${esc(i.name)} × ${i.qty} · ${esc(t(i.station === 'bar' ? 'a.bar' : 'a.kitchen', LANG))}` +
      ` · ${esc(t('a.course.' + (i.course || 0), LANG))}`)));
    row.appendChild(list);
    if (order.note) row.appendChild(el('p', 'ro', esc(order.note)));

    // Запуск курсу — робота залу. Кухня чекає саме цієї кнопки.
    (order.tickets || []).filter(tk => tk.awaiting_fire).forEach(tk => {
      const line = el('div', 'fire-line');
      line.appendChild(el('span', 'ro',
        `${esc(t('a.course.' + tk.course, LANG))} · ${esc(t(tk.station === 'bar' ? 'a.bar' : 'a.kitchen', LANG))}`));
      const go = el('button', 'primary', esc(t('a.fire', LANG)));
      go.type = 'button';
      go.disabled = !tk.can_fire;
      go.addEventListener('click', () => guard(row, async () => {
        await API.post(`/api/orders/tickets/${tk.id}/fire`);
        await reload();
      }));
      line.appendChild(go);
      if (!tk.can_fire) line.appendChild(el('span', 'ro', esc(t('a.fire.wait', LANG))));
      row.appendChild(line);
    });
    if ((order.tickets || []).some(tk => tk.awaiting_fire)) {
      row.appendChild(el('p', 'hint', esc(t('a.fire.hint', LANG))));
    }

    const actions = el('div', 'actions');
    const next = { paid: 'accepted', accepted: 'ready', ready: 'served' }[order.status];
    if (next) {
      const move = el('button', 'primary', esc(t('a.orders.' + next, LANG)));
      move.type = 'button';
      move.addEventListener('click', () => guard(row, async () => {
        await API.post(`/api/orders/${order.id}/status?target=${next}`);
        await reload();
      }));
      actions.appendChild(move);
    }

    if (may('refunds')) {
      const refund = el('button', 'danger', esc(t('a.refund', LANG)));
      refund.type = 'button';
      refund.addEventListener('click', () => askRefund(order, row));
      actions.appendChild(refund);
      const ceiling = ME.refund_limit_pence;
      actions.appendChild(el('span', 'ro',
        `${esc(t('a.refund.limit', LANG))}: ${ceiling === null
          ? esc(t('a.refund.none', LANG))
          : esc(money(ceiling, DATA.menu.venue.currency, LANG))}`));
    }
    row.appendChild(actions);
    mount.appendChild(row);
  });
}

function askRefund(order, row) {
  const box = el('div', 'stack');
  const amount = el('input');
  amount.type = 'number'; amount.step = '0.05'; amount.min = '0.01';
  amount.value = ((order.total_pence - (order.refunded_pence || 0)) / 100).toFixed(2);
  const go = el('button', 'danger', esc(t('a.refund', LANG)));
  go.type = 'button';
  go.addEventListener('click', () => guard(row, async () => {
    await API.post(`/api/orders/${order.id}/refund`, {
      amount_pence: Math.round(parseFloat(amount.value || '0') * 100)
    });
    await reload();
  }));
  box.append(el('label', null, esc(t('a.refund.amount', LANG))), amount, go);
  row.appendChild(box);
}

/* ------------------------------------------------------------- аудит ---- */
function renderAudit(mount) {
  if (!DATA.audit.length) { mount.appendChild(el('p', 'hint', esc(t('a.empty', LANG)))); return; }
  const table = el('table', 'audit');
  table.innerHTML =
    `<thead><tr><th>${esc(t('a.audit.when', LANG))}</th><th>${esc(t('a.audit.who', LANG))}</th>` +
    `<th>${esc(t('a.audit.what', LANG))}</th></tr></thead>`;
  const body = el('tbody');
  DATA.audit.forEach(r => {
    const tr = el('tr');
    const when = new Date(r.at).toLocaleString(LANG, { dateStyle: 'short', timeStyle: 'short' });
    const diff = r.before && r.after
      ? Object.keys(r.after).map(k => `${k}: ${JSON.stringify(r.before[k])} → ${JSON.stringify(r.after[k])}`).join(', ')
      : JSON.stringify(r.after || r.before || {});
    tr.innerHTML = `<td>${esc(when)}</td><td>${esc(r.who)}</td>` +
      `<td><b>${esc(r.action)}</b> ${esc(r.entity)}<small>${esc(diff)}</small></td>`;
    body.appendChild(tr);
  });
  table.appendChild(body);
  mount.appendChild(table);
}

/* ------------------------------------------------------------ збірка ---- */
function renderBody() {
  const mount = document.getElementById('body');
  mount.innerHTML = '';
  ({
    orders: renderOrders,
    items: renderItems,
    sections: renderSections,
    schedules: renderSchedules,
    tables: renderTables,
    users: renderUsers,
    audit: renderAudit
  }[TAB] || renderItems)(mount);
}

/** Перечитати те, що показує гість: після зміни стану підпис «доступно
    зараз» має оновитися й тут, а не лише в гостя. */
async function refreshLive() {
  DATA.menu = await API.get('/api/menu');
  if (TAB === 'items') renderBody();
}

async function reload() {
  const jobs = [
    API.get('/api/menu').then(d => { DATA.menu = d; }),
    API.get('/api/admin/items').then(d => { DATA.items = d; }),
    API.get('/api/admin/sections').then(d => { DATA.sections = d; }),
    API.get('/api/admin/schedules').then(d => { DATA.schedules = d; })
  ];
  if (may('tables.manage')) jobs.push(API.get('/api/admin/tables').then(d => { DATA.tables = d; }));
  if (may('users.create')) {
    jobs.push(API.get('/api/admin/users').then(d => { DATA.users = d; }));
    jobs.push(API.get('/api/admin/devices').then(d => { DATA.devices = d; }));
  }
  if (may('audit.view')) jobs.push(API.get('/api/admin/audit').then(d => { DATA.audit = d; }));
  if (may('orders.view')) {
    jobs.push(API.get('/api/orders').then(d => { DATA.orders = d; }));
    jobs.push(API.get('/api/orders/alerts').then(d => { DATA.alerts = d; }));
  }
  if (may('stripe.manage')) jobs.push(API.get('/api/admin/stripe').then(d => { DATA.stripe = d; }));
  await Promise.all(jobs);
  renderTabs();
  renderBody();
  tickClock();
}

async function boot() {
  document.getElementById('app').innerHTML =
    '<div id="tabs"></div><div id="body"></div>';
  renderHeader();
  if (!tabsFor().some(([k]) => k === TAB)) TAB = 'orders';
  await reload();
  // Черга живе сама: замовлення приходять, поки менеджер дивиться в екран.
  if (ORDERS_TIMER) clearInterval(ORDERS_TIMER);
  ORDERS_TIMER = setInterval(() => { if (ME && TAB === 'orders') reload(); }, 10000);
}

async function initAdmin() {
  applyTheme(getTheme());
  buildSwitches(document.querySelector('.switches'), async code => {
    LANG = code;
    document.querySelectorAll('[data-i18n]').forEach(n => { n.innerHTML = t(n.dataset.i18n, LANG); });
    refreshSwitches(LANG);
    if (ME) await boot(); else renderLogin();
  });
  buildTopButton();
  document.querySelectorAll('[data-i18n]').forEach(n => { n.innerHTML = t(n.dataset.i18n, LANG); });
  refreshSwitches(LANG);
  setInterval(tickClock, 10000);

  try {
    ME = await API.get('/api/auth/me');
    await boot();
  } catch (e) {
    renderLogin();
  }
}
