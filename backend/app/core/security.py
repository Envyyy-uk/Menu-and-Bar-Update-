"""Хешування паролів і PIN-ів, токени сесій.

Argon2 і для пароля, і для PIN. PIN — слабкий фактор за визначенням (шість
цифр), тож його захищає ще й блокування спроб і прив'язка до пристрою;
хешування тут проти витоку таблиці, а не проти перебору.
"""

from __future__ import annotations

import hashlib
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError, VerificationError

_hasher = PasswordHasher()


def hash_secret(raw: str) -> str:
    return _hasher.hash(raw)


def verify_secret(hashed: str | None, raw: str) -> bool:
    if not hashed:
        return False
    try:
        return _hasher.verify(hashed, raw)
    except (VerifyMismatchError, VerificationError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_fingerprint(token: str) -> str:
    """Сесійні токени зберігаємо хешем: витік таблиці не дає входу.
    SHA-256 тут доречний — токен випадковий, словникова атака неможлива."""
    return hashlib.sha256(token.encode()).hexdigest()
