from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session as DbSession

from app.core.config import settings
from app.core.deps import current_identity, get_venue
from app.core.permissions import PERMISSIONS, can, refund_limit_pence
from app.db import get_db
from app.models import Session, User, Venue
from app.services.auth import (
    DEVICE_COOKIE,
    SESSION_COOKIE,
    AuthError,
    close_session,
    find_device,
    login_with_password,
    login_with_pin,
    open_session,
)

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    email: str
    password: str


class PinIn(BaseModel):
    pin: str = Field(min_length=4, max_length=12)


def _set_session_cookie(response: Response, token: str, minutes: int) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=minutes * 60,
        httponly=True,
        samesite="lax",
        secure=settings.public_base_url.startswith("https://"),
        path="/",
    )


def _me(user: User) -> dict:
    return {
        "id": str(user.id),
        "name": user.name,
        "role": user.role,
        "email": user.email,
        # Інтерфейс ховає кнопки за цим списком. Це зручність, не захист:
        # кожен ендпойнт однаково перевіряє право сам.
        "permissions": sorted(p for p in PERMISSIONS if can(user.role, p)),
        "refund_limit_pence": refund_limit_pence(user.role, settings.manager_refund_limit_pence),
    }


@router.post("/login")
def login(
    body: LoginIn,
    response: Response,
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    try:
        user = login_with_password(db, venue.id, body.email, body.password)
    except AuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.message) from None
    token = open_session(db, user)
    db.commit()
    _set_session_cookie(response, token, settings.manager_session_minutes)
    return _me(user)


@router.post("/pin")
def login_pin(
    body: PinIn,
    request: Request,
    response: Response,
    db: DbSession = Depends(get_db),
    venue: Venue = Depends(get_venue),
) -> dict:
    device = find_device(db, venue.id, request.cookies.get(DEVICE_COOKIE))
    try:
        user = login_with_pin(db, venue.id, body.pin, device)
    except AuthError as exc:
        db.commit()  # невдалу спробу треба зберегти, інакше блокування не працює
        raise HTTPException(status_code=exc.status, detail=exc.message) from None
    token = open_session(db, user, device)
    db.commit()
    _set_session_cookie(response, token, settings.staff_session_minutes)
    return _me(user)


@router.post("/logout")
def logout(request: Request, response: Response, db: DbSession = Depends(get_db)) -> dict:
    token = request.cookies.get(SESSION_COOKIE)
    if token:
        close_session(db, token)
        db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "ok"}


@router.get("/me")
def me(identity: tuple[User, Session] = Depends(current_identity)) -> dict:
    return _me(identity[0])
