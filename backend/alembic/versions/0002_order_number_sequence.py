"""order number counter on venues

Номер замовлення рахувався як max(number)+1 поза замком. Чотири замовлення
в одну мить отримували один номер — кухня бачила чотири однакові чеки.
Тепер номер видається атомарно через UPDATE … RETURNING по лічильнику
закладу.

Revision ID: 0002_order_seq
Revises: 0001_initial
Create Date: 2026-08-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0002_order_seq"
down_revision: str | None = "0001_initial"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "venues",
        sa.Column("order_seq", sa.Integer(), server_default="0", nullable=False),
    )
    # Лічильник має продовжити з того місця, де зупинилися наявні замовлення,
    # інакше після оновлення номери підуть по другому колу.
    op.execute(
        "UPDATE venues v SET order_seq = "
        "COALESCE((SELECT MAX(o.number) FROM orders o WHERE o.venue_id = v.id), 0)"
    )


def downgrade() -> None:
    op.drop_column("venues", "order_seq")
