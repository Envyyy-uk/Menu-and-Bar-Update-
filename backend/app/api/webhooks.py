"""Вебхуки Stripe.

Тут — і тільки тут — замовлення стає `paid`. Відповідь браузера гостя ніколи
не є підтвердженням оплати: клієнт може збрехати або обірватися, вебхук — ні.

Обробник ідемпотентний за `stripe_event_id`: вставка в `webhook_events` з
`ON CONFLICT DO NOTHING`. Stripe повторює доставку за дизайном, і повтор не
має ні дублювати роботу, ні падати.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session as DbSession

from app.db import get_db
from app.models import (
    STATUS_FAILED,
    STATUS_PAID,
    STATUS_PAYMENT_PENDING,
    STATUS_REFUNDED,
    Order,
    WebhookEvent,
)
from app.services import realtime
from app.services.audit import record
from app.services.orders import transition
from app.services.stripe_gateway import StripeNotReady, verify_event

router = APIRouter(prefix="/api/webhooks", tags=["webhooks"])


def _already_processed(db: DbSession, event_id: str, event_type: str) -> bool:
    """True — цю подію вже обробляли. Гонка двох доставок ловиться самою
    базою, а не перевіркою «а чи є вже».

    Результат читаємо через RETURNING, а не через `rowcount`: psycopg тут
    віддає -1, і перевірка на нуль мовчки пропускала б кожен повтор.
    """
    inserted = db.execute(
        insert(WebhookEvent)
        .values(stripe_event_id=event_id, type=event_type)
        .on_conflict_do_nothing(index_elements=["stripe_event_id"])
        .returning(WebhookEvent.stripe_event_id)
    ).first()
    return inserted is None


def _order_from(db: DbSession, obj: dict) -> Order | None:
    metadata = obj.get("metadata") or {}
    raw_id = metadata.get("order_id") or obj.get("client_reference_id")
    if raw_id:
        try:
            order = db.get(Order, uuid.UUID(raw_id))
        except ValueError:
            order = None
        if order is not None:
            return order

    # Запасний шлях: подія про сам платіж без нашої метадати
    intent = obj.get("payment_intent") or (obj.get("id") if obj.get("object") == "payment_intent" else None)
    if intent:
        from sqlalchemy import select

        return db.scalars(select(Order).where(Order.payment_intent_id == intent)).first()
    return None


@router.post("/stripe")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default="", alias="Stripe-Signature"),
    db: DbSession = Depends(get_db),
) -> dict:
    payload = await request.body()
    try:
        event = verify_event(payload, stripe_signature)
    except StripeNotReady as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from None
    except Exception:
        # Підпис не зійшовся — це просто чужий запит.
        raise HTTPException(status_code=400, detail="невірний підпис") from None

    event_id = event["id"]
    event_type = event["type"]
    obj = event["data"]["object"]

    if _already_processed(db, event_id, event_type):
        db.commit()
        return {"status": "duplicate", "id": event_id}

    order = _order_from(db, obj)
    handled = "ignored"

    if order is not None:
        if event_type in ("checkout.session.completed", "payment_intent.succeeded"):
            intent = obj.get("payment_intent") or obj.get("id")
            if intent:
                order.payment_intent_id = intent
            if obj.get("object") == "checkout.session":
                order.checkout_session_id = obj.get("id")
            # Гість міг закрити браузер, не дійшовши до нашого /checkout —
            # тоді замовлення ще в draft, і це нормальний шлях, а не помилка.
            if order.status not in (STATUS_PAID,):
                if order.status != STATUS_PAYMENT_PENDING:
                    transition(db, order, STATUS_PAYMENT_PENDING)
                transition(db, order, STATUS_PAID)
            handled = "paid"

        elif event_type in ("payment_intent.payment_failed", "checkout.session.expired"):
            if order.status in (STATUS_PAYMENT_PENDING, "draft"):
                transition(db, order, STATUS_FAILED)
            handled = "failed"

        elif event_type in ("charge.refunded", "refund.created"):
            refunded = obj.get("amount_refunded")
            if refunded is None:
                refunded = obj.get("amount", 0)
            order.refunded_pence = max(order.refunded_pence, int(refunded or 0))
            if order.refunded_pence >= order.total_pence and order.status != STATUS_REFUNDED:
                transition(db, order, STATUS_REFUNDED)
            handled = "refunded"

        record.write(
            db,
            venue_id=order.venue_id,
            user_id=None,
            action=f"webhook.{handled}",
            entity=f"order:{order.number}",
            after={"event": event_type, "status": order.status},
        )

    db.commit()
    if order is not None and handled != "ignored":
        # Кухня дізнається про оплату тієї ж секунди, а не наступним опитуванням
        realtime.publish(
            {"type": "order.new" if handled == "paid" else f"order.{handled}", "number": order.number}
        )
    return {"status": handled, "id": event_id}
