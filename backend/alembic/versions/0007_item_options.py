"""item options: size, flavour, milk

Меню бару складається з варіантів: 50 мл чи пляшка, яке саме мохіто, яке
молоко в капучино. Досі позиція мала рівно одну ціну, тож єдиним виходом
було розбити кожен смак в окрему картку — меню на дев'яносто позицій, де
п'ять із них те саме мохіто.

Тепер варіанти живуть на позиції, а обраний варіант — знімком на позиції
замовлення: саме його читає бармен на марці.

Revision ID: 0007_options
Revises: 0006_no_sections
Create Date: 2026-08-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0007_options"
down_revision: str | None = "0006_no_sections"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "menu_items",
        sa.Column(
            "options",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )
    op.add_column(
        "order_items",
        sa.Column(
            "options_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            server_default="[]",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("order_items", "options_snapshot")
    op.drop_column("menu_items", "options")
