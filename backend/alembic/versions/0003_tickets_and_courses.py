"""per-station tickets and courses

Статус жив на замовленні цілком, тож «Прийнято» на кухні рухало й бар.
Але станції працюють із різною швидкістю: бар віддає напої за хвилину, кухня
смажить основне двадцять. Тепер статус живе на марці — одна марка на пару
«станція × курс».

Курс додано й до позицій меню: подача йде по черзі, а не все підряд.

Revision ID: 0003_tickets
Revises: 0002_order_seq
Create Date: 2026-08-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003_tickets"
down_revision: str | None = "0002_order_seq"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Курс за розділом меню: напої йдуть одразу, далі закуски, основні, десерт.
COURSE_BY_SECTION = {
    "starters": 1,
    "mains": 2,
    "desserts": 3,
}


def upgrade() -> None:
    op.add_column(
        "menu_items", sa.Column("course", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "order_items",
        sa.Column("course_snapshot", sa.Integer(), server_default="0", nullable=False),
    )

    for section, course in COURSE_BY_SECTION.items():
        op.execute(
            "UPDATE menu_items SET course = %d WHERE section_id IN "
            "(SELECT id FROM menu_sections WHERE key = '%s')" % (course, section)
        )
    op.execute(
        "UPDATE order_items oi SET course_snapshot = mi.course "
        "FROM menu_items mi WHERE mi.id = oi.menu_item_id"
    )

    op.create_table(
        "order_tickets",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("order_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("station", sa.String(length=10), nullable=False),
        sa.Column("course", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("ready_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("served_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["order_id"], ["orders.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("order_id", "station", "course", name="uq_ticket_station_course"),
    )
    op.create_index(op.f("ix_order_tickets_order_id"), "order_tickets", ["order_id"])

    # Наявні живі замовлення теж мають марки, інакше екран кухні спорожніє.
    op.execute(
        """
        INSERT INTO order_tickets (id, order_id, station, course, status)
        SELECT gen_random_uuid(), o.id, oi.station_snapshot, oi.course_snapshot, o.status
        FROM orders o
        JOIN order_items oi ON oi.order_id = o.id
        WHERE o.status IN ('paid', 'accepted', 'ready', 'served')
        GROUP BY o.id, oi.station_snapshot, oi.course_snapshot, o.status
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_order_tickets_order_id"), table_name="order_tickets")
    op.drop_table("order_tickets")
    op.drop_column("order_items", "course_snapshot")
    op.drop_column("menu_items", "course")
