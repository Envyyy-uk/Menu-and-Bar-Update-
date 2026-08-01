"""Реалтайм і черга станції.

WebSocket тут перевіряється справжній — TestClient уміє його підняти. Головне,
що доводиться: без сесії сокет не відкривається, ping ходить сам собою, а
подія про нову оплату долітає до підписника.
"""

import time
import uuid

import pytest
from starlette.websockets import WebSocketDisconnect

from app.services import realtime
from tests.test_orders import new_client_token, place
from tests.test_permissions import as_staff
from tests.test_stripe import event, signed, stripe_secret  # noqa: F401 — фікстура


def test_socket_refuses_anonymous(client, db, venue):
    """1008, а не мовчазний порожній список: планшет має показати вхід."""
    client.cookies.clear()
    with pytest.raises(WebSocketDisconnect) as caught:
        with client.websocket_connect("/ws/kitchen") as ws:
            ws.receive_json()
    assert caught.value.code == 1008


def test_socket_greets_and_pings(client, db, venue):
    """Тиша — це теж повідомлення. Щоб екран міг її виміряти, сервер шле
    ping сам, без запиту."""
    as_staff(client)
    with client.websocket_connect("/ws/kitchen") as ws:
        assert ws.receive_json() == {"type": "hello"}
        assert ws.receive_json() == {"type": "ping"}


def test_paid_order_reaches_the_socket(client, db, venue, stripe_secret):
    """Кухня дізнається про оплату подією, а не наступним опитуванням."""
    as_staff(client)
    with client.websocket_connect("/ws/kitchen") as ws:
        assert ws.receive_json() == {"type": "hello"}

        ct = new_client_token()
        order = place(client, db, client_token=ct).json()
        client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})

        body, sig = signed(
            event(
                "checkout.session.completed",
                {
                    "object": "checkout.session",
                    "id": f"cs_{uuid.uuid4().hex[:10]}",
                    "payment_intent": f"pi_{uuid.uuid4().hex[:10]}",
                    "metadata": {"order_id": order["id"]},
                },
            )
        )
        client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})

        seen = []
        for _ in range(6):
            message = ws.receive_json()
            seen.append(message)
            if message["type"] == "order.new":
                break
        assert any(m["type"] == "order.new" and m["number"] == order["number"] for m in seen), seen


def test_status_change_reaches_the_socket(client, db, venue, stripe_secret):
    as_staff(client)
    ct = new_client_token()
    order = place(client, db, client_token=ct).json()
    client.post(f"/api/orders/{order['id']}/checkout", params={"client_token": ct})
    body, sig = signed(
        event(
            "payment_intent.succeeded",
            {"object": "payment_intent", "id": f"pi_{uuid.uuid4().hex[:10]}",
             "metadata": {"order_id": order["id"]}},
        )
    )
    client.post("/api/webhooks/stripe", content=body, headers={"Stripe-Signature": sig})

    with client.websocket_connect("/ws/kitchen") as ws:
        ws.receive_json()  # hello
        client.post(f"/api/orders/{order['id']}/status", params={"target": "accepted"})
        seen = []
        for _ in range(6):
            message = ws.receive_json()
            seen.append(message)
            if message["type"] == "order.status":
                break
        assert any(m["type"] == "order.status" and m["status"] == "accepted" for m in seen), seen


def test_subscribers_are_released(client, db, venue):
    as_staff(client)
    before = realtime.subscriber_count()
    with client.websocket_connect("/ws/kitchen") as ws:
        ws.receive_json()
        assert realtime.subscriber_count() == before + 1
    # закрите з'єднання не має лишати за собою чергу назавжди
    for _ in range(20):
        if realtime.subscriber_count() == before:
            break
        time.sleep(0.05)
    assert realtime.subscriber_count() == before


def test_publish_without_loop_is_harmless():
    """Сідер, скрипти й тести викликають ті самі функції поза застосунком —
    падати там не має чого."""
    saved = realtime._loop
    realtime._loop = None
    try:
        realtime.publish({"type": "order.new", "number": 1})
    finally:
        realtime._loop = saved
