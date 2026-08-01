def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["db"] == "ok"


def test_menu_returns_seed_data(client):
    m = client.get("/api/menu").json()
    assert m["venue"]["key"] == "the-copper-fig"
    assert [s["key"] for s in m["sections"]] == [
        "starters",
        "mains",
        "desserts",
        "cocktails",
        "soft-drinks",
    ]
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
    cocktails = [i for i in m["items"] if i["section"] == "cocktails"]
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
