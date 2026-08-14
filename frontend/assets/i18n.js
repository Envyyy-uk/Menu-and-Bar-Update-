/* ==========================================================================
   Локалізація інтерфейсу — uk / en / es / it / de / ru

   Тут лише інтерфейс. Назви страв, склад і розділи приходять з API вже
   перекладеними: склад — це ключі словника, а не текст.
   ========================================================================== */

const LANGS = [
  { code: 'uk', label: 'Українська', short: 'UA' },
  { code: 'en', label: 'English',    short: 'EN' },
  { code: 'es', label: 'Español',    short: 'ES' },
  { code: 'it', label: 'Italiano',   short: 'IT' },
  { code: 'de', label: 'Deutsch',    short: 'DE' },
  { code: 'ru', label: 'Русский',    short: 'RU' }
];

const I18N = {

  'brand.sub': {
    uk: 'Меню · склад і алергени', en: 'Menu · ingredients & allergens',
    es: 'Carta · ingredientes y alérgenos', it: 'Menu · ingredienti e allergeni',
    de: 'Karte · Zutaten & Allergene', ru: 'Меню · состав и аллергены'
  },

  'lang.label':  { uk: 'Мова', en: 'Language', es: 'Idioma', it: 'Lingua', de: 'Sprache', ru: 'Язык' },
  'theme.label': { uk: 'Тема', en: 'Theme', es: 'Tema', it: 'Tema', de: 'Design', ru: 'Тема' },
  'theme.auto':  { uk: 'Авто', en: 'Auto', es: 'Auto', it: 'Auto', de: 'Auto', ru: 'Авто' },
  'theme.light': { uk: 'Світла', en: 'Light', es: 'Claro', it: 'Chiaro', de: 'Hell', ru: 'Светлая' },
  'theme.dark':  { uk: 'Темна', en: 'Dark', es: 'Oscuro', it: 'Scuro', de: 'Dunkel', ru: 'Тёмная' },
  'ui.top':      { uk: 'Нагору', en: 'Back to top', es: 'Arriba', it: 'Torna su', de: 'Nach oben', ru: 'Наверх' },

  /* ------------------------------------------------------------ шапка --- */
  'guest.table': { uk: 'Стіл', en: 'Table', es: 'Mesa', it: 'Tavolo', de: 'Tisch', ru: 'Стол' },
  'guest.lead': {
    uk: 'Кожна позиція — з повним складом і позначеними алергенами. Оберіть свої алергени у фільтрі: позиції з ними буде приглушено.',
    en: 'Every item broken down into its ingredients, with allergens marked. Tick your allergens in the filter and matching items are dimmed.',
    es: 'Cada plato con sus ingredientes y los alérgenos señalados. Marque sus alérgenos en el filtro y los platos afectados se atenúan.',
    it: 'Ogni voce con gli ingredienti e gli allergeni indicati. Selezionate i vostri allergeni nel filtro: le voci interessate vengono attenuate.',
    de: 'Jede Position mit vollständiger Zutatenliste und gekennzeichneten Allergenen. Wählen Sie Ihre Allergene im Filter — betroffene Positionen werden abgeblendet.',
    ru: 'Каждая позиция — с полным составом и отмеченными аллергенами. Отметьте свои аллергены в фильтре: позиции с ними будут приглушены.'
  },
  'guest.notice': {
    uk: 'Обов’язково скажіть офіціантові про алергію перед замовленням: на кухні спільне обладнання, і слідів уникнути не завжди можливо.',
    en: 'Please tell your server about any allergy before ordering: the kitchen shares equipment and traces cannot always be avoided.',
    es: 'Informe al camarero de cualquier alergia antes de pedir: la cocina comparte equipos y no siempre se pueden evitar las trazas.',
    it: 'Informate il personale di eventuali allergie prima di ordinare: la cucina condivide le attrezzature e le tracce non sono sempre evitabili.',
    de: 'Bitte informieren Sie das Personal vor der Bestellung über Allergien: Die Küche nutzt gemeinsame Geräte, Spuren sind nicht immer vermeidbar.',
    ru: 'Обязательно скажите официанту об аллергии перед заказом: на кухне общее оборудование, и следов не всегда удаётся избежать.'
  },

  /* --------------------------------------------------------- панель --- */
  'tb.search': {
    uk: 'Пошук за назвою або складником', en: 'Search by name or ingredient',
    es: 'Buscar por nombre o ingrediente', it: 'Cerca per nome o ingrediente',
    de: 'Nach Name oder Zutat suchen', ru: 'Поиск по названию или ингредиенту'
  },
  'tb.filter': { uk: 'Алергени', en: 'Allergens', es: 'Alérgenos', it: 'Allergeni', de: 'Allergene', ru: 'Аллергены' },
  'tb.hint': {
    uk: 'Позначте те, чого уникаєте. Приглушується і «містить», і «може містити».',
    en: 'Tick what you avoid. Both “contains” and “may contain” are dimmed.',
    es: 'Marque lo que evita. Se atenúan tanto «contiene» como «puede contener».',
    it: 'Selezionate ciò che evitate. Vengono attenuati sia «contiene» sia «può contenere».',
    de: 'Markieren Sie, was Sie meiden. Abgeblendet werden „enthält“ und „kann enthalten“.',
    ru: 'Отметьте то, чего избегаете. Приглушается и «содержит», и «может содержать».'
  },
  'tb.clear':   { uk: 'Скинути', en: 'Clear', es: 'Borrar', it: 'Azzera', de: 'Zurücksetzen', ru: 'Сбросить' },
  'tb.flagged': { uk: 'з вашими алергенами', en: 'with your allergens', es: 'con sus alérgenos', it: 'con i vostri allergeni', de: 'mit Ihren Allergenen', ru: 'с вашими аллергенами' },
  'count.items': { uk: 'позицій', en: 'items', es: 'platos', it: 'voci', de: 'Positionen', ru: 'позиций' },
  'search.empty': {
    uk: 'Нічого не знайдено. Спробуйте іншу мову або інший складник.',
    en: 'Nothing found. Try another language or another ingredient.',
    es: 'Sin resultados. Pruebe otro idioma u otro ingrediente.',
    it: 'Nessun risultato. Provate un’altra lingua o un altro ingrediente.',
    de: 'Nichts gefunden. Versuchen Sie eine andere Sprache oder Zutat.',
    ru: 'Ничего не найдено. Попробуйте другой язык или другой ингредиент.'
  },

  /* ---------------------------------------------------------- картка --- */
  'dish.ingredients': { uk: 'Склад', en: 'Ingredients', es: 'Ingredientes', it: 'Ingredienti', de: 'Zutaten', ru: 'Состав' },
  'dish.allergens':   { uk: 'Містить', en: 'Contains', es: 'Contiene', it: 'Contiene', de: 'Enthält', ru: 'Содержит' },
  'dish.may':         { uk: 'Може містити', en: 'May contain', es: 'Puede contener', it: 'Può contenere', de: 'Kann enthalten', ru: 'Может содержать' },
  'dish.none':        { uk: 'Із 14 обов’язкових — жодного', en: 'None of the 14 declarable allergens', es: 'Ninguno de los 14 alérgenos declarables', it: 'Nessuno dei 14 allergeni obbligatori', de: 'Keines der 14 deklarationspflichtigen Allergene', ru: 'Из 14 обязательных — ни одного' },
  'alg.removable':    { uk: 'можна прибрати', en: 'can be removed', es: 'se puede retirar', it: 'si può togliere', de: 'kann weggelassen werden', ru: 'можно убрать' },
  'alg.removableFull': {
    uk: 'Позначене R можна прибрати зі страви — скажіть офіціантові.',
    en: 'Anything marked R can be left out — just ask your server.',
    es: 'Lo marcado con R se puede retirar: pídalo al camarero.',
    it: 'Ciò che è contrassegnato con R può essere tolto: chiedete al personale.',
    de: 'Mit R Markiertes kann weggelassen werden — sagen Sie es dem Personal.',
    ru: 'Отмеченное R можно убрать из блюда — скажите официанту.'
  },
  'src.official':      { uk: 'Офіційний лист закладу', en: 'Venue allergen sheet', es: 'Ficha oficial del local', it: 'Scheda ufficiale del locale', de: 'Offizielles Allergenblatt', ru: 'Официальный лист заведения' },
  'src.reconstructed': { uk: 'Реконструкція з опису', en: 'Reconstructed from description', es: 'Reconstruido de la descripción', it: 'Ricostruito dalla descrizione', de: 'Aus der Beschreibung rekonstruiert', ru: 'Реконструкция из описания' },
  'src.reviewed':      { uk: 'перевірено', en: 'checked', es: 'comprobado', it: 'verificato', de: 'geprüft', ru: 'проверено' },

  /* --------------------------------------------------------- розклад --- */
  'sched.days': {
    uk: 'Нд,Пн,Вт,Ср,Чт,Пт,Сб', en: 'Su,Mo,Tu,We,Th,Fr,Sa', es: 'Do,Lu,Ma,Mi,Ju,Vi,Sá',
    it: 'Do,Lu,Ma,Me,Gi,Ve,Sa', de: 'So,Mo,Di,Mi,Do,Fr,Sa', ru: 'Вс,Пн,Вт,Ср,Чт,Пт,Сб'
  },
  'sched.closed':   { uk: 'Зараз не подається', en: 'Not served right now', es: 'Ahora no se sirve', it: 'Ora non servito', de: 'Derzeit nicht im Angebot', ru: 'Сейчас не подаётся' },
  'sched.soldOut':  { uk: 'Наразі немає', en: 'Currently unavailable', es: 'No disponible ahora', it: 'Al momento non disponibile', de: 'Derzeit nicht verfügbar', ru: 'Сейчас нет' },
  'sched.servedAt': { uk: 'Подається', en: 'Served', es: 'Se sirve', it: 'Servito', de: 'Serviert', ru: 'Подаётся' },
  'sched.soonHead': { uk: 'Скоро', en: 'Coming soon', es: 'Muy pronto', it: 'Presto', de: 'Demnächst', ru: 'Скоро' },
  'sched.soon':     { uk: 'Готуємо, незабаром з’явиться', en: 'In the works, arriving soon', es: 'En preparación, llegará pronto', it: 'In arrivo a breve', de: 'In Vorbereitung, bald verfügbar', ru: 'Готовим, скоро появится' },
  'sched.soonFrom': { uk: 'Відкриється', en: 'Opens', es: 'Se abre', it: 'Apre', de: 'Öffnet', ru: 'Откроется' },
  'sched.badge':    { uk: 'немає', en: 'off', es: 'no', it: 'no', de: 'aus', ru: 'нет' },
  'sched.badge.soon': { uk: 'скоро', en: 'soon', es: 'pronto', it: 'presto', de: 'bald', ru: 'скоро' },
  'sched.preview':  { uk: 'Режим перегляду часу', en: 'Time preview mode', es: 'Modo de vista previa horaria', it: 'Modalità anteprima orario', de: 'Zeit-Vorschaumodus', ru: 'Режим просмотра времени' },

  /* ----------------------------------------------------- замовлення --- */
  'order.noAlcohol': {
    uk: 'Алкоголь замовляється в офіціанта: вік перевіряють при подачі.',
    en: 'Alcohol is ordered through your server: age is checked on serving.',
    es: 'El alcohol se pide al camarero: la edad se verifica al servir.',
    it: 'Gli alcolici si ordinano al personale: l’età viene verificata al servizio.',
    de: 'Alkohol bestellen Sie beim Personal: Das Alter wird bei der Ausgabe geprüft.',
    ru: 'Алкоголь заказывается у официанта: возраст проверяют при подаче.'
  },


  /* ------------------------------------------------------------ кошик --- */
  'cart.add':    { uk: 'Додати', en: 'Add', es: 'Añadir', it: 'Aggiungi', de: 'Hinzufügen', ru: 'Добавить' },
  'cart.title':  { uk: 'Замовлення', en: 'Your order', es: 'Su pedido', it: 'Il vostro ordine', de: 'Ihre Bestellung', ru: 'Заказ' },
  'cart.total':  { uk: 'Разом', en: 'Total', es: 'Total', it: 'Totale', de: 'Summe', ru: 'Итого' },
  'cart.note':   { uk: 'Побажання до кухні', en: 'Note for the kitchen', es: 'Nota para la cocina', it: 'Nota per la cucina', de: 'Hinweis für die Küche', ru: 'Пожелания к кухне' },
  'cart.send':   { uk: 'Замовити й оплатити', en: 'Order and pay', es: 'Pedir y pagar', it: 'Ordina e paga', de: 'Bestellen und zahlen', ru: 'Заказать и оплатить' },
  /* --- оплата: гаманці й картка --- */
  'pay.title':   { uk: 'Оплата', en: 'Payment', es: 'Pago', it: 'Pagamento', de: 'Zahlung', ru: 'Оплата' },
  'pay.or':      { uk: 'або карткою', en: 'or pay by card', es: 'o con tarjeta', it: 'oppure con carta', de: 'oder mit Karte', ru: 'или картой' },
  'pay.submit':  { uk: 'Оплатити', en: 'Pay', es: 'Pagar', it: 'Paga', de: 'Bezahlen', ru: 'Оплатить' },
  'pay.working': { uk: 'Проводимо платіж…', en: 'Processing…', es: 'Procesando…', it: 'Elaborazione…', de: 'Wird verarbeitet…', ru: 'Проводим платёж…' },
  'pay.sent':    { uk: 'Оплачено. Передаємо на кухню — статус оновиться сам.', en: 'Paid. Sending to the kitchen — the status updates itself.', es: 'Pagado. Enviando a cocina: el estado se actualiza solo.', it: 'Pagato. Inviamo in cucina — lo stato si aggiorna da solo.', de: 'Bezahlt. Geht an die Küche — der Status aktualisiert sich selbst.', ru: 'Оплачено. Передаём на кухню — статус обновится сам.' },
  'pay.failed':  { uk: 'Платіж не пройшов. Гроші не списано.', en: 'The payment did not go through. You were not charged.', es: 'El pago no se realizó. No se le ha cobrado.', it: 'Il pagamento non è andato a buon fine. Non è stato addebitato nulla.', de: 'Die Zahlung ist fehlgeschlagen. Es wurde nichts abgebucht.', ru: 'Платёж не прошёл. Деньги не списаны.' },
  'pay.noscript':{ uk: 'Не вдалося завантажити платіжну форму. Перевірте зв’язок і спробуйте ще раз.', en: 'The payment form could not load. Check your connection and try again.', es: 'No se pudo cargar el formulario de pago. Compruebe la conexión e inténtelo de nuevo.', it: 'Impossibile caricare il modulo di pagamento. Controllate la connessione e riprovate.', de: 'Das Zahlungsformular konnte nicht geladen werden. Prüfen Sie die Verbindung und versuchen Sie es erneut.', ru: 'Не удалось загрузить платёжную форму. Проверьте связь и попробуйте ещё раз.' },
  'pay.later':   { uk: 'Оплатити пізніше', en: 'Pay later', es: 'Pagar más tarde', it: 'Paga più tardi', de: 'Später bezahlen', ru: 'Оплатить позже' },
  'price.from':  { uk: 'від', en: 'from', es: 'desde', it: 'da', de: 'ab', ru: 'от' },
  'cart.choose':  { uk: 'Обрати', en: 'Choose', es: 'Elegir', it: 'Scegli', de: 'Wählen', ru: 'Выбрать' },
  /* --- підписи груп варіантів. Самі варіанти не перекладаються: гість
         замовляє їх так, як надруковано в меню. --- */
  'opt.size':    { uk: 'Обʼєм', en: 'Size', es: 'Tamaño', it: 'Formato', de: 'Größe', ru: 'Объём' },
  'opt.flavour': { uk: 'Смак', en: 'Flavour', es: 'Sabor', it: 'Gusto', de: 'Geschmack', ru: 'Вкус' },
  'opt.milk':    { uk: 'Молоко', en: 'Milk', es: 'Leche', it: 'Latte', de: 'Milch', ru: 'Молоко' },
  'opt.kind':    { uk: 'Вид', en: 'Kind', es: 'Tipo', it: 'Tipo', de: 'Sorte', ru: 'Вид' },
  'opt.serve':   { uk: 'Подача', en: 'Serve', es: 'Servicio', it: 'Servizio', de: 'Servierart', ru: 'Подача' },
  'opt.style':   { uk: 'Стиль', en: 'Style', es: 'Estilo', it: 'Stile', de: 'Stil', ru: 'Стиль' },
  'cart.sending':{ uk: 'Надсилаємо…', en: 'Sending…', es: 'Enviando…', it: 'Invio…', de: 'Wird gesendet…', ru: 'Отправляем…' },
  'cart.empty':  { uk: 'Кошик порожній', en: 'Your basket is empty', es: 'La cesta está vacía', it: 'Il carrello è vuoto', de: 'Der Warenkorb ist leer', ru: 'Корзина пуста' },
  'cart.remove': { uk: 'Прибрати', en: 'Remove', es: 'Quitar', it: 'Rimuovi', de: 'Entfernen', ru: 'Убрать' },
  'cart.close':  { uk: 'Закрити', en: 'Close', es: 'Cerrar', it: 'Chiudi', de: 'Schließen', ru: 'Закрыть' },
  'cart.needTable': {
    uk: 'Щоб замовити, скануйте QR на своєму столі.',
    en: 'To order, scan the QR code on your table.',
    es: 'Para pedir, escanee el QR de su mesa.',
    it: 'Per ordinare, scansionate il QR del vostro tavolo.',
    de: 'Zum Bestellen scannen Sie den QR-Code an Ihrem Tisch.',
    ru: 'Чтобы заказать, отсканируйте QR на своём столе.'
  },
  'cart.dropped': {
    uk: 'Це щойно закінчилося й не потрапило в замовлення:',
    en: 'These just ran out and are not in the order:',
    es: 'Esto se ha agotado y no entra en el pedido:',
    it: 'Questo è appena finito e non entra nell’ordine:',
    de: 'Das ist gerade ausgegangen und nicht in der Bestellung:',
    ru: 'Это только что закончилось и не попало в заказ:'
  },
  'cart.confirmRest': {
    uk: 'Замовити решту', en: 'Order the rest', es: 'Pedir el resto',
    it: 'Ordina il resto', de: 'Rest bestellen', ru: 'Заказать остальное'
  },

  /* ------------------------------------------------- статус замовлення -- */
  'order.number':   { uk: 'Замовлення №', en: 'Order #', es: 'Pedido n.º', it: 'Ordine n.', de: 'Bestellung Nr.', ru: 'Заказ №' },
  'order.new':      { uk: 'Нове замовлення', en: 'New order', es: 'Nuevo pedido', it: 'Nuovo ordine', de: 'Neue Bestellung', ru: 'Новый заказ' },
  'order.st.draft':           { uk: 'Оформлюється', en: 'Being placed', es: 'En curso', it: 'In corso', de: 'Wird erstellt', ru: 'Оформляется' },
  'order.st.payment_pending': { uk: 'Очікує оплати', en: 'Awaiting payment', es: 'Esperando pago', it: 'In attesa di pagamento', de: 'Zahlung ausstehend', ru: 'Ожидает оплаты' },
  'order.st.paid':            { uk: 'Оплачено, передано на кухню', en: 'Paid, sent to the kitchen', es: 'Pagado, enviado a cocina', it: 'Pagato, inviato in cucina', de: 'Bezahlt, an die Küche gesendet', ru: 'Оплачено, передано на кухню' },
  'order.st.accepted':        { uk: 'Готується', en: 'Being prepared', es: 'Preparándose', it: 'In preparazione', de: 'Wird zubereitet', ru: 'Готовится' },
  'order.st.ready':           { uk: 'Готово, несемо', en: 'Ready, on its way', es: 'Listo, va para allá', it: 'Pronto, in arrivo', de: 'Fertig, kommt gleich', ru: 'Готово, несём' },
  'order.st.served':          { uk: 'Подано', en: 'Served', es: 'Servido', it: 'Servito', de: 'Serviert', ru: 'Подано' },
  'order.st.failed':          { uk: 'Оплата не пройшла', en: 'Payment failed', es: 'El pago no se ha completado', it: 'Pagamento non riuscito', de: 'Zahlung fehlgeschlagen', ru: 'Оплата не прошла' },
  'order.st.refunded':        { uk: 'Повернуто', en: 'Refunded', es: 'Reembolsado', it: 'Rimborsato', de: 'Erstattet', ru: 'Возвращено' },

  /* --------------------------------------------------------- зв’язок --- */
  'net.offline': {
    uk: 'Немає зв’язку із закладом. Показано останній відомий стан меню.',
    en: 'No connection to the venue. Showing the last known menu state.',
    es: 'Sin conexión con el local. Se muestra el último estado conocido de la carta.',
    it: 'Nessuna connessione con il locale. Viene mostrato l’ultimo stato noto del menu.',
    de: 'Keine Verbindung zum Lokal. Angezeigt wird der zuletzt bekannte Kartenstand.',
    ru: 'Нет связи с заведением. Показано последнее известное состояние меню.'
  },
  'net.loading': { uk: 'Завантаження меню…', en: 'Loading the menu…', es: 'Cargando la carta…', it: 'Caricamento del menu…', de: 'Karte wird geladen…', ru: 'Загрузка меню…' },
  'net.failed': {
    uk: 'Меню не завантажилося. Оновіть сторінку або покличте офіціанта.',
    en: 'The menu failed to load. Refresh the page or ask your server.',
    es: 'La carta no se ha cargado. Actualice la página o avise al camarero.',
    it: 'Il menu non si è caricato. Aggiornate la pagina o chiedete al personale.',
    de: 'Die Karte konnte nicht geladen werden. Seite neu laden oder Personal ansprechen.',
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
