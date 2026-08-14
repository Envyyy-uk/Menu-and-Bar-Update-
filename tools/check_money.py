"""Вкладка «Замовлення» в панелі: черга, статуси, повернення, стан Stripe.

Мережевих викликів до Stripe тут немає — і не має бути. Перевіряємо те, що
бачить менеджер: чи видно замовлення, чи рухаються статуси, чи працює
повернення й чи панель чесно каже, що ключів Stripe немає.

    python tools/check_money.py

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
    admin = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    errors = []
    admin.on("pageerror", lambda e: errors.append(str(e)))
    admin.on(
        "console",
        lambda m: errors.append(m.text) if m.type == "error" and "401" not in m.text else None,
    )

    admin.goto(f"{BASE}/admin/?lang=uk", wait_until="networkidle")
    admin.fill('input[type="email"]', EMAIL)
    admin.fill('input[type="password"]', PASSWORD)
    admin.click("button.primary")
    admin.wait_for_selector(".tab", timeout=15000)

    check("панель відкривається на «Замовлення»",
          admin.locator(".tab.on").inner_text() == "Замовлення",
          admin.locator(".tab.on").inner_text())
    check("панель чесно каже, що Stripe не налаштований",
          "режим прогону" in admin.inner_text("#body"), admin.inner_text("#body")[:120])

    # Гаманці мовчать, коли не працюють: кнопки Apple Pay просто немає, без
    # помилки. Панель мусить називати причину, а не лишати зал гадати.
    body = admin.inner_text("#body")
    check("панель показує стан Apple Pay і Google Pay",
          "Apple Pay" in body and "Google Pay" in body, body[:160])
    check("панель називає причину: тут немає HTTPS",
          "✕ HTTPS" in body, body[:200])

    # --- створюємо замовлення очима гостя ---------------------------------
    admin.locator(".tab", has_text="Столи").click()
    admin.wait_for_selector(".arow .url")
    token = admin.locator(".arow .url").first.inner_text().rsplit("/", 1)[1]

    guest = browser.new_context(viewport={"width": 420, "height": 900}).new_page()
    guest.goto(f"{BASE}/t/{token}?lang=uk", wait_until="networkidle")
    guest.wait_for_selector(".add-btn")
    guest.locator("#d-espresso .add-btn").click()
    guest.wait_for_timeout(200)
    guest.locator("#cartbar button").click()
    guest.wait_for_selector(".sheet")
    guest.locator(".sheet .primary.wide").click()
    guest.wait_for_timeout(2500)
    number = guest.inner_text("#cartbar").split("№")[1].split(" ")[0].strip()

    admin.locator(".tab", has_text="Замовлення").click()
    admin.wait_for_selector(f".arow:has-text('№{number}')", timeout=15000)
    row = admin.locator(".arow", has_text=f"№{number}").first
    check("замовлення видно в панелі", row.count() > 0, f"№{number}")
    # Станція з рядка зникла: у меню поки одна станція, і «Бар» біля кожної
    # позиції — це шум, а не інформація. Назва позиції лишається.
    check("видно назву позиції", "Black Coffee" in row.inner_text(), row.inner_text()[:80])
    check("станцію не пишемо, поки вона одна", "Бар" not in row.inner_text(),
          row.inner_text()[:80])
    check("видно стелю повернення", "Ваша стеля" in row.inner_text())

    # --- статуси -----------------------------------------------------------
    row.locator("button", has_text="Прийнято").click()
    admin.wait_for_timeout(1500)
    row = admin.locator(".arow", has_text=f"№{number}").first
    check("статус рухається на «Готується»", "Готується" in row.inner_text(),
          row.inner_text()[:80])

    # --- повернення --------------------------------------------------------
    row.locator("button", has_text="Повернути").click()
    admin.wait_for_timeout(300)
    row.locator("button", has_text="Повернути").last.click()
    admin.wait_for_timeout(1800)

    refunded = admin.evaluate(
        """async ([base, n]) => {
             const rows = await (await fetch(base + '/api/admin/audit')).json();
             return rows.filter(r => r.action === 'order.refund' && r.entity === 'order:' + n);
           }""",
        [BASE, number],
    )
    check("повернення записано в аудит", len(refunded) == 1, refunded[:1])
    check("повернення підписане іменем", refunded and refunded[0]["who"] == "Owner")

    gone = admin.locator(".arow", has_text=f"№{number}").count() == 0
    check("повернуте замовлення пішло з живої черги", gone)

    if os.environ.get("SCREENSHOT"):
        admin.screenshot(path=os.environ["SCREENSHOT"], full_page=False)

    check("без помилок у консолі", not errors, "; ".join(errors[:3]))
    browser.close()

print()
print("FAILED:", fails if fails else "нічого")
sys.exit(1 if fails else 0)
