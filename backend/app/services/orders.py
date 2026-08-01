"""Замовлення: створення, машина станів, наявність у момент оплати.

Два правила, які не порушуються:

1. Замовлення з'являється на екрані кухні **тільки** після `paid`, і `paid`
   виставляється **тільки** з вебхука Stripe — ніколи з відповіді браузера
   гостя. Клієнт може збрехати або обірватися; вебхук — ні.
2. Повторний POST з тим самим `client_token` повертає **те саме** замовлення,
   а не створює друге. Подвійний тап і обрив мережі — це та сама ситуація.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ALLOWED_TRANSITIONS,
    STATUS_ACCEPTED,
    STATUS_PAID,
    STATUS_READY,
    STATUS_SERVED,
    MenuItem,
    Order,
    OrderItem,
    Table,
    Venue,
    utcnow,
)
from app.services.menu import schedules_map
from app.services.schedule import availability_of, venue_now


class OrderError(Exception):
    def __init__(self, message: str, status: int = 400, payload: dict[str, Any] | None = None):
        super().__init__(message)
        self.message = message
        self.status = status
        self.payload = payload or {}


@dataclass
class Line:
    key: str
    qty: int


def _table(db: Session, venue: Venue, token: str) -> Table:
    table = db.scalars(
        select(Table).where(Table.venue_id == venue.id, Table.token == token)
    ).first()
    if table is None or not table.active:
        raise OrderError("невідомий стіл", status=404)
    return table


def unavailable_lines(db: Session, venue: Venue, lines: list[Line]) -> list[dict[str, Any]]:
    """Що з кошика зараз не можна замовити — і чому.

    Перевіряється на сервері й **у момент оплати**, а не при рендері меню:
    позицію можуть вимкнути, поки гість тримає її в кошику.
    """
    now = venue_now(venue.timezone)
    schedules = schedules_map(db, venue.id)
    keys = [line.key for line in lines]
    items = {
        i.key: i
        for i in db.scalars(
            select(MenuItem).where(MenuItem.venue_id == venue.id, MenuItem.key.in_(keys))
        ).all()
    }

    problems: list[dict[str, Any]] = []
    for line in lines:
        item = items.get(line.key)
        if item is None or not item.active:
            problems.append({"key": line.key, "reason": "unknown"})
            continue
        if not item.orderable:
            # Межа v1: алкоголь видно в меню, але він не замовляється —
            # вік перевіряють при подачі.
            problems.append({"key": line.key, "name": item.name, "reason": item.orderable_reason or "not_orderable"})
            continue
        av = availability_of(
            state=item.state,
            schedule_key=item.schedule_key,
            opens_at=item.opens_at,
            hidden_when_closed=item.hidden_when_closed,
            schedules=schedules,
            now=now,
        )
        if not av.open:
            problems.append({"key": line.key, "name": item.name, "reason": av.reason})
    return problems


def find_by_client_token(db: Session, venue: Venue, client_token: str) -> Order | None:
    return db.scalars(
        select(Order).where(Order.venue_id == venue.id, Order.client_token == client_token)
    ).first()


def create_order(
    db: Session,
    venue: Venue,
    *,
    table_token: str,
    client_token: str,
    lines: list[Line],
    note: str | None = None,
) -> tuple[Order, bool]:
    """Повертає (замовлення, created). `created=False` — це вже було.

    Ідемпотентність тримається на унікальному індексі (venue_id,
    client_token), а не на перевірці «а чи є вже»: два запити можуть прийти
    одночасно, і перевірка їх не рятує.
    """
    existing = find_by_client_token(db, venue, client_token)
    if existing is not None:
        return existing, False

    if not lines:
        raise OrderError("порожнє замовлення", status=422)

    table = _table(db, venue, table_token)

    problems = unavailable_lines(db, venue, lines)
    if problems:
        raise OrderError(
            "частина позицій зараз недоступна", status=409, payload={"unavailable": problems}
        )

    items = {
        i.key: i
        for i in db.scalars(
            select(MenuItem).where(
                MenuItem.venue_id == venue.id, MenuItem.key.in_([line.key for line in lines])
            )
        ).all()
    }

    next_number = (
        db.scalar(select(func.max(Order.number)).where(Order.venue_id == venue.id)) or 0
    ) + 1

    order = Order(
        venue_id=venue.id,
        table_id=table.id,
        number=next_number,
        client_token=client_token,
        note=(note or "").strip() or None,
    )
    total = 0
    for line in lines:
        item = items[line.key]
        qty = max(1, min(line.qty, 99))
        total += item.price_pence * qty
        # Знімок на момент замовлення: меню зміниться — історія не попливе.
        order.items.append(
            OrderItem(
                menu_item_id=item.id,
                qty=qty,
                unit_price_pence=item.price_pence,
                name_snapshot=item.name,
                station_snapshot=item.station,
            )
        )
    order.total_pence = total
    db.add(order)

    try:
        db.commit()
    except IntegrityError:
        # Два однакові запити прийшли одночасно — виграв інший. Це не помилка,
        # це рівно те, заради чого існує client_token.
        db.rollback()
        duplicate = find_by_client_token(db, venue, client_token)
        if duplicate is None:
            raise
        return duplicate, False

    db.refresh(order)
    return order, True


def transition(db: Session, order: Order, target: str) -> Order:
    """Єдине місце, де змінюється статус. Усе поза мапою переходів — помилка,
    а не «ну майже»."""
    allowed = ALLOWED_TRANSITIONS.get(order.status, ())
    if target == order.status:
        return order  # повторне натискання на кухні нічого не ламає
    if target not in allowed:
        raise OrderError(
            f"перехід {order.status} → {target} не дозволений", status=409
        )
    order.status = target
    now = utcnow()
    if target == STATUS_PAID:
        order.paid_at = now
    elif target == STATUS_ACCEPTED:
        order.accepted_at = now
    elif target == STATUS_READY:
        order.ready_at = now
    elif target == STATUS_SERVED:
        order.served_at = now
    return order


def order_payload(order: Order, table_label: str | None = None) -> dict[str, Any]:
    return {
        "id": str(order.id),
        "number": order.number,
        "status": order.status,
        "table": table_label,
        "total_pence": order.total_pence,
        "note": order.note,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "accepted_at": order.accepted_at.isoformat() if order.accepted_at else None,
        "ready_at": order.ready_at.isoformat() if order.ready_at else None,
        "items": [
            {
                "name": i.name_snapshot,
                "qty": i.qty,
                "unit_price_pence": i.unit_price_pence,
                "station": i.station_snapshot,
            }
            for i in order.items
        ],
    }


def station_payload(order: Order, station: str, table_label: str | None) -> dict[str, Any] | None:
    """Той самий чек, але лише з позиціями однієї станції. Кухня не має
    бачити коктейлі, бар — стейки."""
    lines = [i for i in order.items if i.station_snapshot == station]
    if not lines:
        return None
    payload = order_payload(order, table_label)
    payload["items"] = [
        {
            "name": i.name_snapshot,
            "qty": i.qty,
            "unit_price_pence": i.unit_price_pence,
            "station": i.station_snapshot,
        }
        for i in lines
    ]
    payload["station"] = station
    return payload


def get_for_guest(db: Session, venue: Venue, order_id: uuid.UUID, client_token: str) -> Order:
    order = db.get(Order, order_id)
    # Знання id недостатньо: без свого токена гість не читає чуже замовлення.
    if order is None or order.venue_id != venue.id or order.client_token != client_token:
        raise OrderError("замовлення не знайдено", status=404)
    return order
