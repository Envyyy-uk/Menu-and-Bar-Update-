"""Перевірка гостьового меню в справжньому браузері.

Не входить у pytest: потребує Playwright і піднятого сервера. Запуск:

    pip install playwright && playwright install chromium
    python tools/check_guest.py            # сервер має бути на :8000

Перевіряє те, що не видно з юніт-тестів: крос-мовний пошук по складнику,
фільтр алергенів, тексти станів і те, що авто-оновлення не збиває фільтр.
"""

import os
import sys

from playwright.sync_api import sync_playwright

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000")
fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not cond:
        fails.append(name)


with sync_playwright() as p:
    b = p.chromium.launch(**({"executable_path": os.environ["CHROMIUM_PATH"]} if os.environ.get("CHROMIUM_PATH") else {}))
    page = b.new_page(viewport={"width": 420, "height": 900})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)

    page.goto(BASE + "/?lang=uk", wait_until="networkidle")
    page.wait_for_selector(".dish")

    check("венью в шапці", page.inner_text("#venue-name") == "PODVAL")
    check("37 позицій", page.locator(".dish").count() == 37, page.locator(".dish").count())
    # меню — один суцільний список: ні заголовків розділів, ні вкладок над ним
    check("вкладок-фільтрів над меню немає", page.locator("#toolbar .tabs").count() == 0)
    # Меню знову згруповане — але категорія це підпис, а не сутність зі станом
    cats = [page.locator("#menu > .cat").nth(i).get_attribute("id")
            for i in range(page.locator("#menu > .cat").count())]
    check("шість категорій у порядку меню",
          cats == ["c-spirits", "c-cocktails", "c-beer-soft", "c-wine", "c-hot", "c-hookah"],
          cats)
    check("кожна позиція під заголовком",
          page.locator("#menu > .cat > .grid > .dish").count() == 37,
          page.locator("#menu > .cat > .grid > .dish").count())
    check("кальяни окремою категорією",
          page.locator("#c-hookah h2").inner_text() == "Кальяни",
          page.locator("#c-hookah h2").inner_text())

    # --- крос-мовний пошук по складнику -----------------------------------
    def search(q):
        page.fill(".search", q)
        page.wait_for_timeout(120)
        return [
            page.locator(".dish").nth(i).get_attribute("id")
            for i in range(page.locator(".dish").count())
            if page.locator(".dish").nth(i).is_visible()
        ]

    for word, lang in [("хміль", "uk"), ("hops", "en"), ("хмель", "ru")]:
        found = search(word)
        check(f"пошук «{word}» ({lang}) → corona", found == ["d-corona"], found)

    found = search("ячмінний солод")
    check("пошук «ячмінний солод» → усе на ньому",
          set(found) == {"d-jack-daniels", "d-black-label", "d-jameson", "d-corona"}, found)

    search("")

    # --- алергенів у меню немає -------------------------------------------
    # Заклад їх не надавав, а виведені з назв продуктів гірші за жодних.
    check("панелі фільтра алергенів немає", page.locator(".filters").count() == 0)
    check("міток алергенів на картках немає", page.locator(".tag").count() == 0)
    check("значка джерела немає", page.locator(".srcbadge").count() == 0)
    check("склад лишився", page.locator("#d-mojito ul.ing li").count() == 4,
          page.locator("#d-mojito").inner_text()[:80])

    # --- алкоголь і ціна ---------------------------------------------------
    # У PODVAL алкоголь замовляється: якби ні, застосунок був би меню для
    # читання. Контроль лишається людині — і гість бачить це в меню.
    mojito = page.locator("#d-mojito")
    check("алкоголь попереджає про вік", "Алкоголь" in mojito.inner_text(),
          mojito.inner_text()[:80])
    # Кнопок замовлення тут немає взагалі: цю сторінку відкрито без QR столу.
    # Що алкоголь замовляється — перевіряє check_order.py, зі столом.
    check("без QR столу кнопок немає ні в кого", page.locator(".add-btn").count() == 0,
          page.locator(".add-btn").count())

    check("ціна у фунтах, а не «13 GBP»",
          "£13.00" in page.locator("#d-absolut").inner_text(),
          page.locator("#d-absolut .price").inner_text())
    # У позиції з варіантами ціна не одна: £13 келих, £80 пляшка
    check("вино показує «від», а не одну ціну",
          "від £13.00" in page.locator("#d-white-wine .price").inner_text(),
          page.locator("#d-white-wine .price").inner_text())
    check("позиція без варіантів — проста ціна",
          page.locator("#d-espresso .price").inner_text() == "£4.00",
          page.locator("#d-espresso .price").inner_text())

    # --- зміна мови --------------------------------------------------------
    check("мов рівно три", page.locator(".langbtn").count() == 3,
          [page.locator(".langbtn").nth(i).inner_text() for i in range(page.locator(".langbtn").count())])
    page.click('.langbtn[data-lang="ru"]')
    page.wait_for_timeout(200)
    check("російська: заголовок складу", "СОСТАВ" in page.locator("#d-espresso").inner_text().upper(),
          page.locator("#d-espresso").inner_text()[:80])
    check("російська: склад перекладено", "кофе" in page.locator("#d-espresso").inner_text().lower())
    page.click('.langbtn[data-lang="uk"]')
    page.wait_for_timeout(200)

    # --- стіл із QR --------------------------------------------------------
    # --- фільтр переживає авто-оновлення ----------------------------------
    page.fill(".search", "moj")
    page.wait_for_timeout(150)
    page.evaluate("MenuStore.refresh()")
    page.wait_for_timeout(400)
    check("пошук не збився після авто-оновлення", page.input_value(".search") == "moj")
    check("порожні категорії ховаються разом із заголовком",
          page.locator("#c-hot").is_hidden(), page.locator("#c-hot").is_visible())
    page.fill(".search", "")

    # --- тема --------------------------------------------------------------
    page.click('.themebtn[data-theme="dark"]')
    page.wait_for_timeout(100)
    check("темна тема застосовується",
          page.evaluate("document.documentElement.dataset.theme") == "dark")

    check("без помилок у консолі", not errors, "; ".join(errors[:3]))
    if os.environ.get("SCREENSHOT"):
        page.screenshot(path=os.environ["SCREENSHOT"], full_page=False)
    b.close()

print()
print("FAILED:", fails if fails else "нічого")
sys.exit(1 if fails else 0)
