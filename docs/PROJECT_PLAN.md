# Платформа замовлення за столом — повний план проєкту

Єдиний документ. Містить контекст, архітектуру, ролі, фази й демонстраційні дані.
Новий репозиторій, будується з нуля. Попередній проєкт використовується тільки як довідник і не змінюється.

---

## 1. Що будуємо

Гість сідає за стіл, сканує QR, бачить меню з повним складом і алергенами однією з шести мов, замовляє, оплачує з телефона. Замовлення потрапляє на екран кухні або бару. Персонал вимикає позиції PIN-кодом. Менеджер бачить, хто й коли змінив ціну.

Ключова відмінність від наявних QR-меню — **структурована модель алергенів**: три рівні (містить / може містити / можна прибрати), джерело даних із датою перевірки, словник інгредієнтів із крос-мовним пошуком. Це переноситься з попереднього проєкту й лишається головною цінністю.

---

## 2. Доступ і посилання

### Референсний репозиторій (тільки читання)

https://github.com/Envyyy-uk/Menu_Bar_and_Food_Guest — публічний.

```bash
# Клонувати ПОЗА новим проєктом, як довідник
git clone --depth 1 https://github.com/Envyyy-uk/Menu_Bar_and_Food_Guest.git ~/reference-menu
```

Нічого туди не комітити, гілок не створювати, PR не відкривати.

Почати з `README.md` у ньому — це журнал ухвалених рішень із поясненням причин. Рішення, описані там як перевірені й відкинуті, не повторювати.

### Правило копіювання

**Копіювати можна все, що потрібно** — код рендерингу, пошук, фільтр алергенів, словник інгредієнтів, переклади інтерфейсу, довідник 14 алергенів, логіку розкладів, стилі, PWA.

**Не копіювати нічого, що належить конкретному закладу:**

- дані меню — усі файли `assets/data-*.js` зі стравами, напоями, десертами й міцним алкоголем;
- офіційні листи алергенів із `data-official.js` — це дані третьої сторони;
- назву, бренд, іконки, кольори й будь-які тексти, пов'язані з Smith & Wollensky.

Меню нового проєкту наповнюється демонстраційними даними з розділу 14. Модель зберігаємо, вміст — ні.

### Зовнішня документація

| Тема | Посилання |
|---|---|
| Stripe Connect, огляд | https://docs.stripe.com/connect |
| Типи акаунтів Connect | https://docs.stripe.com/connect/accounts |
| Direct charges | https://docs.stripe.com/connect/direct-charges |
| Stripe Checkout | https://docs.stripe.com/payments/checkout |
| Вебхуки | https://docs.stripe.com/webhooks |
| Ідемпотентні запити | https://docs.stripe.com/api/idempotent_requests |
| Stripe CLI — локальне тестування вебхуків | https://docs.stripe.com/stripe-cli |
| PCI і зона відповідальності | https://docs.stripe.com/security/guide |
| FastAPI | https://fastapi.tiangolo.com |
| Alembic (міграції) | https://alembic.sqlalchemy.org |
| Argon2 для паролів і PIN | https://argon2-cffi.readthedocs.io |
| FSA: алергени в непакованій їжі | https://www.food.gov.uk — розділ business guidance |
| Ліцензування алкоголю (для v2) | https://www.gov.uk — Licensing Act 2003, age verification |

Якщо посилання не відкривається — шукати за назвою, документація Stripe і FastAPI регулярно перебудовує URL.

---

## 3. Архітектурні рішення, які переносяться

Ці рішення перевірені й не переглядаються:

- Склад страви — це посилання на ключі словника, а не текст. Звідси однакові переклади й пошук «кунжут» = «sesame» = «Sesam».
- Алергени на трьох рівнях: `a` містить, `m` може містити, `r` можна прибрати, плюс `src` — джерело даних із датою.
- Чотири стани позиції: `за розкладом` / `завжди` / `немає` (86) / `скоро`, з датою відкриття для останнього.
- Тижневі розклади з кількома діапазонами на день, включно з переходом через північ.
- Час завжди в поясі закладу, не пристрою — через `Intl`.
- `touch-action: manipulation` замість перехоплення `touchend`. Перехоплення ламало другий тап поспіль по сусідній кнопці.
- Два окремі маніфести PWA з різними `id` і `start_url` — інакше ярлик панелі відкриває меню.

---

## 4. Межі v1

**Входить:** гостьове меню з алергенами шістьма мовами, замовлення їжі й безалкогольних напоїв, оплата на місці, екран кухні й бару, адмін-панель із ролями.

**Не входить свідомо:**

- Алкоголь у потоці замовлення — потрібна перевірка віку при подачі (Licensing Act 2003). Позиції видно в меню, але вони не замовляються. Це v2, і це крок у потоці, а не заборона.
- Спільний рахунок на стіл, розділення рахунку, відкриті таби. При оплаті одразу вони не потрібні.
- Чайові — зачіпає Employment (Allocation of Tips) Act, розбирається окремо.
- Інтеграція з POS.
- Доставка, самовивіз, бронювання.

---

## 5. Архітектура

```
Телефон гостя ──HTTPS──┐
                       ├──> FastAPI ──> PostgreSQL
Планшет кухні ─WS──────┘        │
                                └──> Stripe (Connect, Standard)
Stripe webhooks ────────────────┘
```

- **Бекенд:** FastAPI + PostgreSQL. Вибір за знайомістю, не за фічами: знайомий стек і є надійність, бо причину знаходиш удвічі швидше.
- **Фронтенд:** статика без збірки, як у референсі.
- **Реалтайм:** WebSocket на екран кухні, fallback — polling кожні 3 с.
- **Розробка:** Docker Compose локально. Хостинг не потрібен, поки немає пілотної точки.
- **Джерело правди:** завжди Postgres. Екран кухні — лише відображення стану.

Docker тут дає однакове середовище, а не стійкість. Стійкість береться з розділу 12.

### Структура

```
/
  backend/
    app/
      main.py
      models/          SQLAlchemy
      api/             роутери: menu, orders, admin, auth, webhooks
      services/        stripe, schedule, availability
      core/            config, security, deps
    alembic/
    tests/
  frontend/
    guest/             меню, кошик, оплата
    admin/             панель
    kitchen/           екран кухні
    assets/            i18n, lexicon, allergens, styles
  docker-compose.yml
  seed_menu.json
  README.md
```

---

## 6. Модель даних

| Таблиця | Ключові поля |
|---|---|
| `venues` | `id`, `name`, `stripe_account_id`, `timezone` |
| `tables` | `id`, `venue_id`, `label` («12», «Bar 3»), `token`, `token_rotated_at`, `active` |
| `menu_items` | `id`, `venue_id`, `key`, `name`, `price_pence`, `station` (`kitchen`/`bar`), `state`, `opens_at`, `orderable`, склад і алергени за моделлю `a`/`m`/`r`/`src` |
| `schedules` | `id`, `venue_id`, `key`, діапазони днів і годин |
| `orders` | `id`, `venue_id`, `table_id`, `status`, `total_pence`, `payment_intent_id`, `client_token`, `created_at`, `paid_at`, `accepted_at`, `ready_at` |
| `order_items` | `id`, `order_id`, `menu_item_id`, `qty`, `unit_price_pence`, `name_snapshot` |
| `users` | `id`, `venue_id`, `role`, `email`, `password_hash`, `pin_hash`, `active` |
| `devices` | `id`, `venue_id`, `label`, `device_token`, `registered_by`, `active` |
| `audit_log` | `id`, `venue_id`, `user_id`, `action`, `entity`, `before`, `after`, `at` |
| `webhook_events` | `stripe_event_id` (PK), `processed_at` |

**Важливо:**

- `token` у `tables` — непрозорий випадковий рядок від 16 символів, **не номер столу**. QR веде на `/t/{token}`. Інакше сусід замовляє на чужий стіл, а перехожий з вулиці — на будь-який. Токен має ротуватися: наліпки зношуються, столи переставляють.
- `name_snapshot` і `unit_price_pence` копіюються в `order_items` у момент замовлення. Меню зміниться — історія не попливе.
- `client_token` генерується телефоном гостя і дає ідемпотентність: повторний POST з тим самим токеном повертає те саме замовлення, а не створює друге.

---

## 7. Життєвий цикл замовлення

```
draft ──> payment_pending ──> paid ──> accepted ──> ready ──> served
                │                │
                └──> failed      └──> refunded
```

**Правило, яке не порушується:** замовлення з'являється на екрані кухні **тільки** після `paid`, і `paid` виставляється **тільки** з вебхука Stripe, ніколи з відповіді браузера гостя. Клієнт може збрехати або обірватися; вебхук — ні.

**Звірка, обов'язкова:** фонова задача раз на 30 секунд шукає замовлення у стані `paid`, старші за 60 секунд і не переведені в `accepted`. Кожне таке — гучний алерт на екрані кухні й запис у лог.

Це захист від найгіршого сценарію в системі: гість заплатив, кухня не побачила, гість дізнається про це через двадцять хвилин.

**Наявність при оплаті.** Позиція може бути вимкнена, поки гість тримає її в кошику. Наявність перевіряється на сервері **в момент створення платежу**, а не при рендері меню. Якщо позиція випала — оплата не проводиться, гість бачить, що саме, і може підтвердити решту замовлення.

---

## 8. Гроші: Stripe Connect (Standard)

- Кожен заклад має **власний повноцінний акаунт Stripe**, сам проходить KYC, сам володіє дашбордом.
- Платіж проводиться як **direct charge** на акаунті закладу (заголовок `Stripe-Account`), з `application_fee_amount` на користь платформи, якщо стягуємо комісію.
- **Спори й від'ємні баланси — відповідальність закладу**, не платформи. Це головна причина вибору Standard, а не Express чи Custom.
- Дані картки **ніколи** не торкаються нашого сервера: Stripe Checkout або Elements. Це утримує нас у межах SAQ A. Одна власна форма для номера картки — і це повний аудит PCI.
- Вебхуки: підписка на події підключених акаунтів, обробник ідемпотентний за `stripe_event_id` (таблиця `webhook_events`, вставка з `ON CONFLICT DO NOTHING`). Stripe повторює доставку за дизайном.

---

## 9. Ролі й доступи

Чотири ролі. Ключі в БД англійські, підписи в інтерфейсі — шістьма мовами, як решта панелі.

| Дія | `owner` | `head_manager` | `manager` | `staff` |
|---|:--:|:--:|:--:|:--:|
| Перегляд замовлень, зміна статусу | ✓ | ✓ | ✓ | ✓ |
| 86 і стани позицій | ✓ | ✓ | ✓ | ✓ |
| Редагування розкладів | ✓ | ✓ | ✓ | — |
| Ціни, додавання й видалення позицій | ✓ | ✓ | ✓ | — |
| Столи, друк QR, ротація токенів | ✓ | ✓ | ✓ | — |
| Повернення коштів | ✓ | ✓ | до £50 | — |
| Звіти й виручка | ✓ | ✓ | ✓ | — |
| Створення акаунтів і видача PIN | ✓ | ✓ | — | — |
| Призначення ролей `manager` і `staff` | ✓ | ✓ | — | — |
| Призначення ролі `head_manager` | ✓ | — | — | — |
| Підключення й зміна Stripe | ✓ | — | — | — |
| Аудит-лог | ✓ | ✓ | — | — |
| Видалення закладу | ✓ | — | — | — |

Правила, які не порушуються:

1. Акаунти створюють **тільки** `owner` і `head_manager`.
2. Ніхто не може призначити роль, вищу або рівну власній.
3. `staff` не має доступу до грошей у жодному вигляді — ні повернень, ні звітів по виручці.
4. Перевірка прав — **на сервері, на кожному ендпойнті**. Приховування кнопок в інтерфейсі не є захистом.
5. Останнього `owner` не можна видалити або знизити.

Ліміт £50 на повернення для `manager` — цифра прикладна, поставити свою. Логіка в тому, що повернення це єдина дія, якою співробітник може вивести гроші, тож вона має мати стелю.

---

## 10. Автентифікація

Два різні механізми, і це навмисно. У ресторані пароль на спільному планшеті не працює: офіціант вводить його 50 разів за зміну й через день просто не виходить із сесії.

**`staff` — PIN на зареєстрованому пристрої**

- 6 цифр, унікальний у межах закладу, зберігається хешованим (Argon2).
- Працює тільки з пристрою, який менеджер додав у список: `devices`, з токеном пристрою в cookie.
- Обмеження спроб: 5 підряд — блокування PIN на 15 хвилин і запис в аудит.
- Сесія коротка, продовжується при активності, вихід у кінці зміни.
- PIN видає й скидає `head_manager` або `owner`. Показується один раз при створенні.

**`manager`, `head_manager`, `owner` — пошта й пароль**

- Пароль хешується Argon2, мінімум 12 символів.
- Скидання пароля через пошту.
- Для `owner` передбачити 2FA (TOTP). Можна другою ітерацією, але місце в моделі закласти одразу.

PIN — слабкий фактор, і саме тому за ним не ховаються гроші. Матриця з розділу 9 і ця схема входу — одне рішення, а не два.

---

## 11. Адмін-панель

Панель — приблизно 40% усієї роботи проєкту. Це майже завжди недооцінюють, бо вона «нецікава».

**Чого в ній немає, на відміну від референсу.** Весь механізм публікації: `overrides.js`, токен GitHub у localStorage, чернетки, банер «незбережена чернетка», «скинути чернетку», перечитування файлу повз кеш, боротьба зі застарілою PWA. Зміна стану — це запис у Postgres, гість бачить одразу. Сервер тут не додає складності, а прибирає найбільший її шматок.

**Що переноситься:** чотири стани позицій, тижневі розклади, дата відкриття для «скоро», той самий рівень контролю для позицій, розділів і сторінок, час у поясі закладу, шість мов, мобільний layout із керуванням угорі й липким при прокрутці.

**Що додається:** логін і ролі, ціни й поле `station`, керування столами з друком QR і ротацією токенів, живий список замовлень і історія, повернення коштів, статус підключення Stripe, аудит-лог.

**Окремо від екрана кухні.** Різні поверхні для різних людей: екран кухні робить одну справу великими кнопками й без навігації, панель робить усе інше. Не об'єднувати.

---

## 12. Екран кухні й надійність

Повноекранна веб-сторінка на планшеті, без сну.

- Замовлення картками, розділені на `kitchen` і `bar` за полем `station`.
- Нове замовлення — звук і візуальне виділення.
- Кнопки «Прийнято» і «Готово».
- **Індикатор зв'язку — критична фіча.** Тиша від сервера понад 10 секунд → червоний повноекранний банер і безперервний звук. Тихий застарілий список неприпустимий: кухня спокійно працюватиме, поки замовлення падають у порожнечу.
- Після відновлення зв'язку — повне перезавантаження стану з сервера, не догравання подій.

**Вимоги надійності загалом:**

1. Ідемпотентність на створенні замовлення (`client_token`) і на вебхуках (`stripe_event_id`).
2. Postgres — єдине джерело правди; перезапуск сервера нічого не втрачає.
3. Звірка `paid` → `accepted` з алертом.
4. Індикатор втрати зв'язку на екрані кухні.
5. Обрив мережі в гостя не створює дубль і не втрачає оплату.
6. Health-check ендпойнт.

---

## 13. Фази

Кожна фаза — окремий PR із критерієм готовності. Не починати наступну, поки попередня не проходить свій критерій. **Не робити дві фази одним PR** — інакше наприкінці неможливо зрозуміти, що саме зламалося.

### Фаза 1 — каркас

Docker Compose (FastAPI + Postgres), Alembic, схема з розділу 6, health-check, `GET /api/menu` на демо-даних із розділу 14.

*Готово, коли:* `docker compose up` піднімає все з нуля на чистій машині.

### Фаза 2 — гостьове меню

Перенести інфраструктуру з референсу. Рендеринг з API, фільтр алергенів, пошук по складнику шістьма мовами, теми, PWA, розклади.

*Готово, коли:* гість знаходить страву за інгредієнтом будь-якою з шести мов і фільтрує за своїми алергенами.

### Фаза 3 — автентифікація й ролі

Таблиці `users`, `devices`, `audit_log`. Обидві схеми входу з розділу 10, матриця прав із розділу 9, перевірка на кожному ендпойнті. Сідер першого `owner`.

*Готово, коли:* тести підтверджують, що `staff` отримує 403 на цінах, поверненнях і створенні акаунтів.

### Фаза 4 — панель

Усе з розділу 11. Механізму публікації немає.

*Готово, коли:* менеджер вимикає позицію з телефона, і гість бачить це без перезавантаження.

### Фаза 5 — замовлення без оплат

Токени столів, `/t/{token}`, кошик, машина станів із розділу 7, ідемпотентність, розділення на `kitchen` і `bar`.

*Готово, коли:* подвійний тап не створює два замовлення, а обрив мережі не втрачає жодного.

### Фаза 6 — Stripe Connect

Усе з розділу 8. Повернення з лімітом для `manager`.

*Готово, коли:* `paid` виставляється виключно вебхуком — тест із закритим браузером гостя це підтверджує.

### Фаза 7 — екран кухні

Усе з розділу 12.

*Готово, коли:* вимкнення wifi на планшеті дає гучну помилку, а не тихий застарілий список.

### Фаза 8 — фейковий сервіс

Розділ 15.

---

## 14. Демонстраційні дані

Заклад і всі позиції вигадані. Зберегти як `seed_menu.json` у корені, завантажувати сідером у Фазі 1.

Дані підібрані так, щоб зачепити кожен стан моделі: овес як джерело глютену, сире яйце в коктейлі, зерновий дистилят як «може містити», позиція у стані «скоро» з датою відкриття, позиція у 86, одна реконструйована позиція серед офіційних, і чотири коктейлі з `orderable: false` — межа v1 зашита в дані, а не в код, і в v2 знімається одним прапорцем.

```json
{
  "_note": "Демонстраційні дані для нового проєкту. Заклад і всі страви вигадані. Жодного зв'язку з реальним меню чи чужими листами алергенів. Ключі складу посилаються на lexicon, а не містять текст.",

  "venue": {
    "key": "the-copper-fig",
    "name": "The Copper Fig",
    "timezone": "Europe/London",
    "currency": "GBP"
  },

  "sources": {
    "official-2026-07": {
      "type": "official",
      "label": { "uk": "Офіційний лист закладу", "en": "Venue allergen sheet", "es": "Ficha oficial del local", "it": "Scheda ufficiale del locale", "de": "Offizielles Allergenblatt", "ru": "Официальный лист заведения" },
      "checked": "2026-07-14"
    },
    "reconstructed": {
      "type": "reconstructed",
      "label": { "uk": "Реконструкція з опису", "en": "Reconstructed from description", "es": "Reconstruido de la descripción", "it": "Ricostruito dalla descrizione", "de": "Aus der Beschreibung rekonstruiert", "ru": "Реконструкция из описания" }
    }
  },

  "sections": {
    "starters":    { "uk": "Закуски", "en": "Starters", "es": "Entrantes", "it": "Antipasti", "de": "Vorspeisen", "ru": "Закуски" },
    "mains":       { "uk": "Основні страви", "en": "Mains", "es": "Principales", "it": "Secondi", "de": "Hauptgerichte", "ru": "Основные блюда" },
    "desserts":    { "uk": "Десерти", "en": "Desserts", "es": "Postres", "it": "Dolci", "de": "Desserts", "ru": "Десерты" },
    "cocktails":   { "uk": "Коктейлі", "en": "Cocktails", "es": "Cócteles", "it": "Cocktail", "de": "Cocktails", "ru": "Коктейли" },
    "soft-drinks": { "uk": "Безалкогольні", "en": "Soft drinks", "es": "Sin alcohol", "it": "Analcolici", "de": "Alkoholfrei", "ru": "Безалкогольные" }
  },

  "warnings": {
    "shared-fryer": { "uk": "Спільний фритюр з позиціями, що містять глютен", "en": "Shared fryer with gluten-containing items", "es": "Freidora compartida con productos con gluten", "it": "Friggitrice condivisa con prodotti con glutine", "de": "Gemeinsame Fritteuse mit glutenhaltigen Produkten", "ru": "Общий фритюр с позициями, содержащими глютен" },
    "shared-grill": { "uk": "Спільний гриль з рибою та м'ясом", "en": "Shared grill with fish and meat", "es": "Parrilla compartida con pescado y carne", "it": "Griglia condivisa con pesce e carne", "de": "Gemeinsamer Grill mit Fisch und Fleisch", "ru": "Общий гриль с рыбой и мясом" },
    "raw-egg":      { "uk": "Містить сире яйце", "en": "Contains raw egg", "es": "Contiene huevo crudo", "it": "Contiene uovo crudo", "de": "Enthält rohes Ei", "ru": "Содержит сырое яйцо" }
  },

  "lexicon": {
    "beetroot":            { "uk": "буряк", "en": "beetroot", "es": "remolacha", "it": "barbabietola", "de": "Rote Bete", "ru": "свёкла" },
    "capers":              { "uk": "каперси", "en": "capers", "es": "alcaparras", "it": "capperi", "de": "Kapern", "ru": "каперсы" },
    "shallot":             { "uk": "шалот", "en": "shallot", "es": "chalota", "it": "scalogno", "de": "Schalotte", "ru": "шалот" },
    "dijon-mustard":       { "uk": "діжонська гірчиця", "en": "Dijon mustard", "es": "mostaza de Dijon", "it": "senape di Digione", "de": "Dijon-Senf", "ru": "дижонская горчица" },
    "olive-oil":           { "uk": "оливкова олія", "en": "olive oil", "es": "aceite de oliva", "it": "olio d'oliva", "de": "Olivenöl", "ru": "оливковое масло" },
    "lemon-juice":         { "uk": "лимонний сік", "en": "lemon juice", "es": "zumo de limón", "it": "succo di limone", "de": "Zitronensaft", "ru": "лимонный сок" },
    "sourdough-bread":     { "uk": "хліб на заквасці", "en": "sourdough bread", "es": "pan de masa madre", "it": "pane a lievitazione naturale", "de": "Sauerteigbrot", "ru": "хлеб на закваске" },
    "wheat-flour":         { "uk": "пшеничне борошно", "en": "wheat flour", "es": "harina de trigo", "it": "farina di frumento", "de": "Weizenmehl", "ru": "пшеничная мука" },
    "plain-flour":         { "uk": "борошно вищого ґатунку", "en": "plain flour", "es": "harina común", "it": "farina 00", "de": "Weizenmehl Type 405", "ru": "мука высшего сорта" },
    "breadcrumbs":         { "uk": "панірувальні сухарі", "en": "breadcrumbs", "es": "pan rallado", "it": "pangrattato", "de": "Semmelbrösel", "ru": "панировочные сухари" },
    "water":               { "uk": "вода", "en": "water", "es": "agua", "it": "acqua", "de": "Wasser", "ru": "вода" },
    "yeast":               { "uk": "дріжджі", "en": "yeast", "es": "levadura", "it": "lievito", "de": "Hefe", "ru": "дрожжи" },
    "salt":                { "uk": "сіль", "en": "salt", "es": "sal", "it": "sale", "de": "Salz", "ru": "соль" },
    "sugar":               { "uk": "цукор", "en": "sugar", "es": "azúcar", "it": "zucchero", "de": "Zucker", "ru": "сахар" },
    "black-pepper":        { "uk": "чорний перець", "en": "black pepper", "es": "pimienta negra", "it": "pepe nero", "de": "schwarzer Pfeffer", "ru": "чёрный перец" },
    "octopus":             { "uk": "восьминіг", "en": "octopus", "es": "pulpo", "it": "polpo", "de": "Oktopus", "ru": "осьминог" },
    "parsley":             { "uk": "петрушка", "en": "parsley", "es": "perejil", "it": "prezzemolo", "de": "Petersilie", "ru": "петрушка" },
    "anchovy":             { "uk": "анчоус", "en": "anchovy", "es": "anchoa", "it": "acciuga", "de": "Sardelle", "ru": "анчоус" },
    "garlic":              { "uk": "часник", "en": "garlic", "es": "ajo", "it": "aglio", "de": "Knoblauch", "ru": "чеснок" },
    "potato":              { "uk": "картопля", "en": "potato", "es": "patata", "it": "patata", "de": "Kartoffel", "ru": "картофель" },
    "arborio-rice":        { "uk": "рис арборіо", "en": "arborio rice", "es": "arroz arborio", "it": "riso arborio", "de": "Arborio-Reis", "ru": "рис арборио" },
    "wild-mushroom":       { "uk": "лісові гриби", "en": "wild mushrooms", "es": "setas silvestres", "it": "funghi di bosco", "de": "Waldpilze", "ru": "лесные грибы" },
    "vegetable-stock":     { "uk": "овочевий бульйон", "en": "vegetable stock", "es": "caldo de verduras", "it": "brodo vegetale", "de": "Gemüsebrühe", "ru": "овощной бульон" },
    "beef-stock":          { "uk": "яловичий бульйон", "en": "beef stock", "es": "caldo de ternera", "it": "brodo di manzo", "de": "Rinderbrühe", "ru": "говяжий бульон" },
    "celery":              { "uk": "селера", "en": "celery", "es": "apio", "it": "sedano", "de": "Sellerie", "ru": "сельдерей" },
    "carrot":              { "uk": "морква", "en": "carrot", "es": "zanahoria", "it": "carota", "de": "Karotte", "ru": "морковь" },
    "onion":               { "uk": "цибуля", "en": "onion", "es": "cebolla", "it": "cipolla", "de": "Zwiebel", "ru": "лук" },
    "fennel":              { "uk": "фенхель", "en": "fennel", "es": "hinojo", "it": "finocchio", "de": "Fenchel", "ru": "фенхель" },
    "rocket":              { "uk": "рукола", "en": "rocket", "es": "rúcula", "it": "rucola", "de": "Rucola", "ru": "руккола" },
    "parmesan":            { "uk": "пармезан", "en": "parmesan", "es": "parmesano", "it": "parmigiano", "de": "Parmesan", "ru": "пармезан" },
    "goat-cheese":         { "uk": "козячий сир", "en": "goat cheese", "es": "queso de cabra", "it": "formaggio di capra", "de": "Ziegenkäse", "ru": "козий сыр" },
    "butter":              { "uk": "вершкове масло", "en": "butter", "es": "mantequilla", "it": "burro", "de": "Butter", "ru": "сливочное масло" },
    "double-cream":        { "uk": "жирні вершки", "en": "double cream", "es": "nata espesa", "it": "panna densa", "de": "Schlagsahne", "ru": "жирные сливки" },
    "whole-egg":           { "uk": "куряче яйце", "en": "egg", "es": "huevo", "it": "uovo", "de": "Ei", "ru": "куриное яйцо" },
    "egg-white":           { "uk": "яєчний білок", "en": "egg white", "es": "clara de huevo", "it": "albume", "de": "Eiweiß", "ru": "яичный белок" },
    "sea-bream":           { "uk": "дорада", "en": "sea bream", "es": "dorada", "it": "orata", "de": "Dorade", "ru": "дорада" },
    "beef-short-rib":      { "uk": "яловичі реберця", "en": "beef short rib", "es": "costilla de ternera", "it": "costine di manzo", "de": "Rinderrippe", "ru": "говяжьи рёбра" },
    "red-wine":            { "uk": "червоне вино", "en": "red wine", "es": "vino tinto", "it": "vino rosso", "de": "Rotwein", "ru": "красное вино" },
    "white-wine":          { "uk": "біле вино", "en": "white wine", "es": "vino blanco", "it": "vino bianco", "de": "Weißwein", "ru": "белое вино" },
    "red-wine-vinegar":    { "uk": "винний оцет", "en": "red wine vinegar", "es": "vinagre de vino", "it": "aceto di vino", "de": "Rotweinessig", "ru": "винный уксус" },
    "honey":               { "uk": "мед", "en": "honey", "es": "miel", "it": "miele", "de": "Honig", "ru": "мёд" },
    "fig":                 { "uk": "інжир", "en": "fig", "es": "higo", "it": "fico", "de": "Feige", "ru": "инжир" },
    "fig-syrup":           { "uk": "інжирний сироп", "en": "fig syrup", "es": "sirope de higo", "it": "sciroppo di fico", "de": "Feigensirup", "ru": "инжирный сироп" },
    "walnut":              { "uk": "волоський горіх", "en": "walnut", "es": "nuez", "it": "noce", "de": "Walnuss", "ru": "грецкий орех" },
    "dark-chocolate":      { "uk": "чорний шоколад", "en": "dark chocolate", "es": "chocolate negro", "it": "cioccolato fondente", "de": "Zartbitterschokolade", "ru": "тёмный шоколад" },
    "cocoa":               { "uk": "какао", "en": "cocoa", "es": "cacao", "it": "cacao", "de": "Kakao", "ru": "какао" },
    "soya-lecithin":       { "uk": "соєвий лецитин", "en": "soya lecithin", "es": "lecitina de soja", "it": "lecitina di soia", "de": "Sojalecithin", "ru": "соевый лецитин" },
    "bourbon":             { "uk": "бурбон", "en": "bourbon", "es": "bourbon", "it": "bourbon", "de": "Bourbon", "ru": "бурбон" },
    "whisky":              { "uk": "віскі", "en": "whisky", "es": "whisky", "it": "whisky", "de": "Whisky", "ru": "виски" },
    "gin":                 { "uk": "джин", "en": "gin", "es": "ginebra", "it": "gin", "de": "Gin", "ru": "джин" },
    "prosecco":            { "uk": "просекко", "en": "prosecco", "es": "prosecco", "it": "prosecco", "de": "Prosecco", "ru": "просекко" },
    "angostura-bitters":   { "uk": "біттер ангостура", "en": "Angostura bitters", "es": "bíter Angostura", "it": "bitter Angostura", "de": "Angostura-Bitter", "ru": "биттер ангостура" },
    "elderflower-cordial": { "uk": "сироп бузини", "en": "elderflower cordial", "es": "sirope de saúco", "it": "sciroppo di sambuco", "de": "Holunderblütensirup", "ru": "сироп бузины" },
    "orange-zest":         { "uk": "цедра апельсина", "en": "orange zest", "es": "ralladura de naranja", "it": "scorza d'arancia", "de": "Orangenschale", "ru": "цедра апельсина" },
    "lime-juice":          { "uk": "сік лайма", "en": "lime juice", "es": "zumo de lima", "it": "succo di lime", "de": "Limettensaft", "ru": "сок лайма" },
    "basil":               { "uk": "базилік", "en": "basil", "es": "albahaca", "it": "basilico", "de": "Basilikum", "ru": "базилик" },
    "rosemary":            { "uk": "розмарин", "en": "rosemary", "es": "romero", "it": "rosmarino", "de": "Rosmarin", "ru": "розмарин" },
    "mint":                { "uk": "м'ята", "en": "mint", "es": "menta", "it": "menta", "de": "Minze", "ru": "мята" },
    "soda-water":          { "uk": "содова", "en": "soda water", "es": "agua con gas", "it": "acqua frizzante", "de": "Sodawasser", "ru": "содовая" },
    "apple-juice":         { "uk": "яблучний сік", "en": "apple juice", "es": "zumo de manzana", "it": "succo di mela", "de": "Apfelsaft", "ru": "яблочный сок" },
    "cinnamon":            { "uk": "кориця", "en": "cinnamon", "es": "canela", "it": "cannella", "de": "Zimt", "ru": "корица" },
    "ginger":              { "uk": "імбир", "en": "ginger", "es": "jengibre", "it": "zenzero", "de": "Ingwer", "ru": "имбирь" },
    "coffee":              { "uk": "кава", "en": "coffee", "es": "café", "it": "caffè", "de": "Kaffee", "ru": "кофе" },
    "oat-milk":            { "uk": "вівсяне молоко", "en": "oat milk", "es": "bebida de avena", "it": "bevanda d'avena", "de": "Hafermilch", "ru": "овсяное молоко" },
    "salsa-verde":         { "uk": "зелений соус", "en": "salsa verde", "es": "salsa verde", "it": "salsa verde", "de": "Salsa verde", "ru": "зелёный соус" },
    "dressing":            { "uk": "заправка", "en": "dressing", "es": "aliño", "it": "condimento", "de": "Dressing", "ru": "заправка" },
    "oats":                { "uk": "овес", "en": "oats", "es": "avena", "it": "avena", "de": "Hafer", "ru": "овёс" }
  },

  "items": [
    {
      "key": "smoked-beetroot-tartare",
      "name": "Smoked Beetroot Tartare",
      "section": "starters",
      "station": "kitchen",
      "price_pence": 1150,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Копчений буряк із каперсами та хлібом на заквасці", "en": "Smoked beetroot with capers and sourdough", "es": "Remolacha ahumada con alcaparras y pan de masa madre", "it": "Barbabietola affumicata con capperi e pane a lievitazione naturale", "de": "Geräucherte Rote Bete mit Kapern und Sauerteigbrot", "ru": "Копчёная свёкла с каперсами и хлебом на закваске" },
      "ing": ["beetroot", "capers", "shallot", "dijon-mustard", "olive-oil", "lemon-juice", ["sourdough-bread", ["wheat-flour", "water", "yeast", "salt"]]],
      "a": ["mustard", "cereals-gluten", "sulphites"],
      "m": ["celery"],
      "r": ["mustard"],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "charred-octopus",
      "name": "Charred Octopus",
      "section": "starters",
      "station": "kitchen",
      "price_pence": 1300,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Восьминіг на грилі з зеленим соусом і картоплею", "en": "Grilled octopus with salsa verde and potato", "es": "Pulpo a la parrilla con salsa verde y patata", "it": "Polpo alla griglia con salsa verde e patate", "de": "Gegrillter Oktopus mit Salsa verde und Kartoffeln", "ru": "Осьминог на гриле с зелёным соусом и картофелем" },
      "ing": ["octopus", ["salsa-verde", ["parsley", "capers", "anchovy", "olive-oil", "garlic"]], "potato", "lemon-juice"],
      "a": ["molluscs", "fish"],
      "m": ["celery", "sulphites"],
      "r": [],
      "src": "official-2026-07",
      "w": ["shared-grill"]
    },
    {
      "key": "wild-mushroom-arancini",
      "name": "Wild Mushroom Arancini",
      "section": "starters",
      "station": "kitchen",
      "price_pence": 950,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Смажені рисові кульки з лісовими грибами", "en": "Fried rice balls with wild mushrooms", "es": "Bolas de arroz fritas con setas silvestres", "it": "Arancini fritti ai funghi di bosco", "de": "Frittierte Reisbällchen mit Waldpilzen", "ru": "Жареные рисовые шарики с лесными грибами" },
      "ing": ["arborio-rice", "wild-mushroom", ["vegetable-stock", ["celery", "carrot", "onion"]], "parmesan", "butter", "whole-egg", ["breadcrumbs", ["wheat-flour", "salt"]]],
      "a": ["cereals-gluten", "milk", "eggs", "celery"],
      "m": ["tree-nuts"],
      "r": ["milk"],
      "src": "official-2026-07",
      "w": ["shared-fryer"]
    },
    {
      "key": "pan-seared-sea-bream",
      "name": "Pan-Seared Sea Bream",
      "section": "mains",
      "station": "kitchen",
      "price_pence": 2100,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Дорада на сковороді з фенхелем і білим вином", "en": "Sea bream with fennel and white wine", "es": "Dorada con hinojo y vino blanco", "it": "Orata con finocchio e vino bianco", "de": "Dorade mit Fenchel und Weißwein", "ru": "Дорада с фенхелем и белым вином" },
      "ing": ["sea-bream", "fennel", "white-wine", "butter", "lemon-juice", "olive-oil"],
      "a": ["fish", "milk", "sulphites"],
      "m": [],
      "r": ["milk"],
      "src": "official-2026-07",
      "w": ["shared-grill"]
    },
    {
      "key": "braised-short-rib",
      "name": "Braised Short Rib",
      "section": "mains",
      "station": "kitchen",
      "price_pence": 2450,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Яловичі реберця, тушковані в червоному вині", "en": "Beef short rib braised in red wine", "es": "Costilla de ternera estofada en vino tinto", "it": "Costine di manzo brasate al vino rosso", "de": "In Rotwein geschmorte Rinderrippe", "ru": "Говяжьи рёбра, тушённые в красном вине" },
      "ing": ["beef-short-rib", "red-wine", ["beef-stock", ["celery", "carrot", "onion"]], "plain-flour", "double-cream", "potato"],
      "a": ["celery", "sulphites", "cereals-gluten", "milk"],
      "m": ["mustard"],
      "r": ["milk"],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "fig-walnut-salad",
      "name": "Fig & Walnut Salad",
      "section": "mains",
      "station": "kitchen",
      "price_pence": 1050,
      "orderable": true,
      "state": "soon",
      "opens_at": "2026-09-01T12:00:00",
      "desc": { "uk": "Інжир, волоські горіхи, козячий сир і рукола", "en": "Fig, walnut, goat cheese and rocket", "es": "Higo, nuez, queso de cabra y rúcula", "it": "Fico, noci, formaggio di capra e rucola", "de": "Feige, Walnuss, Ziegenkäse und Rucola", "ru": "Инжир, грецкий орех, козий сыр и руккола" },
      "ing": ["fig", "walnut", "goat-cheese", "rocket", ["dressing", ["dijon-mustard", "olive-oil", "red-wine-vinegar", "honey"]]],
      "a": ["tree-nuts", "milk", "mustard", "sulphites"],
      "m": [],
      "r": ["milk", "tree-nuts"],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "dark-chocolate-tart",
      "name": "Dark Chocolate Tart",
      "section": "desserts",
      "station": "kitchen",
      "price_pence": 850,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Тарт із чорного шоколаду з вершками", "en": "Dark chocolate tart with cream", "es": "Tarta de chocolate negro con nata", "it": "Crostata al cioccolato fondente con panna", "de": "Zartbitterschokoladentarte mit Sahne", "ru": "Тарт из тёмного шоколада со сливками" },
      "ing": [["dark-chocolate", ["cocoa", "sugar", "soya-lecithin"]], "butter", "whole-egg", "plain-flour", "double-cream"],
      "a": ["milk", "eggs", "cereals-gluten", "soya"],
      "m": ["tree-nuts", "peanuts"],
      "r": [],
      "src": "reconstructed",
      "w": []
    },
    {
      "key": "copper-fig-old-fashioned",
      "name": "Copper Fig Old Fashioned",
      "section": "cocktails",
      "station": "bar",
      "price_pence": 1300,
      "orderable": false,
      "orderable_reason": "alcohol-age-check",
      "state": "available",
      "desc": { "uk": "Бурбон, інжирний сироп, біттер, цедра апельсина", "en": "Bourbon, fig syrup, bitters, orange zest", "es": "Bourbon, sirope de higo, bíter, ralladura de naranja", "it": "Bourbon, sciroppo di fico, bitter, scorza d'arancia", "de": "Bourbon, Feigensirup, Bitter, Orangenschale", "ru": "Бурбон, инжирный сироп, биттер, цедра апельсина" },
      "ing": ["bourbon", "fig-syrup", "angostura-bitters", "orange-zest"],
      "a": [],
      "m": ["cereals-gluten"],
      "r": [],
      "src": "reconstructed",
      "w": []
    },
    {
      "key": "smoked-rosemary-sour",
      "name": "Smoked Rosemary Sour",
      "section": "cocktails",
      "station": "bar",
      "price_pence": 1250,
      "orderable": false,
      "orderable_reason": "alcohol-age-check",
      "state": "available",
      "desc": { "uk": "Віскі, лимон, яєчний білок, розмарин", "en": "Whisky, lemon, egg white, rosemary", "es": "Whisky, limón, clara de huevo, romero", "it": "Whisky, limone, albume, rosmarino", "de": "Whisky, Zitrone, Eiweiß, Rosmarin", "ru": "Виски, лимон, яичный белок, розмарин" },
      "ing": ["whisky", "lemon-juice", "egg-white", "rosemary", "sugar"],
      "a": ["eggs"],
      "m": ["cereals-gluten"],
      "r": [],
      "src": "official-2026-07",
      "w": ["raw-egg"]
    },
    {
      "key": "elderflower-spritz",
      "name": "Elderflower Spritz",
      "section": "cocktails",
      "station": "bar",
      "price_pence": 1100,
      "orderable": false,
      "orderable_reason": "alcohol-age-check",
      "state": "available",
      "desc": { "uk": "Просекко, сироп бузини, содова, м'ята", "en": "Prosecco, elderflower, soda, mint", "es": "Prosecco, saúco, soda, menta", "it": "Prosecco, sambuco, soda, menta", "de": "Prosecco, Holunderblüte, Soda, Minze", "ru": "Просекко, бузина, содовая, мята" },
      "ing": ["prosecco", "elderflower-cordial", "soda-water", "mint"],
      "a": ["sulphites"],
      "m": [],
      "r": [],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "basil-garden-gimlet",
      "name": "Basil Garden Gimlet",
      "section": "cocktails",
      "station": "bar",
      "price_pence": 1200,
      "orderable": false,
      "orderable_reason": "alcohol-age-check",
      "state": "86",
      "desc": { "uk": "Джин, базилік, лайм, цукровий сироп", "en": "Gin, basil, lime, sugar syrup", "es": "Ginebra, albahaca, lima, sirope", "it": "Gin, basilico, lime, sciroppo di zucchero", "de": "Gin, Basilikum, Limette, Zuckersirup", "ru": "Джин, базилик, лайм, сахарный сироп" },
      "ing": ["gin", "basil", "lime-juice", "sugar"],
      "a": [],
      "m": [],
      "r": [],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "house-lemonade",
      "name": "House Lemonade",
      "section": "soft-drinks",
      "station": "bar",
      "price_pence": 450,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Домашній лимонад із м'ятою", "en": "House lemonade with mint", "es": "Limonada de la casa con menta", "it": "Limonata della casa con menta", "de": "Hausgemachte Limonade mit Minze", "ru": "Домашний лимонад с мятой" },
      "ing": ["lemon-juice", "sugar", "water", "mint"],
      "a": [],
      "m": [],
      "r": [],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "spiced-apple-cooler",
      "name": "Spiced Apple Cooler",
      "section": "soft-drinks",
      "station": "bar",
      "price_pence": 500,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Яблучний сік, кориця, імбир, содова", "en": "Apple juice, cinnamon, ginger, soda", "es": "Zumo de manzana, canela, jengibre, soda", "it": "Succo di mela, cannella, zenzero, soda", "de": "Apfelsaft, Zimt, Ingwer, Soda", "ru": "Яблочный сок, корица, имбирь, содовая" },
      "ing": ["apple-juice", "cinnamon", "ginger", "soda-water"],
      "a": [],
      "m": ["sulphites"],
      "r": [],
      "src": "official-2026-07",
      "w": []
    },
    {
      "key": "oat-cold-brew",
      "name": "Oat Cold Brew",
      "section": "soft-drinks",
      "station": "bar",
      "price_pence": 475,
      "orderable": true,
      "state": "available",
      "desc": { "uk": "Холодна кава з вівсяним молоком", "en": "Cold brew coffee with oat milk", "es": "Café cold brew con bebida de avena", "it": "Caffè cold brew con bevanda d'avena", "de": "Cold Brew mit Hafermilch", "ru": "Холодный кофе с овсяным молоком" },
      "ing": ["coffee", ["oat-milk", ["oats", "water"]]],
      "a": ["cereals-gluten"],
      "m": [],
      "r": [],
      "src": "official-2026-07",
      "w": []
    }
  ]
}
```

---

## 15. Тестування без ресторану

Симуляція вдома чесно закриває: машину станів, ідемпотентність, вебхуки (Stripe CLI, тестовий режим), паралельні замовлення, обриви мережі.

Не закриває нічого з поведінки людей. Тому — **фейковий сервіс**: шість знайомих, по телефону кожному, планшет на кухні, 30 хвилин реальних замовлень на нуль фунтів у домашній мережі. Що дивитися:

- чи розуміє гість, як обрати позицію й оплатити, без пояснень;
- що станеться, коли чотири замовлення прийдуть в одну хвилину;
- чи помітить «кухня» нове замовлення, якщо в неї зайняті руки;
- що покаже екран, якщо вимкнути wifi на планшеті посеред сервісу.

Кожен збій — в issues.

---

## 16. Обмеження

- Алкоголь у потік замовлення не входить: потрібна перевірка віку при подачі. Це v2.
- Ні спільного рахунку на стіл, ні розділення рахунку, ні відкритих табів.
- Ні чайових, поки не розібрано Employment (Allocation of Tips) Act.
- Ні інтеграції з POS у v1.
- Дані карток не зберігаються в жодному вигляді.
- Відповідь браузера гостя ніколи не є підтвердженням оплати.
- Приховування кнопок в інтерфейсі не є перевіркою прав.
- Нових мов і нових залежностей без явної потреби не додавати.
- Доменну модель розкладів не міняти — вона перевірена.
- Гостьовий шар не переписувати з нуля. Копіювати з референсу й адаптувати.

---

## 17. Що вирішити далі

- Модель заробітку: підписка чи комісія з транзакції. Комісія поверх страйпівських робить дорожче за конкурентів, які беруть нуль за замовлення. Підписка позиціонується чистіше.
- Чи бачить гість статус свого замовлення після оплати — сторінка «готується».
- Скасування: хто ініціює, за яких умов, у якому вікні.
- Пілотна точка. Без неї проєкт не вийде за межі симуляції, а всі справжні проблеми живуть саме там.

---

## 18. Готово загалом

Гість сканує QR на своєму столі, обирає їжу з урахуванням своїх алергенів однією з шести мов, оплачує, і замовлення з'являється на потрібному екрані — кухні чи бару — протягом секунди після підтвердження від Stripe. Персонал вимикає позицію PIN-кодом за десять секунд. Менеджер бачить, хто й коли змінив ціну. Якщо щось із цього ламається, система кричить, а не мовчить.
