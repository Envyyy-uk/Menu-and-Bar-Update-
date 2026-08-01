import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, Timestamped, UUIDPk

ROLE_OWNER = "owner"
ROLE_HEAD_MANAGER = "head_manager"
ROLE_MANAGER = "manager"
ROLE_STAFF = "staff"

# Порядок важливий: ніхто не може призначити роль, вищу або рівну власній.
ROLE_RANK = {ROLE_STAFF: 1, ROLE_MANAGER: 2, ROLE_HEAD_MANAGER: 3, ROLE_OWNER: 4}
ROLES = tuple(ROLE_RANK)


class User(UUIDPk, Timestamped, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("venue_id", "email", name="uq_user_email"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    role: Mapped[str] = mapped_column(String(20), default=ROLE_STAFF)
    name: Mapped[str] = mapped_column(String(120), default="")

    # staff заходить PIN-ом на зареєстрованому пристрої й пошти може не мати.
    email: Mapped[str | None] = mapped_column(String(200), default=None)
    password_hash: Mapped[str | None] = mapped_column(String(255), default=None)

    # PIN — слабкий фактор, і саме тому за ним не ховаються гроші.
    pin_hash: Mapped[str | None] = mapped_column(String(255), default=None)
    pin_failed_attempts: Mapped[int] = mapped_column(Integer, default=0)
    pin_locked_until: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )

    # Місце під 2FA для owner закладено одразу, вмикається другою ітерацією.
    totp_secret: Mapped[str | None] = mapped_column(String(64), default=None)

    active: Mapped[bool] = mapped_column(Boolean, default=True)


class Device(UUIDPk, Timestamped, Base):
    """Планшет чи телефон, з якого дозволено вхід за PIN."""

    __tablename__ = "devices"

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(120))
    device_token: Mapped[str] = mapped_column(String(64), unique=True)
    registered_by: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), default=None
    )
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
