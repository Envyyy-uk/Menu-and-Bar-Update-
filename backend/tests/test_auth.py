"""Вхід персоналу: пошта+пароль для менеджерів, PIN на зареєстрованому
пристрої для залу."""

from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import Device, User, utcnow
from app.models.user import ROLE_OWNER, ROLE_STAFF


def login_owner(client):
    r = client.post(
        "/api/auth/login",
        json={"email": settings.seed_owner_email, "password": settings.seed_owner_password},
    )
    assert r.status_code == 200, r.text
    return r.json()


def test_owner_logs_in_with_password(client):
    me = login_owner(client)
    assert me["role"] == ROLE_OWNER
    assert "stripe.manage" in me["permissions"]
    assert me["refund_limit_pence"] is None  # без стелі


def test_wrong_password_and_unknown_email_look_the_same(client):
    a = client.post("/api/auth/login", json={"email": settings.seed_owner_email, "password": "nope"})
    b = client.post("/api/auth/login", json={"email": "ghost@example.com", "password": "nope"})
    assert a.status_code == b.status_code == 401
    # інакше форма входу перетворюється на список співробітників
    assert a.json()["detail"] == b.json()["detail"]


def test_me_requires_a_session(client):
    client.cookies.clear()
    assert client.get("/api/auth/me").status_code == 401


def test_logout_closes_the_session(client):
    login_owner(client)
    assert client.get("/api/auth/me").status_code == 200
    client.post("/api/auth/logout")
    assert client.get("/api/auth/me").status_code == 401


def test_pin_without_registered_device_is_refused(client):
    client.cookies.clear()
    r = client.post("/api/auth/pin", json={"pin": settings.seed_staff_pin})
    assert r.status_code == 403
    assert "пристрій" in r.json()["detail"]


def test_pin_works_on_a_registered_device(client, db, venue):
    login_owner(client)
    r = client.post("/api/admin/devices", json={"label": "Kitchen tablet 2"})
    assert r.status_code == 201
    client.post("/api/auth/logout")

    # cookie пристрою лишилася в клієнті — саме так це й працює в залі
    r = client.post("/api/auth/pin", json={"pin": settings.seed_staff_pin})
    assert r.status_code == 200, r.text
    me = r.json()
    assert me["role"] == ROLE_STAFF
    assert me["refund_limit_pence"] == 0  # до грошей не допускається взагалі


def test_five_wrong_pins_lock_the_device(client, db, venue):
    login_owner(client)
    created = client.post("/api/admin/devices", json={"label": "Bar tablet"}).json()
    client.post("/api/auth/logout")

    for _ in range(settings.pin_max_attempts):
        assert client.post("/api/auth/pin", json={"pin": "000000"}).status_code == 401

    # після ліміту пристрій вимкнено — правильний PIN уже не проходить
    r = client.post("/api/auth/pin", json={"pin": settings.seed_staff_pin})
    assert r.status_code == 403

    db.expire_all()
    device = db.scalars(select(Device).where(Device.device_token == created["device_token"])).one()
    assert device.active is False

    login_owner(client)
    actions = [row["action"] for row in client.get("/api/admin/audit").json()]
    assert "device.locked" in actions
    assert actions.count("pin.failed") >= settings.pin_max_attempts


def test_session_expires(client, db, venue):
    login_owner(client)
    from app.models import Session as SessionRow

    row = db.scalars(select(SessionRow).order_by(SessionRow.created_at.desc())).first()
    row.expires_at = utcnow() - timedelta(minutes=1)
    db.commit()
    assert client.get("/api/auth/me").status_code == 401


@pytest.mark.parametrize("owner_pin", [True])
def test_owner_cannot_be_given_a_pin(client, db, venue, owner_pin):
    """За роллю owner — Stripe і видалення закладу. Шість цифр до цього
    не допускаються."""
    login_owner(client)
    owner = db.scalars(select(User).where(User.role == ROLE_OWNER)).first()
    r = client.post(f"/api/admin/users/{owner.id}/pin")
    assert r.status_code in (403, 422)
