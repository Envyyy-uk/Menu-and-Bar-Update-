"""Розклади й стани розділів.

Доменну модель розкладів не міняємо — вона перевірена: кілька діапазонів на
розклад, дні тижня від неділі (0), `to <= from` означає перехід через північ.
"""

from __future__ import annotations

import re
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.deps import current_user, get_venue, require
from app.core.permissions import can
from app.db import get_db
from app.models import MenuItem, Schedule, User, Venue
from app.models.menu import ITEM_STATES
from app.services.audit import record

router = APIRouter(prefix="/api/admin", tags=["admin"])

HHMM = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")


class Range(BaseModel):
    days: list[int] = Field(min_length=1)
    from_: str = Field(alias="from")
    to: str

    model_config = {"populate_by_name": True}


class ScheduleIn(BaseModel):
    key: str = Field(min_length=1, max_length=80)
    label: str = ""
    ranges: list[Range] = []


class SchedulePatch(BaseModel):
    label: str | None = None
    ranges: list[Range] | None = None


class SectionPatch(BaseModel):
    state: str | None = None
    schedule_key: str | None = None
    opens_at: str | None = None
    hidden_when_closed: bool | None = None


def _ranges_out(ranges: list[Range]) -> list[dict]:
    out = []
    for r in ranges:
        if not HHMM.match(r.from_) or not HHMM.match(r.to):
            raise HTTPException(status_code=422, detail="час у форматі HH:MM")
        if any(d < 0 or d > 6 for d in r.days):
            raise HTTPException(status_code=422, detail="дні від 0 (неділя) до 6 (субота)")
        out.append({"days": sorted(set(r.days)), "from": r.from_, "to": r.to})
    return out


def _schedule_out(s: Schedule) -> dict:
    return {"id": str(s.id), "key": s.key, "label": s.label, "ranges": s.ranges}


@router.get("/schedules")
def list_schedules(
    actor: User = Depends(current_user),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    # Читати розклади має і зал: без них підпис «Подається Вт–Сб 12:00–17:30»
    # нема з чого зібрати.
    if not can(actor.role, "items.state"):
        raise HTTPException(status_code=403, detail="немає права: items.state")
    rows = db.scalars(select(Schedule).where(Schedule.venue_id == venue.id).order_by(Schedule.key)).all()
    return [_schedule_out(s) for s in rows]


@router.post("/schedules", status_code=201)
def create_schedule(
    body: ScheduleIn,
    actor: User = Depends(require("schedules.edit")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    exists = db.scalars(
        select(Schedule).where(Schedule.venue_id == venue.id, Schedule.key == body.key)
    ).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="розклад із таким ключем уже є")
    schedule = Schedule(
        venue_id=venue.id, key=body.key, label=body.label, ranges=_ranges_out(body.ranges)
    )
    db.add(schedule)
    db.flush()
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="schedule.create",
        entity=f"schedule:{schedule.key}",
        after={"ranges": schedule.ranges},
    )
    db.commit()
    return _schedule_out(schedule)


@router.patch("/schedules/{schedule_id}")
def patch_schedule(
    schedule_id: uuid.UUID,
    body: SchedulePatch,
    actor: User = Depends(require("schedules.edit")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None or schedule.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="розклад не знайдено")
    before = {"label": schedule.label, "ranges": schedule.ranges}
    if body.label is not None:
        schedule.label = body.label
    if body.ranges is not None:
        schedule.ranges = _ranges_out(body.ranges)
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="schedule.update",
        entity=f"schedule:{schedule.key}",
        before=before,
        after={"label": schedule.label, "ranges": schedule.ranges},
    )
    db.commit()
    return _schedule_out(schedule)


@router.delete("/schedules/{schedule_id}")
def delete_schedule(
    schedule_id: uuid.UUID,
    actor: User = Depends(require("schedules.edit")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    schedule = db.get(Schedule, schedule_id)
    if schedule is None or schedule.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="розклад не знайдено")
    # Розклад, на який хтось посилається, мовчки видаляти не можна: позиція
    # лишиться з ключем у нікуди й буде «завжди відкрита» без пояснень.
    used_by = db.scalars(
        select(MenuItem.key).where(
            MenuItem.venue_id == venue.id, MenuItem.schedule_key == schedule.key
        )
    ).all()
    if used_by:
        raise HTTPException(
            status_code=409, detail=f"розклад використовують позиції: {', '.join(used_by[:5])}"
        )
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="schedule.delete",
        entity=f"schedule:{schedule.key}",
        before={"ranges": schedule.ranges},
    )
    db.delete(schedule)
    db.commit()
    return {"status": "deleted"}
