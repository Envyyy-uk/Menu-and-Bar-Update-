import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamped, UUIDPk

# Чотири стани позиції — ті самі, що в референсі, ключі не міняємо.
STATE_AUTO = "auto"  # за розкладом
STATE_ON = "on"  # завжди
STATE_OFF = "off"  # немає (86)
STATE_SOON = "soon"  # скоро
ITEM_STATES = (STATE_AUTO, STATE_ON, STATE_OFF, STATE_SOON)

STATION_KITCHEN = "kitchen"
STATION_BAR = "bar"
STATIONS = (STATION_KITCHEN, STATION_BAR)

# Курс — черга подачі. Напої йдуть одразу, далі закуски, основні, десерти.
# Кухня не готує все підряд: поки не віддали закуски, основні не починають.
COURSE_IMMEDIATE = 0
COURSE_STARTERS = 1
COURSE_MAINS = 2
COURSE_DESSERTS = 3
COURSES = (COURSE_IMMEDIATE, COURSE_STARTERS, COURSE_MAINS, COURSE_DESSERTS)


class Ingredient(UUIDPk, Base):
    """Словник: склад страви — це посилання на ключі, а не текст.
    Звідси однакові переклади й пошук «кунжут» = «sesame» = «Sesam»."""

    __tablename__ = "ingredients"
    __table_args__ = (UniqueConstraint("venue_id", "key", name="uq_ingredient_key"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    names: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)


class MenuSource(UUIDPk, Base):
    """Джерело даних про алергени: офіційний лист із датою перевірки
    або реконструкція з опису."""

    __tablename__ = "menu_sources"
    __table_args__ = (UniqueConstraint("venue_id", "key", name="uq_source_key"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    type: Mapped[str] = mapped_column(String(20), default="official")
    label: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    checked_on: Mapped[datetime | None] = mapped_column(Date, default=None)


class MenuWarning(UUIDPk, Base):
    """Застереження рівня страви: спільний фритюр, сире яйце тощо."""

    __tablename__ = "menu_warnings"
    __table_args__ = (UniqueConstraint("venue_id", "key", name="uq_warning_key"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    text: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)


class Schedule(UUIDPk, Base):
    """Тижневий розклад: кілька діапазонів на день, перехід через північ
    дозволено (to <= from означає «через північ»)."""

    __tablename__ = "schedules"
    __table_args__ = (UniqueConstraint("venue_id", "key", name="uq_schedule_key"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    label: Mapped[str] = mapped_column(String(120), default="")
    # [{"days": [1,2,3], "from": "12:00", "to": "17:30"}]
    ranges: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)


class MenuSection(UUIDPk, Base):
    __tablename__ = "menu_sections"
    __table_args__ = (UniqueConstraint("venue_id", "key", name="uq_section_key"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    key: Mapped[str] = mapped_column(String(80))
    names: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)
    position: Mapped[int] = mapped_column(Integer, default=0)

    # Розділ має ті самі чотири стани, що й позиція.
    state: Mapped[str] = mapped_column(String(10), default=STATE_AUTO)
    schedule_key: Mapped[str | None] = mapped_column(String(80), default=None)
    opens_at: Mapped[str | None] = mapped_column(String(16), default=None)
    hidden_when_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    items: Mapped[list["MenuItem"]] = relationship(
        back_populates="section", order_by="MenuItem.position"
    )


class MenuItem(UUIDPk, Timestamped, Base):
    __tablename__ = "menu_items"
    __table_args__ = (UniqueConstraint("venue_id", "key", name="uq_menu_item_key"),)

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    section_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("menu_sections.id", ondelete="SET NULL"), default=None
    )

    key: Mapped[str] = mapped_column(String(80))
    # Назва не перекладається — гість замовляє так, як надруковано в меню.
    name: Mapped[str] = mapped_column(String(200))
    description: Mapped[dict[str, str]] = mapped_column(JSONB, default=dict)

    price_pence: Mapped[int] = mapped_column(Integer, default=0)
    station: Mapped[str] = mapped_column(String(10), default=STATION_KITCHEN)
    # Черга подачі: 0 — одразу, 1 — закуски, 2 — основні, 3 — десерт.
    course: Mapped[int] = mapped_column(Integer, default=COURSE_IMMEDIATE, server_default="0")
    position: Mapped[int] = mapped_column(Integer, default=0)

    state: Mapped[str] = mapped_column(String(10), default=STATE_AUTO)
    schedule_key: Mapped[str | None] = mapped_column(String(80), default=None)
    # «YYYY-MM-DDTHH:MM» у поясі закладу — такі рядки порівнюються як текст.
    opens_at: Mapped[str | None] = mapped_column(String(16), default=None)
    hidden_when_closed: Mapped[bool] = mapped_column(Boolean, default=False)

    # Межа v1 зашита в дані, а не в код: у v2 знімається одним прапорцем.
    orderable: Mapped[bool] = mapped_column(Boolean, default=True)
    orderable_reason: Mapped[str | None] = mapped_column(String(40), default=None)

    # Склад: ключі словника, вкладені компоненти — ["salsa-verde", ["parsley", …]]
    ingredients: Mapped[list[Any]] = mapped_column(JSONB, default=list)
    # Три рівні алергенів + джерело з датою.
    allergens_a: Mapped[list[str]] = mapped_column(JSONB, default=list)  # містить
    allergens_m: Mapped[list[str]] = mapped_column(JSONB, default=list)  # може містити
    allergens_r: Mapped[list[str]] = mapped_column(JSONB, default=list)  # можна прибрати
    source_key: Mapped[str | None] = mapped_column(String(80), default=None)
    warnings: Mapped[list[str]] = mapped_column(JSONB, default=list)

    active: Mapped[bool] = mapped_column(Boolean, default=True)

    section: Mapped[MenuSection | None] = relationship(back_populates="items")
