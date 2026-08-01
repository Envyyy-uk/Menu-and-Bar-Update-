/* ==========================================================================
   Підписи адмін-панелі — ті самі шість мов, що й у меню.

   Окремим файлом, бо гостьовій сторінці вони не потрібні: вона й так
   найважча частина завантаження на телефоні гостя.
   ========================================================================== */

Object.assign(I18N, {
  'a.title':    { uk: 'Панель', en: 'Admin', es: 'Panel', it: 'Pannello', de: 'Verwaltung', ru: 'Панель' },
  'a.sub':      { uk: 'Меню, розклади, столи', en: 'Menu, schedules, tables', es: 'Carta, horarios, mesas', it: 'Menu, orari, tavoli', de: 'Karte, Zeiten, Tische', ru: 'Меню, расписания, столы' },

  /* ---------------------------------------------------------- вхід ----- */
  'a.login':     { uk: 'Вхід', en: 'Sign in', es: 'Entrar', it: 'Accedi', de: 'Anmelden', ru: 'Вход' },
  'a.email':     { uk: 'Пошта', en: 'Email', es: 'Correo', it: 'Email', de: 'E-Mail', ru: 'Почта' },
  'a.password':  { uk: 'Пароль', en: 'Password', es: 'Contraseña', it: 'Password', de: 'Passwort', ru: 'Пароль' },
  'a.pin':       { uk: 'PIN', en: 'PIN', es: 'PIN', it: 'PIN', de: 'PIN', ru: 'PIN' },
  'a.byPin':     { uk: 'Увійти PIN-ом', en: 'Sign in with PIN', es: 'Entrar con PIN', it: 'Accedi con PIN', de: 'Mit PIN anmelden', ru: 'Войти по PIN' },
  'a.byPassword':{ uk: 'Увійти поштою', en: 'Sign in with email', es: 'Entrar con correo', it: 'Accedi con email', de: 'Mit E-Mail anmelden', ru: 'Войти по почте' },
  'a.pinHint':   {
    uk: 'PIN працює лише з пристрою, який додав менеджер.',
    en: 'The PIN only works on a device a manager has registered.',
    es: 'El PIN solo funciona en un dispositivo registrado por un responsable.',
    it: 'Il PIN funziona solo su un dispositivo registrato da un responsabile.',
    de: 'Die PIN funktioniert nur auf einem vom Manager registrierten Gerät.',
    ru: 'PIN работает только с устройства, которое добавил менеджер.'
  },
  'a.logout':   { uk: 'Вийти', en: 'Sign out', es: 'Salir', it: 'Esci', de: 'Abmelden', ru: 'Выйти' },

  /* -------------------------------------------------------- вкладки ---- */
  'a.tab.items':     { uk: 'Позиції', en: 'Items', es: 'Platos', it: 'Voci', de: 'Positionen', ru: 'Позиции' },
  'a.tab.sections':  { uk: 'Розділи', en: 'Sections', es: 'Secciones', it: 'Sezioni', de: 'Bereiche', ru: 'Разделы' },
  'a.tab.schedules': { uk: 'Розклади', en: 'Schedules', es: 'Horarios', it: 'Orari', de: 'Zeitpläne', ru: 'Расписания' },
  'a.tab.tables':    { uk: 'Столи', en: 'Tables', es: 'Mesas', it: 'Tavoli', de: 'Tische', ru: 'Столы' },
  'a.tab.users':     { uk: 'Люди', en: 'People', es: 'Personal', it: 'Personale', de: 'Personal', ru: 'Люди' },
  'a.tab.audit':     { uk: 'Аудит', en: 'Audit', es: 'Auditoría', it: 'Registro', de: 'Protokoll', ru: 'Аудит' },

  /* ---------------------------------------------------------- стани ---- */
  'a.state.auto': { uk: 'За розкладом', en: 'On schedule', es: 'Según horario', it: 'Da orario', de: 'Nach Zeitplan', ru: 'По расписанию' },
  'a.state.on':   { uk: 'Завжди', en: 'Always', es: 'Siempre', it: 'Sempre', de: 'Immer', ru: 'Всегда' },
  'a.state.off':  { uk: 'Немає', en: 'Off (86)', es: 'Agotado', it: 'Esaurito', de: 'Aus (86)', ru: 'Нет' },
  'a.state.soon': { uk: 'Скоро', en: 'Soon', es: 'Pronto', it: 'Presto', de: 'Bald', ru: 'Скоро' },
  'a.openNow':    { uk: 'Доступно зараз', en: 'Available now', es: 'Disponible ahora', it: 'Disponibile ora', de: 'Jetzt verfügbar', ru: 'Доступно сейчас' },
  'a.closedNow':  { uk: 'Недоступно зараз', en: 'Unavailable now', es: 'No disponible ahora', it: 'Non disponibile ora', de: 'Jetzt nicht verfügbar', ru: 'Недоступно сейчас' },

  /* ---------------------------------------------------------- поля ----- */
  'a.price':    { uk: 'Ціна', en: 'Price', es: 'Precio', it: 'Prezzo', de: 'Preis', ru: 'Цена' },
  'a.station':  { uk: 'Станція', en: 'Station', es: 'Estación', it: 'Postazione', de: 'Station', ru: 'Станция' },
  'a.kitchen':  { uk: 'Кухня', en: 'Kitchen', es: 'Cocina', it: 'Cucina', de: 'Küche', ru: 'Кухня' },
  'a.bar':      { uk: 'Бар', en: 'Bar', es: 'Barra', it: 'Bar', de: 'Bar', ru: 'Бар' },
  'a.opensAt':  { uk: 'Дата відкриття', en: 'Opening date', es: 'Fecha de apertura', it: 'Data di apertura', de: 'Öffnungsdatum', ru: 'Дата открытия' },
  'a.schedule': { uk: 'Розклад', en: 'Schedule', es: 'Horario', it: 'Orario', de: 'Zeitplan', ru: 'Расписание' },
  'a.noSchedule': { uk: '— без розкладу —', en: '— no schedule —', es: '— sin horario —', it: '— senza orario —', de: '— kein Zeitplan —', ru: '— без расписания —' },
  'a.orderable': { uk: 'Можна замовити', en: 'Orderable', es: 'Se puede pedir', it: 'Ordinabile', de: 'Bestellbar', ru: 'Можно заказать' },

  /* ---------------------------------------------------------- дії ------ */
  'a.save':    { uk: 'Зберегти', en: 'Save', es: 'Guardar', it: 'Salva', de: 'Speichern', ru: 'Сохранить' },
  'a.saved':   { uk: 'Збережено', en: 'Saved', es: 'Guardado', it: 'Salvato', de: 'Gespeichert', ru: 'Сохранено' },
  'a.add':     { uk: 'Додати', en: 'Add', es: 'Añadir', it: 'Aggiungi', de: 'Hinzufügen', ru: 'Добавить' },
  'a.delete':  { uk: 'Видалити', en: 'Delete', es: 'Eliminar', it: 'Elimina', de: 'Löschen', ru: 'Удалить' },
  'a.cancel':  { uk: 'Скасувати', en: 'Cancel', es: 'Cancelar', it: 'Annulla', de: 'Abbrechen', ru: 'Отмена' },
  'a.search':  { uk: 'Пошук по назві', en: 'Search by name', es: 'Buscar por nombre', it: 'Cerca per nome', de: 'Nach Name suchen', ru: 'Поиск по названию' },

  /* --------------------------------------------------------- столи ----- */
  'a.tables.new':   { uk: 'Новий стіл', en: 'New table', es: 'Nueva mesa', it: 'Nuovo tavolo', de: 'Neuer Tisch', ru: 'Новый стол' },
  'a.tables.qr':    { uk: 'QR', en: 'QR', es: 'QR', it: 'QR', de: 'QR', ru: 'QR' },
  'a.tables.rotate':{ uk: 'Змінити токен', en: 'Rotate token', es: 'Rotar token', it: 'Ruota token', de: 'Token erneuern', ru: 'Сменить токен' },
  'a.tables.rotateWarn': {
    uk: 'Стара наліпка перестане працювати. Друкувати нову — одразу.',
    en: 'The old sticker stops working. Print the new one right away.',
    es: 'La pegatina antigua deja de funcionar. Imprima la nueva enseguida.',
    it: 'Il vecchio adesivo smette di funzionare. Stampate subito il nuovo.',
    de: 'Der alte Aufkleber funktioniert nicht mehr. Drucken Sie den neuen sofort.',
    ru: 'Старая наклейка перестанет работать. Печатайте новую сразу.'
  },
  'a.tables.print': { uk: 'Друк', en: 'Print', es: 'Imprimir', it: 'Stampa', de: 'Drucken', ru: 'Печать' },
  'a.tables.active':{ uk: 'Активний', en: 'Active', es: 'Activa', it: 'Attivo', de: 'Aktiv', ru: 'Активен' },

  /* ---------------------------------------------------------- люди ----- */
  'a.users.new':    { uk: 'Новий акаунт', en: 'New account', es: 'Nueva cuenta', it: 'Nuovo account', de: 'Neues Konto', ru: 'Новый аккаунт' },
  'a.users.name':   { uk: 'Ім’я', en: 'Name', es: 'Nombre', it: 'Nome', de: 'Name', ru: 'Имя' },
  'a.users.role':   { uk: 'Роль', en: 'Role', es: 'Rol', it: 'Ruolo', de: 'Rolle', ru: 'Роль' },
  'a.users.withPin':{ uk: 'Видати PIN', en: 'Issue a PIN', es: 'Emitir PIN', it: 'Assegna un PIN', de: 'PIN vergeben', ru: 'Выдать PIN' },
  'a.users.resetPin':{ uk: 'Скинути PIN', en: 'Reset PIN', es: 'Restablecer PIN', it: 'Reimposta PIN', de: 'PIN zurücksetzen', ru: 'Сбросить PIN' },
  'a.users.pinOnce':{
    uk: 'PIN показується один раз. Запишіть його зараз.',
    en: 'The PIN is shown once. Write it down now.',
    es: 'El PIN se muestra una vez. Anótelo ahora.',
    it: 'Il PIN viene mostrato una sola volta. Annotatelo adesso.',
    de: 'Die PIN wird einmal angezeigt. Notieren Sie sie jetzt.',
    ru: 'PIN показывается один раз. Запишите его сейчас.'
  },
  'a.devices':      { uk: 'Пристрої', en: 'Devices', es: 'Dispositivos', it: 'Dispositivi', de: 'Geräte', ru: 'Устройства' },
  'a.devices.new':  { uk: 'Додати цей пристрій', en: 'Register this device', es: 'Registrar este dispositivo', it: 'Registra questo dispositivo', de: 'Dieses Gerät registrieren', ru: 'Добавить это устройство' },
  'a.devices.hint': {
    uk: 'Додається саме той пристрій, з якого ви це натискаєте.',
    en: 'This registers the device you are pressing it on.',
    es: 'Se registra el dispositivo desde el que pulsa.',
    it: 'Viene registrato il dispositivo da cui premete.',
    de: 'Registriert wird genau das Gerät, auf dem Sie drücken.',
    ru: 'Добавляется именно то устройство, с которого вы нажимаете.'
  },

  /* --------------------------------------------------------- аудит ----- */
  'a.audit.when':   { uk: 'Коли', en: 'When', es: 'Cuándo', it: 'Quando', de: 'Wann', ru: 'Когда' },
  'a.audit.who':    { uk: 'Хто', en: 'Who', es: 'Quién', it: 'Chi', de: 'Wer', ru: 'Кто' },
  'a.audit.what':   { uk: 'Що', en: 'What', es: 'Qué', it: 'Cosa', de: 'Was', ru: 'Что' },

  /* -------------------------------------------------------- розклади --- */
  'a.sched.new':      { uk: 'Новий розклад', en: 'New schedule', es: 'Nuevo horario', it: 'Nuovo orario', de: 'Neuer Zeitplan', ru: 'Новое расписание' },
  'a.sched.key':      { uk: 'Ключ', en: 'Key', es: 'Clave', it: 'Chiave', de: 'Schlüssel', ru: 'Ключ' },
  'a.sched.addRange': { uk: 'Додати діапазон', en: 'Add a range', es: 'Añadir tramo', it: 'Aggiungi fascia', de: 'Zeitraum hinzufügen', ru: 'Добавить диапазон' },
  'a.sched.midnight': {
    uk: 'Кінець раніше за початок означає перехід через північ.',
    en: 'An end earlier than the start means it runs past midnight.',
    es: 'Un fin anterior al inicio significa que cruza la medianoche.',
    it: 'Una fine precedente all’inizio significa che supera la mezzanotte.',
    de: 'Ein Ende vor dem Beginn bedeutet über Mitternacht hinaus.',
    ru: 'Конец раньше начала означает переход через полночь.'
  },

  /* --------------------------------------------------------- службове -- */
  'a.error':    { uk: 'Не вдалося', en: 'Failed', es: 'Ha fallado', it: 'Non riuscito', de: 'Fehlgeschlagen', ru: 'Не удалось' },
  'a.confirm':  { uk: 'Точно?', en: 'Are you sure?', es: '¿Seguro?', it: 'Sicuro?', de: 'Sicher?', ru: 'Точно?' },
  'a.empty':    { uk: 'Порожньо', en: 'Nothing here', es: 'Vacío', it: 'Vuoto', de: 'Leer', ru: 'Пусто' },
  'a.venueTime':{ uk: 'час закладу', en: 'venue time', es: 'hora del local', it: 'ora del locale', de: 'Ortszeit des Lokals', ru: 'время заведения' }
});
