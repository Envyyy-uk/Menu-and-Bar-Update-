/* ==========================================================================
   Локалізація інтерфейсу — uk / en / es / it / de / ru

   Тут лише інтерфейс. Назви страв, склад і розділи приходять з API вже
   перекладеними: склад — це ключі словника, а не текст.
   ========================================================================== */

const LANGS = [
  { code: 'uk', label: 'Українська', short: 'UA' },
  { code: 'en', label: 'English',    short: 'EN' },
  { code: 'ru', label: 'Русский',    short: 'RU' }
];

const I18N = {

  'brand.sub': {
    uk: 'Меню · склад і алергени', en: 'Menu · ingredients & allergens',    ru: 'Меню · состав и аллергены'
  },

  'lang.label':  { uk: 'Мова', en: 'Language',    ru: 'Язык' },
  'theme.label': { uk: 'Тема', en: 'Theme',    ru: 'Тема' },
  'theme.auto':  { uk: 'Авто', en: 'Auto',    ru: 'Авто' },
  'theme.light': { uk: 'Світла', en: 'Light',    ru: 'Светлая' },
  'theme.dark':  { uk: 'Темна', en: 'Dark',    ru: 'Тёмная' },
  'ui.top':      { uk: 'Нагору', en: 'Back to top',    ru: 'Наверх' },

  /* ------------------------------------------------------------ шапка --- */
  'guest.table': { uk: 'Стіл', en: 'Table',    ru: 'Стол' },
  'guest.lead': {
    uk: 'Кожна позиція — з повним складом і позначеними алергенами. Оберіть свої алергени у фільтрі: позиції з ними буде приглушено.',
    en: 'Every item broken down into its ingredients, with allergens marked. Tick your allergens in the filter and matching items are dimmed.',   
    ru: 'Каждая позиция — с полным составом и отмеченными аллергенами. Отметьте свои аллергены в фильтре: позиции с ними будут приглушены.'
  },
  'guest.notice': {
    uk: 'Обов’язково скажіть офіціантові про алергію перед замовленням: на кухні спільне обладнання, і слідів уникнути не завжди можливо.',
    en: 'Please tell your server about any allergy before ordering: the kitchen shares equipment and traces cannot always be avoided.',   
    ru: 'Обязательно скажите официанту об аллергии перед заказом: на кухне общее оборудование, и следов не всегда удаётся избежать.'
  },

  /* --------------------------------------------------------- панель --- */
  'tb.search': {
    uk: 'Пошук за назвою або складником', en: 'Search by name or ingredient',    ru: 'Поиск по названию или ингредиенту'
  },
  'tb.filter': { uk: 'Алергени', en: 'Allergens',    ru: 'Аллергены' },
  'tb.hint': {
    uk: 'Позначте те, чого уникаєте. Приглушується і «містить», і «може містити».',
    en: 'Tick what you avoid. Both “contains” and “may contain” are dimmed.',   
    ru: 'Отметьте то, чего избегаете. Приглушается и «содержит», и «может содержать».'
  },
  'tb.clear':   { uk: 'Скинути', en: 'Clear',    ru: 'Сбросить' },
  'tb.flagged': { uk: 'з вашими алергенами', en: 'with your allergens',    ru: 'с вашими аллергенами' },
  'count.items': { uk: 'позицій', en: 'items',    ru: 'позиций' },
  'search.empty': {
    uk: 'Нічого не знайдено. Спробуйте іншу мову або інший складник.',
    en: 'Nothing found. Try another language or another ingredient.',   
    ru: 'Ничего не найдено. Попробуйте другой язык или другой ингредиент.'
  },

  /* ---------------------------------------------------------- картка --- */
  'dish.ingredients': { uk: 'Склад', en: 'Ingredients',    ru: 'Состав' },
  'dish.allergens':   { uk: 'Містить', en: 'Contains',    ru: 'Содержит' },
  'dish.may':         { uk: 'Може містити', en: 'May contain',    ru: 'Может содержать' },
  'dish.none':        { uk: 'Із 14 обов’язкових — жодного', en: 'None of the 14 declarable allergens',    ru: 'Из 14 обязательных — ни одного' },
  'alg.removable':    { uk: 'можна прибрати', en: 'can be removed',    ru: 'можно убрать' },
  'alg.removableFull': {
    uk: 'Позначене R можна прибрати зі страви — скажіть офіціантові.',
    en: 'Anything marked R can be left out — just ask your server.',   
    ru: 'Отмеченное R можно убрать из блюда — скажите официанту.'
  },
  'src.official':      { uk: 'Офіційний лист закладу', en: 'Venue allergen sheet',    ru: 'Официальный лист заведения' },
  'src.reconstructed': { uk: 'Реконструкція з опису', en: 'Reconstructed from description',    ru: 'Реконструкция из описания' },
  'src.reviewed':      { uk: 'перевірено', en: 'checked',    ru: 'проверено' },

  /* --------------------------------------------------------- розклад --- */
  'sched.days': {
    uk: 'Нд,Пн,Вт,Ср,Чт,Пт,Сб', en: 'Su,Mo,Tu,We,Th,Fr,Sa',    ru: 'Вс,Пн,Вт,Ср,Чт,Пт,Сб'
  },
  'sched.closed':   { uk: 'Зараз не подається', en: 'Not served right now',    ru: 'Сейчас не подаётся' },
  'sched.soldOut':  { uk: 'Наразі немає', en: 'Currently unavailable',    ru: 'Сейчас нет' },
  'sched.servedAt': { uk: 'Подається', en: 'Served',    ru: 'Подаётся' },
  'sched.soonHead': { uk: 'Скоро', en: 'Coming soon',    ru: 'Скоро' },
  'sched.soon':     { uk: 'Готуємо, незабаром з’явиться', en: 'In the works, arriving soon',    ru: 'Готовим, скоро появится' },
  'sched.soonFrom': { uk: 'Відкриється', en: 'Opens',    ru: 'Откроется' },
  'sched.badge':    { uk: 'немає', en: 'off',    ru: 'нет' },
  'sched.badge.soon': { uk: 'скоро', en: 'soon',    ru: 'скоро' },
  'sched.preview':  { uk: 'Режим перегляду часу', en: 'Time preview mode',    ru: 'Режим просмотра времени' },

  /* ----------------------------------------------------- замовлення --- */
  'order.noAlcohol': {
    uk: 'Алкоголь замовляється в офіціанта: вік перевіряють при подачі.',
    en: 'Alcohol is ordered through your server: age is checked on serving.',   
    ru: 'Алкоголь заказывается у официанта: возраст проверяют при подаче.'
  },


  /* ------------------------------------------------------------ кошик --- */
  'cart.add':    { uk: 'Додати', en: 'Add',    ru: 'Добавить' },
  'cart.title':  { uk: 'Замовлення', en: 'Your order',    ru: 'Заказ' },
  'cart.total':  { uk: 'Разом', en: 'Total',    ru: 'Итого' },
  'cart.note':   { uk: 'Побажання до кухні', en: 'Note for the kitchen',    ru: 'Пожелания к кухне' },
  'cart.send':   { uk: 'Замовити й оплатити', en: 'Order and pay',    ru: 'Заказать и оплатить' },
  /* --- оплата: гаманці й картка --- */
  'pay.title':   { uk: 'Оплата', en: 'Payment',    ru: 'Оплата' },
  'pay.or':      { uk: 'або карткою', en: 'or pay by card',    ru: 'или картой' },
  'pay.submit':  { uk: 'Оплатити', en: 'Pay',    ru: 'Оплатить' },
  'pay.working': { uk: 'Проводимо платіж…', en: 'Processing…',    ru: 'Проводим платёж…' },
  'pay.sent':    { uk: 'Оплачено. Передаємо на кухню — статус оновиться сам.', en: 'Paid. Sending to the kitchen — the status updates itself.',    ru: 'Оплачено. Передаём на кухню — статус обновится сам.' },
  'pay.failed':  { uk: 'Платіж не пройшов. Гроші не списано.', en: 'The payment did not go through. You were not charged.',    ru: 'Платёж не прошёл. Деньги не списаны.' },
  'pay.noscript':{ uk: 'Не вдалося завантажити платіжну форму. Перевірте зв’язок і спробуйте ще раз.', en: 'The payment form could not load. Check your connection and try again.',    ru: 'Не удалось загрузить платёжную форму. Проверьте связь и попробуйте ещё раз.' },
  'pay.later':   { uk: 'Оплатити пізніше', en: 'Pay later',    ru: 'Оплатить позже' },
  'price.from':  { uk: 'від', en: 'from',    ru: 'от' },
  'cart.choose':  { uk: 'Обрати', en: 'Choose',    ru: 'Выбрать' },
  /* --- підписи груп варіантів. Самі варіанти не перекладаються: гість
         замовляє їх так, як надруковано в меню. --- */
  'opt.size':    { uk: 'Обʼєм', en: 'Size',    ru: 'Объём' },
  'opt.flavour': { uk: 'Смак', en: 'Flavour',    ru: 'Вкус' },
  'opt.milk':    { uk: 'Молоко', en: 'Milk',    ru: 'Молоко' },
  'opt.kind':    { uk: 'Вид', en: 'Kind',    ru: 'Вид' },
  'opt.serve':   { uk: 'Подача', en: 'Serve',    ru: 'Подача' },
  'opt.style':   { uk: 'Стиль', en: 'Style',    ru: 'Стиль' },
  'cart.sending':{ uk: 'Надсилаємо…', en: 'Sending…',    ru: 'Отправляем…' },
  'cart.empty':  { uk: 'Кошик порожній', en: 'Your basket is empty',    ru: 'Корзина пуста' },
  'cart.remove': { uk: 'Прибрати', en: 'Remove',    ru: 'Убрать' },
  'cart.close':  { uk: 'Закрити', en: 'Close',    ru: 'Закрыть' },
  'cart.needTable': {
    uk: 'Щоб замовити, скануйте QR на своєму столі.',
    en: 'To order, scan the QR code on your table.',   
    ru: 'Чтобы заказать, отсканируйте QR на своём столе.'
  },
  'cart.dropped': {
    uk: 'Це щойно закінчилося й не потрапило в замовлення:',
    en: 'These just ran out and are not in the order:',   
    ru: 'Это только что закончилось и не попало в заказ:'
  },
  'cart.confirmRest': {
    uk: 'Замовити решту', en: 'Order the rest',    ru: 'Заказать остальное'
  },

  /* ------------------------------------------------- статус замовлення -- */
  'order.number':   { uk: 'Замовлення №', en: 'Order #',    ru: 'Заказ №' },
  'order.new':      { uk: 'Нове замовлення', en: 'New order',    ru: 'Новый заказ' },
  'order.st.draft':           { uk: 'Оформлюється', en: 'Being placed',    ru: 'Оформляется' },
  'order.st.payment_pending': { uk: 'Очікує оплати', en: 'Awaiting payment',    ru: 'Ожидает оплаты' },
  'order.st.paid':            { uk: 'Оплачено, передано на кухню', en: 'Paid, sent to the kitchen',    ru: 'Оплачено, передано на кухню' },
  'order.st.accepted':        { uk: 'Готується', en: 'Being prepared',    ru: 'Готовится' },
  'order.st.ready':           { uk: 'Готово, несемо', en: 'Ready, on its way',    ru: 'Готово, несём' },
  'order.st.served':          { uk: 'Подано', en: 'Served',    ru: 'Подано' },
  'order.st.failed':          { uk: 'Оплата не пройшла', en: 'Payment failed',    ru: 'Оплата не прошла' },
  'order.st.refunded':        { uk: 'Повернуто', en: 'Refunded',    ru: 'Возвращено' },

  /* --------------------------------------------------------- зв’язок --- */
  'net.offline': {
    uk: 'Немає зв’язку із закладом. Показано останній відомий стан меню.',
    en: 'No connection to the venue. Showing the last known menu state.',   
    ru: 'Нет связи с заведением. Показано последнее известное состояние меню.'
  },
  'net.loading': { uk: 'Завантаження меню…', en: 'Loading the menu…',    ru: 'Загрузка меню…' },
  'net.failed': {
    uk: 'Меню не завантажилося. Оновіть сторінку або покличте офіціанта.',
    en: 'The menu failed to load. Refresh the page or ask your server.',   
    ru: 'Меню не загрузилось. Обновите страницу или позовите официанта.'
  }
};

/* -------------------------------------------------------------------------
   Поточна мова
   ------------------------------------------------------------------------- */
const LANG_STORAGE_KEY = 'menu-lang';

function getLang() {
  const url = new URLSearchParams(location.search).get('lang');
  if (url && LANGS.some(l => l.code === url)) return url;
  try {
    const saved = localStorage.getItem(LANG_STORAGE_KEY);
    if (saved && LANGS.some(l => l.code === saved)) return saved;
  } catch (e) { /* приватний режим */ }
  const nav = (navigator.language || 'en').slice(0, 2).toLowerCase();
  return LANGS.some(l => l.code === nav) ? nav : 'en';
}

function setLang(code) {
  try { localStorage.setItem(LANG_STORAGE_KEY, code); } catch (e) { /* ігноруємо */ }
}

/** t('tb.filter') — рядок поточною мовою, з відкатом на англійську */
function t(key, lang) {
  const entry = I18N[key];
  if (!entry) return key;
  return entry[lang || getLang()] || entry.en || key;
}

/** Багатомовне поле з API: { uk: '…', en: '…' } → рядок */
function pick(field, lang) {
  if (!field) return '';
  if (typeof field === 'string') return field;
  return field[lang] || field.en || Object.values(field)[0] || '';
}
