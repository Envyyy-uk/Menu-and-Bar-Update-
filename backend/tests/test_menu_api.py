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
    assert len(m["items"]) == 30
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
    item.ingredients = ["cocoa", ["milk", ["water", "sugar"]]]
    db.commit()

    m = client.get("/api/menu").json()
    drink = next(i for i in m["items"] if i["key"] == "hot-chocolate")
    assert drink["ing"] == ["cocoa", ["milk", ["water", "sugar"]]]
    assert m["lexicon"]["water"]["uk"] == "вода"

    item.ingredients = before
    db.commit()
def test_alcohol_is_orderable_and_warns_about_age(client):
    """PODVAL — бар. Якби алкоголь не замовлявся, застосунок був би меню для
    читання: у цьому меню алкоголь — майже все. Контроль лишається людині —
    бармен перевіряє документ при подачі."""
    m = client.get("/api/menu").json()
    booze = [i for i in m["items"] if "age-check" in i["w"]]
    assert len(booze) == 23
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
    size = next(g for g in by_key["vodka-house"]["options"] if g["key"] == "size")
    assert [(c["name"], c["price_pence"]) for c in size["choices"]] == [
        ("50 ml", 1300), ("100 ml", 2600), ("150 ml", 3900),
        ("200 ml", 5200), ("250 ml", 6500), ("300 ml", 7800),
        ("Bottle", 23000),
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
    assert len(keys) == len(set(keys)) == 30
    # порядок меню: міцне, коктейлі, пиво, вино, гаряче
    assert keys[0] == "vodka-house"
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
    for cat in m["categories"]:
        assert set(cat["names"]) == wanted, cat

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


def test_menu_is_grouped_into_categories(client):
    """Меню знову згруповане — але категорія це підпис, а не сутність зі
    станом. Закривають позицію, не групу."""
    m = client.get("/api/menu").json()

    # Порядок важливий, тож це список, а не словник: JSONB не зберігає
    # порядок ключів, і категорії приїхали б перетасованими.
    assert [c["key"] for c in m["categories"]] == [
        "spirits", "cocktails", "beer-soft", "wine", "hot", "hookah",
    ]
    assert next(c for c in m["categories"] if c["key"] == "hookah")["names"]["uk"] == "Кальяни"

    used = {i["category"] for i in m["items"]}
    assert used == {c["key"] for c in m["categories"]}, "позиція без категорії загубиться"

    by_cat = {}
    for i in m["items"]:
        by_cat.setdefault(i["category"], []).append(i["key"])
    assert by_cat["hookah"] == ["hookah"]
    assert "mojito" in by_cat["cocktails"]
    assert "vodka-house" in by_cat["spirits"]


def test_pour_sizes_are_multiples_of_the_shot(client):
    """У меню вказана ціна лише за 50 мл, тож решта сітки кратна їй."""
    m = client.get("/api/menu").json()
    by_key = {i["key"]: i for i in m["items"]}

    for key, shot in (("vodka-house", 1300), ("patron-silver", 1600), ("nalivka", 900)):
        size = next(g for g in by_key[key]["options"] if g["key"] == "size")
        pours = [c for c in size["choices"] if c["name"].endswith(" ml")]
        assert [c["name"] for c in pours] == [
            "50 ml", "100 ml", "150 ml", "200 ml", "250 ml", "300 ml",
        ]
        assert [c["price_pence"] for c in pours] == [shot * n for n in range(1, 7)]


def test_one_line_in_the_menu_is_one_item_with_a_choice(client):
    """У PDF лікери стоять одним рядком з однією ціною — отже, це один пункт
    із вибором, а не чотири майже однакові картки."""
    m = client.get("/api/menu").json()
    keys = {i["key"] for i in m["items"]}
    assert "liqueur" in keys
    for gone in ("disaronno", "baileys", "jagermeister", "malibu"):
        assert gone not in keys

    liqueur = next(i for i in m["items"] if i["key"] == "liqueur")
    kind = next(g for g in liqueur["options"] if g["key"] == "kind")
    assert [c["name"] for c in kind["choices"]] == [
        "Disaronno Amaretto", "Baileys", "Jägermeister", "Malibu",
    ]


def test_allergens_are_gone_from_the_menu(client):
    """Заклад алергенів не надавав, а виведені з назв продуктів гірші за
    жодних: гість вірить міткам. Тому їх немає ніде — ні полями, ні
    джерелом, ні окремим попередженням."""
    m = client.get("/api/menu").json()

    assert "sources" not in m
    for i in m["items"]:
        assert not ({"a", "m", "r", "src"} & set(i)), i["key"]

    # Склад лишився: на ньому тримається пошук трьома мовами
    assert next(i for i in m["items"] if i["key"] == "mojito")["ing"]
    assert "allergen-by-option" not in m["warnings"]
