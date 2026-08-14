"""categories for display, allergens removed

Дві зміни, що йдуть разом.

**Категорії.** Меню знову згруповане — але тільки для показу: категорія це
підпис, за яким гість гортає, а не сутність зі своїм станом. Закривають
позицію, а не групу. Саме тому назви категорій лежать полем на закладі, а не
окремою таблицею з розкладами: та вже була й була знята.

**Алергени зняті повністю.** Заклад їх не надавав, а виведені з назв продуктів
алергени гірші за жодних: гість вірить міткам. Разом із ними йде й таблиця
джерел — вона існувала рівно для того, щоб сказати, звідки алергени взялися.

Склад лишається: на ньому тримається пошук трьома мовами.

Revision ID: 0008_categories
Revises: 0007_options
Create Date: 2026-08-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0008_categories"
down_revision: str | None = "0007_options"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("menu_items", sa.Column("category", sa.String(length=80), nullable=True))
    op.add_column(
        "venues",
        sa.Column(
            "categories",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="{}",
            nullable=False,
        ),
    )

    op.drop_column("menu_items", "allergens_a")
    op.drop_column("menu_items", "allergens_m")
    op.drop_column("menu_items", "allergens_r")
    op.drop_column("menu_items", "source_key")
    op.drop_table("menu_sources")


def downgrade() -> None:
    op.create_table(
        "menu_sources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("venue_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("key", sa.String(length=80), nullable=False),
        sa.Column("type", sa.String(length=20), nullable=False),
        sa.Column("label", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.ForeignKeyConstraint(["venue_id"], ["venues.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("venue_id", "key", name="uq_source_key"),
    )
    op.create_index("ix_menu_sources_venue_id", "menu_sources", ["venue_id"])
    for column in ("allergens_a", "allergens_m", "allergens_r"):
        op.add_column(
            "menu_items",
            sa.Column(
                column,
                postgresql.JSONB(astext_type=sa.Text()),
                server_default="[]",
                nullable=False,
            ),
        )
    op.add_column("menu_items", sa.Column("source_key", sa.String(length=80), nullable=True))

    # Самі алергени не відновлюються: їх ніде не збережено, і вигадати їх
    # удруге було б тією самою помилкою. Повертаються лише колонки — порожні.
    op.drop_column("venues", "categories")
    op.drop_column("menu_items", "category")
