/* ==========================================================================
   Підписи адмін-панелі — ті самі шість мов, що й у меню.

   Окремим файлом, бо гостьовій сторінці вони не потрібні: вона й так
   найважча частина завантаження на телефоні гостя.
   ========================================================================== */

Object.assign(I18N, {
  'a.title':    { uk: 'Панель', en: 'Admin',    ru: 'Панель' },
  'a.sub':      { uk: 'Меню, розклади, столи', en: 'Menu, schedules, tables',    ru: 'Меню, расписания, столы' },

  /* ---------------------------------------------------------- вхід ----- */
  'a.login':     { uk: 'Вхід', en: 'Sign in',    ru: 'Вход' },
  'a.email':     { uk: 'Пошта', en: 'Email',    ru: 'Почта' },
  'a.password':  { uk: 'Пароль', en: 'Password',    ru: 'Пароль' },
  'a.pin':       { uk: 'PIN', en: 'PIN',    ru: 'PIN' },
  'a.byPin':     { uk: 'Увійти PIN-ом', en: 'Sign in with PIN',    ru: 'Войти по PIN' },
  'a.byPassword':{ uk: 'Увійти поштою', en: 'Sign in with email',    ru: 'Войти по почте' },
  'a.pinHint':   {
    uk: 'PIN працює лише з пристрою, який додав менеджер.',
    en: 'The PIN only works on a device a manager has registered.',   
    ru: 'PIN работает только с устройства, которое добавил менеджер.'
  },
  'a.logout':   { uk: 'Вийти', en: 'Sign out',    ru: 'Выйти' },

  /* -------------------------------------------------------- вкладки ---- */
  'a.tab.items':     { uk: 'Позиції', en: 'Items',    ru: 'Позиции' },
  'a.tab.schedules': { uk: 'Розклади', en: 'Schedules',    ru: 'Расписания' },
  'a.tab.tables':    { uk: 'Столи', en: 'Tables',    ru: 'Столы' },
  'a.tab.users':     { uk: 'Люди', en: 'People',    ru: 'Люди' },
  'a.tab.audit':     { uk: 'Аудит', en: 'Audit',    ru: 'Аудит' },

  /* ---------------------------------------------------------- стани ---- */
  'a.state.auto': { uk: 'За розкладом', en: 'On schedule',    ru: 'По расписанию' },
  'a.state.on':   { uk: 'Завжди', en: 'Always',    ru: 'Всегда' },
  'a.state.off':  { uk: 'Немає', en: 'Off (86)',    ru: 'Нет' },
  'a.state.soon': { uk: 'Скоро', en: 'Soon',    ru: 'Скоро' },
  'a.openNow':    { uk: 'Доступно зараз', en: 'Available now',    ru: 'Доступно сейчас' },
  'a.closedNow':  { uk: 'Недоступно зараз', en: 'Unavailable now',    ru: 'Недоступно сейчас' },

  /* ---------------------------------------------------------- поля ----- */
  'a.price':    { uk: 'Ціна', en: 'Price',    ru: 'Цена' },
  'a.station':  { uk: 'Станція', en: 'Station',    ru: 'Станция' },
  'a.kitchen':  { uk: 'Кухня', en: 'Kitchen',    ru: 'Кухня' },
  'a.bar':      { uk: 'Бар', en: 'Bar',    ru: 'Бар' },
  'a.opensAt':  { uk: 'Дата відкриття', en: 'Opening date',    ru: 'Дата открытия' },
  'a.schedule': { uk: 'Розклад', en: 'Schedule',    ru: 'Расписание' },
  'a.noSchedule': { uk: '— без розкладу —', en: '— no schedule —',    ru: '— без расписания —' },
  'a.orderable': { uk: 'Можна замовити', en: 'Orderable',    ru: 'Можно заказать' },

  /* ---------------------------------------------------------- дії ------ */
  'a.save':    { uk: 'Зберегти', en: 'Save',    ru: 'Сохранить' },
  'a.saved':   { uk: 'Збережено', en: 'Saved',    ru: 'Сохранено' },
  'a.add':     { uk: 'Додати', en: 'Add',    ru: 'Добавить' },
  'a.delete':  { uk: 'Видалити', en: 'Delete',    ru: 'Удалить' },
  'a.cancel':  { uk: 'Скасувати', en: 'Cancel',    ru: 'Отмена' },
  'a.search':  { uk: 'Пошук по назві', en: 'Search by name',    ru: 'Поиск по названию' },

  /* --------------------------------------------------------- столи ----- */
  'a.tables.new':   { uk: 'Новий стіл', en: 'New table',    ru: 'Новый стол' },
  'a.tables.qr':    { uk: 'QR', en: 'QR',    ru: 'QR' },
  'a.tables.rotate':{ uk: 'Змінити токен', en: 'Rotate token',    ru: 'Сменить токен' },
  'a.tables.rotateWarn': {
    uk: 'Стара наліпка перестане працювати. Друкувати нову — одразу.',
    en: 'The old sticker stops working. Print the new one right away.',   
    ru: 'Старая наклейка перестанет работать. Печатайте новую сразу.'
  },
  'a.tables.print': { uk: 'Друк', en: 'Print',    ru: 'Печать' },
  'a.tables.printHint': {
    uk: 'Наклейте на стіл. Після зміни токена надрукуйте нову — стара перестане працювати.',
    en: 'Stick it on the table. After rotating the token print a new one — the old sticker stops working.',   
    ru: 'Наклейте на стол. После смены токена напечатайте новую — старая перестанет работать.'
  },
  'a.tables.active':{ uk: 'Активний', en: 'Active',    ru: 'Активен' },

  /* ---------------------------------------------------------- люди ----- */
  'a.users.new':    { uk: 'Новий акаунт', en: 'New account',    ru: 'Новый аккаунт' },
  'a.users.name':   { uk: 'Ім’я', en: 'Name',    ru: 'Имя' },
  'a.users.role':   { uk: 'Роль', en: 'Role',    ru: 'Роль' },
  'a.users.withPin':{ uk: 'Видати PIN', en: 'Issue a PIN',    ru: 'Выдать PIN' },
  'a.users.resetPin':{ uk: 'Скинути PIN', en: 'Reset PIN',    ru: 'Сбросить PIN' },
  'a.users.pinOnce':{
    uk: 'PIN показується один раз. Запишіть його зараз.',
    en: 'The PIN is shown once. Write it down now.',   
    ru: 'PIN показывается один раз. Запишите его сейчас.'
  },
  'a.devices':      { uk: 'Пристрої', en: 'Devices',    ru: 'Устройства' },
  'a.devices.new':  { uk: 'Додати цей пристрій', en: 'Register this device',    ru: 'Добавить это устройство' },
  'a.devices.hint': {
    uk: 'Додається саме той пристрій, з якого ви це натискаєте.',
    en: 'This registers the device you are pressing it on.',   
    ru: 'Добавляется именно то устройство, с которого вы нажимаете.'
  },

  /* --------------------------------------------------------- аудит ----- */
  'a.audit.when':   { uk: 'Коли', en: 'When',    ru: 'Когда' },
  'a.audit.who':    { uk: 'Хто', en: 'Who',    ru: 'Кто' },
  'a.audit.what':   { uk: 'Що', en: 'What',    ru: 'Что' },

  /* -------------------------------------------------------- розклади --- */
  'a.sched.new':      { uk: 'Новий розклад', en: 'New schedule',    ru: 'Новое расписание' },
  'a.sched.key':      { uk: 'Ключ', en: 'Key',    ru: 'Ключ' },
  'a.sched.addRange': { uk: 'Додати діапазон', en: 'Add a range',    ru: 'Добавить диапазон' },
  'a.sched.midnight': {
    uk: 'Кінець раніше за початок означає перехід через північ.',
    en: 'An end earlier than the start means it runs past midnight.',   
    ru: 'Конец раньше начала означает переход через полночь.'
  },

  /* --------------------------------------------------------- службове -- */
  'a.error':    { uk: 'Не вдалося', en: 'Failed',    ru: 'Не удалось' },
  'a.confirm':  { uk: 'Точно?', en: 'Are you sure?',    ru: 'Точно?' },
  'a.empty':    { uk: 'Порожньо', en: 'Nothing here',    ru: 'Пусто' },
  'a.venueTime':{ uk: 'час закладу', en: 'venue time',    ru: 'время заведения' },

  /* --------------------------------------------------- замовлення й гроші */
  'a.tab.orders':   { uk: 'Замовлення', en: 'Orders',    ru: 'Заказы' },
  'a.orders.empty': { uk: 'Живих замовлень немає', en: 'No live orders',    ru: 'Живых заказов нет' },
  'a.orders.accepted':{ uk: 'Прийнято', en: 'Accepted',    ru: 'Принято' },
  'a.orders.ready': { uk: 'Готово', en: 'Ready',    ru: 'Готово' },
  'a.orders.served':{ uk: 'Подано', en: 'Served',    ru: 'Подано' },
  'a.orders.late':  {
    uk: 'Оплачено й досі не прийнято', en: 'Paid and still not accepted',    ru: 'Оплачено и до сих пор не принято'
  },
  'a.wallets':          { uk: 'Apple Pay і Google Pay', en: 'Apple Pay and Google Pay',    ru: 'Apple Pay и Google Pay' },
  'a.wallets.https':    { uk: 'HTTPS', en: 'HTTPS',    ru: 'HTTPS' },
  'a.wallets.domain':   { uk: 'домен зареєстровано для Apple Pay', en: 'domain registered for Apple Pay',    ru: 'домен зарегистрирован для Apple Pay' },
  'a.wallets.register': { uk: 'Зареєструвати домен', en: 'Register domain',    ru: 'Зарегистрировать домен' },
  'a.wallets.hint': {
    uk: 'Гаманці ще треба ввімкнути в дашборді закладу. Якщо кнопки немає — вона не ламається, її просто не показують.',
    en: 'Wallets also have to be switched on in the venue dashboard. A missing button is not an error — it is simply not shown.',   
    ru: 'Кошельки нужно ещё включить в дашборде заведения. Если кнопки нет — она не сломалась, её просто не показывают.'
  },
  'a.refund':       { uk: 'Повернути', en: 'Refund',    ru: 'Вернуть' },
  'a.refund.amount':{ uk: 'Сума повернення', en: 'Refund amount',    ru: 'Сумма возврата' },
  'a.refund.limit': { uk: 'Ваша стеля', en: 'Your ceiling',    ru: 'Ваш потолок' },
  'a.refund.none':  { uk: 'без стелі', en: 'no ceiling',    ru: 'без потолка' },
  'a.refunded':     { uk: 'Повернуто', en: 'Refunded',    ru: 'Возвращено' },

  'a.stripe':          { uk: 'Stripe', en: 'Stripe',    ru: 'Stripe' },
  'a.stripe.connect':  { uk: 'Підключити Stripe', en: 'Connect Stripe',    ru: 'Подключить Stripe' },
  'a.stripe.ok':       { uk: 'Підключено, платежі приймаються', en: 'Connected, charges enabled',    ru: 'Подключено, платежи принимаются' },
  'a.stripe.pending':  { uk: 'Акаунт створено, KYC не завершено', en: 'Account created, KYC unfinished',    ru: 'Аккаунт создан, KYC не завершён' },
  'a.stripe.offline':  {
    uk: 'Ключів немає — замовлення підтверджуються без оплати. Це режим прогону, не робочий.',
    en: 'No keys — orders are confirmed without payment. This is the rehearsal mode, not production.',   
    ru: 'Ключей нет — заказы подтверждаются без оплаты. Это режим прогона, не рабочий.'
  }

});
