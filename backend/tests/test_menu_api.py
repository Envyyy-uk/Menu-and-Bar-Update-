def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_menu_returns_seed_data(client):
    m = client.get("/api/menu").json()
    assert m["venue"]["key"] == "podval"
    assert m["venue"]["name"] == "PODVAL"
    assert m["venue"]["currency"] == "GBP"
    assert "sections" not in m          # меню один список, груп немає
    assert len(m["items"]) == 40
    assert m["lexicon"]["coffee"]["ru"] == "кофе"
    # Меню виходить трьома мовами — зайвих у файлі бути не має
    assert set(m["lexicon"]["coffee"]) == {"uk", "en", "ru"}


def test_ingredients_are_keys_not_text(client):
    """Склад — посилання на словник. Саме звідси беруться однакові переклади
    й пошук «кава» = «coffee» = «Kaffee»."""
    m = client.get("/api/menu").json()
    mojito = next(i for i in m["items"] if i["key"] == "mojito")
    assert mojito["ing"] == ["rum", "sugar", "lime", "mint"]
    assert all(k in m["lexicon"] for k in mojito["ing"])
    assert m["lexicon"]["mint"]["en"] == "mint"


def test_nested_ingredients_still_render(client, db, venue):
    """Вкладені складники — «молоко (вода, сухе молоко)». Меню PODVAL їх не
    використовує, але механізм лишається робочим, і це варто тримати під
    тестом, а не з'ясовувати колись у меню з їжею."""
    from sqlalchemy import select

    from app.models import MenuItem

    item = db.scalars(select(MenuItem).where(MenuItem.key == "hot-chocolate")).one()
    before = item.ingredients
    item.ingredients = ["cocoa", ["almond-milk", ["almonds", "water"]]]
    db.commit()

    m = client.get("/api/menu").json()
    drink = next(i for i in m["items"] if i["key"] == "hot-chocolate")
    assert drink["ing"] == ["cocoa", ["almond-milk", ["almonds", "water"]]]
    assert m["lexicon"]["almonds"]["uk"] == "мигдаль"

    item.ingredients = before
    db.commit()


def test_allergen_levels_survive_the_round_trip(client):
    m = client.get("/api/menu").json()
    by_key = {i["key"]: i for i in m["items"]}

    assert by_key["baileys"]["a"] == ["milk"]          # вершковий лікер
    assert by_key["disaronno"]["m"] == ["tree-nuts"]   # абрикосова кісточка
    assert by_key["corona"]["a"] == ["cereals-gluten"]  # ячмінний солод
    assert by_key["white-wine"]["a"] == ["sulphites"]

    # Джерело всюди одне й чесне: алергени відновлені з назв продуктів, а не
    # взяті з листа закладу. Гість бачить це на кожній картці.
    assert {i["src"] for i in m["items"]} == {"reconstructed"}
    assert m["sources"]["reconstructed"]["type"] == "reconstructed"


def test_alcohol_is_orderable_and_warns_about_age(client):
    """PODVAL — бар. Якби алкоголь не замовлявся, застосунок був би меню для
    читання: у цьому меню алкоголь — майже все. Контроль лишається людині —
    бармен перевіряє документ при подачі."""
    m = client.get("/api/menu").json()
    booze = [i for i in m["items"] if "age-check" in i["w"]]
    assert len(booze) >= 25
    assert all(i["orderable"] is True for i in booze)

    # А безалкогольне цього попередження не носить
    for key in ("espresso", "soft-drink", "tea-pot"):
        assert "age-check" not in next(i for i in m["items"] if i["key"] == key)["w"]


def test_options_reach_the_guest(client):
    """Без варіантів бар не знає, яке саме мохіто робити."""
    m = client.get("/api/menu").json()
    by_key = {i["key"]: i for i in m["items"]}

    mojito = by_key["mojito"]["options"]
    assert [g["key"] for g in mojito] == ["flavour"]
    assert [c["name"] for c in mojito[0]["choices"]] == [
        "Classic", "Strawberry", "Raspberry", "Passion", "Mango",
    ]

    # 50 мл проти пляшки — різні ціни на тій самій позиції
    size = next(g for g in by_key["absolut"]["options"] if g["key"] == "size")
    assert [(c["name"], c["price_pence"]) for c in size["choices"]] == [
        ("50 ml", 1300), ("Bottle", 23000),
    ]

    # Позиції без вибору лишаються простими
    assert by_key["espresso"]["options"] == []


def test_states_come_out_computed(client, db, venue):
    """Стани рахує сервер. Сідер PODVAL нікого не вимикає — заклад
    відкривається з повним меню, — тож стан для перевірки ставимо самі."""
    from sqlalchemy import select

    from app.models import MenuItem
    from tests.test_permissions import as_owner

    as_owner(client)
    item = db.scalars(select(MenuItem).where(MenuItem.key == "patron-silver")).one()
    client.patch(f"/api/admin/items/{item.id}", json={"state": "off"})

    by_key = {i["key"]: i for i in client.get("/api/menu").json()["items"]}
    assert by_key["patron-silver"]["available"]["reason"] == "sold_out"
    assert by_key["espresso"]["available"]["open"] is True

    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto"})


def test_bad_at_is_rejected(client):
    assert client.get("/api/menu", params={"at": "невчасно"}).status_code == 400


def test_menu_is_one_flat_list_ordered_by_position(client):
    """Меню — один список. Порядок задає зал позицією, а не групою."""
    m = client.get("/api/menu").json()
    keys = [i["key"] for i in m["items"]]
    assert len(keys) == len(set(keys)) == 40
    # порядок меню: міцне, коктейлі, пиво, вино, гаряче
    assert keys[0] == "absolut"
    assert keys[-1] == "hookah"


# --------------------------------------------- три способи зняти страву ----
# Розділів більше немає: закриває страву тільки вона сама. Способи — 86,
# розклад і дата відкриття («по таймеру»).


def _item(db, key):
    from sqlalchemy import select

    from app.models import MenuItem

    return db.scalars(select(MenuItem).where(MenuItem.key == key)).one()


def _available(client, key):
    m = client.get("/api/menu").json()
    return next(i for i in m["items"] if i["key"] == key)["available"]


def test_86_takes_one_dish_off(client, db, venue):
    """Найчастіша дія зміни: страва закінчилась просто зараз."""
    from tests.test_permissions import as_staff

    as_staff(client)
    item = _item(db, "espresso")
    assert _available(client, "espresso")["open"] is True

    assert client.patch(f"/api/admin/items/{item.id}", json={"state": "off"}).status_code == 200
    av = _available(client, "espresso")
    assert av["open"] is False
    assert av["reason"] == "sold_out"
    # сусідню страву це не зачепило
    assert _available(client, "corona")["open"] is True

    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto"})


def test_schedule_closes_one_dish_by_hours(client, db, venue):
    """Розклад тепер живе на страві, а не на групі. 'late-bar' — 22:00–01:00."""
    from tests.test_permissions import as_owner

    as_owner(client)
    item = _item(db, "espresso")
    client.patch(f"/api/admin/items/{item.id}", json={"schedule_key": "late-bar"})

    closed = client.get("/api/menu", params={"at": "2026-08-07T15:00"}).json()
    av = next(i for i in closed["items"] if i["key"] == "espresso")["available"]
    assert av["open"] is False
    assert av["reason"] == "scheduled"
    assert av["schedule"] == "late-bar"

    # у свої години — відкрито, і навіть по той бік півночі
    for stamp in ("2026-08-07T23:30", "2026-08-08T00:30"):
        opened = client.get("/api/menu", params={"at": stamp}).json()
        assert next(i for i in opened["items"] if i["key"] == "espresso")["available"]["open"]

    # решта меню працює за своїм часом
    assert next(
        i for i in closed["items"] if i["key"] == "corona"
    )["available"]["open"] is True

    client.patch(f"/api/admin/items/{item.id}", json={"schedule_key": None})


def test_timer_opens_a_dish_by_itself(client, db, venue):
    """«По таймеру»: дата відкриття, після якої страва відкривається сама,
    без жодного натискання в панелі."""
    from tests.test_permissions import as_owner

    as_owner(client)
    item = _item(db, "espresso")
    client.patch(
        f"/api/admin/items/{item.id}",
        json={"state": "soon", "opens_at": "2026-12-24T18:00"},
    )

    before = client.get("/api/menu", params={"at": "2026-12-24T17:59"}).json()
    av = next(i for i in before["items"] if i["key"] == "espresso")["available"]
    assert av["open"] is False
    assert av["reason"] == "soon"
    assert av["opens_at"] == "2026-12-24T18:00"

    after = client.get("/api/menu", params={"at": "2026-12-24T18:00"}).json()
    assert next(i for i in after["items"] if i["key"] == "espresso")["available"]["open"]

    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto", "opens_at": None})


def test_every_allergen_key_is_a_real_one(client):
    """Невідомий ключ алергену інтерфейс просто **не показує** — мовчки.

    Саме так у це меню потрапило `nuts` замість `tree-nuts`: мигдалевий
    лікер лишився без мітки про горіхи, і жоден тест цього не бачив. Список
    із чотирнадцяти закріплений законом, тож звіряємось із ним.
    """
    allowed = {
        "cereals-gluten", "crustaceans", "eggs", "fish", "peanuts", "soya",
        "milk", "tree-nuts", "celery", "mustard", "sesame", "sulphites",
        "lupin", "molluscs",
    }
    m = client.get("/api/menu").json()
    used = set()
    for i in m["items"]:
        used |= set(i["a"]) | set(i["m"]) | set(i["r"])
    assert used <= allowed, f"невідомі ключі: {sorted(used - allowed)}"
    assert used, "у меню має бути хоч один алерген"


def test_menu_speaks_three_languages_only(client):
    """Меню виходить українською, англійською та російською. Зайва мова у
    файлі — це напівперекладене меню: частина карток чужою мовою, і гість
    вирішує, що застосунок зламався."""
    m = client.get("/api/menu").json()
    wanted = {"uk", "en", "ru"}

    for entry in m["lexicon"].values():
        assert set(entry) == wanted, entry
    for text in m["warnings"].values():
        assert set(text) == wanted, text
    for src in m["sources"].values():
        assert set(src["label"]) == wanted, src

    described = [i for i in m["items"] if i["desc"]]
    assert described, "описи мають бути"
    for i in described:
        assert set(i["desc"]) == wanted, i["key"]


def test_hookah_is_on_the_menu(client):
    m = client.get("/api/menu").json()
    hookah = next(i for i in m["items"] if i["key"] == "hookah")

    assert hookah["name"] == "Hookah"
    assert hookah["price_pence"] == 5000
    assert hookah["orderable"] is True
    # Тютюн, як і алкоголь: замовляється, документ перевіряє бармен при подачі
    assert hookah["w"] == ["tobacco-age-check"]
    assert m["warnings"]["tobacco-age-check"]["uk"].startswith("Тютюн")


def test_everything_is_on_the_bar_for_now(client):
    """Страв поки немає — усе меню йде на бар. Станція кухні лишається в
    моделі: коли з'явиться їжа, її позиції просто отримають `kitchen`."""
    m = client.get("/api/menu").json()
    assert {i["station"] for i in m["items"]} == {"bar"}
