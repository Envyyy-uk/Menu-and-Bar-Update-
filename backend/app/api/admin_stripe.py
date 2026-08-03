"""Підключення Stripe. Тільки `owner` — це його акаунт, його KYC, його спори."""

from __future__ import annotations

from urllib.parse import urlparse

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.deps import get_venue, require
from app.db import get_db
from app.models import User, Venue
from app.services import stripe_gateway
from app.services.audit import record
from app.services.stripe_gateway import StripeNotReady

router = APIRouter(prefix="/api/admin/stripe", tags=["admin"])


@router.get("")
def status(
    actor: User = Depends(require("stripe.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    if not settings.stripe_enabled:
        return {
            "enabled": False,
            "connected": False,
            "mode": "offline",
            "note": "STRIPE_SECRET_KEY не заданий: замовлення підтверджуються без оплати",
        }
    try:
        out = stripe_gateway.account_status(venue)
    except Exception as exc:  # noqa: BLE001 — Stripe може бути недоступний
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {"enabled": True, "mode": "stripe", "fee_bps": settings.platform_fee_bps, **out}


@router.post("/connect")
def connect(
    actor: User = Depends(require("stripe.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Створює Standard-акаунт (якщо його ще немає) і віддає посилання на
    онбординг. KYC заклад проходить сам — ми лише даємо двері."""
    try:
        out = stripe_gateway.account_link(venue)
    except StripeNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None

    if venue.stripe_account_id != out["account_id"]:
        record.write(
            db,
            venue_id=venue.id,
            user_id=actor.id,
            action="stripe.connect",
            entity=f"venue:{venue.key}",
            before={"account_id": venue.stripe_account_id},
            after={"account_id": out["account_id"]},
        )
        venue.stripe_account_id = out["account_id"]
        db.commit()
    return out


@router.get("/wallets")
def wallets(
    actor: User = Depends(require("stripe.manage")),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Стан Apple Pay / Google Pay.

    Найгірша вада гаманців — тиша: якщо домен не зареєстровано, кнопки Apple
    Pay просто немає, без жодної помилки. Тому панель має показувати це
    прямо, а не залишати зал гадати, чому в гостя нічого не з'явилось.
    """
    host = urlparse(settings.public_base_url).hostname or ""
    secure = settings.public_base_url.startswith("https://")
    if not settings.stripe_enabled:
        return {
            "enabled": False,
            "https": secure,
            "domain": host,
            "domains": [],
            "note": "STRIPE_SECRET_KEY не заданий: гаманці недоступні",
        }
    try:
        rows = stripe_gateway.wallet_domains(venue)
    except StripeNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception as exc:  # noqa: BLE001 — Stripe може бути недоступний
        raise HTTPException(status_code=503, detail=str(exc)) from None
    return {
        "enabled": True,
        # Без HTTPS гаманця не буде на жодному пристрої — це не наша перевірка,
        # а вимога Apple і Google.
        "https": secure,
        "domain": host,
        "registered": any(d["domain"] == host and d["enabled"] for d in rows),
        "domains": rows,
    }


@router.post("/wallets")
def register_wallet_domain(
    actor: User = Depends(require("stripe.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Реєструє домен закладу для Apple Pay.

    Google Pay цього не потребує — йому досить HTTPS.
    """
    host = urlparse(settings.public_base_url).hostname or ""
    if not host:
        raise HTTPException(status_code=422, detail="PUBLIC_BASE_URL без домену")
    if not settings.public_base_url.startswith("https://"):
        raise HTTPException(
            status_code=422,
            detail="Apple Pay вимагає HTTPS: зареєструвати http-домен неможливо",
        )
    try:
        out = stripe_gateway.register_wallet_domain(venue, host)
    except StripeNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception as exc:  # noqa: BLE001 — Stripe може бути недоступний
        raise HTTPException(status_code=503, detail=str(exc)) from None

    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="stripe.wallet_domain",
        entity=f"venue:{venue.key}",
        after={"domain": out["domain"], "enabled": out["enabled"]},
    )
    db.commit()
    return out
