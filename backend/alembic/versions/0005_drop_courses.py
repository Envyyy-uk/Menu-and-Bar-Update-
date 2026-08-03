"""one whole menu: no courses, no firing

Розділення на закуски / основні / десерти як черга подачі знято. Меню —
одне ціле: позиція йде на свою станцію й готується без черги курсів. Разом
із курсами зникає й запуск залом: підтверджувати замовлення офіціант більше
не мусить, бо чекати немає чого.

Розділи меню (Напої, Закуски, Основні, Десерти) лишаються — це те, як гість
гортає меню, а не команда кухні.

Revision ID: 0005_no_courses
Revises: 0004_firing
Create Date: 2026-08-03
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0005_no_courses"
down_revision: str | None = "0004_firing"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Ранг статусу: марка не може «поїхати назад», тож зливаємо за найменшим.
_RANK = (
    "CASE status WHEN 'accepted' THEN 1 WHEN 'ready' THEN 2 "
    "WHEN 'served' THEN 3 ELSE 0 END"
)


def upgrade() -> None:
    # На станції може бути кілька марок різних курсів — а тепер має лишитись
    # одна. Зливаємо їх у ту, що з найменшим курсом.
    #
    # Статус беремо **найменший**, не найбільший: якщо закуски вже віддали, а
    # основне ще не починали, злита марка мусить показувати «не почато». Інакше
    # кухня побачила б кнопку «Готово» на страві, якої ніхто не готував.
    op.execute(
        f"""
        WITH survivor AS (
            SELECT DISTINCT ON (order_id, station) id, order_id, station
            FROM order_tickets ORDER BY order_id, station, course
        ),
        merged AS (
            SELECT t.order_id, t.station,
                   MIN({_RANK}) AS rank,
                   COUNT(*) AS total,
                   COUNT(t.accepted_at) AS accepted_n, MAX(t.accepted_at) AS accepted_at,
                   COUNT(t.ready_at)    AS ready_n,    MAX(t.ready_at)    AS ready_at,
                   COUNT(t.served_at)   AS served_n,   MAX(t.served_at)   AS served_at
            FROM order_tickets t GROUP BY t.order_id, t.station
        )
        UPDATE order_tickets t SET
            status = CASE m.rank WHEN 1 THEN 'accepted' WHEN 2 THEN 'ready'
                                 WHEN 3 THEN 'served' ELSE 'paid' END,
            -- Позначку часу лишаємо тільки тоді, коли етап пройшли **всі**
            -- курси станції; інакше вона брехала б про роботу, яку не робили.
            accepted_at = CASE WHEN m.accepted_n = m.total THEN m.accepted_at END,
            ready_at    = CASE WHEN m.ready_n    = m.total THEN m.ready_at    END,
            served_at   = CASE WHEN m.served_n   = m.total THEN m.served_at   END
        FROM survivor s JOIN merged m ON m.order_id = s.order_id AND m.station = s.station
        WHERE t.id = s.id
        """
    )
    op.execute(
        "DELETE FROM order_tickets t WHERE t.id NOT IN "
        "(SELECT DISTINCT ON (order_id, station) id FROM order_tickets "
        "ORDER BY order_id, station, course)"
    )

    op.drop_constraint("uq_ticket_station_course", "order_tickets", type_="unique")
    op.create_unique_constraint(
        "uq_ticket_station", "order_tickets", ["order_id", "station"]
    )

    op.drop_constraint("fk_order_tickets_fired_by", "order_tickets", type_="foreignkey")
    op.drop_column("order_tickets", "fired_by")
    op.drop_column("order_tickets", "fired_at")
    op.drop_column("order_tickets", "course")
    op.drop_column("order_items", "course_snapshot")
    op.drop_column("menu_items", "course")


def downgrade() -> None:
    # Курси не відновлюються: злиті марки не пам'ятають, з чого їх злили.
    # Повертаємо лише колонки — з нульовим курсом і запущеним станом, щоб
    # старий код побачив звичне «все вже в роботі», а не завислу чергу.
    op.add_column(
        "menu_items", sa.Column("course", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column(
        "order_items",
        sa.Column("course_snapshot", sa.Integer(), server_default="0", nullable=False),
    )
    op.add_column(
        "order_tickets", sa.Column("course", sa.Integer(), server_default="0", nullable=False)
    )
    op.add_column("order_tickets", sa.Column("fired_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "order_tickets", sa.Column("fired_by", postgresql.UUID(as_uuid=True), nullable=True)
    )
    op.create_foreign_key(
        "fk_order_tickets_fired_by", "order_tickets", "users", ["fired_by"], ["id"],
        ondelete="SET NULL",
    )
    op.execute("UPDATE order_tickets SET fired_at = now()")

    op.drop_constraint("uq_ticket_station", "order_tickets", type_="unique")
    op.create_unique_constraint(
        "uq_ticket_station_course", "order_tickets", ["order_id", "station", "course"]
    )
