"""Stripe Connect: вебхуки, ідемпотентність, повернення, звірка.

Мережі тут немає й не потрібно. Перевіряємо саме те, що належить нам:
підпис вебхука, ідемпотентність за `stripe_event_id`, і головне правило —
`paid` виставляється **тільки** з вебхука, ніколи з відповіді браузера.
"""

import json
import time
import uuid
from datetime import timedelta

import pytest
from sqlalchemy import select

from app.core.config import settings
from app.models import STATUS_PAID, Order, Venue, WebhookEvent, utcnow
from app.services import reconcile
from app.services.stripe_gateway import platform_fee_pence
from tests.test_orders import new_client_token, place
from tests.test_permissions import as_owner, as_staff

WEBHOOK_SECRET = "whsec_test_secret_for_tests_only"


@pytest.fixture()
def stripe_secret(monkeypatch):
    """Вмикаємо перевірку підпису, не вмикаючи справжніх ключів."""
    monkeypatch.setattr(settings, "stripe_webhook_secret", WEBHOOK_SECRET)
    return WEBHOOK_SECRET


def signed(payload: dict, secret: str = WEBHOOK_SECRET, timestamp: int | None = None):
    """Той самий підпис, що шле Stripe: t=…,v1=HMAC-SHA256(t.payload)."""
    import hashlib
    import hmac

    body = json.dumps(payload).encode()
    ts = timestamp or int(time.time())
    signature = hmac.new(secret.encode(), f"{ts}.".encode() + body, hashlib.sha256).hexdigest()
    return body, f"t={ts},v1={signature}"


def event(kind: str, obj: dict, event_id: str | None = None) -> dict:
    return {
        "id": event_id or f"evt_{uuid.uuid4().hex[:24]}",
        "type": kind,
        "data": {"object": obj},
    }


def draft_order(client, db, items=None):
    ct = new_client_token()
    order = place(client, db, items=items, client_token=ct).json()
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    return order, ct


# ------------------------------------------------- головне правило спринту -


def test_paid_comes_only_from_the_webhook(client, db, venue, stripe_secret):
    """Тест «із закритим браузером»: після checkout гість зникає. Замовлення
    стає `paid` виключно тому, що прийшов вебхук."""
    order, ct = draft_order(client, db)
    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "payment_pending"

    # Гість закрив браузер: жодного запиту від нього більше не буде.
    client.cookies.clear()

    body, sig = signed(
        event(
            "checkout.session.completed",
            {
                "object": "checkout.session",
                "id": "cs_test_1",
                "payment_intent": "pi_test_1",
                "metadata": {"order_id": order["id"]},
            },
        )
    )
    r = client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    assert r.status_code == 200
    assert r.json()["status"] == "paid"

    db.expire_all()
    fresh = db.get(Order, uuid.UUID(order["id"]))
    assert fresh.status == STATUS_PAID
    assert fresh.paid_at is not None
    assert fresh.payment_intent_id == "pi_test_1"


def test_guest_cannot_declare_itself_paid(client, db, venue, monkeypatch):
    """З увімкненим Stripe ендпойнт «підтвердити без оплати» закритий."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    order, ct = draft_order(client, db)
    r = client.post(f"/api/orders/{order['id']}/confirm-offline", params={"client_token": ct})
    assert r.status_code == 409
    assert "вебхуком" in r.json()["detail"]
    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status != STATUS_PAID


def test_unsigned_webhook_moves_nothing(client, db, venue, stripe_secret):
    order, _ = draft_order(client, db)
    body = json.dumps(
        event("checkout.session.completed", {"metadata": {"order_id": order["id"]}})
    ).encode()

    for headers in ({}, {"Stripe-Signature": "t=1,v1=deadbeef"}):
        r = client.post("/api/webhooks/stripe", content=body, headers=headers)
        assert r.status_code == 400

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status != STATUS_PAID


def test_old_signature_is_refused(client, db, venue, stripe_secret):
    """Захист від повторного програвання перехопленого запиту."""
    order, _ = draft_order(client, db)
    body, sig = signed(
        event("checkout.session.completed", {"metadata": {"order_id": order["id"]}}),
        timestamp=int(time.time()) - 3600,
    )
    r = client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    assert r.status_code == 400


# ----------------------------------------------------- ідемпотентність -----


def test_repeated_delivery_is_a_no_op(client, db, venue, stripe_secret):
    """Stripe повторює доставку за дизайном. Повтор не має ні дублювати
    роботу, ні падати."""
    order, _ = draft_order(client, db)
    payload = event(
        "checkout.session.completed",
        {
            "object": "checkout.session",
            "id": "cs_test_2",
            "payment_intent": "pi_test_2",
            "metadata": {"order_id": order["id"]},
        },
    )
    body, sig = signed(payload)

    first = client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    assert first.json()["status"] == "paid"

    for _ in range(3):
        again = client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
        assert again.status_code == 200
        assert again.json()["status"] == "duplicate"

    stored = db.scalars(
        select(WebhookEvent).where(WebhookEvent.stripe_event_id == payload["id"])
    ).all()
    assert len(stored) == 1

    db.expire_all()
    fresh = db.get(Order, uuid.UUID(order["id"]))
    assert fresh.status == STATUS_PAID
    paid_at = fresh.paid_at
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    db.expire_all()
    # час оплати не «оновлюється» від повторної доставки
    assert db.get(Order, uuid.UUID(order["id"])).paid_at == paid_at


def test_webhook_for_a_guest_who_never_reached_checkout(client, db, venue, stripe_secret):
    """Гість міг оплатити й закрити вкладку, не дійшовши до нашого
    /checkout — замовлення тоді ще в draft. Це нормальний шлях."""
    ct = new_client_token()
    order = place(client, db, client_token=ct).json()
    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "draft"

    body, sig = signed(
        event(
            "payment_intent.succeeded",
            {"object": "payment_intent", "id": "pi_test_3", "metadata": {"order_id": order["id"]}},
        )
    )
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == STATUS_PAID


def test_failed_payment_marks_the_order(client, db, venue, stripe_secret):
    order, _ = draft_order(client, db)
    body, sig = signed(
        event(
            "payment_intent.payment_failed",
            {"object": "payment_intent", "id": "pi_test_4", "metadata": {"order_id": order["id"]}},
        )
    )
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "failed"


def test_unknown_order_does_not_crash_the_webhook(client, db, venue, stripe_secret):
    body, sig = signed(
        event("checkout.session.completed", {"metadata": {"order_id": str(uuid.uuid4())}})
    )
    r = client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    assert r.status_code == 200
    assert r.json()["status"] == "ignored"


# ---------------------------------------------------------- повернення -----


def paid_order(client, db, stripe_secret, items=None):
    order, _ = draft_order(client, db, items=items)
    body, sig = signed(
        event(
            "checkout.session.completed",
            {
                "object": "checkout.session",
                "id": f"cs_{uuid.uuid4().hex[:12]}",
                "payment_intent": f"pi_{uuid.uuid4().hex[:12]}",
                "metadata": {"order_id": order["id"]},
            },
        )
    )
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})
    return order


def test_staff_cannot_refund(client, db, venue, stripe_secret):
    order = paid_order(client, db, stripe_secret)
    as_staff(client)
    r = client.post(f"/api/orders/{order['id']}/refund", json={"amount_pence": 100})
    assert r.status_code == 403
    assert "refunds" in r.json()["detail"]


def test_manager_hits_the_ceiling(client, db, venue, stripe_secret):
    # Замовлення навмисно дороге за стелю manager (£50) — інакше спрацювала б
    # перевірка «сума більша за залишок», а не сама стеля.
    order = paid_order(client, db, stripe_secret, items=[{"key": "braised-short-rib", "qty": 4}])
    assert order["total_pence"] > settings.manager_refund_limit_pence
    as_owner(client)
    client.post(
        "/api/admin/users",
        json={
            "name": "Manager",
            "role": "manager",
            "email": f"m{uuid.uuid4().hex[:6]}@example.com",
            "password": "manager-password-1",
        },
    )
    email = client.get("/api/admin/users").json()
    email = next(u["email"] for u in email if u["role"] == "manager" and u["email"])
    client.post("/api/auth/logout")
    client.post("/api/auth/login", json={"email": email, "password": "manager-password-1"})

    over = client.post(
        f"/api/orders/{order['id']}/refund",
        json={"amount_pence": settings.manager_refund_limit_pence + 1},
    )
    assert over.status_code == 403
    assert "ліміт" in over.json()["detail"]

    ok = client.post(f"/api/orders/{order['id']}/refund", json={"amount_pence": 100})
    assert ok.status_code == 200


def test_owner_has_no_ceiling_and_refund_is_audited(client, db, venue, stripe_secret):
    order = paid_order(client, db, stripe_secret)
    as_owner(client)
    r = client.post(f"/api/orders/{order['id']}/refund", json={"reason": "розлили"})
    assert r.status_code == 200

    db.expire_all()
    fresh = db.get(Order, uuid.UUID(order["id"]))
    assert fresh.refunded_pence == fresh.total_pence
    assert fresh.status == "refunded"

    entry = next(
        row for row in client.get("/api/admin/audit").json() if row["action"] == "order.refund"
    )
    assert entry["who"] == "Owner"
    assert entry["after"]["reason"] == "розлили"


def test_refund_cannot_exceed_the_total(client, db, venue, stripe_secret):
    order = paid_order(client, db, stripe_secret)
    as_owner(client)
    r = client.post(
        f"/api/orders/{order['id']}/refund", json={"amount_pence": order["total_pence"] + 1}
    )
    assert r.status_code == 422


def test_charge_refunded_webhook_updates_the_order(client, db, venue, stripe_secret):
    order = paid_order(client, db, stripe_secret)
    db.expire_all()
    intent = db.get(Order, uuid.UUID(order["id"])).payment_intent_id

    body, sig = signed(
        event(
            "charge.refunded",
            {
                "object": "charge",
                "payment_intent": intent,
                "amount_refunded": order["total_pence"],
            },
        )
    )
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})

    db.expire_all()
    fresh = db.get(Order, uuid.UUID(order["id"]))
    assert fresh.refunded_pence == order["total_pence"]
    assert fresh.status == "refunded"


# ------------------------------------------------------------- звірка ------


def test_reconcile_flags_paid_orders_nobody_accepted(client, db, venue, stripe_secret):
    """Найгірший сценарій у системі: гість заплатив, кухня не побачила.
    Через 60 секунд це має стати гучним, а не лишитися тихим."""
    order = paid_order(client, db, stripe_secret)
    row = db.get(Order, uuid.UUID(order["id"]))
    db.expire_all()
    row = db.get(Order, uuid.UUID(order["id"]))
    row.paid_at = utcnow() - timedelta(seconds=settings.reconcile_alert_after_seconds + 5)
    db.commit()

    late = reconcile.sweep(db)
    assert any(str(o.id) == order["id"] for o in late)

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).alerted_at is not None

    as_staff(client)
    alerts = client.get("/api/orders/alerts").json()
    assert any(a["id"] == order["id"] for a in alerts)
    assert alerts[0]["paid_seconds_ago"] >= settings.reconcile_alert_after_seconds

    # Прийняли — і з алертів зникло
    client.post(f"/api/orders/{order['id']}/status", params={"target": "accepted"})
    assert all(a["id"] != order["id"] for a in client.get("/api/orders/alerts").json())


def test_fresh_paid_order_is_not_flagged(client, db, venue, stripe_secret):
    order = paid_order(client, db, stripe_secret)
    assert all(str(o.id) != order["id"] for o in reconcile.late_orders(db))


# --------------------------------------------------------------- комісія ---


@pytest.mark.parametrize(
    "bps,total,expected",
    [(0, 2500, 0), (100, 2500, 25), (250, 1000, 25), (100, 10, 1)],
)
def test_platform_fee(monkeypatch, bps, total, expected):
    monkeypatch.setattr(settings, "platform_fee_bps", bps)
    assert platform_fee_pence(total) == expected


def test_stripe_status_is_owner_only(client, db, venue):
    as_staff(client)
    assert client.get("/api/admin/stripe").status_code == 403
    assert client.post("/api/admin/stripe/connect").status_code == 403

    as_owner(client)
    body = client.get("/api/admin/stripe").json()
    assert body["enabled"] is False
    assert body["mode"] == "offline"


def test_connect_without_keys_is_honest(client, db, venue):
    as_owner(client)
    r = client.post("/api/admin/stripe/connect")
    assert r.status_code == 503
    assert "не налаштований" in r.json()["detail"]
