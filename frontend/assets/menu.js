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
const FILTER = { query: '', allergens: new Set(), open: false };

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

/* -------------------------------------------------------------- мітки --- */
function tagList(item, keys, maybe) {
  const box = el('div', 'tags');
  (keys || []).forEach(k => {
    if (!ALLERGENS[k]) return;
    const removable = !maybe && (item.r || []).includes(k);
    const tag = el('span', 'tag' + (maybe ? ' maybe' : ''));
    tag.title = aNote(k, LANG) + (removable ? ' · ' + t('alg.removable', LANG) : '');
    tag.innerHTML =
      `<span aria-hidden="true">${ALLERGENS[k].icon}</span>${esc(aName(k, LANG))}` +
      (removable ? `<span class="rem" title="${esc(t('alg.removable', LANG))}">R</span>` : '');
    box.appendChild(tag);
  });
  return box;
}

function sourceBadge(item, sources) {
  const s = item.src ? sources[item.src] : null;
  if (s && s.type === 'official') {
    const checked = s.checked ? ` · ${t('src.reviewed', LANG)} ${s.checked}` : '';
    const b = el('p', 'srcbadge',
      `<span class="dot" aria-hidden="true">●</span>${esc(pick(s.label, LANG) || t('src.official', LANG))}${esc(checked)}`);
    return b;
  }
  return el('p', 'srcbadge est',
    `<span class="dot" aria-hidden="true">○</span>${esc(s ? pick(s.label, LANG) : t('src.reconstructed', LANG))}`);
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
  card.dataset.allergens = (item.a || []).join(' ');
  card.dataset.maybe = (item.m || []).join(' ');
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

  card.appendChild(el('p', 'alg-label', esc(t('dish.allergens', LANG))));
  if (item.a && item.a.length) {
    card.appendChild(tagList(item, item.a, false));
  } else {
    const box = el('div', 'tags');
    box.appendChild(el('span', 'tag none', esc(t('dish.none', LANG))));
    card.appendChild(box);
  }

  if (item.m && item.m.length) {
    card.appendChild(el('p', 'alg-label', esc(t('dish.may', LANG))));
    card.appendChild(tagList(item, item.m, true));
  }

  if ((item.r || []).length) card.appendChild(el('p', 'rem-note', esc(t('alg.removableFull', LANG))));

  card.appendChild(sourceBadge(item, data.sources));
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
/** Меню — один суцільний список. Без заголовків розділів і без вкладок:
 *  гість гортає страви підряд, а не блукає між групами. Порядок задає зал
 *  позицією страви. Розділ, закритий за розкладом, гасить свої позиції —
 *  це вже враховано сервером у `available`. */
function renderMenu(mount, data) {
  mount.innerHTML = '';
  const grid = el('div', 'grid');
  data.items.forEach(i => {
    if (!(i.available || {}).open && (i.available || {}).hidden) return;
    grid.appendChild(dishCard(i, data));
  });
  mount.appendChild(grid);
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

  const toggle = el('button', 'filter-toggle', esc(t('tb.filter', LANG)));
  toggle.type = 'button';
  toggle.setAttribute('aria-expanded', String(FILTER.open));

  const count = el('span', 'result-count');
  wrap.append(search, toggle, count);
  bar.appendChild(wrap);

  const filtersWrap = el('div', 'wrap');
  const filters = el('div', 'filters' + (FILTER.open ? ' open' : ''));
  filters.appendChild(el('p', 'hint', esc(t('tb.hint', LANG))));
  const chips = el('div', 'chips');
  ALLERGEN_KEYS.forEach(k => {
    const label = el('label', 'chip' + (FILTER.allergens.has(k) ? ' on' : ''));
    label.title = aNote(k, LANG);
    label.innerHTML =
      `<input type="checkbox" value="${k}"${FILTER.allergens.has(k) ? ' checked' : ''}>` +
      `<span aria-hidden="true">${ALLERGENS[k].icon}</span>${esc(aName(k, LANG))}`;
    chips.appendChild(label);
  });
  filters.appendChild(chips);
  const clear = el('button', 'clear-btn', esc(t('tb.clear', LANG)));
  clear.type = 'button';
  filters.appendChild(clear);
  filtersWrap.appendChild(filters);
  bar.appendChild(filtersWrap);
  mount.appendChild(bar);

  toggle.addEventListener('click', () => {
    FILTER.open = filters.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(FILTER.open));
  });

  const apply = () => {
    FILTER.allergens = new Set([...chips.querySelectorAll('input:checked')].map(i => i.value));
    chips.querySelectorAll('.chip').forEach(c => c.classList.toggle('on', c.querySelector('input').checked));
    const q = FILTER.query.trim().toLowerCase();
    const active = [...FILTER.allergens];
    let shown = 0, flagged = 0;

    document.querySelectorAll('.dish').forEach(node => {
      const has = (node.dataset.allergens || '').split(' ').filter(Boolean);
      const may = (node.dataset.maybe || '').split(' ').filter(Boolean);
      const hit = active.some(a => has.includes(a) || may.includes(a));
      const match = !q || (node.dataset.search || '').includes(q);
      node.style.display = match ? '' : 'none';
      node.classList.toggle('flagged', hit);
      if (match) { shown++; if (hit) flagged++; }
    });

    count.textContent = (active.length || q)
      ? `${shown} ${t('count.items', LANG)}${flagged ? ` · ${flagged} ${t('tb.flagged', LANG)}` : ''}`
      : '';

    const empty = document.getElementById('empty');
    if (empty) empty.hidden = shown > 0;
  };

  search.addEventListener('input', () => {
    FILTER.query = search.value;
    apply();
  });
  chips.addEventListener('change', apply);
  clear.addEventListener('click', () => {
    chips.querySelectorAll('input').forEach(i => (i.checked = false));
    search.value = '';
    FILTER.query = '';
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
