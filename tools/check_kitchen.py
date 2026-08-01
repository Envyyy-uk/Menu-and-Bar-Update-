"""Екран кухні в справжньому браузері.

Критерій спринту 7: вимкнення мережі на планшеті дає **гучну помилку**, а не
тихий застарілий список. Тут це і перевіряється — сторінці ріжуть мережу й
дивляться, чи вона закричала, а потім повертають і дивляться, чи вона
перезавантажила стан із сервера.

    python tools/check_kitchen.py

Змінні: BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, CHROMIUM_PATH, SCREENSHOT.
"""

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
EMAIL = os.environ.get("ADMIN_EMAIL", "owner@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me-please-12")

fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(name)


launch = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}

with sync_playwright() as p:
    browser = p.chromium.launch(**launch)

    # --- панель: токен столу, чиста черга --------------------------------
    admin = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    admin.goto(f"{BASE}/admin/?lang=uk", wait_until="networkidle")
    admin.fill('input[type="email"]', EMAIL)
    admin.fill('input[type="password"]', PASSWORD)
    admin.click("button.primary")
    admin.wait_for_selector(".tab", timeout=15000)
    admin.evaluate(
        """async base => {
             const rows = await (await fetch(base + '/api/orders')).json();
             for (const o of rows) {
               for (const s of ['accepted', 'ready', 'served']) {
                 await fetch(base + '/api/orders/' + o.id + '/status?target=' + s, {method: 'POST'});
               }
             }
           }""",
        BASE,
    )
    admin.locator(".tab", has_text="Столи").click()
    admin.wait_for_selector(".arow .url")
    token = admin.locator(".arow .url").first.inner_text().rsplit("/", 1)[1]

    # --- екран кухні: сесія планшета --------------------------------------
    tablet = browser.new_context(viewport={"width": 1024, "height": 768})
    kitchen = tablet.new_page()
    errors = []
    kitchen.on("pageerror", lambda e: errors.append(str(e)))
    kitchen.on(
        "console",
        lambda m: errors.append(m.text) if m.type == "error" and "401" not in m.text else None,
    )

    kitchen.goto(f"{BASE}/kitchen/?lang=uk", wait_until="networkidle")
    check("без сесії планшет просить PIN", kitchen.locator(".login input").count() == 1)

    # реєструємо цей планшет як пристрій і заходимо PIN-ом
    device = tablet.request.post(f"{BASE}/api/admin/devices", data={"label": "Kitchen check"})
    if device.status != 201:
        # cookie панелі живе в іншому контексті — реєструємо з панелі, а токен
        # переносимо в контекст планшета
        created = admin.evaluate(
            """async base => {
                 const r = await fetch(base + '/api/admin/devices', {
                   method: 'POST', headers: {'Content-Type': 'application/json'},
                   body: JSON.stringify({label: 'Kitchen check'})});
                 return await r.json();
               }""",
            BASE,
        )
        tablet.add_cookies([
            {"name": "device", "value": created["device_token"], "url": BASE}
        ])

    kitchen.reload(wait_until="networkidle")
    kitchen.fill(".login input", os.environ.get("STAFF_PIN", "246810"))
    kitchen.click(".login button")
    kitchen.wait_for_selector(".kbar", timeout=15000)
    kitchen.wait_for_timeout(1500)
    check("індикатор зв'язку зелений", "netdot ok" == kitchen.get_attribute("#link", "class"),
          kitchen.get_attribute("#link", "class"))
    check("порожня черга підписана", "Замовлень немає" in kitchen.inner_text("#board"),
          kitchen.inner_text("#board")[:60])

    # --- нове замовлення долітає саме ---------------------------------------
    guest = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    guest.goto(f"{BASE}/t/{token}?lang=uk", wait_until="networkidle")
    guest.wait_for_selector(".add-btn")
    guest.locator("#d-charred-octopus .add-btn").click()
    guest.wait_for_timeout(200)
    guest.locator("#cartbar button").click()
    guest.wait_for_selector(".sheet")
    guest.locator(".sheet .primary.wide").click()

    got = False
    for _ in range(15):
        kitchen.wait_for_timeout(500)
        if kitchen.locator(".kcard").count():
            got = True
            break
    check("замовлення з'явилося на кухні саме, без перезавантаження", got)
    card = kitchen.locator(".kcard").first
    check("нове замовлення виділено", "fresh" in (card.get_attribute("class") or ""),
          card.get_attribute("class"))
    check("на кухні видно позицію кухні", "Charred Octopus" in card.inner_text(),
          card.inner_text()[:80])

    # --- бар не бачить кухонного -------------------------------------------
    bar = tablet.new_page()
    bar.goto(f"{BASE}/kitchen/?station=bar&lang=uk", wait_until="networkidle")
    bar.wait_for_selector(".kbar")
    bar.wait_for_timeout(1500)
    check("бар не бачить кухонної позиції",
          "Charred Octopus" not in bar.inner_text("#board"), bar.inner_text("#board")[:60])
    bar.close()

    # --- КРИТЕРІЙ: вимикаємо мережу ----------------------------------------
    kitchen.context.set_offline(True)
    shouted = False
    for _ in range(20):
        kitchen.wait_for_timeout(1000)
        if not kitchen.locator("#offline").is_hidden():
            shouted = True
            break
    check("втрата зв'язку дає повноекранний банер", shouted)
    if shouted:
        check("банер кричить, а не шепоче",
              "ЗВ’ЯЗКУ НЕМАЄ" in kitchen.inner_text("#offline"),
              kitchen.inner_text("#offline")[:60])
        check("індикатор став червоним", "bad" in kitchen.get_attribute("#link", "class"))
        check("список при цьому не зник — але позначений застарілим",
              kitchen.locator(".kcard").count() > 0)
    if os.environ.get("SCREENSHOT"):
        kitchen.screenshot(path=os.environ["SCREENSHOT"], full_page=False)

    # --- і повертаємо ------------------------------------------------------
    kitchen.context.set_offline(False)
    recovered = False
    for _ in range(20):
        kitchen.wait_for_timeout(1000)
        if kitchen.locator("#offline").is_hidden():
            recovered = True
            break
    check("зв'язок відновився — банер зник сам", recovered)
    check("індикатор знову зелений", "ok" in kitchen.get_attribute("#link", "class"))

    # --- кнопки рухають статус ---------------------------------------------
    kitchen.locator(".kcard .kbtn").first.click()
    kitchen.wait_for_timeout(1500)
    check("«Прийнято» змінює кнопку на «Готово»",
          "Готово" in kitchen.locator(".kcard .kbtn").first.inner_text(),
          kitchen.locator(".kcard .kbtn").first.inner_text())

    check("без помилок у консолі", not errors, "; ".join(errors[:3]))
    browser.close()

print()
print("FAILED:", fails if fails else "нічого")
sys.exit(1 if fails else 0)
