"""WebSocket для екрана кухні.

Сервер шле ping кожні 3 секунди. Це не косметика: **тиша — це теж
повідомлення**. Клієнт міряє час від останнього повідомлення й, коли той
переходить за 10 секунд, кричить. Без ping-ів мовчазний сокет і робочий
сокет виглядають однаково.
"""

from __future__ import annotations

import asyncio
import contextlib
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.permissions import can
from app.db import SessionLocal
from app.services import realtime
from app.services.auth import SESSION_COOKIE, resolve_session

router = APIRouter(tags=["kitchen"])
log = logging.getLogger("kitchen")

PING_SECONDS = 3


def _authorised(token: str | None) -> bool:
    if not token:
        return False
    with SessionLocal() as db:
        found = resolve_session(db, token)
        if found is None:
            return False
        db.commit()
        return can(found[0].role, "orders.view")


@router.websocket("/ws/kitchen")
async def kitchen_socket(websocket: WebSocket) -> None:
    token = websocket.cookies.get(SESSION_COOKIE)
    if not await asyncio.to_thread(_authorised, token):
        # 1008 — policy violation. Планшет має показати екран входу, а не
        # мовчазний порожній список.
        await websocket.close(code=1008)
        return

    await websocket.accept()
    queue = realtime.subscribe()
    try:
        # Перше повідомлення одразу: екран не має чекати три секунди, щоб
        # зрозуміти, що зв'язок є.
        await websocket.send_json({"type": "hello"})
        while True:
            try:
                event = await asyncio.wait_for(queue.get(), timeout=PING_SECONDS)
            except asyncio.TimeoutError:
                event = {"type": "ping"}
            await websocket.send_json(event)
    except WebSocketDisconnect:
        pass
    except Exception:  # noqa: BLE001 — обрив мережі на планшеті це норма
        log.debug("kitchen socket closed", exc_info=True)
    finally:
        realtime.unsubscribe(queue)
        with contextlib.suppress(Exception):
            await websocket.close()
