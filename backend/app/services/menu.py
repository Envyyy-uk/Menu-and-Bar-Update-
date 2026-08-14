"""Збірка гостьового меню: одна відповідь, з якої фронт рендерить усе."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Ingredient,
    MenuItem,
    MenuWarning,
    Schedule,
    Venue,
)
from app.services.schedule import availability_dict, availability_of, venue_now


def schedules_map(db: Session, venue_id) -> dict[str, list[dict[str, Any]]]:
    rows = db.scalars(select(Schedule).where(Schedule.venue_id == venue_id)).all()
    return {s.key: s.ranges for s in rows}


def item_payload(
    item: MenuItem,
    schedules: dict[str, list[dict[str, Any]]],
    now,
) -> dict[str, Any]:
    av = availability_of(
        state=item.state,
        schedule_key=item.schedule_key,
        opens_at=item.opens_at,
        hidden_when_closed=item.hidden_when_closed,
        schedules=schedules,
        now=now,
    )
    return {
        "id": str(item.id),
        "key": item.key,
        "name": item.name,
        "station": item.station,
        "price_pence": item.price_pence,
        # Варіанти: «50 мл чи пляшка», «яке мохіто». Ціну за ними
        # рахує сервер — фронт лише запитує вибір.
        "category": item.category,
        "options": item.options or [],
        "desc": item.description,
        "ing": item.ingredients,
        "w": item.warnings,
        "state": item.state,
        "orderable": item.orderable,
        "orderable_reason": item.orderable_reason,
        # Чи можна це замовити просто зараз — рахує сервер. Фронт це лише
        # показує; повторна перевірка все одно буде в момент оплати.
        "available": availability_dict(av),
    }


def menu_payload(db: Session, venue: Venue, at: datetime | None = None) -> dict[str, Any]:
    now = venue_now(venue.timezone, at)
    schedules = schedules_map(db, venue.id)

    items = db.scalars(
        select(MenuItem)
        .where(MenuItem.venue_id == venue.id, MenuItem.active.is_(True))
        .order_by(MenuItem.position, MenuItem.key)
    ).all()

    lexicon = {
        i.key: i.names
        for i in db.scalars(select(Ingredient).where(Ingredient.venue_id == venue.id)).all()
    }
    warnings = {
        w.key: w.text
        for w in db.scalars(select(MenuWarning).where(MenuWarning.venue_id == venue.id)).all()
    }

    return {
        "venue": {
            "key": venue.key,
            "name": venue.name,
            "timezone": venue.timezone,
            "currency": venue.currency,
        },
        "now": {"day": now.day, "minutes": now.minutes, "stamp": now.stamp},
        "lexicon": lexicon,
        # Підписи категорій: гість гортає меню за ними.
        "categories": venue.categories or {},
        "warnings": warnings,
        "schedules": schedules,
        "items": [item_payload(i, schedules, now) for i in items],
    }
