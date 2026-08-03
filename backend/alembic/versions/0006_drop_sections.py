"""no sections: every dish carries its own schedule

Розділи були другим місцем, де страву можна було закрити — розкладом на цілу
групу. Гість їх більше не бачить (меню один список), тож інструмент, який
нічого не показує й дублює те, що вміє сама страва, знято.

Виключення лишаються, але кожне на своїй позиції: розклад, дата відкриття
(«по таймеру») і 86. Усе це вже є в `menu_items` — тут нічого додавати.

Revision ID: 0006_no_sections
Revises: 0005_no_courses
Create Date: 2026-08-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0006_no_sections"
down_revision: str | None = "0005_no_courses"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Розділ міг гасити свої страви розкладом. Після видалення таблиці це
    # правило нема кому застосувати, тож те, що зараз закрите **лише** через
    # розділ, переносимо на самі страви: інакше зачинена група мовчки
    # відкриється. Стан страви, який зал уже виставив (86, «скоро»), не чіпаємо.
    op.execute(
        """
        UPDATE menu_items i
        SET schedule_key = s.schedule_key
        FROM menu_sections s
        WHERE i.section_id = s.id
          AND i.state = 'auto'
          AND i.schedule_key IS NULL
          AND s.schedule_key IS NOT NULL
        """
    )
    # Розділ, знятий вручну (86 або «скоро»), — це рішення про групу, і на
    # окремих стравах воно стає їхнім власним станом.
    op.execute(
        """
        UPDATE menu_items i
        SET state = s.state, opens_at = COALESCE(i.opens_at, s.opens_at)
        FROM menu_sections s
        WHERE i.section_id = s.id AND i.state = 'auto' AND s.state IN ('off', 'soon')
        """
    )

    op.drop_column("menu_items", "section_id")
    op.drop_table("menu_sections")


def downgrade() -> None:
    op.create_table(
        "menu_sections",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("names", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=10), nullable=False),
        sa.Column("schedule_key", sa.String(length=80), nullable=True),
        sa.Column("opens_at", sa.String(length=16), nullable=True),
        sa.Column("hidden_when_closed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "key", name="uq_section_key"),
    )
    op.create_index("ix_menu_sections_venue_id", "menu_sections", ["venue_id"])
    op.add_column(
        "menu_items", sa.Column("section_id", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "menu_items_section_id_fkey", "menu_items", "menu_sections",
        ["section_id"], ["id"], ondelete="SET NULL",
    )
    # Розділи не відновлюються: до якої групи належала страва, більше ніде не
    # записано. Таблиця повертається порожньою, страви — без розділу.
