"""Акаунти, ролі, PIN-и й пристрої.

Правила, які не порушуються (розділ 9):
  1. Акаунти створюють тільки `owner` і `head_manager`.
  2. Ніхто не може призначити роль, вищу або рівну власній.
  3. `staff` не має доступу до грошей у жодному вигляді.
  4. Перевірка прав — на сервері, на кожному ендпойнті.
  5. Останнього `owner` не можна видалити або знизити.
"""

from __future__ import annotations

import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.deps import get_venue, require
from app.core.permissions import can_assign_role
from app.core.security import hash_secret
from app.db import get_db
from app.models import Device, User, Venue
from app.models.user import ROLE_OWNER, ROLES
from app.services.audit import record
from app.services.auth import DEVICE_COOKIE, AuthError, issue_pin

router = APIRouter(prefix="/api/admin", tags=["admin"])

MIN_PASSWORD = 12


class UserIn(BaseModel):
    name: str = Field(min_length=1, max_length=120)
    role: str
    email: EmailStr | None = None
    password: str | None = None
    with_pin: bool = False


class UserPatch(BaseModel):
    name: str | None = None
    role: str | None = None
    active: bool | None = None
    password: str | None = None


class DeviceIn(BaseModel):
    label: str = Field(min_length=1, max_length=120)


def _user_out(user: User, pin: str | None = None) -> dict:
    out = {
        "id": str(user.id),
        "name": user.name,
        "role": user.role,
        "email": user.email,
        "active": user.active,
        "has_pin": user.pin_hash is not None,
    }
    # PIN показується один раз — при створенні або скиданні.
    if pin:
        out["pin"] = pin
    return out


def _owners_left(db: DbSession, venue_id, excluding: uuid.UUID) -> int:
    return db.scalar(
        select(func.count())
        .select_from(User)
        .where(
            User.venue_id == venue_id,
            User.role == ROLE_OWNER,
            User.active.is_(True),
            User.id != excluding,
        )
    ) or 0


def _get_user(db: DbSession, venue: Venue, user_id: uuid.UUID) -> User:
    user = db.get(User, user_id)
    if user is None or user.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="користувача не знайдено")
    return user


@router.get("/users")
def list_users(
    actor: User = Depends(require("users.create")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    users = db.scalars(
        select(User).where(User.venue_id == venue.id).order_by(User.role, User.name)
    ).all()
    return [_user_out(u) for u in users]


@router.post("/users", status_code=201)
def create_user(
    body: UserIn,
    actor: User = Depends(require("users.create")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    if body.role not in ROLES:
        raise HTTPException(status_code=422, detail="невідома роль")
    if not can_assign_role(actor.role, body.role):
        raise HTTPException(
            status_code=403, detail="не можна призначити роль, вищу або рівну власній"
        )

    user = User(venue_id=venue.id, role=body.role, name=body.name)

    if body.email:
        email = str(body.email).lower()
        taken = db.scalars(
            select(User).where(User.venue_id == venue.id, User.email == email)
        ).first()
        if taken is not None:
            raise HTTPException(status_code=409, detail="таку пошту вже використано")
        user.email = email

    if body.password:
        if len(body.password) < MIN_PASSWORD:
            raise HTTPException(
                status_code=422, detail=f"пароль коротший за {MIN_PASSWORD} символів"
            )
        if not user.email:
            raise HTTPException(status_code=422, detail="пароль без пошти не має сенсу")
        user.password_hash = hash_secret(body.password)

    db.add(user)
    db.flush()

    pin = None
    if body.with_pin:
        pin = _issue_pin_checked(db, user)

    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="user.create",
        entity=f"user:{user.id}",
        after={"role": user.role, "name": user.name, "email": user.email, "pin": bool(pin)},
    )
    db.commit()
    return _user_out(user, pin)


def _issue_pin_checked(db: DbSession, user: User) -> str:
    # Власника не пускаємо за шість цифр: за його роллю Stripe і видалення
    # закладу, а PIN — слабкий фактор за визначенням.
    if user.role == ROLE_OWNER:
        raise HTTPException(status_code=422, detail="owner заходить лише поштою й паролем")
    try:
        return issue_pin(db, user)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from None


@router.post("/users/{user_id}/pin")
def reset_pin(
    user_id: uuid.UUID,
    actor: User = Depends(require("users.create")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    user = _get_user(db, venue, user_id)
    if not can_assign_role(actor.role, user.role):
        raise HTTPException(status_code=403, detail="не ваш рівень доступу")
    pin = _issue_pin_checked(db, user)
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="user.pin_reset",
        entity=f"user:{user.id}",
        after={"name": user.name},
    )
    db.commit()
    return _user_out(user, pin)


@router.patch("/users/{user_id}")
def update_user(
    user_id: uuid.UUID,
    body: UserPatch,
    actor: User = Depends(require("users.create")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    user = _get_user(db, venue, user_id)
    before = {"role": user.role, "active": user.active, "name": user.name}

    # Чужий рівень чіпати не можна — ні вгору, ні вниз.
    if user.id != actor.id and not can_assign_role(actor.role, user.role):
        raise HTTPException(status_code=403, detail="не ваш рівень доступу")

    if body.role is not None and body.role != user.role:
        if body.role not in ROLES:
            raise HTTPException(status_code=422, detail="невідома роль")
        if not can_assign_role(actor.role, body.role):
            raise HTTPException(
                status_code=403, detail="не можна призначити роль, вищу або рівну власній"
            )
        if user.role == ROLE_OWNER and _owners_left(db, venue.id, user.id) == 0:
            raise HTTPException(status_code=409, detail="останнього owner не можна знизити")
        user.role = body.role

    if body.active is not None and body.active != user.active:
        if not body.active and user.role == ROLE_OWNER and _owners_left(db, venue.id, user.id) == 0:
            raise HTTPException(status_code=409, detail="останнього owner не можна вимкнути")
        user.active = body.active

    if body.name is not None:
        user.name = body.name

    if body.password is not None:
        if len(body.password) < MIN_PASSWORD:
            raise HTTPException(
                status_code=422, detail=f"пароль коротший за {MIN_PASSWORD} символів"
            )
        if not user.email:
            raise HTTPException(status_code=422, detail="пароль без пошти не має сенсу")
        user.password_hash = hash_secret(body.password)

    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="user.update",
        entity=f"user:{user.id}",
        before=before,
        after={"role": user.role, "active": user.active, "name": user.name},
    )
    db.commit()
    return _user_out(user)


@router.delete("/users/{user_id}")
def delete_user(
    user_id: uuid.UUID,
    actor: User = Depends(require("users.create")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    user = _get_user(db, venue, user_id)
    if user.role == ROLE_OWNER and _owners_left(db, venue.id, user.id) == 0:
        raise HTTPException(status_code=409, detail="останнього owner не можна видалити")
    if user.id != actor.id and not can_assign_role(actor.role, user.role):
        raise HTTPException(status_code=403, detail="не ваш рівень доступу")
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="user.delete",
        entity=f"user:{user.id}",
        before={"role": user.role, "name": user.name, "email": user.email},
    )
    db.delete(user)
    db.commit()
    return {"status": "deleted"}


# --------------------------------------------------------------- пристрої --
@router.get("/devices")
def list_devices(
    actor: User = Depends(require("devices.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> list[dict]:
    rows = db.scalars(
        select(Device).where(Device.venue_id == venue.id).order_by(Device.label)
    ).all()
    return [
        {
            "id": str(d.id),
            "label": d.label,
            "active": d.active,
            "last_seen_at": d.last_seen_at.isoformat() if d.last_seen_at else None,
        }
        for d in rows
    ]


@router.post("/devices", status_code=201)
def create_device(
    body: DeviceIn,
    response: Response,
    actor: User = Depends(require("devices.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    """Реєструє пристрій і одразу кладе його токен у cookie того браузера,
    з якого це зробили: менеджер заводить планшет, стоячи біля нього."""
    token = secrets.token_urlsafe(24)
    device = Device(venue_id=venue.id, label=body.label, device_token=token, registered_by=actor.id)
    db.add(device)
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="device.create",
        entity=f"device:{device.id}",
        after={"label": device.label},
    )
    db.commit()
    response.set_cookie(
        DEVICE_COOKIE,
        token,
        max_age=60 * 60 * 24 * 365,
        httponly=True,
        samesite="lax",
        secure=settings.public_base_url.startswith("https://"),
        path="/",
    )
    return {"id": str(device.id), "label": device.label, "device_token": token}


@router.patch("/devices/{device_id}")
def update_device(
    device_id: uuid.UUID,
    body: dict,
    actor: User = Depends(require("devices.manage")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    device = db.get(Device, device_id)
    if device is None or device.venue_id != venue.id:
        raise HTTPException(status_code=404, detail="пристрій не знайдено")
    before = {"active": device.active, "label": device.label}
    if "active" in body:
        device.active = bool(body["active"])
    if "label" in body:
        device.label = str(body["label"])[:120]
    record.write(
        db,
        venue_id=venue.id,
        user_id=actor.id,
        action="device.update",
        entity=f"device:{device.id}",
        before=before,
        after={"active": device.active, "label": device.label},
    )
    db.commit()
    return {"id": str(device.id), "label": device.label, "active": device.active}


@router.get("/audit")
def audit_log(
    actor: User = Depends(require("audit.view")),
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
    limit: int = 100,
) -> list[dict]:
    from app.models import AuditLog

    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.venue_id == venue.id)
        .order_by(AuditLog.at.desc())
        .limit(min(limit, 500))
    ).all()
    names = {
        u.id: u.name for u in db.scalars(select(User).where(User.venue_id == venue.id)).all()
    }
    return [
        {
            "at": r.at.isoformat(),
            "who": names.get(r.user_id, "—"),
            "action": r.action,
            "entity": r.entity,
            "before": r.before,
            "after": r.after,
        }
        for r in rows
    ]
