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
    check("39 карток", page.locator(".dish").count() == 39, page.locator(".dish").count())
    # меню — один суцільний список: ні заголовків розділів, ні вкладок над ним
    check("немає заголовків розділів", page.locator(".section").count() == 0)
    check("немає вкладок розділів", page.locator("#toolbar .tabs").count() == 0)
    check("усі 39 позицій в одній сітці",
          page.locator("#menu > .grid").count() == 1
          and page.locator("#menu > .grid > .dish").count() == 39,
          page.locator("#menu > .grid > .dish").count())

    # --- крос-мовний пошук по складнику -----------------------------------
    def search(q):
        page.fill(".search", q)
        page.wait_for_timeout(120)
        return [
            page.locator(".dish").nth(i).get_attribute("id")
            for i in range(page.locator(".dish").count())
            if page.locator(".dish").nth(i).is_visible()
        ]

    for word, lang in [("хміль", "uk"), ("hops", "en"), ("Hopfen", "de"),
                       ("lúpulo", "es"), ("luppolo", "it"), ("хмель", "ru")]:
        found = search(word)
        check(f"пошук «{word}» ({lang}) → corona", found == ["d-corona"], found)

    found = search("Gerstenmalz")
    check("пошук «Gerstenmalz» → усе на ячмінному солоді",
          set(found) == {"d-jack-daniels", "d-black-label", "d-jameson", "d-corona"}, found)

    search("")

    # --- фільтр за алергенами ---------------------------------------------
    page.click(".filter-toggle")
    page.locator(".chip", has_text="Молоко").first.click()
    page.wait_for_timeout(150)
    flagged = page.locator(".dish.flagged").count()
    check("фільтр «Молоко» приглушує 5 позицій", flagged == 5, flagged)
    check("лічильник згадує алергени", "з вашими алергенами" in page.inner_text(".result-count"),
          page.inner_text(".result-count"))
    page.click(".clear-btn")
    page.wait_for_timeout(150)
    # «може містити» приглушується нарівні з «містить»
    page.locator(".chip", has_text="Горіхи").first.click()
    page.wait_for_timeout(150)
    check("горіхи: «може містити» приглушується нарівні з «містить»",
          page.locator(".dish.flagged").count() == 5, page.locator(".dish.flagged").count())
    page.click(".clear-btn")
    page.wait_for_timeout(150)
    check("скидання знімає приглушення", page.locator(".dish.flagged").count() == 0)

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

    # --- рівні алергенів і чесність джерела --------------------------------
    disaronno = page.locator("#d-disaronno")
    check("«може містити» пунктиром", disaronno.locator(".tag.maybe").count() == 1,
          disaronno.inner_text()[:80])
    check("джерело названо чесно: відновлено, а не лист закладу",
          "Відновлено з назви продукту" in disaronno.inner_text(),
          disaronno.inner_text()[-90:])
    check("вершковий лікер помічено молоком",
          page.locator("#d-baileys .tag").first.inner_text().strip() != "",
          page.locator("#d-baileys").inner_text()[:80])

    # --- зміна мови --------------------------------------------------------
    page.click('.langbtn[data-lang="de"]')
    page.wait_for_timeout(200)
    check("німецька: заголовок складу", "ZUTATEN" in page.locator("#d-espresso").inner_text().upper(),
          page.locator("#d-espresso").inner_text()[:80])
    check("німецька: склад перекладено", "Kaffee" in page.locator("#d-espresso").inner_text())
    page.click('.langbtn[data-lang="uk"]')
    page.wait_for_timeout(200)

    # --- стіл із QR --------------------------------------------------------
    # --- фільтр переживає авто-оновлення ----------------------------------
    if not page.locator(".filters").first.evaluate("n => n.classList.contains('open')"):
        page.click(".filter-toggle")
    page.fill(".search", "moj")
    page.wait_for_timeout(150)
    page.evaluate("MenuStore.refresh()")
    page.wait_for_timeout(400)
    check("фільтр лишається відкритим після авто-оновлення",
          page.locator(".filters").first.evaluate("n => n.classList.contains('open')"))
    check("пошук не збився після авто-оновлення", page.input_value(".search") == "moj")
    page.click(".clear-btn")

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
