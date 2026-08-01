"""Сідер: заливає seed_menu.json у порожню базу.

Ідемпотентний — запускається на кожному старті контейнера й нічого не дублює.
Позиції меню оновлюються за ключем, стани, які змінив персонал, не чіпаються:
сідер — це початкові дані, а не щоденне перезаписування залу.
"""

from __future__ import annotations

import json
import secrets
from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import hash_secret
from app.db import SessionLocal
from app.models import (
    Device,
    Ingredient,
    MenuItem,
    MenuSection,
    MenuSource,
    MenuWarning,
    Schedule,
    Table,
    User,
    Venue,
)
from app.models.user import ROLE_OWNER, ROLE_STAFF

DEMO_TABLES = ["1", "2", "3", "4", "5", "Bar 1"]

# Словник демо-даних говорить мовою меню, база — мовою станів із розділу 11.
SEED_STATE_MAP = {"available": "auto", "soon": "soon", "86": "off", "off": "off"}

# Курс подачі за розділом: напої йдуть одразу, далі закуски, основні, десерт.
# Зал може перевизначити це в панелі для будь-якої позиції.
COURSE_BY_SECTION = {"starters": 1, "mains": 2, "desserts": 3}

# Пресети розкладів: самі по собі нічого не закривають, але дають панелі
# з чого обирати з першого дня. 'late-bar' навмисно перетинає північ.
DEMO_SCHEDULES = {
    "lunch": {
        "label": "Lunch",
        "ranges": [{"days": [1, 2, 3, 4, 5], "from": "12:00", "to": "17:30"}],
    },
    "weekend-brunch": {
        "label": "Weekend brunch",
        "ranges": [{"days": [6, 0], "from": "11:00", "to": "16:30"}],
    },
    "late-bar": {
        "label": "Late bar",
        "ranges": [{"days": [4, 5, 6], "from": "22:00", "to": "01:00"}],
    },
}


def _load() -> dict[str, Any]:
    with settings.seed_file.open(encoding="utf-8") as fh:
        return json.load(fh)


def _venue(db: Session, data: dict[str, Any]) -> Venue:
    spec = data["venue"]
    venue = db.scalars(select(Venue).where(Venue.key == spec["key"])).first()
    if venue is None:
        venue = Venue(key=spec["key"])
        db.add(venue)
    venue.name = spec["name"]
    venue.timezone = spec["timezone"]
    venue.currency = spec["currency"]
    db.flush()
    return venue


def _upsert(db: Session, model, venue_id, key: str):
    row = db.scalars(select(model).where(model.venue_id == venue_id, model.key == key)).first()
    if row is None:
        row = model(venue_id=venue_id, key=key)
        db.add(row)
    return row


def seed(db: Session) -> Venue:
    data = _load()
    venue = _venue(db, data)

    for key, names in data.get("lexicon", {}).items():
        _upsert(db, Ingredient, venue.id, key).names = names

    for key, spec in data.get("sources", {}).items():
        row = _upsert(db, MenuSource, venue.id, key)
        row.type = spec.get("type", "official")
        row.label = spec.get("label", {})
        row.checked_on = date.fromisoformat(spec["checked"]) if spec.get("checked") else None

    for key, text in data.get("warnings", {}).items():
        _upsert(db, MenuWarning, venue.id, key).text = text

    for key, spec in DEMO_SCHEDULES.items():
        row = _upsert(db, Schedule, venue.id, key)
        if not row.ranges:
            row.label = spec["label"]
            row.ranges = spec["ranges"]

    sections: dict[str, MenuSection] = {}
    for position, (key, names) in enumerate(data.get("sections", {}).items()):
        row = _upsert(db, MenuSection, venue.id, key)
        row.names = names
        row.position = position
        sections[key] = row
    db.flush()

    for position, spec in enumerate(data.get("items", [])):
        item = _upsert(db, MenuItem, venue.id, spec["key"])
        is_new = item.created_at is None
        item.name = spec["name"]
        item.section_id = sections[spec["section"]].id if spec.get("section") in sections else None
        item.station = spec.get("station", "kitchen")
        if is_new:
            item.course = COURSE_BY_SECTION.get(spec.get("section"), 0)
        item.price_pence = spec.get("price_pence", 0)
        item.description = spec.get("desc", {})
        item.ingredients = spec.get("ing", [])
        item.allergens_a = spec.get("a", [])
        item.allergens_m = spec.get("m", [])
        item.allergens_r = spec.get("r", [])
        item.source_key = spec.get("src")
        item.warnings = spec.get("w", [])
        item.orderable = spec.get("orderable", True)
        item.orderable_reason = spec.get("orderable_reason")
        item.position = position
        # Стан і дату відкриття ставимо лише при створенні: після запуску цим
        # керує зал, і перезапуск контейнера не має «вмикати» 86-позицію.
        if is_new:
            item.state = SEED_STATE_MAP.get(spec.get("state", "available"), "auto")
            item.opens_at = _stamp(spec.get("opens_at"))

    for label in DEMO_TABLES:
        exists = db.scalars(
            select(Table).where(Table.venue_id == venue.id, Table.label == label)
        ).first()
        if exists is None:
            db.add(Table(venue_id=venue.id, label=label))

    _users(db, venue)
    db.commit()
    return venue


def _stamp(value: str | None) -> str | None:
    """'2026-09-01T12:00:00' → '2026-09-01T12:00' — далі це порівнюється як текст."""
    return value[:16] if value else None


def _users(db: Session, venue: Venue) -> None:
    owner = db.scalars(
        select(User).where(User.venue_id == venue.id, User.role == ROLE_OWNER)
    ).first()
    if owner is None:
        db.add(
            User(
                venue_id=venue.id,
                role=ROLE_OWNER,
                name="Owner",
                email=settings.seed_owner_email.lower(),
                password_hash=hash_secret(settings.seed_owner_password),
            )
        )

    staff = db.scalars(
        select(User).where(User.venue_id == venue.id, User.role == ROLE_STAFF)
    ).first()
    if staff is None:
        db.add(
            User(
                venue_id=venue.id,
                role=ROLE_STAFF,
                name="Demo staff",
                pin_hash=hash_secret(settings.seed_staff_pin),
            )
        )

    device = db.scalars(select(Device).where(Device.venue_id == venue.id)).first()
    if device is None:
        db.add(
            Device(
                venue_id=venue.id,
                label="Kitchen tablet",
                device_token=secrets.token_urlsafe(24),
            )
        )


def main() -> None:
    with SessionLocal() as db:
        venue = seed(db)
        print(f"seed: {venue.name} ({venue.key}) ready")


if __name__ == "__main__":
    main()
