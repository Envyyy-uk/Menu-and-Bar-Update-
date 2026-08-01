from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.deps import get_venue, require
from app.db import get_db
from app.models import (
    STATUS_ACCEPTED,
    STATUS_PAID,
    STATUS_PAYMENT_PENDING,
    STATUS_READY,
    STATUS_SERVED,
    MenuItem,
    Order,
    OrderItem,
    Table,
    User,
    Venue,
)
from app.services.audit import record
from app.services.orders import (
    Line,
    OrderError,
    create_order,
    get_for_guest,
    order_payload,
    station_payload,
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
        # Stripe Checkout приходить у Спринті 6.
        raise HTTPException(status_code=501, detail="stripe checkout is not wired yet")
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
    return order_payload(order, _table_label(db, order))


# ------------------------------------------------------------------ зал ---
@router.get("")
def queue(
    station: str | None = Query(default=None, pattern="^(kitchen|bar)$"),
    actor: User = Depends(require("orders.view")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    """Черга станції. Замовлення потрапляє сюди **тільки** після `paid`."""
    orders = db.scalars(
        select(Order)
        .where(Order.venue_id == venue.id, Order.status.in_(LIVE_STATUSES))
        .order_by(Order.created_at)
    ).all()
    out = []
    for order in orders:
        label = _table_label(db, order)
        if station:
            payload = station_payload(order, station, label)
            if payload:
                out.append(payload)
        else:
            out.append(order_payload(order, label))
    return out


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
    return order_payload(order, _table_label(db, order))
