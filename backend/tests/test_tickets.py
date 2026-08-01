"""Марки станцій і черговість курсів.

Дві речі, які були зламані й знайшлися на живому демо:

1. «Прийнято» на кухні рухало й бар. Але станції працюють із різною
   швидкістю: бар віддає напої за хвилину, кухня смажить основне двадцять.
2. Кухня отримувала все підряд — закуски й основне разом. Подача так не
   працює: поки не віддали закуски, основне не починають.
"""

import uuid

from sqlalchemy import select

from app.models import MenuItem, Order, OrderTicket
from tests.test_orders import new_client_token, place, token
from tests.test_permissions import as_owner, as_staff

# закуска (кухня, курс 1), основне (кухня, курс 2), напій (бар, курс 0)
STARTER = "charred-octopus"
MAIN = "braised-short-rib"
DRINK = "house-lemonade"

FULL = [{"key": STARTER, "qty": 1}, {"key": MAIN, "qty": 1}, {"key": DRINK, "qty": 2}]


def paid(client, db, items=None):
    ct = new_client_token()
    order = place(client, db, items=items or FULL, client_token=ct).json()
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    client.post(f"/api/orders/{order['id']}/confirm-offline", params={"client_token": ct})
    return order, ct


def tickets_of(client, station):
    return client.get("/api/orders", params={"station": station}).json()


def find(rows, number, course=None):
    return next(r for r in rows if r["number"] == number and (course is None or r["course"] == course))


# ------------------------------------------------------ марки на станцію ---


def test_order_splits_into_tickets(client, db, venue):
    order, _ = paid(client, db)
    db.expire_all()
    rows = db.scalars(
        select(OrderTicket).where(OrderTicket.order_id == uuid.UUID(order["id"]))
    ).all()
    assert sorted((t.station, t.course) for t in rows) == [
        ("bar", 0),
        ("kitchen", 1),
        ("kitchen", 2),
    ]


def test_bar_finishing_does_not_finish_the_kitchen(client, db, venue):
    """Те, що знайшов користувач: бар віддав напої — кухня лишається в роботі."""
    order, _ = paid(client, db)
    as_staff(client)

    bar = find(tickets_of(client, "bar"), order["number"])
    client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": "accepted"})
    client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": "ready"})
    client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": "served"})

    kitchen = tickets_of(client, "kitchen")
    starter = find(kitchen, order["number"], course=1)
    assert starter["status"] == "paid"          # кухні ніхто нічого не рухав

    db.expire_all()
    # бар усе віддав, але для гостя замовлення не «готове»: кухня ще працює
    assert db.get(Order, uuid.UUID(order["id"])).status == "accepted"


def test_kitchen_accept_does_not_touch_the_bar(client, db, venue):
    order, _ = paid(client, db)
    as_staff(client)

    starter = find(tickets_of(client, "kitchen"), order["number"], course=1)
    client.post(f"/api/orders/tickets/{starter['id']}/status", params={"target": "accepted"})

    bar = find(tickets_of(client, "bar"), order["number"])
    assert bar["status"] == "paid"


def test_served_ticket_leaves_its_own_queue_only(client, db, venue):
    order, _ = paid(client, db)
    as_staff(client)
    bar = find(tickets_of(client, "bar"), order["number"])
    for target in ("accepted", "ready", "served"):
        client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": target})

    assert all(r["number"] != order["number"] for r in tickets_of(client, "bar"))
    assert any(r["number"] == order["number"] for r in tickets_of(client, "kitchen"))


# ---------------------------------------------------------- черга курсів ---


def test_mains_wait_for_the_starters(client, db, venue):
    order, _ = paid(client, db)
    as_staff(client)

    rows = tickets_of(client, "kitchen")
    starter = find(rows, order["number"], course=1)
    main = find(rows, order["number"], course=2)

    assert starter["blocked_by_course"] is None
    assert main["blocked_by_course"] == 1

    refused = client.post(f"/api/orders/tickets/{main['id']}/status", params={"target": "accepted"})
    assert refused.status_code == 409
    assert refused.json()["detail"]["blocked_by_course"] == 1

    # віддали закуски — основне розблокувалося
    client.post(f"/api/orders/tickets/{starter['id']}/status", params={"target": "accepted"})
    client.post(f"/api/orders/tickets/{starter['id']}/status", params={"target": "ready"})

    main = find(tickets_of(client, "kitchen"), order["number"], course=2)
    assert main["blocked_by_course"] is None
    ok = client.post(f"/api/orders/tickets/{main['id']}/status", params={"target": "accepted"})
    assert ok.status_code == 200


def test_drinks_never_wait(client, db, venue):
    """Напої — курс 0: вони нікого не чекають, їх несуть одразу."""
    order, _ = paid(client, db)
    as_staff(client)
    bar = find(tickets_of(client, "bar"), order["number"])
    assert bar["course"] == 0
    assert bar["blocked_by_course"] is None
    assert client.post(
        f"/api/orders/tickets/{bar['id']}/status", params={"target": "accepted"}
    ).status_code == 200


def test_single_course_order_is_not_blocked(client, db, venue):
    order, _ = paid(client, db, items=[{"key": MAIN, "qty": 1}])
    as_staff(client)
    main = find(tickets_of(client, "kitchen"), order["number"], course=2)
    # закусок у замовленні немає — чекати нема на що
    assert main["blocked_by_course"] is None
    assert client.post(
        f"/api/orders/tickets/{main['id']}/status", params={"target": "accepted"}
    ).status_code == 200


# ------------------------------------------------- статус для гостя й залу -


def test_guest_sees_the_slowest_ticket(client, db, venue):
    order, ct = paid(client, db)
    as_staff(client)
    rows = tickets_of(client, "kitchen")
    starter = find(rows, order["number"], course=1)
    bar = find(tickets_of(client, "bar"), order["number"])

    client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": "accepted"})
    client.post(f"/api/orders/tickets/{starter['id']}/status", params={"target": "accepted"})
    client.post("/api/auth/logout")

    guest = client.get(f"/api/orders/{order['id']}", params={"client_token": ct}).json()
    # хтось узявся до роботи — для гостя це вже «готується»
    assert guest["status"] == "accepted"
    assert len(guest["tickets"]) == 3


def test_panel_moves_the_whole_order(client, db, venue):
    """Менеджер рухає замовлення цілком — свідома «важка» дія, і вона тягне
    за собою всі марки, включно з тими, що чекали своєї черги."""
    order, _ = paid(client, db)
    as_owner(client)
    r = client.post(f"/api/orders/{order['id']}/status", params={"target": "accepted"})
    assert r.status_code == 200

    db.expire_all()
    rows = db.scalars(
        select(OrderTicket).where(OrderTicket.order_id == uuid.UUID(order["id"]))
    ).all()
    assert {t.status for t in rows} == {"accepted"}


def test_course_is_editable_only_with_items_edit(client, db, venue):
    item = db.scalars(select(MenuItem).where(MenuItem.key == DRINK)).one()
    as_staff(client)
    assert client.patch(f"/api/admin/items/{item.id}", json={"course": 2}).status_code == 403

    as_owner(client)
    assert client.patch(f"/api/admin/items/{item.id}", json={"course": 9}).status_code == 422
    assert client.patch(f"/api/admin/items/{item.id}", json={"course": 2}).status_code == 200
    db.expire_all()
    assert db.get(MenuItem, item.id).course == 2
    client.patch(f"/api/admin/items/{item.id}", json={"course": 0})


def test_course_snapshot_survives_menu_changes(client, db, venue):
    """Курс, як ціна й назва, знімається на момент замовлення."""
    order, _ = paid(client, db, items=[{"key": STARTER, "qty": 1}])
    as_owner(client)
    item = db.scalars(select(MenuItem).where(MenuItem.key == STARTER)).one()
    client.patch(f"/api/admin/items/{item.id}", json={"course": 3})

    db.expire_all()
    fresh = db.get(Order, uuid.UUID(order["id"]))
    assert fresh.items[0].course_snapshot == 1
    assert [t.course for t in fresh.tickets] == [1]

    client.patch(f"/api/admin/items/{item.id}", json={"course": 1})


def test_order_is_ready_only_when_every_station_is(client, db, venue):
    """«Готово» — лише коли всі. Інакше офіціант понесе половину."""
    order, _ = paid(client, db)
    as_staff(client)

    bar = find(tickets_of(client, "bar"), order["number"])
    for target in ("accepted", "ready"):
        client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": target})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "accepted"

    for course in (1, 2):
        ticket = find(tickets_of(client, "kitchen"), order["number"], course=course)
        for target in ("accepted", "ready"):
            client.post(f"/api/orders/tickets/{ticket['id']}/status", params={"target": target})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "ready"
