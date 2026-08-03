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

    check("венью в шапці", page.inner_text("#venue-name") == "The Copper Fig")
    check("14 карток", page.locator(".dish").count() == 14, page.locator(".dish").count())
    # меню — один суцільний список: ні заголовків розділів, ні вкладок над ним
    check("немає заголовків розділів", page.locator(".section").count() == 0)
    check("немає вкладок розділів", page.locator("#toolbar .tabs").count() == 0)
    check("усі 14 страв в одній сітці",
          page.locator("#menu > .grid").count() == 1
          and page.locator("#menu > .grid > .dish").count() == 14,
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

    for word, lang in [("овес", "uk"), ("oats", "en"), ("Hafer", "de"), ("avena", "es/it"), ("овёс", "ru")]:
        found = search(word)
        check(f"пошук «{word}» ({lang}) → oat-cold-brew", found == ["d-oat-cold-brew"], found)

    found = search("восьминіг")
    check("пошук «восьминіг» → charred-octopus", found == ["d-charred-octopus"], found)
    found = search("Weizenmehl")
    check("пошук «Weizenmehl» (вкладений склад) → 4 позиції з борошном",
          set(found) == {"d-smoked-beetroot-tartare", "d-wild-mushroom-arancini",
                         "d-braised-short-rib", "d-dark-chocolate-tart"}, found)

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
    check("горіхи: 1 «містить» + 2 «може містити» = 3",
          page.locator(".dish.flagged").count() == 3, page.locator(".dish.flagged").count())
    page.click(".clear-btn")
    page.wait_for_timeout(150)
    check("скидання знімає приглушення", page.locator(".dish.flagged").count() == 0)

    # --- стани позицій -----------------------------------------------------
    gimlet = page.locator("#d-basil-garden-gimlet")
    check("86 підписано «Наразі немає»", "Наразі немає" in gimlet.inner_text(), gimlet.inner_text()[:60])
    salad = page.locator("#d-fig-walnut-salad")
    check("«Скоро» з датою відкриття", "Скоро" in salad.inner_text() and "вересня" in salad.inner_text(),
          salad.inner_text()[:80])
    check("алкоголь: пояснення замість кнопки",
          "Алкоголь замовляється" in page.locator("#d-copper-fig-old-fashioned").inner_text())

    check("ціна у фунтах, а не «11,50 GBP»",
          "£11.50" in page.locator("#d-smoked-beetroot-tartare").inner_text(),
          page.locator("#d-smoked-beetroot-tartare .price").inner_text())

    # --- три рівні алергенів ----------------------------------------------
    tartare = page.locator("#d-smoked-beetroot-tartare")
    check("мітка R на гірчиці", tartare.locator(".tag .rem").count() == 1)
    check("«може містити» пунктиром", tartare.locator(".tag.maybe").count() == 1)
    check("джерело з датою перевірки", "2026-07-14" in tartare.inner_text())

    # --- зміна мови --------------------------------------------------------
    page.click('.langbtn[data-lang="de"]')
    page.wait_for_timeout(200)
    check("німецька: заголовок складу", "ZUTATEN" in page.locator("#d-oat-cold-brew").inner_text().upper(),
          page.locator("#d-oat-cold-brew").inner_text()[:80])
    check("німецька: склад перекладено", "Hafer" in page.locator("#d-oat-cold-brew").inner_text())
    page.click('.langbtn[data-lang="uk"]')
    page.wait_for_timeout(200)

    # --- стіл із QR --------------------------------------------------------
    # --- фільтр переживає авто-оновлення ----------------------------------
    if not page.locator(".filters").first.evaluate("n => n.classList.contains('open')"):
        page.click(".filter-toggle")
    page.fill(".search", "fig")
    page.wait_for_timeout(150)
    page.evaluate("MenuStore.refresh()")
    page.wait_for_timeout(400)
    check("фільтр лишається відкритим після авто-оновлення",
          page.locator(".filters").first.evaluate("n => n.classList.contains('open')"))
    check("пошук не збився після авто-оновлення", page.input_value(".search") == "fig")
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
