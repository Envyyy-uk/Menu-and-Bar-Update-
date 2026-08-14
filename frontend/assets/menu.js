/* ==========================================================================
   Гостьове меню: рендеринг з API, пошук по складнику шістьма мовами,
   фільтр за алергенами, розклади.

   Головна відмінність від референсу — джерело даних. Меню, стани й розклади
   приходять з сервера й перепитуються самі, тож зміна в панелі доходить до
   гостя без перезавантаження. Модель даних та сама: склад — ключі словника,
   алергени на трьох рівнях, джерело з датою.
   ========================================================================== */

let LANG = getLang();

/* Стан фільтрів переживає перемальовування: меню оновлюється саме, і
   скидати гостю пошук посеред читання неприпустимо. */
const FILTER = { query: '' };

/* Чи вже намальовано хоч раз. Меню перепитується щохвилини кілька разів, і
   перемальовувати його, коли нічого не змінилося, не можна: це закриває
   панель фільтрів під пальцем і забирає фокус із пошуку. */
let RENDERED = false;

/* Стіл із QR: { id, label }. Порожньо — меню просто читають. */
let TABLE = null;

/* ------------------------------------------------------------- склад ---- */
function ingName(key, lexicon, lang) {
  if (typeof key !== 'string') return '';
  if (key.startsWith('~')) return key.slice(1);   // марка — як є
  const entry = lexicon[key];
  if (!entry) return key;
  return entry[lang] || entry.en || key;
}

function ingLine(item, lexicon, lang) {
  if (typeof item === 'string') return cap(ingName(item, lexicon, lang));
  const [head, subs] = item;
  const parts = (subs || []).map(k => ingName(k, lexicon, lang)).join(', ');
  return head.startsWith('~')
    ? `${cap(ingName(head, lexicon, lang))} (${parts})`
    : `${cap(ingName(head, lexicon, lang))}: ${parts}`;
}

/** Текст для пошуку: кожен складник усіма шістьма мовами.
    Саме звідси «кунжут», «sesame» і «Sesam» знаходять одне й те саме. */
function ingSearchText(list, lexicon) {
  const out = [];
  (list || []).forEach(item => {
    const keys = typeof item === 'string' ? [item] : [item[0], ...(item[1] || [])];
    keys.forEach(k => LANGS.forEach(l => out.push(ingName(k, lexicon, l.code))));
  });
  return out.join(' ');
}

/* --------------------------------------------------- чому недоступно ---- */
/**
 * Один рядок пояснення. «Скоро» має три відтінки: з датою відкриття,
 * з годинами подачі й просто «готуємо» — і для гостя це різні обіцянки.
 */
function closedText(av, schedules) {
  if (av.reason === 'soon') {
    const head = `<b>${esc(t('sched.soonHead', LANG))}.</b> `;
    if (av.opens_at) return head + `${esc(t('sched.soonFrom', LANG))} ${esc(formatUntil(av.opens_at, LANG))}`;
    if (av.schedule) return head + `${esc(t('sched.servedAt', LANG))} ${esc(describeSchedule(schedules[av.schedule], LANG))}`;
    return head + esc(t('sched.soon', LANG));
  }
  if (av.reason === 'sold_out') return `<b>${esc(t('sched.soldOut', LANG))}</b>`;
  return `<b>${esc(t('sched.closed', LANG))}.</b> ` +
    `${esc(t('sched.servedAt', LANG))} ${esc(describeSchedule(schedules[av.schedule], LANG))}`;
}

/** Ціна на картці.

    Позиція з варіантами має не одну ціну: біле вино — £13 за келих і £80 за
    пляшку. Показати саме £13 означало б пообіцяти те, чого немає, тож
    показуємо найменшу з «від». Позиції без вибору лишаються з простою ціною. */
function priceLabel(item, currency) {
  const prices = [];
  (item.options || []).forEach(group => {
    (group.choices || []).forEach(choice => {
      if (choice.price_pence !== undefined && choice.price_pence !== null) {
        prices.push(choice.price_pence);
      }
    });
  });
  if (!prices.length) return money(item.price_pence, currency, LANG);
  const low = Math.min(...prices);
  const high = Math.max(...prices);
  return low === high
    ? money(low, currency, LANG)
    : `${t('price.from', LANG)} ${money(low, currency, LANG)}`;
}

/* --------------------------------------------------------- картка ------- */
function dishCard(item, data) {
  const card = el('article', 'dish');
  card.id = 'd-' + item.key;
  card.dataset.search = [
    item.name,
    Object.values(item.desc || {}).join(' '),
    ingSearchText(item.ing, data.lexicon)
  ].join(' ').toLowerCase();

  const av = item.available || { open: true };
  card.classList.toggle('scheduled-off', !av.open);
  if (!av.open) card.appendChild(el('p', 'sched-note', closedText(av, data.schedules)));

  const head = el('div', 'dish-head');
  head.appendChild(el('h3', null, esc(item.name)));
  head.appendChild(el('span', 'price', esc(priceLabel(item, data.venue.currency))));
  card.appendChild(head);

  const desc = pick(item.desc, LANG);
  if (desc) card.appendChild(el('p', 'desc', esc(desc)));

  if (item.ing && item.ing.length) {
    card.appendChild(el('p', 'ing-label', esc(t('dish.ingredients', LANG))));
    const ul = el('ul', 'ing');
    item.ing.forEach(i => ul.appendChild(el('li', null, esc(ingLine(i, data.lexicon, LANG)))));
    card.appendChild(ul);
  }

  (item.w || []).forEach(k => {
    const text = pick(data.warnings[k], LANG);
    if (text) card.appendChild(el('p', 'warn', esc(text)));
  });

  if (!item.orderable && item.orderable_reason === 'alcohol-age-check') {
    card.appendChild(el('p', 'note-inline', esc(t('order.noAlcohol', LANG))));
  }

  // Кнопка «до кошика» з'являється у Спринті 5 — тут лишається місце під неї.
  const slot = el('div', 'order-slot');
  slot.dataset.itemKey = item.key;
  card.appendChild(slot);

  return card;
}

/* -------------------------------------------------------------- меню ---- */
/** Меню згруповане за категоріями: сорок позицій одним списком гортати
 *  довше, ніж читати. Категорія тут — лише підпис: власного стану чи
 *  розкладу в неї немає, закривають позицію, а не групу.
 *
 *  Порядок категорій задає заклад (порядок ключів), порядок усередині —
 *  позиція страви. Категорія, якої немає в підписах, іде під власним
 *  ключем, а не зникає: краще незграбний заголовок, ніж загублений напій. */
function renderMenu(mount, data) {
  mount.innerHTML = '';
  const cats = data.categories || [];
  const names = {};
  cats.forEach(cat => { names[cat.key] = cat.names; });
  const visible = data.items.filter(
    i => !(!(i.available || {}).open && (i.available || {}).hidden)
  );

  const order = cats.map(cat => cat.key);
  visible.forEach(i => {
    const key = i.category || '';
    if (!order.includes(key)) order.push(key);
  });

  order.forEach(key => {
    const items = visible.filter(i => (i.category || '') === key);
    if (!items.length) return;

    const box = el('section', 'cat');
    box.id = 'c-' + (key || 'other');
    if (key) box.appendChild(el('h2', null, esc(pick(names[key], LANG) || key)));

    const grid = el('div', 'grid');
    items.forEach(i => grid.appendChild(dishCard(i, data)));
    box.appendChild(grid);
    mount.appendChild(box);
  });
}

/* ------------------------------------------------- панель пошуку/фільтра - */
function buildToolbar(mount, data) {
  mount.innerHTML = '';
  const bar = el('div', 'toolbar');

  const wrap = el('div', 'wrap');
  const search = el('input', 'search');
  search.type = 'search';
  search.value = FILTER.query;
  search.placeholder = t('tb.search', LANG);
  search.setAttribute('aria-label', t('tb.search', LANG));

  const count = el('span', 'result-count');
  wrap.append(search, count);
  bar.appendChild(wrap);
  mount.appendChild(bar);

  const apply = () => {
    const q = FILTER.query.trim().toLowerCase();
    let shown = 0;

    document.querySelectorAll('.dish').forEach(node => {
      const match = !q || (node.dataset.search || '').includes(q);
      node.style.display = match ? '' : 'none';
      if (match) shown++;
    });

    // Категорія без жодного видимого пункту ховається разом із заголовком:
    // порожня рубрика в результатах пошуку читається як помилка.
    document.querySelectorAll('.cat').forEach(box => {
      const any = [...box.querySelectorAll('.dish')].some(n => n.style.display !== 'none');
      box.style.display = any ? '' : 'none';
    });

    count.textContent = q ? `${shown} ${t('count.items', LANG)}` : '';
    const empty = document.getElementById('empty');
    if (empty) empty.hidden = shown > 0;
  };

  search.addEventListener('input', () => {
    FILTER.query = search.value;
    apply();
  });

  apply();
}

/* ------------------------------------------------------------ сторінка -- */
function renderStatic(data) {
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i18n]').forEach(n => { n.innerHTML = t(n.dataset.i18n, LANG); });

  const title = document.getElementById('venue-name');
  if (title && data) title.textContent = data.venue.name;

  const badge = document.getElementById('table-badge');
  if (badge) {
    badge.hidden = !TABLE;
    if (TABLE) badge.textContent = `${t('guest.table', LANG)} ${TABLE.label}`;
  }

  const preview = document.getElementById('preview-banner');
  const at = new URLSearchParams(location.search).get('at');
  if (preview) {
    preview.hidden = !at;
    if (at) preview.textContent = `${t('sched.preview', LANG)}: ${at}`;
  }
}

function render(data, meta) {
  const offline = document.getElementById('offline-banner');
  if (offline) {
    offline.hidden = meta.online;
    offline.textContent = t('net.offline', LANG);
  }

  if (!data) {
    const mount = document.getElementById('menu');
    if (mount) mount.innerHTML = `<p class="notice">${esc(t('net.failed', LANG))}</p>`;
    return;
  }

  // Нічого не змінилося — не чіпаємо DOM. Гість може стояти з відкритим
  // фільтром і курсором у пошуку; перемальовування посеред цього — гірше,
  // ніж застарілий на секунду список.
  if (RENDERED && meta.changed === false) return;

  renderStatic(data);
  renderMenu(document.getElementById('menu'), data);
  buildToolbar(document.getElementById('toolbar'), data);
  refreshSwitches(LANG);
  RENDERED = true;
  if (typeof onMenuRendered === 'function') onMenuRendered(data);
}

function initGuest() {
  applyTheme(getTheme());
  buildSwitches(document.querySelector('.switches'), code => {
    LANG = code;
    if (MenuStore.data) render(MenuStore.data, { online: MenuStore.ok, changed: true });
  });
  buildTopButton();
  renderStatic(null);

  const token = API.tableToken();
  if (token) {
    API.get('/api/table/' + token)
      .then(tb => { TABLE = tb; renderStatic(MenuStore.data); })
      .catch(() => { /* невідомий стіл — меню все одно читається */ });
  }

  MenuStore.onChange((data, meta) => render(data, meta));
  MenuStore.start();
}
