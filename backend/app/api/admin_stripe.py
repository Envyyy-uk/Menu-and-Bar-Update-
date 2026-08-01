"""Підключення Stripe. Тільки `owner` — це його акаунт, його KYC, його спори."""

from __future__ import annotations

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
