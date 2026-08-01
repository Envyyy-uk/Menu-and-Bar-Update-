"""Залежності FastAPI: хто робить запит і що йому дозволено.

Перевірка прав живе тут і застосовується на **кожному** ендпойнті, який
щось змінює. Кнопки в інтерфейсі ховаються окремо й захистом не є.
"""

from __future__ import annotations

from collections.abc import Callable

from fastapi import Cookie, Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.permissions import can
from app.db import get_db
from app.models import Session, User, Venue
from app.services.auth import DEVICE_COOKIE, SESSION_COOKIE, resolve_session


def get_venue(db: DbSession = Depends(get_db)) -> Venue:
    venue = db.scalars(select(Venue).order_by(Venue.created_at)).first()
    if venue is None:
        raise HTTPException(status_code=503, detail="venue is not seeded")
    return venue


def current_identity(
    request: Request,
    db: DbSession = Depends(get_db),
) -> tuple[User, Session]:
    found = resolve_session(db, request.cookies.get(SESSION_COOKIE))
    if found is None:
        raise HTTPException(status_code=401, detail="потрібен вхід")
    db.commit()  # продовження сесії при активності
    return found


def current_user(identity: tuple[User, Session] = Depends(current_identity)) -> User:
    return identity[0]


def device_token(request: Request) -> str | None:
    return request.cookies.get(DEVICE_COOKIE)


def require(permission: str) -> Callable[[User], User]:
    """`Depends(require('items.edit'))` — і ендпойнт закритий на сервері.

    403, а не 404: приховувати сам факт існування ендпойнта від власного
    персоналу немає сенсу, а зрозуміла відмова економить зміну.
    """

    def dependency(user: User = Depends(current_user)) -> User:
        if not can(user.role, permission):
            raise HTTPException(status_code=403, detail=f"немає права: {permission}")
        return user

    return dependency


def optional_user(
    request: Request,
    db: DbSession = Depends(get_db),
) -> User | None:
    """Для ендпойнтів, які працюють і для гостя, і для персоналу."""
    found = resolve_session(db, request.cookies.get(SESSION_COOKIE))
    if found is None:
        return None
    db.commit()
    return found[0]
