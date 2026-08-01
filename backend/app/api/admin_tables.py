"""Столи, QR-коди й ротація токенів.

Токен столу — непрозорий випадковий рядок, а не номер столу: інакше сусід
замовляє на чужий стіл, а перехожий з вулиці — на будь-який. Наліпки
зношуються, столи переставляють — тому токен має ротуватися, і стара наліпка
після ротації перестає працювати того ж дня.
"""

from __future__ import annotations

import io
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.deps import get_venue, require
from app.db import get_db
from app.models import Table, User, Venue, new_table_token, utcnow
from app.services.audit import record

router = APIRouter(prefix="/api/admin", tags=["admin"])


class TableIn(BaseModel):
    label: str = Field(min_length=1, max_length=40)


class TablePatch(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=40)
    active: bool | None = None


def _table_out(table: Table) -> dict:
    return {
        "id": str(table.id),
        "label": table.label,
        "active": table.active,
        "url": f"{settings.public_base_url}/t/{table.token}",
        "token_rotated_at": table.token_rotated_at.isoformat() if table.token_rotated_at else None,
    }


def _get(db: DbSession, venue: Venue, table_id: uuid.UUID) -> Table:
    table = db.get(Table, table_id)
    if table is None or table.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="стіл не знайдено")
    return table


@router.get("/tables")
def list_tables(
    actor: User = Depends(require("tables.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    rows = db.scalars(select(Table).where(Table.venue_id == venue.id).order_by(Table.label)).all()
    return [_table_out(t) for t in rows]


@router.post("/tables", status_code=201)
def create_table(
    body: TableIn,
    actor: User = Depends(require("tables.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    exists = db.scalars(
        select(Table).where(Table.venue_id == venue.id, Table.label == body.label)
    ).first()
    if exists is not None:
        raise HTTPException(status_code=409, detail="стіл із такою назвою вже є")
    table = Table(venue_id=venue.id, label=body.label)
    db.add(table)
    db.flush()
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="table.create",
        entity=f"table:{table.id}",
        after={"label": table.label},
    )
    db.commit()
    return _table_out(table)


@router.patch("/tables/{table_id}")
def patch_table(
    table_id: uuid.UUID,
    body: TablePatch,
    actor: User = Depends(require("tables.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    table = _get(db, venue, table_id)
    before = {"label": table.label, "active": table.active}
    if body.label is not None:
        table.label = body.label
    if body.active is not None:
        table.active = body.active
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="table.update",
        entity=f"table:{table.id}",
        before=before,
        after={"label": table.label, "active": table.active},
    )
    db.commit()
    return _table_out(table)


@router.post("/tables/{table_id}/rotate")
def rotate_token(
    table_id: uuid.UUID,
    actor: User = Depends(require("tables.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Стара наліпка після цього не працює — так і задумано."""
    table = _get(db, venue, table_id)
    table.token = new_table_token()
    table.token_rotated_at = utcnow()
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="table.rotate_token",
        entity=f"table:{table.id}",
        after={"label": table.label},
    )
    db.commit()
    return _table_out(table)


@router.get("/tables/{table_id}/qr.png")
def table_qr(
    table_id: uuid.UUID,
    actor: User = Depends(require("tables.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> Response:
    import qrcode

    table = _get(db, venue, table_id)
    img = qrcode.make(f"{settings.public_base_url}/t/{table.token}")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    # Кешувати не можна: після ротації токена стара картинка веде в нікуди.
    return Response(
        buf.getvalue(), media_type="image/png", headers={"Cache-Control": "no-store"}
    )
