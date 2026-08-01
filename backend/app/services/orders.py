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

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models import (
    ALLOWED_TRANSITIONS,
    STATUS_ACCEPTED,
    STATUS_PAID,
    STATUS_READY,
    STATUS_SERVED,
    TICKET_ORDER,
    MenuItem,
    Order,
    OrderItem,
    OrderTicket,
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

    # Атомарна видача номера: рядок закладу блокується до кінця транзакції,
    # тож одночасні замовлення стають у чергу, а не отримують один номер.
    next_number = db.execute(
        update(Venue)
        .where(Venue.id == venue.id)
        .values(order_seq=Venue.order_seq + 1)
        .returning(Venue.order_seq)
    ).scalar_one()

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
                course_snapshot=item.course,
            )
        )
    order.total_pence = total

    # Одна марка на кожну пару «станція × курс»: саме її бачить екран і саме
    # її рухають кнопки. Бар і кухня далі не заважають одне одному.
    pairs = sorted({(i.station_snapshot, i.course_snapshot) for i in order.items})
    now = utcnow()
    first_course: dict[str, int] = {}
    for station, course in pairs:
        if course > 0 and station not in first_course:
            first_course[station] = course

    for station, course in pairs:
        ticket = OrderTicket(station=station, course=course)
        # Одразу запускаємо напої й **перший** курс кожної станції: закуски
        # чекати нема чого. Усе наступне запускає зал, коли побачить стіл.
        if course == 0 or first_course.get(station) == course:
            ticket.fired_at = now
        order.tickets.append(ticket)

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

    # Панель рухає замовлення цілком — свідома «важка» дія менеджера. Марки
    # підтягуються за нею, включно з тими, що чекали своєї черги.
    # `paid` сюди теж приходить — це просто оплата, а не команда залу, і вона
    # не має запускати наступні курси. Запускає лише свідомий рух статусу.
    if target in TICKET_ORDER and TICKET_ORDER[target] > TICKET_ORDER[STATUS_PAID]:
        for ticket in order.tickets:
            if ticket.fired_at is None:
                ticket.fired_at = now
            if TICKET_ORDER[ticket.status] < TICKET_ORDER[target]:
                ticket.status = target
                if target == STATUS_ACCEPTED and ticket.accepted_at is None:
                    ticket.accepted_at = now
                if target == STATUS_READY and ticket.ready_at is None:
                    ticket.ready_at = now
                if target == STATUS_SERVED and ticket.served_at is None:
                    ticket.served_at = now
    return order


def sync_order_status(order: Order) -> None:
    """Статус замовлення для гостя — з марок, але не «найповільніша».

    Правило асиметричне навмисно:
      · «готується» — щойно **хоч хтось** узявся до роботи;
      · «готово» і «подано» — лише коли **всі** дійшли, бо поки кухня смажить
        основне, замовлення не готове, хай навіть бар уже приніс напої.
    """
    if order.status in ("draft", "payment_pending", "failed", "refunded"):
        return
    if not order.tickets:
        return

    ranks = [TICKET_ORDER[t.status] for t in order.tickets]
    if min(ranks) >= TICKET_ORDER[STATUS_SERVED]:
        order.status = STATUS_SERVED
    elif min(ranks) >= TICKET_ORDER[STATUS_READY]:
        order.status = STATUS_READY
    elif max(ranks) >= TICKET_ORDER[STATUS_ACCEPTED]:
        order.status = STATUS_ACCEPTED
    else:
        order.status = STATUS_PAID
    now = utcnow()
    if order.status == STATUS_ACCEPTED and order.accepted_at is None:
        order.accepted_at = now
    if order.status == STATUS_READY and order.ready_at is None:
        order.ready_at = now
    if order.status == STATUS_SERVED and order.served_at is None:
        order.served_at = now


def previous_course_ticket(order: Order, ticket: OrderTicket) -> OrderTicket | None:
    """Попередній курс тієї ж станції, який ще не готовий.

    Курси йдуть по черзі: поки закуски не віддали, основне не запускають.
    Напої (курс 0) нікого не чекають.
    """
    if ticket.course <= 0:
        return None
    earlier = [
        t
        for t in order.tickets
        if t.station == ticket.station
        and 0 < t.course < ticket.course
        and TICKET_ORDER[t.status] < TICKET_ORDER[STATUS_READY]
    ]
    if not earlier:
        return None
    return min(earlier, key=lambda t: t.course)


def fire_ticket(order: Order, ticket: OrderTicket, user_id) -> OrderTicket:
    """Зал запускає курс у роботу.

    Це навмисно рішення людини, а не таймера: тільки офіціант бачить, чи
    доїв гість закуску. Основне, запущене «за розкладом», приїде холодним.
    """
    if ticket.fired_at is not None:
        return ticket  # повторне натискання нічого не ламає
    blocker = previous_course_ticket(order, ticket)
    if blocker is not None:
        raise OrderError(
            f"спершу віддайте курс {blocker.course}",
            status=409,
            payload={"blocked_by_course": blocker.course},
        )
    ticket.fired_at = utcnow()
    ticket.fired_by = user_id
    return ticket


def ticket_transition(order: Order, ticket: OrderTicket, target: str) -> OrderTicket:
    if target == ticket.status:
        return ticket  # повторне натискання на кухні нічого не ламає
    if target not in ALLOWED_TRANSITIONS.get(ticket.status, ()):
        raise OrderError(f"перехід {ticket.status} → {target} не дозволений", status=409)

    if ticket.fired_at is None:
        raise OrderError(
            "курс ще не запустив зал",
            status=409,
            payload={"awaiting_fire": True},
        )

    ticket.status = target
    now = utcnow()
    if target == STATUS_ACCEPTED:
        ticket.accepted_at = now
    elif target == STATUS_READY:
        ticket.ready_at = now
    elif target == STATUS_SERVED:
        ticket.served_at = now
    sync_order_status(order)
    return ticket


def ticket_payload(order: Order, ticket: OrderTicket, table_label: str | None) -> dict[str, Any]:
    blocker = previous_course_ticket(order, ticket)
    return {
        "id": str(ticket.id),
        "order_id": str(order.id),
        "number": order.number,
        "station": ticket.station,
        "course": ticket.course,
        "status": ticket.status,
        "table": table_label,
        "note": order.note,
        "total_pence": order.total_pence,
        "created_at": order.created_at.isoformat() if order.created_at else None,
        "paid_at": order.paid_at.isoformat() if order.paid_at else None,
        "accepted_at": ticket.accepted_at.isoformat() if ticket.accepted_at else None,
        "ready_at": ticket.ready_at.isoformat() if ticket.ready_at else None,
        # Заблокована марка видима, але не натискається: кухня має бачити, що
        # її чекає далі, а не отримати основне сюрпризом.
        "blocked_by_course": blocker.course if blocker else None,
        "fired_at": ticket.fired_at.isoformat() if ticket.fired_at else None,
        # Кухня чекає не таймера, а команди залу
        "awaiting_fire": ticket.fired_at is None,
        "can_fire": ticket.fired_at is None and blocker is None,
        "items": [
            {
                "name": i.name_snapshot,
                "qty": i.qty,
                "unit_price_pence": i.unit_price_pence,
                "station": i.station_snapshot,
                "course": i.course_snapshot,
            }
            for i in order.items
            if i.station_snapshot == ticket.station and i.course_snapshot == ticket.course
        ],
    }


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
                "course": i.course_snapshot,
            }
            for i in order.items
        ],
        "tickets": [
            {
                "id": str(t.id),
                "station": t.station,
                "course": t.course,
                "status": t.status,
                "awaiting_fire": t.fired_at is None,
                "can_fire": t.fired_at is None and previous_course_ticket(order, t) is None,
                "blocked_by_course": (
                    previous_course_ticket(order, t).course
                    if previous_course_ticket(order, t)
                    else None
                ),
            }
            for t in sorted(order.tickets, key=lambda t: (t.station, t.course))
        ],
    }


def get_for_guest(db: Session, venue: Venue, order_id: uuid.UUID, client_token: str) -> Order:
    order = db.get(Order, order_id)
    # Знання id недостатньо: без свого токена гість не читає чуже замовлення.
    if order is None or order.venue_id != venue.id or order.client_token != client_token:
        raise OrderError("замовлення не знайдено", status=404)
    return order
