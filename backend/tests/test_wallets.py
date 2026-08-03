"""Apple Pay, Google Pay і картка на нашій сторінці.

Мережі тут немає: справжній виклик Stripe підмінено. Перевіряємо саме те, що
належить нам — які параметри йдуть у намір платежу, що дістається браузеру
гостя, і головне правило, яке не змінилося: **успішний платіж у браузері не
робить замовлення оплаченим**. `paid` виставляє вебхук.

Чого перевірити тут неможливо й чесно сказано в docs/WALLETS.md: сама кнопка
гаманця. Вона залежить від пристрою, HTTPS і зареєстрованого домену — жодного
з цих трьох у тестовому середовищі немає.
"""

import uuid

import pytest

from app.core.config import settings
from app.models import Order
from app.services import stripe_gateway
from tests.test_orders import new_client_token, place
from tests.test_permissions import as_owner, as_staff
from tests.test_stripe import event, signed

ACCOUNT = "acct_test_venue"


class FakeIntent:
    def __init__(self, **kw):
        self.id = "pi_test_123"
        self.client_secret = "pi_test_123_secret_abc"
        self.kw = kw


@pytest.fixture()
def stripe_on(monkeypatch, db, venue):
    """Stripe «увімкнено», але жодного справжнього виклику не буде."""
    monkeypatch.setattr(settings, "stripe_secret_key", "sk_test_x")
    monkeypatch.setattr(settings, "stripe_publishable_key", "pk_test_x")
    monkeypatch.setattr(settings, "stripe_webhook_secret", "whsec_test_secret_for_tests_only")
    venue.stripe_account_id = ACCOUNT
    db.commit()

    calls: list[dict] = []

    def fake_create(**kw):
        calls.append(kw)
        return FakeIntent(**kw)

    monkeypatch.setattr(stripe_gateway.stripe.PaymentIntent, "create", staticmethod(fake_create))
    return calls


def paid_ready(client, db, items=None):
    ct = new_client_token()
    order = place(client, db, items=items, client_token=ct).json()
    return order, ct


# ------------------------------------------------------- намір платежу -----


def test_checkout_returns_a_secret_not_a_redirect(client, db, venue, stripe_on):
    """Гість лишається на нашій сторінці: замість посилання — client_secret."""
    order, ct = paid_ready(client, db)
    r = client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    assert r.status_code == 200

    body = r.json()
    assert body["mode"] == "stripe"
    assert body["client_secret"] == "pi_test_123_secret_abc"
    assert body["publishable_key"] == "pk_test_x"
    # Direct charge: без акаунта закладу Stripe.js не покаже гаманця
    assert body["account_id"] == ACCOUNT
    assert "url" not in body          # нікуди не перекидаємо

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).payment_intent_id == "pi_test_123"


def test_intent_asks_stripe_for_every_method_it_can_show(client, db, venue, stripe_on):
    """Apple Pay і Google Pay вмикаються не списком, а automatic_payment_methods:
    що показати саме цьому пристрою, вирішує Stripe."""
    order, ct = paid_ready(client, db)
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})

    kw = stripe_on[0]
    assert kw["automatic_payment_methods"] == {"enabled": True}
    assert kw["amount"] == order["total_pence"]
    assert kw["currency"] == "gbp"
    assert kw["metadata"]["order_id"] == order["id"]
    # Платіж живе на акаунті закладу, не платформи
    assert kw["stripe_account"] == ACCOUNT
    # Подвійний тап не має створити два платежі
    assert kw["idempotency_key"] == f"intent:{ct}"


def test_platform_fee_rides_along_only_when_set(client, db, venue, stripe_on, monkeypatch):
    order, ct = paid_ready(client, db)
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    assert "application_fee_amount" not in stripe_on[0]

    monkeypatch.setattr(settings, "platform_fee_bps", 250)
    order2, ct2 = paid_ready(client, db)
    client.post(f"/api/orders/{order2['id']}/checkout", params={"client_token": ct2})
    assert stripe_on[1]["application_fee_amount"] == max(
        1, round(order2["total_pence"] * 250 / 10_000)
    )


def test_offline_mode_never_hands_out_a_secret(client, db, venue):
    """Без ключів Stripe гість не бачить платіжної форми — і не має бачити."""
    order, ct = paid_ready(client, db)
    body = client.post(
        f"/api/orders/{order['id']}/checkout", params={"client_token": ct}
    ).json()
    assert body["mode"] == "offline"
    assert "client_secret" not in body


# ------------------------------------------- оплатив гаманець — платить вебхук


def test_wallet_payment_becomes_paid_only_through_the_webhook(
    client, db, venue, stripe_on
):
    """Гість натиснув Apple Pay, Stripe.js сказав «успіх» — для нас це ще не
    оплата. Замовлення рухає лише вебхук."""
    order, ct = paid_ready(client, db)
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "payment_pending"

    body, sig = signed(
        event(
            "payment_intent.succeeded",
            {
                "object": "payment_intent",
                "id": "pi_test_123",
                "metadata": {"order_id": order["id"]},
            },
        )
    )
    r = client.post(
        "/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig}
    )
    assert r.status_code == 200
    assert r.json()["status"] == "paid"

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "paid"


def test_declined_wallet_payment_does_not_reach_the_kitchen(client, db, venue, stripe_on):
    order, ct = paid_ready(client, db)
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})

    body, sig = signed(
        event(
            "payment_intent.payment_failed",
            {
                "object": "payment_intent",
                "id": "pi_test_123",
                "metadata": {"order_id": order["id"]},
            },
        )
    )
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})

    db.expire_all()
    assert db.get(Order, uuid.UUID(order["id"])).status == "failed"
    as_staff(client)
    assert all(r["number"] != order["number"] for r in client.get("/api/orders").json())


# ------------------------------------------------------- домен для Apple ----


def test_wallet_status_is_owner_only(client, db, venue):
    as_staff(client)
    assert client.get("/api/admin/stripe/wallets").status_code == 403
    assert client.post("/api/admin/stripe/wallets").status_code == 403


def test_wallet_status_is_honest_without_keys(client, db, venue):
    as_owner(client)
    body = client.get("/api/admin/stripe/wallets").json()
    assert body["enabled"] is False
    # У розробці база на http — і панель має сказати це прямо, бо саме через
    # це гаманця не буде на жодному пристрої.
    assert body["https"] is False


def test_apple_pay_domain_cannot_be_registered_over_http(client, db, venue, stripe_on):
    """Найтихіша вада гаманців: без HTTPS кнопки просто немає, без помилки.
    Тому відмовляємо голосно, а не мовчки реєструємо те, що не працюватиме."""
    as_owner(client)
    r = client.post("/api/admin/stripe/wallets")
    assert r.status_code == 422
    assert "HTTPS" in r.json()["detail"]
