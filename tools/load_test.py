"""Навантаження, яке справді буває в залі.

Симуляція вдома чесно закриває машину станів, ідемпотентність і паралельні
замовлення. Саме це тут і робиться — але **справжніми одночасними запитами**,
а не по черзі: послідовний виклик не перевіряє нічого, бо гонки в ньому немає.

    python tools/load_test.py                 # усі сценарії
    python tools/load_test.py --burst 8        # вісім замовлень в одну секунду

Змінні: BASE_URL, ADMIN_EMAIL, ADMIN_PASSWORD.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from concurrent.futures import ThreadPoolExecutor

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8000").rstrip("/")
EMAIL = os.environ.get("ADMIN_EMAIL", "owner@example.com")
PASSWORD = os.environ.get("ADMIN_PASSWORD", "change-me-please-12")

fails: list[str] = []


def check(name: str, ok: bool, extra: str = "") -> None:
    print(("PASS " if ok else "FAIL ") + name + (f"  {extra}" if extra else ""))
    if not ok:
        fails.append(name)


def call(method: str, path: str, body=None, cookie: str | None = None):
    data = json.dumps(body).encode() if body is not None else None
    request = urllib.request.Request(BASE + path, data=data, method=method)
    request.add_header("Content-Type", "application/json")
    if cookie:
        request.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            raw = response.read().decode()
            return response.status, json.loads(raw) if raw else None, response.headers
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode()
        return exc.code, json.loads(raw) if raw else None, exc.headers


def sign_in() -> str:
    status, _, headers = call("POST", "/api/auth/login", {"email": EMAIL, "password": PASSWORD})
    if status != 200:
        raise SystemExit(f"вхід не вдався: {status}. Сервер піднятий? Пароль правильний?")
    raw = headers.get("set-cookie", "")
    return raw.split(";")[0]


def table_token(cookie: str) -> str:
    status, rows, _ = call("GET", "/api/admin/tables", cookie=cookie)
    if status != 200 or not rows:
        raise SystemExit("не вдалося отримати столи")
    return rows[0]["url"].rsplit("/", 1)[1]


def order_body(token: str, client_token: str, items=None):
    return {
        "table_token": token,
        "client_token": client_token,
        "items": items or [{"key": "house-lemonade", "qty": 1}],
    }


def place(token: str, client_token: str, items=None):
    return call("POST", "/api/orders", order_body(token, client_token, items))


def pay(order_id: str, client_token: str) -> None:
    call("POST", f"/api/orders/{order_id}/checkout?client_token={client_token}")
    call("POST", f"/api/orders/{order_id}/confirm-offline?client_token={client_token}")


def drain(cookie: str) -> None:
    """Черга від попередніх прогонів — не наша справа."""
    _, rows, _ = call("GET", "/api/orders", cookie=cookie)
    for row in rows or []:
        for target in ("accepted", "ready", "served"):
            call("POST", f"/api/orders/{row['id']}/status?target={target}", cookie=cookie)


# ---------------------------------------------------------------- сценарії --


def scenario_same_second(token: str, cookie: str, count: int) -> None:
    """Що станеться, коли кілька замовлень прийдуть в одну хвилину.

    У залі це буває щовечора: столи замовляють одночасно.
    """
    tokens = [f"ct-{uuid.uuid4().hex}" for _ in range(count)]
    started = time.monotonic()
    with ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(lambda ct: place(token, ct), tokens))
    elapsed = time.monotonic() - started

    created = [body for status, body, _ in results if status == 201]
    numbers = sorted(o["number"] for o in created)
    check(f"{count} одночасних замовлень створено", len(created) == count, f"{len(created)}")
    check("номери не повторилися", len(set(numbers)) == len(numbers), str(numbers))
    check("усі відповіді швидші за 5 секунд", elapsed < 5, f"{elapsed:.2f}s")

    for order in created:
        pay(order["id"], order["client_token"] if "client_token" in order else "")
    # платимо за токенами, які знаємо
    for ct, (status, body, _) in zip(tokens, results):
        if status == 201:
            pay(body["id"], ct)

    _, queue, _ = call("GET", "/api/orders", cookie=cookie)
    check("усі опинилися в черзі кухні", len(queue) == count, f"{len(queue)}")


def scenario_double_tap(token: str, cookie: str, count: int = 6) -> None:
    """Подвійний тап і повтор після обриву — це та сама ситуація.

    Тут вона відтворюється чесно: `count` потоків стріляють одним і тим самим
    `client_token` в одну мить.
    """
    client_token = f"ct-{uuid.uuid4().hex}"
    with ThreadPoolExecutor(max_workers=count) as pool:
        results = list(pool.map(lambda _: place(token, client_token), range(count)))

    ids = {body["id"] for status, body, _ in results if status == 201}
    created_flags = [body.get("created") for status, body, _ in results if status == 201]
    check(f"{count} одночасних повторів дали одне замовлення", len(ids) == 1, str(ids))
    check("рівно одна відповідь каже «створено»", created_flags.count(True) == 1,
          str(created_flags))

    order_id = next(iter(ids))
    pay(order_id, client_token)
    _, queue, _ = call("GET", "/api/orders", cookie=cookie)
    check("у черзі теж одне", sum(1 for o in queue if o["id"] == order_id) == 1)


def scenario_pay_twice(token: str, cookie: str) -> None:
    """Гість натиснув «оплатити» двічі — гроші не мають піти двічі."""
    client_token = f"ct-{uuid.uuid4().hex}"
    status, order, _ = place(token, client_token)
    if status != 201:
        check("замовлення створено", False, str(status))
        return

    with ThreadPoolExecutor(max_workers=4) as pool:
        pool.map(lambda _: pay(order["id"], client_token), range(4))

    _, fresh, _ = call("GET", f"/api/orders/{order['id']}?client_token={client_token}")
    check("статус після чотирьох оплат — paid", fresh["status"] == "paid", fresh["status"])
    _, queue, _ = call("GET", "/api/orders", cookie=cookie)
    check("у черзі не з'явився дубль", sum(1 for o in queue if o["id"] == order["id"]) == 1)


def scenario_sold_out_race(token: str, cookie: str) -> None:
    """Позицію вимкнули рівно тоді, коли її замовляють."""
    _, items, _ = call("GET", "/api/admin/items", cookie=cookie)
    item = next(i for i in items if i["key"] == "spiced-apple-cooler")
    call("PATCH", f"/api/admin/items/{item['id']}", {"state": "off"}, cookie=cookie)

    status, body, _ = place(token, f"ct-{uuid.uuid4().hex}",
                            [{"key": "spiced-apple-cooler", "qty": 1}])
    check("вимкнену позицію не замовити", status == 409, str(status))
    check("гість бачить, що саме випало",
          bool(body) and body["detail"]["unavailable"][0]["reason"] == "sold_out",
          json.dumps(body, ensure_ascii=False)[:100] if body else "")

    call("PATCH", f"/api/admin/items/{item['id']}", {"state": "auto"}, cookie=cookie)


def scenario_health_under_load(cookie: str) -> None:
    """Health-check має відповідати навіть коли всі зайняті."""
    with ThreadPoolExecutor(max_workers=10) as pool:
        codes = list(pool.map(lambda _: call("GET", "/health")[0], range(20)))
    check("health відповідає 200 під навантаженням", set(codes) == {200}, str(set(codes)))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--burst", type=int, default=4,
                        help="скільки замовлень слати одночасно (за замовчуванням 4)")
    parser.add_argument("--keep", action="store_true",
                        help="не прибирати чергу перед прогоном")
    args = parser.parse_args()

    cookie = sign_in()
    token = table_token(cookie)
    if not args.keep:
        drain(cookie)

    print(f"— {args.burst} замовлень в одну мить —")
    scenario_same_second(token, cookie, args.burst)
    drain(cookie)

    print("\n— подвійний тап —")
    scenario_double_tap(token, cookie)
    drain(cookie)

    print("\n— подвійна оплата —")
    scenario_pay_twice(token, cookie)
    drain(cookie)

    print("\n— позицію вимкнули під час замовлення —")
    scenario_sold_out_race(token, cookie)

    print("\n— health під навантаженням —")
    scenario_health_under_load(cookie)

    drain(cookie)
    print()
    print("FAILED:", fails if fails else "нічого")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
