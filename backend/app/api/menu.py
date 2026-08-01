from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import Venue
from app.services.menu import menu_payload

router = APIRouter(prefix="/api", tags=["menu"])


def current_venue(db: Session) -> Venue:
    """У v1 заклад один. Мультитенантність уже в схемі — коли з'явиться
    друга точка, сюди прийде розбір домену або токена столу."""
    venue = db.scalars(select(Venue).order_by(Venue.created_at)).first()
    if venue is None:
        raise HTTPException(status_code=503, detail="venue is not seeded")
    return venue


@router.get("/menu")
def get_menu(
    db: Session = Depends(get_db),
    at: str | None = Query(
        default=None,
        description="ISO-час у поясі закладу: перевірити розклад, не чекаючи години",
    ),
) -> dict:
    venue = current_venue(db)
    moment = None
    if at:
        try:
            moment = datetime.fromisoformat(at)
        except ValueError:
            raise HTTPException(status_code=400, detail="at: очікується ISO-8601") from None
    return menu_payload(db, venue, moment)
