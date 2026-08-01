"""Матриця прав розділу 9 — і на рівні функції, і на живих ендпойнтах.

Критерій спринту: `staff` отримує 403 на цінах, поверненнях і створенні
акаунтів.
"""

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.core.permissions import can, can_assign_role, refund_limit_pence
from app.models import MenuItem, User
from app.models.user import ROLE_HEAD_MANAGER, ROLE_MANAGER, ROLE_OWNER, ROLE_STAFF

# --------------------------------------------------------------- матриця ---


@pytest.mark.parametrize(
    "role,permission,expected",
    [
        (ROLE_STAFF, "orders.status", True),
        (ROLE_STAFF, "items.state", True),  # 86 — так
        (ROLE_STAFF, "items.edit", False),  # ціни — ні
        (ROLE_STAFF, "refunds", False),
        (ROLE_STAFF, "reports", False),
        (ROLE_STAFF, "users.create", False),
        (ROLE_MANAGER, "items.edit", True),
        (ROLE_MANAGER, "refunds", True),
        (ROLE_MANAGER, "users.create", False),
        (ROLE_MANAGER, "audit.view", False),
        (ROLE_HEAD_MANAGER, "users.create", True),
        (ROLE_HEAD_MANAGER, "audit.view", True),
        (ROLE_HEAD_MANAGER, "stripe.manage", False),
        (ROLE_OWNER, "stripe.manage", True),
        (ROLE_OWNER, "venue.delete", True),
    ],
)
def test_matrix(role, permission, expected):
    assert can(role, permission) is expected


def test_unknown_permission_is_denied():
    """Друкарська помилка в назві права не має відкривати ендпойнт усім."""
    assert can(ROLE_OWNER, "items.editt") is False


@pytest.mark.parametrize(
    "actor,target,allowed",
    [
        (ROLE_OWNER, ROLE_HEAD_MANAGER, True),
        (ROLE_OWNER, ROLE_OWNER, False),  # рівну власній — ні
        (ROLE_HEAD_MANAGER, ROLE_MANAGER, True),
        (ROLE_HEAD_MANAGER, ROLE_HEAD_MANAGER, False),
        (ROLE_HEAD_MANAGER, ROLE_OWNER, False),
        (ROLE_MANAGER, ROLE_STAFF, False),  # manager акаунтів не створює
        (ROLE_STAFF, ROLE_STAFF, False),
    ],
)
def test_nobody_assigns_a_role_at_or_above_their_own(actor, target, allowed):
    assert can_assign_role(actor, target) is allowed


def test_refund_ceilings():
    limit = settings.manager_refund_limit_pence
    assert refund_limit_pence(ROLE_OWNER, limit) is None
    assert refund_limit_pence(ROLE_HEAD_MANAGER, limit) is None
    assert refund_limit_pence(ROLE_MANAGER, limit) == limit
    # єдина дія, якою співробітник міг би вивести гроші — тож нуль
    assert refund_limit_pence(ROLE_STAFF, limit) == 0


# ------------------------------------------------------------ ендпойнти ---


def as_owner(client):
    r = client.post(
        "/api/auth/login",
        json={"email": settings.seed_owner_email, "password": settings.seed_owner_password},
    )
    assert r.status_code == 200
    return r.json()


def as_staff(client):
    """Заводимо пристрій від owner, виходимо, заходимо PIN-ом як зал."""
    as_owner(client)
    client.post("/api/admin/devices", json={"label": f"tablet-{id(client)}"})
    client.post("/api/auth/logout")
    r = client.post("/api/auth/pin", json={"pin": settings.seed_staff_pin})
    assert r.status_code == 200, r.text
    return r.json()


def first_item(db):
    return db.scalars(select(MenuItem).order_by(MenuItem.position)).first()


def test_staff_gets_403_on_prices(client, db, venue):
    item = first_item(db)
    as_staff(client)
    r = client.patch(f"/api/admin/items/{item.id}", json={"price_pence": 100})
    assert r.status_code == 403
    assert "items.edit" in r.json()["detail"]
    db.expire_all()
    assert db.get(MenuItem, item.id).price_pence != 100


def test_staff_gets_403_on_creating_accounts(client, db, venue):
    as_staff(client)
    r = client.post("/api/admin/users", json={"name": "Ghost", "role": ROLE_MANAGER})
    assert r.status_code == 403
    assert client.get("/api/admin/users").status_code == 403
    assert client.get("/api/admin/audit").status_code == 403
    assert client.post("/api/admin/devices", json={"label": "x"}).status_code == 403


def test_staff_can_86_an_item(client, db, venue):
    """Те, заради чого зал взагалі логіниться: вимкнути позицію за десять
    секунд — можна, чіпнути ціну — ні."""
    item = first_item(db)
    as_staff(client)
    r = client.patch(f"/api/admin/items/{item.id}", json={"state": "off"})
    assert r.status_code == 200, r.text
    db.expire_all()
    assert db.get(MenuItem, item.id).state == "off"


def test_mixed_patch_is_refused_whole(client, db, venue):
    """Один запит, два поля: дозволене й заборонене. Проходити не має нічого."""
    item = first_item(db)
    as_owner(client)
    client.patch(f"/api/admin/items/{item.id}", json={"state": "auto"})
    db.expire_all()
    before_price = db.get(MenuItem, item.id).price_pence
    client.post("/api/auth/logout")

    as_staff(client)
    r = client.patch(f"/api/admin/items/{item.id}", json={"state": "off", "price_pence": 1})
    assert r.status_code == 403
    db.expire_all()
    fresh = db.get(MenuItem, item.id)
    assert fresh.price_pence == before_price
    assert fresh.state == "auto"  # дозволене поле теж не пройшло


def test_anonymous_cannot_touch_admin(client, db, venue):
    client.cookies.clear()
    item = first_item(db)
    assert client.patch(f"/api/admin/items/{item.id}", json={"state": "off"}).status_code == 401
    assert client.get("/api/admin/users").status_code == 401


def test_head_manager_creates_staff_but_not_a_peer(client, db, venue):
    as_owner(client)
    r = client.post(
        "/api/admin/users",
        json={
            "name": "Head",
            "role": ROLE_HEAD_MANAGER,
            "email": "head@example.com",
            "password": "head-password-1",
        },
    )
    assert r.status_code == 201, r.text
    client.post("/api/auth/logout")

    client.post("/api/auth/login", json={"email": "head@example.com", "password": "head-password-1"})
    ok = client.post("/api/admin/users", json={"name": "Waiter", "role": ROLE_STAFF, "with_pin": True})
    assert ok.status_code == 201
    assert len(ok.json()["pin"]) == 6  # показується один раз

    peer = client.post(
        "/api/admin/users",
        json={"name": "Another head", "role": ROLE_HEAD_MANAGER, "email": "h2@example.com"},
    )
    assert peer.status_code == 403


def test_last_owner_cannot_be_demoted_or_deleted(client, db, venue):
    as_owner(client)
    owner = db.scalars(select(User).where(User.role == ROLE_OWNER)).one()
    assert client.patch(f"/api/admin/users/{owner.id}", json={"role": ROLE_MANAGER}).status_code == 409
    assert client.patch(f"/api/admin/users/{owner.id}", json={"active": False}).status_code == 409
    assert client.delete(f"/api/admin/users/{owner.id}").status_code == 409


def test_price_change_lands_in_the_audit_log(client, db, venue):
    """Менеджер бачить, хто й коли змінив ціну."""
    item = first_item(db)
    as_owner(client)
    client.patch(f"/api/admin/items/{item.id}", json={"price_pence": 1234})
    rows = client.get("/api/admin/audit").json()
    entry = next(r for r in rows if r["entity"] == f"item:{item.key}")
    assert entry["after"]["price_pence"] == 1234
    assert entry["before"]["price_pence"] != 1234
    assert entry["who"] == "Owner"
