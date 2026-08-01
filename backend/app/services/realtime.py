"""Реалтайм для екрана кухні.

Подія тут — це **сигнал «щось змінилося»**, а не сам стан. Отримавши її,
екран перечитує чергу з сервера цілком. Так само він робить після відновлення
зв'язку: повне перезавантаження стану, а не догравання подій. Догравання
означало б, що пропущена подія тихо лишає екран застарілим — а саме цього
допустити не можна.

Джерело правди — Postgres. Це лише спосіб не чекати наступного опитування.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

log = logging.getLogger("realtime")

# Черга на кожне підключення. Розмір обмежений навмисно: якщо планшет не
# встигає, ми не ростемо в пам'ять, а викидаємо сигнал — наступний однаково
# змусить перечитати все.
QUEUE_SIZE = 32

_loop: asyncio.AbstractEventLoop | None = None
_subscribers: set[asyncio.Queue] = set()


def bind_loop(loop: asyncio.AbstractEventLoop) -> None:
    global _loop
    _loop = loop


def subscribe() -> asyncio.Queue:
    queue: asyncio.Queue = asyncio.Queue(maxsize=QUEUE_SIZE)
    _subscribers.add(queue)
    return queue


def unsubscribe(queue: asyncio.Queue) -> None:
    _subscribers.discard(queue)


def subscriber_count() -> int:
    return len(_subscribers)


def _put(queue: asyncio.Queue, event: dict[str, Any]) -> None:
    try:
        queue.put_nowait(event)
    except asyncio.QueueFull:
        log.warning("kitchen queue full, dropping %s", event.get("type"))


def publish(event: dict[str, Any]) -> None:
    """Викликається з синхронних обробників (вони живуть у пулі потоків),
    тому кладемо в чергу через `call_soon_threadsafe`."""
    if _loop is None or not _subscribers:
        return
    for queue in list(_subscribers):
        try:
            _loop.call_soon_threadsafe(_put, queue, event)
        except RuntimeError:  # цикл уже зупинено — сервер вимикається
            return
