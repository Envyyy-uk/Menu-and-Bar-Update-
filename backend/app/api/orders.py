from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.deps import current_user, get_venue, require
from app.core.permissions import refund_limit_pence
from app.db import get_db
from app.models import (
    STATUS_ACCEPTED,
    STATUS_PAID,
    STATUS_PAYMENT_PENDING,
    STATUS_READY,
    STATUS_REFUNDED,
    STATUS_SERVED,
    MenuItem,
    Order,
    OrderItem,
    OrderTicket,
    Table,
    User,
    Venue,
    utcnow,
)
from app.services import realtime, stripe_gateway
from app.services.audit import record
from app.services.reconcile import late_orders
from app.services.stripe_gateway import StripeNotReady
from app.services.orders import (
    Line,
    OrderError,
    create_order,
    get_for_guest,
    order_payload,
    ticket_payload,
    ticket_transition,
    transition,
    unavailable_lines,
)

router = APIRouter(prefix="/api/orders", tags=["orders"])

LIVE_STATUSES = (STATUS_PAID, STATUS_ACCEPTED, STATUS_READY)


class LineIn(BaseModel):
    key: str
    qty: int = Field(default=1, ge=1, le=99)


class OrderIn(BaseModel):
    table_token: str
    # Генерується телефоном гостя. Той самий токен = те саме замовлення.
    client_token: str = Field(min_length=8, max_length=80)
    items: list[LineIn]
    note: str | None = None


def _fail(exc: OrderError):
    raise HTTPException(status_code=exc.status, detail={"message": exc.message, **exc.payload})


def _table_label(db: DbSession, order: Order) -> str | None:
    if order.table_id is None:
        return None
    table = db.get(Table, order.table_id)
    return table.label if table else None


@router.post("", status_code=201)
def place_order(
    body: OrderIn,
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Подвійний тап і обрив мережі — це та сама ситуація: той самий
    `client_token` повертає те саме замовлення, і 200 замість 201."""
    try:
        order, created = create_order(
            db,
            venue,
            table_token=body.table_token,
            client_token=body.client_token,
            lines=[Line(key=i.key, qty=i.qty) for i in body.items],
            note=body.note,
        )
    except OrderError as exc:
        _fail(exc)
    payload = order_payload(order, _table_label(db, order))
    payload["created"] = created
    payload["payment_mode"] = "stripe" if settings.stripe_enabled else "offline"
    return payload


@router.get("/alerts")
def alerts(
    actor: User = Depends(require("orders.view")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    """Оплачені й не прийняті довше за норму. Це те, через що екран кухні
    має кричати, а не мовчати."""
    return [
        {
            **order_payload(o, _table_label(db, o)),
            "paid_seconds_ago": int((utcnow() - o.paid_at).total_seconds()),
        }
        for o in late_orders(db)
        if o.venue_id == venue.id
    ]


@router.get("/{order_id}")
def guest_order(
    order_id: uuid.UUID,
    client_token: str = Query(min_length=8),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Сторінка «готується» для гостя після оплати."""
    try:
        order = get_for_guest(db, venue, order_id, client_token)
    except OrderError as exc:
        _fail(exc)
    return order_payload(order, _table_label(db, order))


@router.post("/{order_id}/checkout")
def checkout(
    order_id: uuid.UUID,
    client_token: str = Query(min_length=8),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Наявність перевіряється саме тут — у момент створення платежу, а не
    при рендері меню. Якщо позиція випала, оплата не проводиться, і гість
    бачить, що саме."""
    try:
        order = get_for_guest(db, venue, order_id, client_token)
        # Перевіряємо за ключами позицій, а не за знімками назв: назву могли
        # відредагувати, поки кошик лежав відкритим.
        lines = [
            Line(key=key, qty=qty)
            for key, qty in db.execute(
                select(MenuItem.key, OrderItem.qty)
                .join(MenuItem, MenuItem.id == OrderItem.menu_item_id)
                .where(OrderItem.order_id == order.id)
            ).all()
        ]
        problems = unavailable_lines(db, venue, lines)
        if problems:
            raise OrderError(
                "частина позицій зараз недоступна", status=409, payload={"unavailable": problems}
            )
        transition(db, order, STATUS_PAYMENT_PENDING)
        db.commit()
    except OrderError as exc:
        _fail(exc)

    if settings.stripe_enabled:
        try:
            table = db.get(Table, order.table_id)
            session = stripe_gateway.create_checkout_session(venue, order, table.token)
        except StripeNotReady as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
        order.checkout_session_id = session["id"]
        db.commit()
        # Далі гість іде на сторінку Stripe. Назад він повернеться вже після
        # оплати, але `paid` виставить вебхук, а не це повернення.
        return {"mode": "stripe", "url": session["url"], "session_id": session["id"]}
    return {"mode": "offline", "order": order_payload(order, _table_label(db, order))}


@router.post("/{order_id}/confirm-offline")
def confirm_offline(
    order_id: uuid.UUID,
    client_token: str = Query(min_length=8),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Оплата «повз касу» — **лише** коли Stripe не налаштований.

    Це режим розробки й фейкового сервісу з розділу 15: замовлення на нуль
    фунтів у домашній мережі. Щойно в `.env` з'являється ключ Stripe, цей
    ендпойнт відповідає 409 — і `paid` можна виставити тільки вебхуком.
    """
    if settings.stripe_enabled:
        raise HTTPException(
            status_code=409,
            detail="Stripe увімкнено: paid виставляється лише вебхуком",
        )
    try:
        order = get_for_guest(db, venue, order_id, client_token)
        if order.status == STATUS_PAYMENT_PENDING:
            transition(db, order, STATUS_PAID)
        record.write(
            db,
            venue_id=venue.id,
            user_id=None,
            action="order.paid_offline",
            entity=f"order:{order.number}",
            after={"total_pence": order.total_pence},
        )
        db.commit()
    except OrderError as exc:
        _fail(exc)
    realtime.publish({"type": "order.new", "number": order.number})
    return order_payload(order, _table_label(db, order))


# ------------------------------------------------------------------ зал ---
@router.get("")
def queue(
    station: str | None = Query(default=None, pattern="^(kitchen|bar)$"),
    actor: User = Depends(require("orders.view")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    """Черга станції — це **марки**, а не замовлення цілком.

    Кухня й бар працюють із різною швидкістю, тож у кожного свій рядок і свій
    статус. Без станції (панель) віддаємо замовлення як єдине ціле.

    Сюди потрапляє **тільки** оплачене.
    """
    orders = db.scalars(
        select(Order)
        .where(Order.venue_id == venue.id, Order.status.in_(LIVE_STATUSES))
        .order_by(Order.created_at)
    ).all()

    out = []
    for order in orders:
        label = _table_label(db, order)
        if not station:
            out.append(order_payload(order, label))
            continue
        tickets = [t for t in order.tickets if t.station == station]
        for ticket in sorted(tickets, key=lambda t: t.course):
            if ticket.status == STATUS_SERVED:
                continue
            out.append(ticket_payload(order, ticket, label))
    return out


@router.post("/tickets/{ticket_id}/status")
def set_ticket_status(
    ticket_id: uuid.UUID,
    target: str = Query(pattern="^(accepted|ready|served)$"),
    actor: User = Depends(require("orders.status")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Кнопка на екрані кухні рухає **свою** марку, а не все замовлення.

    Тому «Готово» в барі не робить готовим те, що кухня ще смажить.
    """
    ticket = db.get(OrderTicket, ticket_id)
    if ticket is None:
        raise HTTPException(status_code=404, detail="марку не знайдено")
    order = db.get(Order, ticket.order_id)
    if order is None or order.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="замовлення не знайдено")

    status_map = {"accepted": STATUS_ACCEPTED, "ready": STATUS_READY, "served": STATUS_SERVED}
    try:
        ticket_transition(order, ticket, status_map[target])
    except OrderError as exc:
        _fail(exc)
    db.commit()
    realtime.publish({"type": "order.status", "number": order.number, "status": order.status})
    return ticket_payload(order, ticket, _table_label(db, order))


class RefundIn(BaseModel):
    amount_pence: int | None = Field(default=None, ge=1)
    reason: str | None = None


@router.post("/{order_id}/refund")
def refund_order(
    order_id: uuid.UUID,
    body: RefundIn,
    actor: User = Depends(require("refunds")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Повернення — єдина дія, якою співробітник може вивести гроші, тож у
    `manager` вона має стелю. Перевіряється тут, на сервері."""
    order = db.get(Order, order_id)
    if order is None or order.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="замовлення не знайдено")

    remaining = order.total_pence - order.refunded_pence
    if remaining <= 0:
        raise HTTPException(status_code=409, detail="повертати нічого")
    amount = body.amount_pence or remaining
    if amount > remaining:
        raise HTTPException(status_code=422, detail="сума більша за залишок")

    ceiling = refund_limit_pence(actor.role, settings.manager_refund_limit_pence)
    if ceiling is not None and amount > ceiling:
        raise HTTPException(
            status_code=403,
            detail=f"ліміт повернення для вашої ролі — {ceiling / 100:.2f}",
        )

    if settings.stripe_enabled:
        try:
            stripe_gateway.refund(venue, order, amount, body.reason)
        except StripeNotReady as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from None
        # Підсумковий стан виставить вебхук charge.refunded — так само, як
        # і з оплатою, ми не віримо власній відповіді Stripe наосліп.
    else:
        order.refunded_pence += amount
        if order.refunded_pence >= order.total_pence:
            transition(db, order, STATUS_REFUNDED)

    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="order.refund",
        entity=f"order:{order.number}",
        after={"amount_pence": amount, "reason": body.reason},
    )
    db.commit()
    return order_payload(order, _table_label(db, order))


@router.post("/{order_id}/status")
def set_status(
    order_id: uuid.UUID,
    target: str = Query(pattern="^(accepted|ready|served)$"),
    actor: User = Depends(require("orders.status")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    order = db.get(Order, order_id)
    if order is None or order.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="замовлення не знайдено")
    status_map = {"accepted": STATUS_ACCEPTED, "ready": STATUS_READY, "served": STATUS_SERVED}
    try:
        transition(db, order, status_map[target])
    except OrderError as exc:
        _fail(exc)
    db.commit()
    realtime.publish({"type": "order.status", "number": order.number, "status": order.status})
    return order_payload(order, _table_label(db, order))
