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
    check("30 позицій", page.locator(".dish").count() == 30, page.locator(".dish").count())
    # меню — один суцільний список: ні заголовків розділів, ні вкладок над ним
    # Рядок категорій угорі: це навігація, а не фільтр
    tabs = [page.locator("#toolbar .tab").nth(i).inner_text()
            for i in range(page.locator("#toolbar .tab").count())]
    check("категорії винесені вгору",
          tabs == ["Міцне", "Коктейлі", "Пиво й безалкогольне", "Вино й ігристе",
                   "Гарячі напої", "Кальяни"], tabs)
    # Меню знову згруповане — але категорія це підпис, а не сутність зі станом
    cats = [page.locator("#menu > .cat").nth(i).get_attribute("id")
            for i in range(page.locator("#menu > .cat").count())]
    check("шість категорій у порядку меню",
          cats == ["c-spirits", "c-cocktails", "c-beer-soft", "c-wine", "c-hot", "c-hookah"],
          cats)
    check("кожна позиція під заголовком",
          page.locator("#menu > .cat > .grid > .dish").count() == 30,
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
          set(found) == {"d-whiskey", "d-corona"}, found)

    search("")

    # --- алергенів у меню немає -------------------------------------------
    # Заклад їх не надавав, а виведені з назв продуктів гірші за жодних.
    check("панелі фільтра алергенів немає", page.locator(".filters").count() == 0)
    check("міток алергенів на картках немає", page.locator(".tag").count() == 0)
    check("значка джерела немає", page.locator(".srcbadge").count() == 0)
    check("застереження про алергію теж прибрано",
          "алерг" not in page.inner_text("main").lower(),
          page.inner_text("main")[:80])
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
          "£13.00" in page.locator("#d-vodka-house").inner_text(),
          page.locator("#d-vodka-house .price").inner_text())
    # У позиції з варіантами ціна не одна: £13 келих, £80 пляшка
    check("вино показує «від», а не одну ціну",
          "від £13.00" in page.locator("#d-white-wine .price").inner_text(),
          page.locator("#d-white-wine .price").inner_text())
    check("позиція без варіантів — проста ціна",
          page.locator("#d-espresso .price").inner_text() == "£4.00",
          page.locator("#d-espresso .price").inner_text())

    # --- зміна мови --------------------------------------------------------
    boxes = page.evaluate("""() => {
      const l = document.querySelector('.langswitch').getBoundingClientRect();
      const t = document.querySelector('.themeswitch').getBoundingClientRect();
      return {langBottom: l.bottom, themeTop: t.top};
    }""")
    check("мова й тема різними рядками", boxes["themeTop"] >= boxes["langBottom"] - 1,
          boxes)
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
    check("кнопка порожньої категорії теж ховається",
          page.locator('#toolbar .tab[data-cat="hot"]').is_hidden())
    page.fill(".search", "")

    # --- тема --------------------------------------------------------------
    page.click('.themebtn[data-theme="dark"]')
    page.wait_for_timeout(100)
    check("темна тема застосовується",
          page.evaluate("document.documentElement.dataset.theme") == "dark")

    # Видалили ключ із словника, а `data-i18n` лишився — і гість бачить на
    # екрані «guest.notice» замість тексту. Саме так і сталося з демо.
    import re as _re
    leftovers = _re.findall(r"\b[a-z]{2,10}\.[a-zA-Z]{2,20}(?:\.[a-zA-Z0-9]+)?\b",
                            page.inner_text("body"))
    leftovers = [x for x in leftovers if not x.startswith(("www.", "http"))
                 and "." in x and " " not in x
                 and x.split(".")[0] in {"guest", "tb", "cart", "order", "sched",
                                         "dish", "count", "search", "net", "brand",
                                         "lang", "theme", "ui", "opt", "pay", "cat",
                                         "price", "alg", "src"}]
    check("неперекладених ключів на екрані немає", not leftovers, leftovers[:3])

    check("без помилок у консолі", not errors, "; ".join(errors[:3]))
    if os.environ.get("SCREENSHOT"):
        page.screenshot(path=os.environ["SCREENSHOT"], full_page=False)
    b.close()

print()
print("FAILED:", fails if fails else "нічого")
sys.exit(1 if fails else 0)
