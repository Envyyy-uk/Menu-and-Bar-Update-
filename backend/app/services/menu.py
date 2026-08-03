"""Збірка гостьового меню: одна відповідь, з якої фронт рендерить усе."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import (
    Ingredient,
    MenuItem,
    MenuSection,
    MenuSource,
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
    section_key: str | None,
    schedules: dict[str, list[dict[str, Any]]],
    now,
    section_av=None,
) -> dict[str, Any]:
    av = availability_of(
        state=item.state,
        schedule_key=item.schedule_key,
        opens_at=item.opens_at,
        hidden_when_closed=item.hidden_when_closed,
        schedules=schedules,
        now=now,
    )
    # Меню гість бачить одним списком, без заголовків розділів. Але розділ
    # досі можна закрити за розкладом — і тоді закривається кожна його
    # позиція. Раніше це робив заголовок; тепер нема кому, тож рахуємо тут.
    # Власна причина позиції важливіша: «закінчилось» точніше, ніж «зачинено».
    if av.open and section_av is not None and not section_av.open:
        av = section_av
    return {
        "id": str(item.id),
        "key": item.key,
        "name": item.name,
        "section": section_key,
        "station": item.station,
        "price_pence": item.price_pence,
        "desc": item.description,
        "ing": item.ingredients,
        "a": item.allergens_a,
        "m": item.allergens_m,
        "r": item.allergens_r,
        "src": item.source_key,
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

    sections = db.scalars(
        select(MenuSection)
        .where(MenuSection.venue_id == venue.id)
        .order_by(MenuSection.position, MenuSection.key)
    ).all()
    section_key_by_id = {s.id: s.key for s in sections}
    section_av_by_id = {
        s.id: availability_of(
            state=s.state,
            schedule_key=s.schedule_key,
            opens_at=s.opens_at,
            hidden_when_closed=s.hidden_when_closed,
            schedules=schedules,
            now=now,
        )
        for s in sections
    }

    items = db.scalars(
        select(MenuItem)
        .where(MenuItem.venue_id == venue.id, MenuItem.active.is_(True))
        .order_by(MenuItem.position, MenuItem.key)
    ).all()

    lexicon = {
        i.key: i.names
        for i in db.scalars(select(Ingredient).where(Ingredient.venue_id == venue.id)).all()
    }
    sources = {
        s.key: {
            "type": s.type,
            "label": s.label,
            "checked": s.checked_on.isoformat() if s.checked_on else None,
        }
        for s in db.scalars(select(MenuSource).where(MenuSource.venue_id == venue.id)).all()
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
        "sources": sources,
        "warnings": warnings,
        "schedules": schedules,
        # Розділи лишаються — ними зал закриває цілу групу одним розкладом.
        # Гість їх не бачить: меню для нього один список.
        "sections": [
            {
                "key": s.key,
                "names": s.names,
                "state": s.state,
                "available": availability_dict(section_av_by_id[s.id]),
            }
            for s in sections
        ],
        "items": [
            item_payload(
                i,
                section_key_by_id.get(i.section_id),
                schedules,
                now,
                section_av_by_id.get(i.section_id),
            )
            for i in items
        ],
    }
