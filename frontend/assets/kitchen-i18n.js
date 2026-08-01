/* ==========================================================================
   Підписи екрана кухні. Їх мало навмисно: екран робить одну справу.
   ========================================================================== */

Object.assign(I18N, {
  'k.title':   { uk: 'Кухня', en: 'Kitchen', es: 'Cocina', it: 'Cucina', de: 'Küche', ru: 'Кухня' },
  'k.bar':     { uk: 'Бар', en: 'Bar', es: 'Barra', it: 'Bar', de: 'Bar', ru: 'Бар' },
  'k.accept':  { uk: 'Прийнято', en: 'Accepted', es: 'Aceptado', it: 'Accettato', de: 'Angenommen', ru: 'Принято' },
  'k.ready':   { uk: 'Готово', en: 'Ready', es: 'Listo', it: 'Pronto', de: 'Fertig', ru: 'Готово' },
  'k.served':  { uk: 'Віддано', en: 'Served', es: 'Servido', it: 'Servito', de: 'Ausgegeben', ru: 'Отдано' },
  'k.empty':   { uk: 'Замовлень немає', en: 'No orders', es: 'Sin pedidos', it: 'Nessun ordine', de: 'Keine Bestellungen', ru: 'Заказов нет' },
  'k.table':   { uk: 'Стіл', en: 'Table', es: 'Mesa', it: 'Tavolo', de: 'Tisch', ru: 'Стол' },
  'k.waiting': { uk: 'чекає', en: 'waiting', es: 'esperando', it: 'in attesa', de: 'wartet', ru: 'ждёт' },

  'k.online':  { uk: 'Зв’язок є', en: 'Connected', es: 'Conectado', it: 'Connesso', de: 'Verbunden', ru: 'Связь есть' },
  'k.offline.head': {
    uk: 'ЗВ’ЯЗКУ НЕМАЄ', en: 'CONNECTION LOST', es: 'SIN CONEXIÓN',
    it: 'CONNESSIONE PERSA', de: 'KEINE VERBINDUNG', ru: 'СВЯЗИ НЕТ'
  },
  'k.offline.body': {
    uk: 'Список застарілий. Замовлення можуть приходити й не з’являтися тут. Перевірте wifi.',
    en: 'This list is stale. Orders may be arriving and not showing here. Check the wifi.',
    es: 'Esta lista está desactualizada. Pueden estar llegando pedidos que no se ven aquí. Revise el wifi.',
    it: 'Questa lista è vecchia. Potrebbero arrivare ordini che qui non si vedono. Controllate il wifi.',
    de: 'Diese Liste ist veraltet. Es können Bestellungen eingehen, die hier nicht erscheinen. WLAN prüfen.',
    ru: 'Список устарел. Заказы могут приходить и не появляться здесь. Проверьте wifi.'
  },
  'k.late': {
    uk: 'ОПЛАЧЕНО Й ДОСІ НЕ ПРИЙНЯТО', en: 'PAID AND STILL NOT ACCEPTED',
    es: 'PAGADO Y AÚN SIN ACEPTAR', it: 'PAGATO E ANCORA NON ACCETTATO',
    de: 'BEZAHLT UND NOCH NICHT ANGENOMMEN', ru: 'ОПЛАЧЕНО И ДО СИХ ПОР НЕ ПРИНЯТО'
  },
  'k.mute':    { uk: 'Стишити', en: 'Mute', es: 'Silenciar', it: 'Silenzia', de: 'Stumm', ru: 'Приглушить' },
  'k.unmute':  { uk: 'Звук', en: 'Sound', es: 'Sonido', it: 'Suono', de: 'Ton', ru: 'Звук' },
  'k.course.0': { uk: 'Одразу', en: 'Right away', es: 'De inmediato', it: 'Subito', de: 'Sofort', ru: 'Сразу' },
  'k.course.1': { uk: 'Закуски', en: 'Starters', es: 'Entrantes', it: 'Antipasti', de: 'Vorspeisen', ru: 'Закуски' },
  'k.course.2': { uk: 'Основні', en: 'Mains', es: 'Principales', it: 'Secondi', de: 'Hauptgerichte', ru: 'Основные' },
  'k.course.3': { uk: 'Десерт', en: 'Dessert', es: 'Postre', it: 'Dolce', de: 'Dessert', ru: 'Десерт' },
  'k.blocked': {
    uk: 'Чекає: спершу віддайте попередній курс',
    en: 'On hold: send the previous course first',
    es: 'En espera: primero sirva el plato anterior',
    it: 'In attesa: prima servite la portata precedente',
    de: 'Wartet: zuerst den vorherigen Gang ausgeben',
    ru: 'Ждёт: сначала отдайте предыдущий курс'
  },
  'k.awaitFire': {
    uk: 'Чекає команди залу — офіціант запустить, коли гість доїсть попереднє',
    en: 'Waiting for the floor — the server fires it when the guests finish the previous course',
    es: 'Esperando a la sala: el camarero lo lanza cuando terminen el plato anterior',
    it: 'In attesa della sala: il cameriere la lancia quando finiscono la portata precedente',
    de: 'Wartet auf den Service — der Kellner stößt ihn an, wenn der vorige Gang gegessen ist',
    ru: 'Ждёт команды зала — официант запустит, когда гость доест предыдущее'
  },
  'k.enter':   { uk: 'Увійти PIN-ом', en: 'Sign in with PIN', es: 'Entrar con PIN', it: 'Accedi con PIN', de: 'Mit PIN anmelden', ru: 'Войти по PIN' },
  'k.switch':  { uk: 'Станція', en: 'Station', es: 'Estación', it: 'Postazione', de: 'Station', ru: 'Станция' }
});
