"""Замовлення в справжньому браузері.

Доводить критерій спринту 5 очима гостя: подвійний тап по «Замовити» не
створює двох замовлень, а позиція, яку вимкнули, поки кошик був відкритий,
не потрапляє в оплату.

    python tools/check_order.py

Змінні: BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD, CHROMIUM_PATH, SCREENSHOT.
"""

import json
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


def api_orders_count(page, token):
    """Скільки замовлень пішло з цього столу — рахуємо на боці сервера."""
    return page.evaluate(
        """async ([base, tok]) => {
             const r = await fetch(base + '/api/table/' + tok);
             return r.ok;
           }""",
        [BASE, token],
    )


launch = {"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}

with sync_playwright() as p:
    browser = p.chromium.launch(**launch)

    # --- панель: дізнатися токен столу й тримати сесію для 86 --------------
    admin = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    admin.goto(f"{BASE}/admin/?lang=uk", wait_until="networkidle")
    admin.fill('input[type="email"]', EMAIL)
    admin.fill('input[type="password"]', PASSWORD)
    admin.click("button.primary")
    admin.wait_for_selector(".arow", timeout=15000)
    admin.locator(".tab", has_text="Столи").click()
    admin.wait_for_selector(".arow .url")
    table_url = admin.locator(".arow .url").first.inner_text()
    token = table_url.rsplit("/", 1)[1]

    # Черга від попередніх прогонів — не наша справа: доводимо її до кінця,
    # щоб рахувати тільки те, що створить цей тест.
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

    # усе меню в робочий стан
    admin.locator(".tab", has_text="Позиції").click()
    admin.wait_for_selector(".arow")
    for name in ("Black Coffee. Espresso", "Tea Pot Special"):
        admin.locator(".arow", has_text=name).first.locator("button", has_text="За розкладом").click()
        admin.wait_for_timeout(500)

    guest = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    errors = []
    guest.on("pageerror", lambda e: errors.append(str(e)))
    # 409 тут очікуваний: тест навмисно вимикає позицію, поки кошик відкритий,
    # і саме цією відповіддю сервер каже, що оплата не пройшла.
    guest.on(
        "console",
        lambda m: errors.append(m.text)
        if m.type == "error" and "409" not in m.text
        else None,
    )

    # --- без столу замовити не можна ---------------------------------------
    guest.goto(f"{BASE}/?lang=uk", wait_until="networkidle")
    guest.wait_for_selector(".dish")
    check("без QR столу кнопок замовлення немає", guest.locator(".add-btn").count() == 0)

    # --- зі столом ---------------------------------------------------------
    guest.goto(f"{BASE}/t/{token}?lang=uk", wait_until="networkidle")
    guest.wait_for_selector(".dish")
    guest.wait_for_selector(".add-btn")
    # У PODVAL алкоголь замовляється — контроль лишається бармену при подачі
    check("алкоголь замовляється, але попереджає про вік",
          guest.locator("#d-mojito .add-btn").count() == 1
          and "Алкоголь" in guest.locator("#d-mojito").inner_text(),
          guest.locator("#d-mojito").inner_text()[:70])
    check("позиція з варіантами веде через вибір, а не одразу в кошик",
          guest.locator("#d-mojito .add-btn").inner_text() == "Обрати",
          guest.locator("#d-mojito .add-btn").inner_text())

    guest.locator("#d-espresso .add-btn").click()
    guest.locator("#d-espresso .qty-btn").nth(1).click()
    guest.wait_for_timeout(200)
    check("кількість рахується", guest.locator("#d-espresso .qty").inner_text() == "2")
    check("панель кошика показує суму", "£8.00" in guest.inner_text("#cartbar"),
          guest.inner_text("#cartbar"))

    # --- кошик редагується зсередини --------------------------------------
    guest.locator("#d-corona .add-btn").click()
    guest.wait_for_timeout(200)
    guest.locator("#cartbar button").click()
    guest.wait_for_selector(".sheet")
    check("у кошику видно обидві позиції", guest.locator(".cart-list li").count() == 2,
          guest.locator(".cart-list li").count())

    coffee_line = guest.locator(".cart-list li", has_text="Black Coffee")
    coffee_line.locator(".qty-btn").first.click()   # −
    guest.wait_for_timeout(200)
    check("кількість зменшується прямо в кошику",
          guest.locator(".cart-list li", has_text="Black Coffee").locator(".qty").inner_text() == "1")
    check("сума перерахувалася", "£12.00" in guest.inner_text(".cart-total"),
          guest.inner_text(".cart-total"))

    guest.locator(".cart-list li", has_text="Corona").locator(".drop-btn").click()
    guest.wait_for_timeout(200)
    check("страву можна прибрати з кошика",
          guest.locator(".cart-list li").count() == 1, guest.locator(".cart-list li").count())
    check("картка в меню синхронізувалася",
          guest.locator("#d-corona .add-btn").count() == 1)

    guest.locator(".cart-list li", has_text="Black Coffee").locator(".qty-btn").nth(1).click()
    guest.wait_for_timeout(200)
    check("кількість повертається назад",
          guest.locator(".cart-list li", has_text="Black Coffee").locator(".qty").inner_text() == "2")

    guest.locator(".sheet button.wide:not(.primary)").click()
    guest.wait_for_timeout(200)

    # --- позиція випала, поки кошик відкритий ------------------------------
    guest.locator("#d-tea-pot-special .add-btn").click()
    guest.wait_for_timeout(200)
    admin.locator(".arow", has_text="Tea Pot Special").first.locator(
        "button", has_text="Немає").click()
    admin.wait_for_timeout(1000)

    guest.locator("#cartbar button").click()
    guest.wait_for_selector(".sheet")
    guest.locator(".sheet .primary.wide").click()
    guest.wait_for_selector(".dropped", timeout=15000)
    check("гість бачить, що саме випало",
          "Tea Pot Special" in guest.inner_text(".dropped"), guest.inner_text(".dropped")[:80])

    # --- замовляємо решту, двічі поспіль -----------------------------------
    guest.locator(".dropped button").click()
    guest.wait_for_selector(".sheet .primary.wide")
    send = guest.locator(".sheet .primary.wide")
    send.click()
    send.click(force=True)  # подвійний тап — саме те, від чого захищає client_token
    guest.wait_for_timeout(3000)

    bar = guest.inner_text("#cartbar")
    check("замовлення прийнято й показано гостю", "Замовлення №" in bar, bar)
    check("статус — оплачено або далі",
          any(word in bar for word in ("Оплачено", "Готується", "Готово")), bar)

    # --- скільки насправді створено ----------------------------------------
    admin.reload(wait_until="networkidle")
    count = admin.evaluate(
        """async base => {
             const r = await fetch(base + '/api/orders');
             const rows = await r.json();
             return rows.length;
           }""",
        BASE,
    )
    check("подвійний тап дав рівно одне замовлення в черзі", count == 1, f"у черзі: {count}")

    queue = admin.evaluate(
        """async base => {
             const k = await (await fetch(base + '/api/orders?station=kitchen')).json();
             const b = await (await fetch(base + '/api/orders?station=bar')).json();
             return {kitchen: k.length, bar: b.length,
                     barItems: b.length ? b[0].items.map(i => i.name) : []};
           }""",
        BASE,
    )
    check("напій пішов на бар, а не на кухню",
          queue["bar"] == 1 and queue["kitchen"] == 0 and queue["barItems"] == ["Black Coffee. Espresso"],
          json.dumps(queue, ensure_ascii=False))

    # --- варіант доїжджає до бару ------------------------------------------
    # Головне, заради чого варіанти й з'явились: бармен має бачити, яке саме
    # мохіто робити. «Mojito» без смаку — це загадка посеред зміни.
    guest.locator("#cartbar button", has_text="Нове замовлення").click()
    guest.wait_for_timeout(400)
    guest.locator("#d-mojito .add-btn").click()
    guest.wait_for_selector(".opt-box")
    check("аркуш вибору відкрився", guest.locator(".opt-box .opt-btn").count() == 5,
          guest.locator(".opt-box .opt-btn").count())
    check("поки не обрано — додати не можна",
          guest.locator(".opt-box .primary.wide").is_disabled())
    guest.locator(".opt-box .opt-btn", has_text="Mango").click()
    guest.wait_for_timeout(200)
    check("після вибору кнопка ожила",
          not guest.locator(".opt-box .primary.wide").is_disabled())
    guest.locator(".opt-box .primary.wide").click()
    guest.wait_for_timeout(300)

    guest.locator("#cartbar button").click()
    guest.wait_for_selector(".sheet .cart-list")
    check("варіант видно в кошику", "Mango" in guest.inner_text(".cart-list"),
          guest.inner_text(".cart-list")[:70])
    guest.locator(".sheet .primary.wide").click()
    guest.wait_for_timeout(3000)

    made = admin.evaluate(
        """async base => {
             const b = await (await fetch(base + '/api/orders?station=bar')).json();
             const last = b[b.length - 1];
             return last.items.map(i => i.name + ' / ' + (i.options || []).join(','));
           }""",
        BASE,
    )
    check("бар бачить, яке саме мохіто робити", "Mojito / Mango" in made,
          json.dumps(made, ensure_ascii=False))

    # --- перезавантаження сторінки не створює дубль ------------------------
    guest.reload(wait_until="networkidle")
    guest.wait_for_selector("#cartbar")
    guest.wait_for_timeout(1500)
    check("після перезавантаження гість бачить своє замовлення",
          "Замовлення №" in guest.inner_text("#cartbar"), guest.inner_text("#cartbar"))

    # --- зал рухає статуси --------------------------------------------------
    order_id = guest.evaluate("() => JSON.parse(sessionStorage.getItem('order')).id")
    moved = admin.evaluate(
        """async ([base, id]) => {
             const r1 = await fetch(base + '/api/orders/' + id + '/status?target=accepted', {method:'POST'});
             const r2 = await fetch(base + '/api/orders/' + id + '/status?target=served', {method:'POST'});
             return {accepted: r1.status, skipped: r2.status};
           }""",
        [BASE, order_id],
    )
    check("«Прийнято» проходить", moved["accepted"] == 200, moved)
    check("перескочити через «Готово» не можна", moved["skipped"] == 409, moved)

    got = False
    for _ in range(15):
        guest.wait_for_timeout(1000)
        if "Готується" in guest.inner_text("#cartbar"):
            got = True
            break
    check("гість бачить «Готується» без перезавантаження", got, guest.inner_text("#cartbar"))

    if os.environ.get("SCREENSHOT"):
        guest.screenshot(path=os.environ["SCREENSHOT"], full_page=False)

    # --- прибирання ---------------------------------------------------------
    admin.locator(".tab", has_text="Позиції").click()
    admin.wait_for_selector(".arow")
    admin.locator(".arow", has_text="Tea Pot Special").first.locator(
        "button", has_text="За розкладом").click()
    admin.wait_for_timeout(600)

    check("без помилок у консолі гостя", not errors, "; ".join(errors[:3]))
    browser.close()

print()
print("FAILED:", fails if fails else "нічого")
sys.exit(1 if fails else 0)
