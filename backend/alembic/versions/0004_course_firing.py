"""waiter fires the next course

Кухня починала наступний курс, щойно попередній ішов із пасу. Але тільки зал
бачить стіл: якщо гість ще їсть закуску, основне доїде холодним. Тому запуск
курсу став рішенням людини — марка чекає, поки офіціант її не запустить.

Напої та перший курс кожної станції запускаються самі: їх нема чого чекати.

Revision ID: 0004_firing
Revises: 0003_tickets
Create Date: 2026-08-01
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004_firing"
down_revision: str | None = "0003_tickets"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("order_tickets", sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "order_tickets", sa.Column("fired_by", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_order_tickets_fired_by", "order_tickets", "users", ["fired_by"], ["id"],
        ondelete="SET NULL",
    )

    # Наявні марки вважаємо запущеними: вони вже в роботі, і зупиняти зал
    # посеред зміни оновленням — найгірше, що можна зробити.
    op.execute("UPDATE order_tickets SET fired_at = now()")


def downgrade() -> None:
    op.drop_constraint("fk_order_tickets_fired_by", "order_tickets", type_="foreignkey")
    op.drop_column("order_tickets", "fired_by")
    op.drop_column("order_tickets", "fired_at")
