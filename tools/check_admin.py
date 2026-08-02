"""Перевірка адмін-панелі в справжньому браузері.

Головне, що тут доводиться, — критерій спринту: менеджер вимикає позицію
з телефона, і гість бачить це **без перезавантаження сторінки**. Гостьова
вкладка відкривається першою й до кінця тесту не перезавантажується.

    pip install playwright && playwright install chromium
    python tools/check_admin.py

Змінні: BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, CHROMIUM_PATH, SCREENSHOT.
"""

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
EMAIL = os.environ.get("ADMIN_EMAIL", "owner@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me-please-12")
ITEM = "House Lemonade"

fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(name)


launch = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}

with sync_playwright() as p:
    browser = p.chromium.launch(**launch)

    admin = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    errors = []
    admin.on("pageerror", lambda e: errors.append(str(e)))
    # 401 на /api/auth/me — це не помилка, а звичайна перевірка сесії при
    # відкритті панелі: саме так вона й вирішує, показувати форму входу.
    admin.on(
        "console",
        lambda m: errors.append(m.text)
        if m.type == "error" and "401" not in m.text
        else None,
    )

    admin.goto(f"{BASE}/admin/?lang=uk", wait_until="networkidle")
    check("без сесії — форма входу", admin.locator(".login").count() == 1)

    admin.fill('input[type="email"]', EMAIL)
    admin.fill('input[type="password"]', PASSWORD)
    admin.click("button.primary")
    admin.wait_for_selector(".tab", timeout=15000)
    check("вхід поштою й паролем", "owner" in admin.inner_text("#who"))
    # клас `.link` кнопки «Вийти» колись перетинався з індикатором зв'язку
    # на кухні — 14×14 і текст поверх перемикача мов
    logout = admin.evaluate("""() => {
      const b = document.querySelector('#who button');
      const s = document.querySelector('.switches');
      const r = b.getBoundingClientRect(), q = s.getBoundingClientRect();
      return { w: r.width, h: r.height, overlap: r.bottom > q.top + 1 };
    }""")
    check("кнопка «Вийти» читабельна", logout["w"] > 40 and logout["h"] > 18, str(logout))
    check("шапка не накладається на перемикач мов", not logout["overlap"], str(logout))
    # Панель відкривається на черзі замовлень — позиції на сусідній вкладці
    admin.locator(".tab", has_text="Позиції").click()
    admin.wait_for_selector(".arow", timeout=15000)
    check("вкладки за правами owner",
          {"Позиції", "Розділи", "Розклади", "Столи", "Люди", "Аудит"} <=
          set(admin.locator(".tab").all_inner_texts()),
          admin.locator(".tab").all_inner_texts())

    # Тест міг обірватися раніше — приводимо позицію до відомого стану.
    row = admin.locator(".arow", has_text=ITEM).first
    row.locator("button", has_text="За розкладом").click()
    admin.wait_for_timeout(900)

    # Гість — окремий контекст: ні сесії панелі, ні її cookie. Відкривається
    # ДО зміни й до кінця тесту не перезавантажується.
    guest = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    guest.goto(f"{BASE}/?lang=uk", wait_until="networkidle")
    guest.wait_for_selector(".dish")
    check("до змін: позиція в меню доступна",
          "Наразі немає" not in guest.locator("#d-house-lemonade").inner_text())

    row = admin.locator(".arow", has_text=ITEM).first
    check("рядок позиції показує наявність зараз", "Доступно зараз" in row.inner_text(),
          row.inner_text()[:70])

    row.locator("button", has_text="Немає").click()
    admin.wait_for_timeout(1200)
    row = admin.locator(".arow", has_text=ITEM).first
    check("панель показує «Недоступно зараз»", "Недоступно зараз" in row.inner_text(),
          row.inner_text()[:70])

    # --- критерій спринту -------------------------------------------------
    got = False
    for _ in range(30):
        guest.wait_for_timeout(1000)
        if "Наразі немає" in guest.locator("#d-house-lemonade").inner_text():
            got = True
            break
    check("гість бачить 86 БЕЗ перезавантаження сторінки", got,
          guest.locator("#d-house-lemonade").inner_text()[:60])

    # --- ціна ------------------------------------------------------------
    price = row.locator('input[type="number"]')
    price.fill("5.25")
    price.dispatch_event("change")
    admin.wait_for_timeout(900)
    check("ціна збереглася", "Збережено" in row.inner_text(), row.inner_text()[:80])

    # --- столи й QR -------------------------------------------------------
    admin.locator(".tab", has_text="Столи").click()
    admin.wait_for_selector("img.qr")
    first_url = admin.locator(".arow .url").first.inner_text()
    admin.locator("img.qr").first.evaluate(
        "img => img.complete ? true : new Promise(r => img.addEventListener('load', r))")
    check("QR-картинка вантажиться",
          admin.locator("img.qr").first.evaluate("img => img.naturalWidth > 0"))
    check("посилання столу — токен, а не номер",
          "/t/" in first_url and first_url.rsplit("/", 1)[1] not in ("1", "2", "3"), first_url)

    # «Друк» друкує зі свого ж вікна: нове вікно блокує і Safari, і фрейм
    admin.evaluate("() => { window.__printed = 0; window.print = () => { window.__printed++; }; }")
    admin.locator(".arow", has_text="/t/").first.locator("button", has_text="Друк").click()
    admin.wait_for_timeout(1200)
    check("«Друк» викликає друк, а не мовчить", admin.evaluate("window.__printed") == 1,
          admin.evaluate("window.__printed"))
    check("на аркуш іде наліпка з QR і посиланням",
          admin.locator("#printarea img").count() == 1 and "/t/" in admin.inner_text("#printarea .url"),
          admin.inner_text("#printarea")[:60])

    admin.once("dialog", lambda d: d.accept())
    admin.locator(".arow", has_text=first_url.rsplit("/", 1)[1]).first.locator(
        "button", has_text="Змінити токен").click()
    admin.wait_for_timeout(1200)
    new_url = admin.locator(".arow .url").first.inner_text()
    check("ротація змінює токен", new_url != first_url, f"{first_url} → {new_url}")

    # --- аудит ------------------------------------------------------------
    admin.locator(".tab", has_text="Аудит").click()
    admin.wait_for_selector("table.audit")
    audit = admin.inner_text("table.audit")
    check("аудит показує зміну ціни", "item.update" in audit)
    check("аудит показує ротацію токена", "table.rotate_token" in audit)
    check("аудит називає, хто це зробив", "Owner" in audit)

    # --- повернення стану -------------------------------------------------
    admin.locator(".tab", has_text="Позиції").click()
    admin.wait_for_selector(".arow")
    row = admin.locator(".arow", has_text=ITEM).first
    row.locator("button", has_text="За розкладом").click()
    admin.wait_for_timeout(800)
    price = row.locator('input[type="number"]')
    price.fill("4.50")
    price.dispatch_event("change")
    admin.wait_for_timeout(800)

    check("без помилок у консолі", not errors, "; ".join(errors[:3]))
    if os.environ.get("SCREENSHOT"):
        admin.screenshot(path=os.environ["SCREENSHOT"], full_page=False)
    browser.close()

print()
print("FAILED:", fails if fails else "нічого")
sys.exit(1 if fails else 0)
