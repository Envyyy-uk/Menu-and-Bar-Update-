"""Звірка `paid` → `accepted`.

Захист від найгіршого сценарію в системі: гість заплатив, кухня не побачила,
гість дізнається про це через двадцять хвилин.

Раз на 30 секунд шукаємо замовлення у стані `paid`, старші за 60 секунд і не
переведені в `accepted`. Кожне таке — гучний алерт на екрані кухні й запис
у лог. Тиха черга гірша за помилку.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db import SessionLocal
from app.models import STATUS_PAID, Order, utcnow
from app.services import realtime
from app.services.audit import record

log = logging.getLogger("reconcile")


def late_orders(db: Session, older_than_seconds: int | None = None) -> list[Order]:
    limit = utcnow() - timedelta(
        seconds=older_than_seconds
        if older_than_seconds is not None
        else settings.reconcile_alert_after_seconds
    )
    return list(
        db.scalars(
            select(Order)
            .where(Order.status == STATUS_PAID, Order.paid_at.is_not(None), Order.paid_at <= limit)
            .order_by(Order.paid_at)
        ).all()
    )


def sweep(db: Session) -> list[Order]:
    """Позначає прострочені й пише в лог. Повертає їх — це ті, через які
    екран кухні має кричати."""
    late = late_orders(db)
    for order in late:
        if order.alerted_at is not None:
            continue  # уже кричали — другий запис у лог нічого не додає
        order.alerted_at = utcnow()
        seconds = int((utcnow() - order.paid_at).total_seconds())
        log.error("order %s paid %ss ago and still not accepted", order.number, seconds)
        record.write(
            db,
            venue_id=order.venue_id,
            user_id=None,
            action="order.late",
            entity=f"order:{order.number}",
            after={"paid_seconds_ago": seconds},
        )
    db.commit()
    if late:
        realtime.publish({"type": "alert.late", "numbers": [o.number for o in late]})
    return late


async def run_forever() -> None:
    while True:
        try:
            with SessionLocal() as db:
                sweep(db)
        except Exception:  # noqa: BLE001 — фонова задача не має вмирати мовчки
            log.exception("reconcile sweep failed")
        await asyncio.sleep(settings.reconcile_interval_seconds)
