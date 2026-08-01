"""Розклад подачі й наявність.

Доменна модель перенесена з референсу без змін: тижневі діапазони, перехід
через північ, чотири стани. Різниця одна й важлива — рахує це сервер, а не
браузер гостя. Тому «немає» тепер справді означає «не замовиш», а не «не видно».

Час завжди в поясі закладу, не пристрою.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
from zoneinfo import ZoneInfo

# 0 = неділя … 6 = субота — як у референсі, щоб розклади переносились дослівно
DAY_INDEX_FROM_PY = {0: 1, 1: 2, 2: 3, 3: 4, 4: 5, 5: 6, 6: 0}


@dataclass(frozen=True)
class VenueNow:
    day: int
    minutes: int
    stamp: str  # «YYYY-MM-DDTHH:MM» у поясі закладу — порівнюється як текст


def venue_now(timezone: str, at: datetime | None = None) -> VenueNow:
    tz = ZoneInfo(timezone)
    if at is None:
        local = datetime.now(tz)
    elif at.tzinfo is None:
        # Час без поясу — це час закладу, а не машини, на якій крутиться
        # сервер. Інакше `?at=` показував би не ту годину, ніж просили.
        local = at.replace(tzinfo=tz)
    else:
        local = at.astimezone(tz)
    return VenueNow(
        day=DAY_INDEX_FROM_PY[local.weekday()],
        minutes=local.hour * 60 + local.minute,
        stamp=local.strftime("%Y-%m-%dT%H:%M"),
    )


def _to_minutes(hhmm: str) -> int:
    hours, minutes = hhmm.split(":")
    return int(hours) * 60 + int(minutes)


def is_serving_now(ranges: list[dict[str, Any]] | None, now: VenueNow) -> bool:
    """Немає розкладу — доступно завжди. to <= from означає перехід через північ."""
    if not ranges:
        return True
    for r in ranges:
        days = r.get("days") or []
        start, end = _to_minutes(r["from"]), _to_minutes(r["to"])
        if end > start:
            if now.day in days and start <= now.minutes < end:
                return True
        else:
            day_before = (now.day + 6) % 7
            if (now.day in days and now.minutes >= start) or (
                day_before in days and now.minutes < end
            ):
                return True
    return False


@dataclass(frozen=True)
class Availability:
    open: bool
    reason: str  # 'open' | 'closed' | 'sold_out' | 'soon' | 'scheduled'
    opens_at: str | None = None
    schedule_key: str | None = None
    hidden: bool = False


def availability_of(
    *,
    state: str,
    schedule_key: str | None,
    opens_at: str | None,
    hidden_when_closed: bool,
    schedules: dict[str, list[dict[str, Any]]],
    now: VenueNow,
) -> Availability:
    """Підсумковий стан однієї позиції, розділу чи сторінки.

    «Скоро» має три відтінки: з датою відкриття, з розкладом, і просто
    «готуємо». Це не косметика — від відтінку залежить текст для гостя.
    """
    ranges = schedules.get(schedule_key) if schedule_key else None

    if state == "off":
        return Availability(False, "sold_out", hidden=hidden_when_closed)

    if state == "soon":
        # Дата відкриття має пріоритет: після неї позиція відкривається сама,
        # без панелі.
        if opens_at and now.stamp < opens_at:
            return Availability(False, "soon", opens_at=opens_at, hidden=hidden_when_closed)
        if schedule_key:
            if is_serving_now(ranges, now):
                return Availability(True, "open")
            return Availability(
                False, "soon", schedule_key=schedule_key, hidden=hidden_when_closed
            )
        if opens_at:
            return Availability(True, "open")
        return Availability(False, "soon", hidden=hidden_when_closed)

    if state == "on":
        return Availability(True, "open")

    # 'auto' — за розкладом
    if not schedule_key:
        return Availability(True, "open")
    if is_serving_now(ranges, now):
        return Availability(True, "open")
    return Availability(False, "scheduled", schedule_key=schedule_key, hidden=hidden_when_closed)


def availability_dict(a: Availability) -> dict[str, Any]:
    return {
        "open": a.open,
        "reason": a.reason,
        "opens_at": a.opens_at,
        "schedule": a.schedule_key,
        "hidden": a.hidden,
    }
