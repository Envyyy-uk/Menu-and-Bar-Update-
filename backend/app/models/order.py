import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, Timestamped, UUIDPk

# draft → payment_pending → paid → accepted → ready → served
#            │                 │
#            └→ failed         └→ refunded
STATUS_DRAFT = "draft"
STATUS_PAYMENT_PENDING = "payment_pending"
STATUS_PAID = "paid"
STATUS_ACCEPTED = "accepted"
STATUS_READY = "ready"
STATUS_SERVED = "served"
STATUS_FAILED = "failed"
STATUS_REFUNDED = "refunded"

ORDER_STATUSES = (
    STATUS_DRAFT,
    STATUS_PAYMENT_PENDING,
    STATUS_PAID,
    STATUS_ACCEPTED,
    STATUS_READY,
    STATUS_SERVED,
    STATUS_FAILED,
    STATUS_REFUNDED,
)

# Єдина дозволена мапа переходів. Усе поза нею — помилка, а не «ну майже».
ALLOWED_TRANSITIONS: dict[str, tuple[str, ...]] = {
    STATUS_DRAFT: (STATUS_PAYMENT_PENDING, STATUS_FAILED),
    STATUS_PAYMENT_PENDING: (STATUS_PAID, STATUS_FAILED),
    STATUS_PAID: (STATUS_ACCEPTED, STATUS_REFUNDED),
    STATUS_ACCEPTED: (STATUS_READY, STATUS_REFUNDED),
    STATUS_READY: (STATUS_SERVED, STATUS_REFUNDED),
    STATUS_SERVED: (STATUS_REFUNDED,),
    STATUS_FAILED: (),
    STATUS_REFUNDED: (),
}


# Марка (ticket) — те, що бачить одна станція про один курс. Кухня й бар
# працюють із різною швидкістю: коли бар віддав напої, це не означає, що
# кухня віддала основне. Тому статус живе на марці, а не на замовленні.
TICKET_STATUSES = (STATUS_PAID, STATUS_ACCEPTED, STATUS_READY, STATUS_SERVED)
TICKET_ORDER = {STATUS_PAID: 0, STATUS_ACCEPTED: 1, STATUS_READY: 2, STATUS_SERVED: 3}


class Order(UUIDPk, Timestamped, Base):
    __tablename__ = "orders"
    __table_args__ = (
        # Ідемпотентність: повторний POST з тим самим токеном повертає те саме
        # замовлення, а не створює друге.
        UniqueConstraint("venue_id", "client_token", name="uq_order_client_token"),
    )

    venue_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("venues.id", ondelete="CASCADE"), index=True
    )
    table_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("tables.id", ondelete="SET NULL"), default=None
    )
    number: Mapped[int] = mapped_column(Integer, default=0)

    status: Mapped[str] = mapped_column(String(20), default=STATUS_DRAFT, index=True)
    total_pence: Mapped[int] = mapped_column(Integer, default=0)

    client_token: Mapped[str] = mapped_column(String(80))
    payment_intent_id: Mapped[str | None] = mapped_column(String(80), default=None, index=True)
    checkout_session_id: Mapped[str | None] = mapped_column(String(120), default=None)
    refunded_pence: Mapped[int] = mapped_column(Integer, default=0)

    note: Mapped[str | None] = mapped_column(Text, default=None)

    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    alerted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    items: Mapped[list["OrderItem"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )
    tickets: Mapped[list["OrderTicket"]] = relationship(
        back_populates="order", cascade="all, delete-orphan"
    )


class OrderItem(UUIDPk, Base):
    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    menu_item_id: Mapped[uuid.UUID | None] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("menu_items.id", ondelete="SET NULL"), default=None
    )
    qty: Mapped[int] = mapped_column(Integer, default=1)

    # Знімок на момент замовлення: меню зміниться — історія не попливе.
    unit_price_pence: Mapped[int] = mapped_column(Integer, default=0)
    name_snapshot: Mapped[str] = mapped_column(String(200), default="")
    station_snapshot: Mapped[str] = mapped_column(String(10), default="kitchen")
    # Обрані варіанти як текст на момент замовлення: ["Bottle", "Strawberry"].
    # Саме це читає бармен на марці — і саме це не має попливти, якщо завтра
    # смак перейменують.
    options_snapshot: Mapped[list[str]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )

    order: Mapped[Order] = relationship(back_populates="items")


class OrderTicket(UUIDPk, Base):
    """Одна марка = одна станція.

    Саме її бачить екран кухні, і саме її статус рухають кнопки «Прийнято» /
    «Готово». Бар може віддати напої, поки кухня ще смажить гаряче, — і одне
    одному не заважає. Усередині станції замовлення одне ціле: кухня бачить
    увесь свій список одразу й сама вирішує, з чого починати.
    """

    __tablename__ = "order_tickets"
    __table_args__ = (UniqueConstraint("order_id", "station", name="uq_ticket_station"),)

    order_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    station: Mapped[str] = mapped_column(String(10))
    status: Mapped[str] = mapped_column(String(20), default=STATUS_PAID)

    accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    ready_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)
    served_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), default=None)

    order: Mapped[Order] = relationship(back_populates="tickets")
