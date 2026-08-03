def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_menu_returns_seed_data(client):
    m = client.get("/api/menu").json()
    assert m["venue"]["key"] == "the-copper-fig"
    assert "sections" not in m          # меню один список, груп немає
    assert len(m["items"]) == 14
    assert m["lexicon"]["oats"]["de"] == "Hafer"
    assert m["sources"]["official-2026-07"]["checked"] == "2026-07-14"


def test_ingredients_are_keys_not_text(client):
    """Склад — посилання на словник. Саме звідси беруться однакові переклади
    й пошук «кунжут» = «sesame» = «Sesam»."""
    m = client.get("/api/menu").json()
    brew = next(i for i in m["items"] if i["key"] == "oat-cold-brew")
    assert brew["ing"] == ["coffee", ["oat-milk", ["oats", "water"]]]
    assert all(k in m["lexicon"] for k in ("coffee", "oat-milk", "oats", "water"))


def test_allergen_levels_survive_the_round_trip(client):
    m = client.get("/api/menu").json()
    tartare = next(i for i in m["items"] if i["key"] == "smoked-beetroot-tartare")
    assert tartare["a"] == ["mustard", "cereals-gluten", "sulphites"]
    assert tartare["m"] == ["celery"]
    assert tartare["r"] == ["mustard"]
    assert tartare["src"] == "official-2026-07"


def test_alcohol_is_visible_but_not_orderable(client):
    """Межа v1 зашита в дані, а не в код: коктейлі видно, замовити не можна."""
    m = client.get("/api/menu").json()
    cocktails = [i for i in m["items"] if i["orderable_reason"] == "alcohol-age-check"]
    assert len(cocktails) == 4
    assert all(i["orderable"] is False for i in cocktails)
    assert all(i["orderable_reason"] == "alcohol-age-check" for i in cocktails)


def test_states_come_out_computed(client):
    m = client.get("/api/menu").json()
    by_key = {i["key"]: i for i in m["items"]}
    assert by_key["basil-garden-gimlet"]["available"]["reason"] == "sold_out"
    assert by_key["fig-walnut-salad"]["available"]["opens_at"] == "2026-09-01T12:00"
    assert by_key["house-lemonade"]["available"]["open"] is True


def test_time_travel_opens_a_soon_item(client):
    m = client.get("/api/menu", params={"at": "2026-09-02T13:00"}).json()
    by_key = {i["key"]: i for i in m["items"]}
    assert by_key["fig-walnut-salad"]["available"]["open"] is True
    assert m["now"]["stamp"] == "2026-09-02T13:00"


def test_bad_at_is_rejected(client):
    assert client.get("/api/menu", params={"at": "невчасно"}).status_code == 400


def test_menu_is_one_flat_list_ordered_by_position(client):
    """Меню — один список. Порядок задає зал позицією, а не групою."""
    m = client.get("/api/menu").json()
    keys = [i["key"] for i in m["items"]]
    assert len(keys) == len(set(keys)) == 14
    # позиції не перетасовані за розділами: перша страва сідера лишається першою
    assert keys[0] == "smoked-beetroot-tartare"


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
    item = _item(db, "house-lemonade")
    assert _available(client, "house-lemonade")["open"] is True

    assert client.patch(f"/api/admin/items/{item.id}", json={"state": "off"}).status_code == 200
    av = _available(client, "house-lemonade")
    assert av["open"] is False
    assert av["reason"] == "sold_out"
    # сусідню страву це не зачепило
    assert _available(client, "oat-cold-brew")["open"] is True

    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto"})


def test_schedule_closes_one_dish_by_hours(client, db, venue):
    """Розклад тепер живе на страві, а не на групі. 'late-bar' — 22:00–01:00."""
    from tests.test_permissions import as_owner

    as_owner(client)
    item = _item(db, "house-lemonade")
    client.patch(f"/api/admin/items/{item.id}", json={"schedule_key": "late-bar"})

    closed = client.get("/api/menu", params={"at": "2026-08-07T15:00"}).json()
    av = next(i for i in closed["items"] if i["key"] == "house-lemonade")["available"]
    assert av["open"] is False
    assert av["reason"] == "scheduled"
    assert av["schedule"] == "late-bar"

    # у свої години — відкрито, і навіть по той бік півночі
    for stamp in ("2026-08-07T23:30", "2026-08-08T00:30"):
        opened = client.get("/api/menu", params={"at": stamp}).json()
        assert next(i for i in opened["items"] if i["key"] == "house-lemonade")["available"]["open"]

    # решта меню працює за своїм часом
    assert next(
        i for i in closed["items"] if i["key"] == "oat-cold-brew"
    )["available"]["open"] is True

    client.patch(f"/api/admin/items/{item.id}", json={"schedule_key": None})


def test_timer_opens_a_dish_by_itself(client, db, venue):
    """«По таймеру»: дата відкриття, після якої страва відкривається сама,
    без жодного натискання в панелі."""
    from tests.test_permissions import as_owner

    as_owner(client)
    item = _item(db, "house-lemonade")
    client.patch(
        f"/api/admin/items/{item.id}",
        json={"state": "soon", "opens_at": "2026-12-24T18:00"},
    )

    before = client.get("/api/menu", params={"at": "2026-12-24T17:59"}).json()
    av = next(i for i in before["items"] if i["key"] == "house-lemonade")["available"]
    assert av["open"] is False
    assert av["reason"] == "soon"
    assert av["opens_at"] == "2026-12-24T18:00"

    after = client.get("/api/menu", params={"at": "2026-12-24T18:00"}).json()
    assert next(i for i in after["items"] if i["key"] == "house-lemonade")["available"]["open"]

    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto", "opens_at": None})
