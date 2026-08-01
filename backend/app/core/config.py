from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

# /srv/backend/app/core/config.py → /srv
ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://menu:menu@localhost:5432/menu"

    secret_key: str = "dev-secret-change-me-in-production"

    seed_owner_email: str = "owner@example.com"
    seed_owner_password: str = "change-me-please-12"
    seed_staff_pin: str = "246810"

    # Порожній ключ = Stripe вимкнено. Замовлення тоді проходять шлях
    # payment_pending → paid лише через ручне підтвердження в тестах,
    # а не через відповідь браузера.
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_publishable_key: str = ""
    platform_fee_bps: int = 0

    public_base_url: str = "http://localhost:8000"

    # Сесії: коротка для планшета в залі, довша для панелі.
    staff_session_minutes: int = 240
    manager_session_minutes: int = 720

    pin_max_attempts: int = 5
    pin_lockout_minutes: int = 15

    # Ліміт повернення для ролі manager, у пенсах.
    manager_refund_limit_pence: int = 5000

    # Звірка paid → accepted.
    reconcile_interval_seconds: int = 30
    reconcile_alert_after_seconds: int = 60

    @property
    def frontend_dir(self) -> Path:
        return ROOT / "frontend"

    @property
    def seed_file(self) -> Path:
        return ROOT / "seed_menu.json"

    @property
    def stripe_enabled(self) -> bool:
        return bool(self.stripe_secret_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
