"""Позиції меню з боку панелі.

Права перевіряються **по полях**, а не по ендпойнту: офіціант має вимикати
позицію PIN-кодом за десять секунд, але не має чіпати ціну. Один запит може
нести і те, і те — тож перевіряємо кожне поле окремо.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.deps import current_user, get_venue
from app.core.permissions import can
from app.db import get_db
from app.models import MenuItem, User, Venue
from app.models.menu import ITEM_STATES, STATIONS
from app.services.audit import record

router = APIRouter(prefix="/api/admin", tags=["admin"])

# Яке право потрібне, щоб змінити конкретне поле.
FIELD_PERMISSION = {
    "state": "items.state",
    "opens_at": "items.state",
    "schedule_key": "items.state",
    "hidden_when_closed": "items.state",
    "price_pence": "items.edit",
    "station": "items.edit",
    "orderable": "items.edit",
    "name": "items.edit",
    "active": "items.edit",
}


class ItemPatch(BaseModel):
    state: str | None = None
    opens_at: str | None = None
    schedule_key: str | None = None
    hidden_when_closed: bool | None = None
    price_pence: int | None = Field(default=None, ge=0)
    station: str | None = None
    orderable: bool | None = None
    name: str | None = None
    active: bool | None = None


@router.get("/items")
def list_items(
    actor: User = Depends(current_user),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    if not can(actor.role, "items.state"):
        raise HTTPException(status_code=403, detail="немає права: items.state")
    items = db.scalars(
        select(MenuItem).where(MenuItem.venue_id == venue.id).order_by(MenuItem.position)
    ).all()
    return [
        {
            "id": str(i.id),
            "key": i.key,
            "name": i.name,
            "station": i.station,
            "options": i.options or [],
            "price_pence": i.price_pence,
            "state": i.state,
            "opens_at": i.opens_at,
            "schedule_key": i.schedule_key,
            "hidden_when_closed": i.hidden_when_closed,
            "orderable": i.orderable,
            "active": i.active,
        }
        for i in items
    ]


@router.patch("/items/{item_id}")
def patch_item(
    item_id: uuid.UUID,
    body: ItemPatch,
    actor: User = Depends(current_user),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    item = db.get(MenuItem, item_id)
    if item is None or item.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="позицію не знайдено")

    changes = body.model_dump(exclude_unset=True)
    if not changes:
        raise HTTPException(status_code=422, detail="нічого змінювати")

    for field in changes:
        permission = FIELD_PERMISSION[field]
        if not can(actor.role, permission):
            raise HTTPException(status_code=403, detail=f"немає права: {permission}")

    if "state" in changes and changes["state"] not in ITEM_STATES:
        raise HTTPException(status_code=422, detail="невідомий стан")
    if "station" in changes and changes["station"] not in STATIONS:
        raise HTTPException(status_code=422, detail="невідома станція")

    before = {f: getattr(item, f) for f in changes}
    for field, value in changes.items():
        setattr(item, field, value)

    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="item.update",
        entity=f"item:{item.key}",
        before=before,
        after=changes,
    )
    db.commit()
    return {"id": str(item.id), "key": item.key, **changes}
