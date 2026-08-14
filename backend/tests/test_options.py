"""Варіанти позиції: 50 мл чи пляшка, який смак, яке молоко.

Дві речі, які тут перевіряються найпильніше:

1. **Ціну рахує сервер.** Інакше пляшку за £230 можна було б замовити за
   ціною чарки, підмінивши один рядок у запиті з телефона.
2. **Вибір не можна пропустити.** «Мохіто» без смаку — це не замовлення, а
   загадка для бармена, і розбиратися з нею він буде посеред зміни.
"""

import uuid

from app.models import Order
from tests.test_orders import new_client_token, place


def line(key, qty=1, **options):
    return {"key": key, "qty": qty, "options": options}


# ------------------------------------------------------------- ціна --------


def test_bottle_costs_what_the_bottle_costs(client, db, venue):
    """50 мл — £13, 150 мл — £39, пляшка — £230. Це та сама позиція меню."""
    shot = place(client, db, items=[line("absolut", size="ml50")]).json()
    assert shot["total_pence"] == 1300

    triple = place(client, db, items=[line("absolut", size="ml150")]).json()
    assert triple["total_pence"] == 3900

    bottle = place(client, db, items=[line("absolut", size="bottle")]).json()
    assert bottle["total_pence"] == 23000


def test_price_is_taken_from_the_server_not_the_phone(client, db, venue):
    """Замовити пляшку за ціною чарки не вийде: ціну бере сервер із меню, а
    не з того, що надіслав браузер."""
    r = place(
        client,
        db,
        items=[{"key": "absolut", "qty": 1, "options": {"size": "bottle"},
                "unit_price_pence": 1, "price_pence": 1}],
    )
    assert r.status_code == 201
    assert r.json()["total_pence"] == 23000


def test_quantity_multiplies_the_chosen_variant(client, db, venue):
    order = place(client, db, items=[line("absolut", 3, size="bottle")]).json()
    assert order["total_pence"] == 69000


def test_choice_without_its_own_price_keeps_the_item_price(client, db, venue):
    """Смак мохіто ціну не змінює — усі коктейлі по £16."""
    for flavour in ("classic", "mango"):
        order = place(client, db, items=[line("mojito", flavour=flavour)]).json()
        assert order["total_pence"] == 1600


def test_two_groups_on_one_item(client, db, venue):
    """Маргарита: подача й смак — два різні питання до гостя."""
    order = place(
        client, db, items=[line("margarita", serve="crushed", flavour="passion")]
    ).json()
    assert order["total_pence"] == 1600
    assert sorted(order["items"][0]["options"]) == ["Crushed Ice", "Passion"]


# --------------------------------------------------- вибір обов'язковий ----


def test_missing_choice_is_refused(client, db, venue):
    """Мохіто без смаку до бару не доїде."""
    r = place(client, db, items=[{"key": "mojito", "qty": 1}])
    assert r.status_code == 422
    assert r.json()["detail"]["missing_option"] == "flavour"
    assert r.json()["detail"]["item"] == "mojito"


def test_half_answered_item_is_refused(client, db, venue):
    r = place(client, db, items=[line("margarita", serve="martini")])
    assert r.status_code == 422
    assert r.json()["detail"]["missing_option"] == "flavour"


def test_unknown_choice_is_refused(client, db, venue):
    r = place(client, db, items=[line("mojito", flavour="bubblegum")])
    assert r.status_code == 422


def test_unknown_group_is_refused(client, db, venue):
    r = place(client, db, items=[line("mojito", flavour="classic", size="bottle")])
    assert r.status_code == 422


def test_item_without_options_takes_none(client, db, venue):
    order = place(client, db, items=[{"key": "espresso", "qty": 1}]).json()
    assert order["total_pence"] == 400
    assert order["items"][0]["options"] == []


# ------------------------------------------------- що бачить бармен --------


def test_the_bar_sees_which_one_to_make(client, db, venue):
    """Головне, заради чого варіанти й з'явились: на марці видно, що робити."""
    from tests.test_permissions import as_staff

    ct = new_client_token()
    order = place(
        client, db,
        items=[line("mojito", 2, flavour="strawberry"), line("cappuccino", milk="soya")],
        client_token=ct,
    ).json()
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    client.post(f"/api/orders/{order['id']}/confirm-offline", params={"client_token": ct})

    as_staff(client)
    ticket = next(
        t for t in client.get("/api/orders", params={"station": "bar"}).json()
        if t["number"] == order["number"]
    )
    got = {i["name"]: i["options"] for i in ticket["items"]}
    assert got["Mojito"] == ["Strawberry"]
    assert got["Cappuccino"] == ["Soya"]


def test_the_choice_is_frozen_at_order_time(client, db, venue):
    """Знімок, як ціна й назва: завтра смак перейменують — чек не попливе."""
    from sqlalchemy import select

    from app.models import MenuItem
    from tests.test_permissions import as_owner

    order = place(client, db, items=[line("mojito", flavour="mango")]).json()

    as_owner(client)
    item = db.scalars(select(MenuItem).where(MenuItem.key == "mojito")).one()
    fresh_options = [
        {
            "key": "flavour",
            "label": "opt.flavour",
            "choices": [{"key": "mango", "name": "Alphonso Mango"}],
        }
    ]
    item.options = fresh_options
    db.commit()

    db.expire_all()
    stored = db.get(Order, uuid.UUID(order["id"]))
    assert stored.items[0].options_snapshot == ["Mango"]


def test_same_drink_different_flavours_are_separate_lines(client, db, venue):
    """Два мохіто різних смаків — дві позиції в замовленні, а не одна на два."""
    order = place(
        client, db,
        items=[line("mojito", flavour="classic"), line("mojito", flavour="mango")],
    ).json()
    assert len(order["items"]) == 2
    assert sorted(i["options"][0] for i in order["items"]) == ["Classic", "Mango"]
    assert order["total_pence"] == 3200
