import secrets
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamped, UUIDPk

TOKEN_BYTES = 16  # → 22 символи base64url, значно більше за мінімальні 16


def new_table_token() -> str:
    return secrets.token_urlsafe(TOKEN_BYTES)


class Venue(UUIDPk, Timestamped, Base):
    __tablename__ = "venues"

    key: Mapped[str] = mapped_column(String(64), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    timezone: Mapped[str] = mapped_column(String(64), default="Europe/London")
    currency: Mapped[str] = mapped_column(String(3), default="GBP")

    # Standard-акаунт закладу: KYC, дашборд і спори — на боці закладу.
    stripe_account_id: Mapped[str | None] = mapped_column(String(64), default=None)
    stripe_charges_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Лічильник номерів замовлень. Живе тут, а не рахується як max(number)+1:
    # чотири замовлення в одну мить інакше отримують один номер, і кухня
    # бачить чотири однакові чеки. UPDATE … RETURNING серіалізує видачу.
    # Назви категорій меню: {"spirits": {"uk": "Міцне", …}}. Це підписи для
    # гостя, а не сутність із власним станом — закривають позицію, не групу.
    categories: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )

    order_seq: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    tables: Mapped[list["Table"]] = relationship(back_populates="venue")


class Table(UUIDPk, Timestamped, Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("venue_id", "label", name="uq_table_label"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    label: Mapped[str] = mapped_column(String(40))

    # Непрозорий випадковий рядок, а НЕ номер столу: інакше сусід замовляє на
    # чужий стіл, а перехожий з вулиці — на будь-який.
    token: Mapped[str] = mapped_column(String(64), unique=True, default=new_table_token)
    token_rotated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), default=None
    )
    active: Mapped[bool] = mapped_column(Boolean, default=True)

    venue: Mapped[Venue] = relationship(back_populates="tables")
