"""Stripe Connect, тип акаунта — Standard.

Чому Standard: кожен заклад має власний повноцінний акаунт, сам проходить
KYC, сам володіє дашбордом, і **спори й від'ємні баланси — його
відповідальність**, не платформи. Це головна причина вибору, а не зручність.

Платіж проводиться як **direct charge** на акаунті закладу (заголовок
`Stripe-Account`), з `application_fee_amount` на користь платформи.

Дані картки ніколи не торкаються нашого сервера: поля малює Stripe.js у
своєму фреймі, ми бачимо лише `client_secret`. Це утримує нас у межах SAQ A.
Одна власна форма для номера картки — і це повний аудит PCI.

Apple Pay й Google Pay вмикаються не тут: це `automatic_payment_methods`
плюс три речі поза кодом — HTTPS, увімкнені гаманці в дашборді закладу й
зареєстрований домен (для Apple). Див. `docs/WALLETS.md`.
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


def create_payment_intent(venue: Venue, order: Order) -> dict[str, Any]:
    """Намір платежу для оплати **на нашій сторінці**.

    Раніше гість ішов на сторінку Stripe. Але гість сидить за столом із
    телефоном у руці: перекидати його на чужий домен, щоб він повернувся
    назад, — зайвий крок, на якому губляться замовлення. Тепер картка й
    гаманці живуть у тому ж аркуші, де кошик.

    `automatic_payment_methods` — це і є Apple Pay з Google Pay: Stripe сам
    вирішує, що показати саме цьому пристрою. Вмикати їх окремо в коді не
    треба (і не можна) — вони залежать від пристрою, браузера й того, що
    ввімкнено в дашборді закладу.

    Номер картки й далі не торкається нашого сервера: поля малює Stripe.js,
    ми бачимо тільки `client_secret`. Межі SAQ A не змінилися.
    """
    _ready(venue)

    params: dict[str, Any] = {
        "amount": order.total_pence,
        "currency": venue.currency.lower(),
        "automatic_payment_methods": {"enabled": True},
        "metadata": {"order_id": str(order.id), "venue_id": str(venue.id)},
        # Гість бачить це в застосунку гаманця й у виписці
        "description": f"{venue.name} · замовлення №{order.number}",
    }
    fee = platform_fee_pence(order.total_pence)
    if fee:
        params["application_fee_amount"] = fee

    intent = stripe.PaymentIntent.create(
        **params,
        # Той самий кошик не має створити два платежі, якщо запит повторився
        idempotency_key=f"intent:{order.client_token}",
        # Direct charge: платіж живе на акаунті закладу
        stripe_account=venue.stripe_account_id,
    )
    return {
        "id": intent.id,
        "client_secret": intent.client_secret,
        # Ключ і акаунт потрібні Stripe.js: при direct charge елементи
        # створюються від імені закладу, інакше гаманець не з'явиться.
        "publishable_key": settings.stripe_publishable_key,
        "account_id": venue.stripe_account_id,
    }


def register_wallet_domain(venue: Venue, domain: str) -> dict[str, Any]:
    """Реєстрація домену для Apple Pay.

    Apple вимагає довести, що сайт наш: інакше кнопки просто не буде — без
    помилки й без пояснення. Для direct charge домен реєструється на акаунті
    закладу, а не платформи.

    Google Pay такої реєстрації не потребує — йому достатньо HTTPS.
    """
    _ready(venue)
    out = stripe.PaymentMethodDomain.create(
        domain_name=domain,
        stripe_account=venue.stripe_account_id,
    )
    apple = getattr(out, "apple_pay", None) or {}
    return {
        "id": out.id,
        "domain": out.domain_name,
        "enabled": bool(getattr(out, "enabled", False)),
        # Stripe каже прямо, чому саме гаманець не працює — передаємо як є
        "apple_pay": dict(apple) if apple else {},
    }


def wallet_domains(venue: Venue) -> list[dict[str, Any]]:
    _ready(venue)
    rows = stripe.PaymentMethodDomain.list(stripe_account=venue.stripe_account_id)
    return [
        {
            "id": d.id,
            "domain": d.domain_name,
            "enabled": bool(getattr(d, "enabled", False)),
        }
        for d in rows.data
    ]


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
