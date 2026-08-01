"""Матриця прав із розділу 9 плану.

Одне місце, де записано, хто що може. Ендпойнти посилаються сюди й ніколи не
перевіряють роль рядком: інакше через півроку «manager» у трьох місцях
означатиме три різні речі.

Приховування кнопок в інтерфейсі захистом не є — перевірка тут і на кожному
ендпойнті.
"""

from app.models.user import (
    ROLE_HEAD_MANAGER,
    ROLE_MANAGER,
    ROLE_OWNER,
    ROLE_RANK,
    ROLE_STAFF,
)

ALL = (ROLE_OWNER, ROLE_HEAD_MANAGER, ROLE_MANAGER, ROLE_STAFF)
MANAGERS = (ROLE_OWNER, ROLE_HEAD_MANAGER, ROLE_MANAGER)
SENIOR = (ROLE_OWNER, ROLE_HEAD_MANAGER)
OWNER_ONLY = (ROLE_OWNER,)

PERMISSIONS: dict[str, tuple[str, ...]] = {
    # Зал
    "orders.view": ALL,
    "orders.status": ALL,
    "items.state": ALL,  # 86 і стани позицій
    # Меню й розклади
    "schedules.edit": MANAGERS,
    "items.edit": MANAGERS,  # ціни, додавання, видалення
    "tables.manage": MANAGERS,  # столи, друк QR, ротація токенів
    # Гроші
    "refunds": MANAGERS,  # у manager — з лімітом, див. refund_limit_for
    "reports": MANAGERS,
    # Доступи
    "users.create": SENIOR,  # створення акаунтів і видача PIN
    "devices.manage": SENIOR,
    "audit.view": SENIOR,
    # Найвищі
    "stripe.manage": OWNER_ONLY,
    "venue.delete": OWNER_ONLY,
}


def can(role: str, permission: str) -> bool:
    allowed = PERMISSIONS.get(permission)
    if allowed is None:
        # Невідоме право — не «можна за замовчуванням». Друкарська помилка в
        # назві не має відкривати ендпойнт усім.
        return False
    return role in allowed


def can_assign_role(actor_role: str, target_role: str) -> bool:
    """Ніхто не може призначити роль, вищу або рівну власній.

    Тому `head_manager` не робить другого `head_manager`, а `owner` лишається
    єдиним, хто роздає `head_manager`.
    """
    if not can(actor_role, "users.create"):
        return False
    return ROLE_RANK.get(target_role, 99) < ROLE_RANK.get(actor_role, 0)


def refund_limit_pence(role: str, manager_limit: int) -> int | None:
    """None — без стелі. Повернення це єдина дія, якою співробітник може
    вивести гроші, тож у `manager` вона має стелю."""
    if role in SENIOR:
        return None
    if role == ROLE_MANAGER:
        return manager_limit
    return 0  # staff до грошей не допускається взагалі
