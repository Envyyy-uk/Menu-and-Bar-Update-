"""Stripe Connect, тип акаунта — Standard.

Чому Standard: кожен заклад має власний повноцінний акаунт, сам проходить
KYC, сам володіє дашбордом, і **спори й від'ємні баланси — його
відповідальність**, не платформи. Це головна причина вибору, а не зручність.

Платіж проводиться як **direct charge** на акаунті закладу (заголовок
`Stripe-Account`), з `application_fee_amount` на користь платформи.

Дані картки ніколи не торкаються нашого сервера: тільки Stripe Checkout.
Це утримує нас у межах SAQ A. Одна власна форма для номера картки — і це
повний аудит PCI.
"""

from __future__ import annotations

from typing import Any

import stripe

from app.core.config import settings
from app.models import Order, Venue


class StripeNotReady(Exception):
    pass


def _ready(venue: Venue) -> None:
    if not settings.stripe_enabled:
        raise StripeNotReady("Stripe не налаштований")
    if not venue.stripe_account_id:
        raise StripeNotReady("заклад не підключив Stripe")
    stripe.api_key = settings.stripe_secret_key


def platform_fee_pence(total_pence: int) -> int:
    """Комісія платформи в базисних пунктах. Нуль — беремо нуль за замовлення
    (модель заробітку ще не вибрана, розділ 17 плану)."""
    if settings.platform_fee_bps <= 0:
        return 0
    return max(1, round(total_pence * settings.platform_fee_bps / 10_000))


def create_checkout_session(venue: Venue, order: Order, table_token: str) -> dict[str, Any]:
    _ready(venue)

    line_items = [
        {
            "price_data": {
                "currency": venue.currency.lower(),
                "unit_amount": item.unit_price_pence,
                "product_data": {"name": item.name_snapshot},
            },
            "quantity": item.qty,
        }
        for item in order.items
    ]

    payment_intent_data: dict[str, Any] = {
        "metadata": {"order_id": str(order.id), "venue_id": str(venue.id)},
    }
    fee = platform_fee_pence(order.total_pence)
    if fee:
        payment_intent_data["application_fee_amount"] = fee

    base = settings.public_base_url.rstrip("/")
    session = stripe.checkout.Session.create(
        mode="payment",
        line_items=line_items,
        payment_intent_data=payment_intent_data,
        metadata={"order_id": str(order.id)},
        client_reference_id=str(order.id),
        success_url=f"{base}/t/{table_token}?order={order.id}",
        cancel_url=f"{base}/t/{table_token}?cancelled={order.id}",
        # Той самий кошик не має створити два платежі, якщо запит повторився
        idempotency_key=f"checkout:{order.client_token}",
        # Direct charge: платіж живе на акаунті закладу
        stripe_account=venue.stripe_account_id,
    )
    return {"id": session.id, "url": session.url}


def refund(venue: Venue, order: Order, amount_pence: int, reason: str | None = None) -> dict[str, Any]:
    _ready(venue)
    if not order.payment_intent_id:
        raise StripeNotReady("у замовлення немає платежу")
    out = stripe.Refund.create(
        payment_intent=order.payment_intent_id,
        amount=amount_pence,
        metadata={"order_id": str(order.id), "reason": reason or ""},
        # Повторний клік по «повернути» не має повернути гроші двічі
        idempotency_key=f"refund:{order.id}:{order.refunded_pence + amount_pence}",
        stripe_account=venue.stripe_account_id,
    )
    return {"id": out.id, "amount": out.amount, "status": out.status}


def account_link(venue: Venue) -> dict[str, Any]:
    """Посилання на онбординг Standard-акаунта. KYC проходить заклад — ми
    лише даємо йому двері."""
    if not settings.stripe_enabled:
        raise StripeNotReady("Stripe не налаштований")
    stripe.api_key = settings.stripe_secret_key
    base = settings.public_base_url.rstrip("/")

    account_id = venue.stripe_account_id
    if not account_id:
        account = stripe.Account.create(type="standard", metadata={"venue_id": str(venue.id)})
        account_id = account.id

    link = stripe.AccountLink.create(
        account=account_id,
        refresh_url=f"{base}/admin/",
        return_url=f"{base}/admin/",
        type="account_onboarding",
    )
    return {"account_id": account_id, "url": link.url}


def account_status(venue: Venue) -> dict[str, Any]:
    if not settings.stripe_enabled or not venue.stripe_account_id:
        return {"connected": False, "charges_enabled": False}
    stripe.api_key = settings.stripe_secret_key
    account = stripe.Account.retrieve(venue.stripe_account_id)
    return {
        "connected": True,
        "account_id": account.id,
        "charges_enabled": bool(account.charges_enabled),
        "payouts_enabled": bool(account.payouts_enabled),
    }


def verify_event(payload: bytes, signature: str) -> dict[str, Any]:
    """Підпис перевіряємо завжди. Незапитаний POST на вебхук — це просто
    чужий запит, і він не має рухати замовлення."""
    if not settings.stripe_webhook_secret:
        raise StripeNotReady("STRIPE_WEBHOOK_SECRET не заданий")
    event = stripe.Webhook.construct_event(
        payload=payload, sig_header=signature, secret=settings.stripe_webhook_secret
    )
    return event
