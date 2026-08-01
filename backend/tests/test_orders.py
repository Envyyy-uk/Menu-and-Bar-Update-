"""Замовлення без оплат: ідемпотентність, машина станів, наявність у момент
оплати, розділення на кухню й бар."""

import uuid

import pytest
from sqlalchemy import select

from app.models import MenuItem, Order, Table
from tests.test_permissions import as_owner, as_staff


def token(db):
    return db.scalars(select(Table).where(Table.label == "1")).one().token


def new_client_token():
    return "ct-" + uuid.uuid4().hex


DEFAULT_ITEMS = [{"key": "house-lemonade", "qty": 2}]


def place(client, db, items=None, client_token=None, note=None):
    return client.post(
        "/api/orders",
        json={
            "table_token": token(db),
            "client_token": client_token or new_client_token(),
            "items": DEFAULT_ITEMS if items is None else items,
            "note": note,
        },
    )


# ------------------------------------------------------- ідемпотентність ---


def test_double_tap_does_not_create_two_orders(client, db, venue):
    ct = new_client_token()
    first = place(client, db, client_token=ct)
    second = place(client, db, client_token=ct)

    assert first.status_code == 201
    assert first.json()["created"] is True
    assert second.status_code == 201
    assert second.json()["created"] is False
    assert first.json()["id"] == second.json()["id"]

    count = len(db.scalars(select(Order).where(Order.client_token == ct)).all())
    assert count == 1


def test_retry_after_a_dropped_connection_returns_the_same_order(client, db, venue):
    """Обрив мережі й подвійний тап — та сама ситуація: гість повторює запит
    із тим самим токеном і має отримати те саме замовлення."""
    ct = new_client_token()
    first = place(client, db, client_token=ct).json()
    for _ in range(4):
        again = place(client, db, client_token=ct).json()
        assert again["id"] == first["id"]
        assert again["number"] == first["number"]


def test_different_tokens_make_different_orders(client, db, venue):
    a = place(client, db).json()
    b = place(client, db).json()
    assert a["id"] != b["id"]
    assert b["number"] == a["number"] + 1


# -------------------------------------------------------------- вміст -----


def test_prices_and_names_are_snapshotted(client, db, venue):
    """Меню зміниться — історія не попливе."""
    order = place(client, db, items=[{"key": "house-lemonade", "qty": 2}]).json()
    assert order["items"][0]["name"] == "House Lemonade"
    assert order["total_pence"] == order["items"][0]["unit_price_pence"] * 2

    as_owner(client)
    item = db.scalars(select(MenuItem).where(MenuItem.key == "house-lemonade")).one()
    old_price = item.price_pence
    client.patch(f"/api/admin/items/{item.id}", json={"price_pence": old_price + 500})

    fresh = db.get(Order, uuid.UUID(order["id"]))
    assert fresh.items[0].unit_price_pence == old_price

    client.patch(f"/api/admin/items/{item.id}", json={"price_pence": old_price})


def test_unknown_table_is_refused(client, db, venue):
    r = client.post(
        "/api/orders",
        json={
            "table_token": "not-a-real-token",
            "client_token": new_client_token(),
            "items": [{"key": "house-lemonade", "qty": 1}],
        },
    )
    assert r.status_code == 404


def test_empty_order_is_refused(client, db, venue):
    assert place(client, db, items=[]).status_code == 422


# ------------------------------------------------------- межа v1: алкоголь -


def test_alcohol_cannot_be_ordered(client, db, venue):
    """Позиції видно в меню, але вони не замовляються: вік перевіряють при
    подачі. Межа зашита в дані, а не в код."""
    r = place(client, db, items=[{"key": "elderflower-spritz", "qty": 1}])
    assert r.status_code == 409
    problems = r.json()["detail"]["unavailable"]
    assert problems[0]["reason"] == "alcohol-age-check"


def test_86_item_cannot_be_ordered(client, db, venue):
    as_owner(client)
    item = db.scalars(select(MenuItem).where(MenuItem.key == "spiced-apple-cooler")).one()
    client.patch(f"/api/admin/items/{item.id}", json={"state": "off"})
    client.post("/api/auth/logout")

    r = place(client, db, items=[{"key": "spiced-apple-cooler", "qty": 1}])
    assert r.status_code == 409
    assert r.json()["detail"]["unavailable"][0]["reason"] == "sold_out"

    as_owner(client)
    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto"})
    client.post("/api/auth/logout")


def test_availability_is_checked_again_at_payment(client, db, venue):
    """Позицію можуть вимкнути, поки гість тримає її в кошику. Оплата тоді
    не проводиться, і гість бачить, що саме випало."""
    ct = new_client_token()
    order = place(client, db, items=[{"key": "oat-cold-brew", "qty": 1}], client_token=ct).json()

    as_owner(client)
    item = db.scalars(select(MenuItem).where(MenuItem.key == "oat-cold-brew")).one()
    client.patch(f"/api/admin/items/{item.id}", json={"state": "off"})
    client.post("/api/auth/logout")

    r = client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    assert r.status_code == 409
    assert r.json()["detail"]["unavailable"][0]["name"] == "Oat Cold Brew"

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "draft"

    as_owner(client)
    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto"})
    client.post("/api/auth/logout")

    ok = client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    assert ok.status_code == 200


# --------------------------------------------------------- машина станів ---


def paid_order(client, db, items=None):
    ct = new_client_token()
    order = place(client, db, items=items, client_token=ct).json()
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    client.post(f"/api/orders/{order['id']}/confirm-offline", params={"client_token": ct})
    return order, ct


def test_full_happy_path(client, db, venue):
    order, ct = paid_order(client, db)
    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "paid"

    as_staff(client)
    for target, expected in [("accepted", "accepted"), ("ready", "ready"), ("served", "served")]:
        r = client.post(f"/api/orders/{order['id']}/status", params={"target": target})
        assert r.status_code == 200
        assert r.json()["status"] == expected


def test_pressing_accepted_twice_is_harmless(client, db, venue):
    order, _ = paid_order(client, db)
    as_staff(client)
    first = client.post(f"/api/orders/{order['id']}/status", params={"target": "accepted"})
    second = client.post(f"/api/orders/{order['id']}/status", params={"target": "accepted"})
    assert first.status_code == second.status_code == 200


def test_skipping_states_is_refused(client, db, venue):
    order, ct = paid_order(client, db)
    as_staff(client)
    r = client.post(f"/api/orders/{order['id']}/status", params={"target": "served"})
    assert r.status_code == 409


def test_confirm_offline_needs_the_guests_own_token(client, db, venue):
    ct = new_client_token()
    order = place(client, db, client_token=ct).json()
    # Знання id недостатньо: без свого токена гість не читає чуже замовлення
    r = client.post(
        f"/api/orders/{order['id']}/confirm-offline", params={"client_token": "ct-" + "0" * 30}
    )
    assert r.status_code == 404


# --------------------------------------------------------- черга станцій ---


def test_order_reaches_the_queue_only_after_paid(client, db, venue):
    ct = new_client_token()
    order = place(client, db, client_token=ct).json()

    as_staff(client)
    assert all(o["id"] != order["id"] for o in client.get("/api/orders").json())
    client.post("/api/auth/logout")

    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    as_staff(client)
    assert all(o["id"] != order["id"] for o in client.get("/api/orders").json())
    client.post("/api/auth/logout")

    client.post(f"/api/orders/{order['id']}/confirm-offline", params={"client_token": ct})
    as_staff(client)
    assert any(o["id"] == order["id"] for o in client.get("/api/orders").json())


def test_queue_splits_kitchen_and_bar(client, db, venue):
    """Кухня не має бачити коктейлі, бар — стейки."""
    order, _ = paid_order(
        client,
        db,
        items=[{"key": "charred-octopus", "qty": 1}, {"key": "house-lemonade", "qty": 1}],
    )
    as_staff(client)

    kitchen = next(o for o in client.get("/api/orders", params={"station": "kitchen"}).json()
                   if o["id"] == order["id"])
    bar = next(o for o in client.get("/api/orders", params={"station": "bar"}).json()
               if o["id"] == order["id"])

    assert [i["name"] for i in kitchen["items"]] == ["Charred Octopus"]
    assert [i["name"] for i in bar["items"]] == ["House Lemonade"]
    # сума лишається сумою всього замовлення — це один чек, а не два
    assert kitchen["total_pence"] == bar["total_pence"] == order["total_pence"]


def test_queue_needs_a_session(client, db, venue):
    client.cookies.clear()
    assert client.get("/api/orders").status_code == 401


@pytest.mark.parametrize("target", ["accepted", "ready", "served"])
def test_anonymous_cannot_move_orders(client, db, venue, target):
    order, _ = paid_order(client, db)
    client.cookies.clear()
    r = client.post(f"/api/orders/{order['id']}/status", params={"target": target})
    assert r.status_code == 401
