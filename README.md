# Платформа замовлення за столом

Гість сідає за стіл, сканує QR, бачить меню з повним складом і алергенами
однією з шести мов, замовляє й оплачує з телефона. Замовлення потрапляє на
екран кухні або бару. Персонал вимикає позиції PIN-кодом. Менеджер бачить,
хто й коли змінив ціну.

Головна цінність — **структурована модель алергенів**: три рівні
(містить / може містити / можна прибрати), джерело даних із датою перевірки,
словник інгредієнтів із крос-мовним пошуком.

Повний план — `docs/PROJECT_PLAN.md`. Розбивка на спринти — `SPRINTS.md`.
Звіт після кожного спринту — `docs/FEEDBACK.md`.

## Швидкий старт

```bash
cp .env.example .env          # секрети за замовчуванням годяться для локалі
docker compose up --build     # http://localhost:8000
```

Піднімається Postgres, застосовуються міграції, сідер заливає
`seed_menu.json`, і на `http://localhost:8000` відкривається гостьове меню.

| Адреса | Що це |
|---|---|
| `/` | гостьове меню (демо-стіл) |
| `/t/{token}` | меню конкретного столу — те, куди веде QR |
| `/admin/` | адмін-панель |
| `/kitchen/` | екран кухні та бару |
| `/health` | health-check |
| `/api/docs` | OpenAPI |

Перший `owner` створюється сідером із `.env`
(`SEED_OWNER_EMAIL` / `SEED_OWNER_PASSWORD`).

### Без Docker

```bash
python -m venv .venv && . .venv/bin/activate
pip install -r backend/requirements.txt
export DATABASE_URL=postgresql+psycopg://menu:menu@localhost:5432/menu
alembic -c backend/alembic.ini upgrade head
python -m app.seed                     # з каталогу backend
uvicorn app.main:app --reload --app-dir backend
```

## Структура

```
backend/
  app/
    main.py           збірка застосунку, статика, health
    models/           SQLAlchemy: venues, tables, menu_items, orders, users …
    api/              роутери: menu, orders, admin, auth, webhooks, kitchen
    services/         stripe, schedule, availability, реалтайм
    core/             config, security, deps
  alembic/            міграції
  tests/
frontend/
  guest/              меню, кошик, оплата
  admin/              панель
  kitchen/            екран кухні
  assets/             i18n, lexicon, allergens, styles, pwa
docker-compose.yml
seed_menu.json        демонстраційні дані (заклад і страви вигадані)
```

## Правила, які не порушуються

1. Замовлення з'являється на кухні **тільки** після `paid`, і `paid`
   виставляється **тільки** з вебхука Stripe — ніколи з відповіді браузера.
2. Дані картки ніколи не торкаються нашого сервера (Stripe Checkout).
3. Перевірка прав — на сервері, на кожному ендпойнті. Приховані кнопки
   захистом не є.
4. Токен столу — непрозорий випадковий рядок, а не номер столу, і його можна
   ротувати.
5. Джерело правди — Postgres. Екран кухні лише відображає стан і кричить,
   коли зв'язок зник.

## Тести

```bash
docker compose run --rm api pytest        # або: pytest  з каталогу backend
```

Перевірка гостьового меню в справжньому браузері — окремо, бо потребує
Playwright і піднятого сервера:

```bash
pip install playwright && playwright install chromium
python tools/check_guest.py
```

## Ліцензія і дані

Заклад «The Copper Fig» і всі позиції в `seed_menu.json` вигадані. Жодного
зв'язку з реальним меню чи чужими листами алергенів.
