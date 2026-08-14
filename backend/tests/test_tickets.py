"""Марки станцій.

Замовлення ділиться тільки за станціями — кухня й бар. Далі воно одне ціле:
кухня бачить увесь свій список одразу й сама вирішує, з чого починати. Черги
курсів немає, і команди залу кухня не чекає.

Те, що ділити станції все-таки треба, знайшлося на живому демо: «Прийнято» на
кухні рухало й бар. Але бар віддає напої за хвилину, а кухня смажить двадцять.
"""

import uuid

import pytest
from sqlalchemy import select

from app.models import Order, OrderTicket
from tests.test_orders import new_client_token, place
from tests.test_permissions import as_owner, as_staff

# У меню PODVAL кухонних позицій немає — їжа ще «Coming Soon», усе йде на
# бар. Розділення станцій від цього не зникло, тож тест сам переводить дві
# позиції на кухню замість того, щоб залежати від вмісту сідера.
KITCHEN_A = "tea-pot-special"
KITCHEN_B = "espresso"
DRINK = "corona"

FULL = [{"key": KITCHEN_A, "qty": 1}, {"key": KITCHEN_B, "qty": 1}, {"key": DRINK, "qty": 2}]


@pytest.fixture(autouse=True)
def two_stations(client, db, venue):
    """Дві позиції на кухню, решта — бар. Після тесту повертаємо як було."""
    from sqlalchemy import select as _select

    from app.models import MenuItem

    as_owner(client)
    ids = {}
    for key in (KITCHEN_A, KITCHEN_B):
        item = db.scalars(_select(MenuItem).where(MenuItem.key == key)).one()
        ids[key] = item.id
        client.patch(f"/api/admin/items/{item.id}", json={"station": "kitchen"})
    client.post("/api/auth/logout")
    yield
    as_owner(client)
    for key, item_id in ids.items():
        client.patch(f"/api/admin/items/{item_id}", json={"station": "bar"})
    client.post("/api/auth/logout")


def paid(client, db, items=None):
    ct = new_client_token()
    order = place(client, db, items=items or FULL, client_token=ct).json()
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    client.post(f"/api/orders/{order['id']}/confirm-offline", params={"client_token": ct})
    return order, ct


def tickets_of(client, station):
    return client.get("/api/orders", params={"station": station}).json()


def find(rows, number):
    return next(r for r in rows if r["number"] == number)


# ------------------------------------------------------ марки на станцію ---


def test_order_splits_by_station_only(client, db, venue):
    """Дві страви кухні — одна марка, а не дві. Меню одне ціле."""
    order, _ = paid(client, db)
    db.expire_all()
    rows = db.scalars(
        select(OrderTicket).where(OrderTicket.order_id == uuid.UUID(order["id"]))
    ).all()
    assert sorted(t.station for t in rows) == ["bar", "kitchen"]


def test_kitchen_sees_all_its_dishes_on_one_ticket(client, db, venue):
    order, _ = paid(client, db)
    as_staff(client)
    ticket = find(tickets_of(client, "kitchen"), order["number"])
    assert sorted(i["name"] for i in ticket["items"]) == ["Black Coffee · Espresso", "Tea Pot Special"]
    # напій на кухонну марку не потрапив
    assert all(i["station"] == "kitchen" for i in ticket["items"])


def test_kitchen_starts_without_anyone_s_permission(client, db, venue):
    """Ніякого «чекає команди залу»: марка прийшла — кухня береться."""
    order, _ = paid(client, db)
    as_staff(client)
    ticket = find(tickets_of(client, "kitchen"), order["number"])
    r = client.post(f"/api/orders/tickets/{ticket['id']}/status", params={"target": "accepted"})
    assert r.status_code == 200
    assert r.json()["status"] == "accepted"


def test_bar_finishing_does_not_finish_the_kitchen(client, db, venue):
    """Те, що знайшов користувач: бар віддав напої — кухня лишається в роботі."""
    order, _ = paid(client, db)
    as_staff(client)

    bar = find(tickets_of(client, "bar"), order["number"])
    for target in ("accepted", "ready", "served"):
        client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": target})

    kitchen = find(tickets_of(client, "kitchen"), order["number"])
    assert kitchen["status"] == "paid"          # кухні ніхто нічого не рухав

    db.expire_all()
    # бар усе віддав, але для гостя замовлення не «готове»: кухня ще працює
    assert db.get(Order, uuid.UUID(order["id"])).status == "accepted"


def test_kitchen_accept_does_not_touch_the_bar(client, db, venue):
    order, _ = paid(client, db)
    as_staff(client)

    kitchen = find(tickets_of(client, "kitchen"), order["number"])
    client.post(f"/api/orders/tickets/{kitchen['id']}/status", params={"target": "accepted"})

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


def test_drinks_only_order_has_no_kitchen_ticket(client, db, venue):
    order, _ = paid(client, db, items=[{"key": DRINK, "qty": 1}])
    as_staff(client)
    assert all(r["number"] != order["number"] for r in tickets_of(client, "kitchen"))
    assert find(tickets_of(client, "bar"), order["number"])["status"] == "paid"


# ------------------------------------------------- статус для гостя й залу -


def test_guest_sees_the_slowest_ticket(client, db, venue):
    order, ct = paid(client, db)
    as_staff(client)
    kitchen = find(tickets_of(client, "kitchen"), order["number"])
    bar = find(tickets_of(client, "bar"), order["number"])

    client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": "accepted"})
    client.post(f"/api/orders/tickets/{kitchen['id']}/status", params={"target": "accepted"})
    client.post("/api/auth/logout")

    guest = client.get(f"/api/orders/{order['id']}", params={"client_token": ct}).json()
    # хтось узявся до роботи — для гостя це вже «готується»
    assert guest["status"] == "accepted"
    assert len(guest["tickets"]) == 2


def test_order_is_ready_only_when_every_station_is(client, db, venue):
    """«Готово» — лише коли всі. Інакше офіціант понесе половину."""
    order, _ = paid(client, db)
    as_staff(client)

    bar = find(tickets_of(client, "bar"), order["number"])
    for target in ("accepted", "ready"):
        client.post(f"/api/orders/tickets/{bar['id']}/status", params={"target": target})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "accepted"

    kitchen = find(tickets_of(client, "kitchen"), order["number"])
    for target in ("accepted", "ready"):
        client.post(f"/api/orders/tickets/{kitchen['id']}/status", params={"target": target})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "ready"


def test_panel_moves_the_whole_order(client, db, venue):
    """Менеджер рухає замовлення цілком — свідома «важка» дія, і вона тягне
    за собою всі марки."""
    order, _ = paid(client, db)
    as_owner(client)
    r = client.post(f"/api/orders/{order['id']}/status", params={"target": "accepted"})
    assert r.status_code == 200

    db.expire_all()
    rows = db.scalars(
        select(OrderTicket).where(OrderTicket.order_id == uuid.UUID(order["id"]))
    ).all()
    assert {t.status for t in rows} == {"accepted"}


def test_no_fire_endpoint_left(client, db, venue):
    """Запуск курсу знято разом із курсами — офіціант більше нічого не
    підтверджує, і шлях не має воскреснути «про всяк випадок»."""
    from app.main import app

    assert not any(getattr(r, "path", "").endswith("/fire") for r in app.routes)

    order, _ = paid(client, db)
    as_staff(client)
    ticket = find(tickets_of(client, "kitchen"), order["number"])
    # 405, а не 404: на «/» висить статика, і POST у будь-який неіснуючий
    # шлях упирається саме в неї. Головне — що запит не проходить.
    assert client.post(f"/api/orders/tickets/{ticket['id']}/fire").status_code == 405
