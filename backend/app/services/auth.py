"""Вхід персоналу: два механізми, і це навмисно.

У ресторані пароль на спільному планшеті не працює: офіціант вводить його
50 разів за зміну й через день просто не виходить із сесії. Тому `staff`
заходить PIN-ом — але лише з пристрою, який менеджер додав у список, і з
блокуванням після п'яти спроб.

PIN — слабкий фактор, і саме тому за ним не ховаються гроші: матриця прав і
ця схема входу — одне рішення, а не два.
"""

from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.security import hash_secret, new_token, token_fingerprint, verify_secret
from app.models import Device, Session, User, utcnow
from app.models.user import ROLE_STAFF
from app.services.audit import record

SESSION_COOKIE = "session"
DEVICE_COOKIE = "device"


class AuthError(Exception):
    def __init__(self, message: str, status: int = 401):
        super().__init__(message)
        self.message = message
        self.status = status


def session_lifetime(role: str) -> timedelta:
    minutes = (
        settings.staff_session_minutes if role == ROLE_STAFF else settings.manager_session_minutes
    )
    return timedelta(minutes=minutes)


def open_session(db: DbSession, user: User, device: Device | None = None) -> str:
    """Повертає токен у відкритому вигляді — єдиний раз, коли він існує
    поза cookie. У базі лежить лише хеш."""
    token = new_token()
    db.add(
        Session(
            venue_id=user.venue_id,
            user_id=user.id,
            device_id=device.id if device else None,
            token_hash=token_fingerprint(token),
            expires_at=utcnow() + session_lifetime(user.role),
            last_seen_at=utcnow(),
        )
    )
    return token


def close_session(db: DbSession, token: str) -> None:
    row = db.scalars(
        select(Session).where(Session.token_hash == token_fingerprint(token))
    ).first()
    if row is not None:
        db.delete(row)


def resolve_session(db: DbSession, token: str | None) -> tuple[User, Session] | None:
    if not token:
        return None
    row = db.scalars(select(Session).where(Session.token_hash == token_fingerprint(token))).first()
    if row is None:
        return None
    if row.expires_at <= utcnow():
        db.delete(row)
        db.commit()
        return None
    user = db.get(User, row.user_id)
    if user is None or not user.active:
        return None
    # Сесія продовжується при активності: зміна довша за таймер, а виганяти
    # офіціанта посеред замовлення — гірше, ніж тримати сесію відкритою.
    row.last_seen_at = utcnow()
    row.expires_at = utcnow() + session_lifetime(user.role)
    return user, row


def login_with_password(db: DbSession, venue_id, email: str, password: str) -> User:
    user = db.scalars(
        select(User).where(User.venue_id == venue_id, User.email == email.strip().lower())
    ).first()
    # Однакова відповідь і на невідому пошту, і на невірний пароль: інакше
    # форма входу перетворюється на список співробітників.
    if user is None or not user.active or not verify_secret(user.password_hash, password):
        raise AuthError("невірна пошта або пароль")
    return user


def find_device(db: DbSession, venue_id, device_token: str | None) -> Device | None:
    if not device_token:
        return None
    device = db.scalars(
        select(Device).where(Device.venue_id == venue_id, Device.device_token == device_token)
    ).first()
    if device is None or not device.active:
        return None
    return device


def login_with_pin(db: DbSession, venue_id, pin: str, device: Device | None) -> User:
    if device is None:
        raise AuthError("пристрій не зареєстровано", status=403)

    candidates = db.scalars(
        select(User).where(User.venue_id == venue_id, User.pin_hash.is_not(None))
    ).all()

    now = utcnow()
    for user in candidates:
        if not verify_secret(user.pin_hash, pin):
            continue
        if not user.active:
            raise AuthError("акаунт вимкнено", status=403)
        if user.pin_locked_until and user.pin_locked_until > now:
            raise AuthError("PIN заблоковано, спробуйте пізніше", status=429)
        user.pin_failed_attempts = 0
        user.pin_locked_until = None
        device.last_seen_at = now
        return user

    # PIN не підійшов нікому. Лічильник спроб ведемо на пристрої — рахувати
    # його на користувачі неможливо, ми ж не знаємо, хто саме помилився.
    _register_failed_pin(db, venue_id, device)
    raise AuthError("невірний PIN")


def _register_failed_pin(db: DbSession, venue_id, device: Device) -> None:
    """П'ять невдалих спроб поспіль — пристрій вимикається на 15 хвилин
    і це видно в аудиті. Лічильник живе в тій же таблиці сесій? Ні:
    достатньо аудит-логу, з якого й рахуємо."""
    window_start = utcnow() - timedelta(minutes=settings.pin_lockout_minutes)
    recent = record.count_recent(
        db, venue_id, action="pin.failed", entity=f"device:{device.id}", since=window_start
    )
    record.write(
        db,
        venue_id=venue_id,
        user_id=None,
        action="pin.failed",
        entity=f"device:{device.id}",
        after={"label": device.label, "attempt": recent + 1},
    )
    if recent + 1 >= settings.pin_max_attempts:
        device.active = False
        record.write(
            db,
            venue_id=venue_id,
            user_id=None,
            action="device.locked",
            entity=f"device:{device.id}",
            after={"label": device.label, "reason": "pin attempts"},
        )


def issue_pin(db: DbSession, user: User) -> str:
    """Шість цифр, унікальні в межах закладу. Показується один раз при
    створенні — далі в базі лише хеш."""
    others = db.scalars(
        select(User).where(User.venue_id == user.venue_id, User.pin_hash.is_not(None))
    ).all()
    for _ in range(200):
        pin = f"{secrets.randbelow(1_000_000):06d}"
        if any(verify_secret(o.pin_hash, pin) for o in others if o.id != user.id):
            continue
        user.pin_hash = hash_secret(pin)
        user.pin_failed_attempts = 0
        user.pin_locked_until = None
        return pin
    raise AuthError("не вдалося підібрати вільний PIN", status=500)
