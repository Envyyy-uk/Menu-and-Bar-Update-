"""Столи, розклади й розділи з боку панелі."""

from sqlalchemy import select

from app.models import MenuSection, Schedule, Table
from tests.test_permissions import as_owner, as_staff


def test_rotation_kills_the_old_sticker(client, db, venue):
    as_owner(client)
    table = db.scalars(select(Table).where(Table.label == "1")).one()
    old_token = table.token

    assert client.get(f"/api/table/{old_token}").status_code == 200
    out = client.post(f"/api/admin/tables/{table.id}/rotate").json()

    db.expire_all()
    new_token = db.get(Table, table.id).token
    assert new_token != old_token
    assert new_token in out["url"]
    # Стара наліпка перестає працювати того ж дня — саме заради цього ротація
    assert client.get(f"/api/table/{old_token}").status_code == 404
    assert client.get(f"/api/table/{new_token}").status_code == 200


def test_table_token_is_not_the_label(client, db, venue):
    as_owner(client)
    rows = client.get("/api/admin/tables").json()
    for row in rows:
        token = row["url"].rsplit("/", 1)[1]
        assert token != row["label"]
        assert len(token) >= 16  # непрозорий рядок, а не номер столу


def test_qr_is_a_png_and_is_not_cached(client, db, venue):
    as_owner(client)
    table = db.scalars(select(Table)).first()
    r = client.get(f"/api/admin/tables/{table.id}/qr.png")
    assert r.status_code == 200
    assert r.headers["content-type"] == "image/png"
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"
    # після ротації стара картинка веде в нікуди — кешувати не можна
    assert r.headers["cache-control"] == "no-store"


def test_staff_cannot_touch_tables(client, db, venue):
    table = db.scalars(select(Table)).first()
    as_staff(client)
    assert client.get("/api/admin/tables").status_code == 403
    assert client.post("/api/admin/tables", json={"label": "9"}).status_code == 403
    assert client.post(f"/api/admin/tables/{table.id}/rotate").status_code == 403
    assert client.get(f"/api/admin/tables/{table.id}/qr.png").status_code == 403


def test_staff_reads_schedules_but_does_not_edit_them(client, db, venue):
    """Без розкладів залу нема з чого зібрати підпис «Подається Вт–Сб»."""
    schedule = db.scalars(select(Schedule).where(Schedule.key == "lunch")).one()
    as_staff(client)
    assert client.get("/api/admin/schedules").status_code == 200
    assert client.patch(f"/api/admin/schedules/{schedule.id}", json={"label": "x"}).status_code == 403
    assert client.post("/api/admin/schedules", json={"key": "x"}).status_code == 403


def test_schedule_in_use_is_not_deleted_silently(client, db, venue):
    as_owner(client)
    schedule = db.scalars(select(Schedule).where(Schedule.key == "lunch")).one()
    item = client.get("/api/admin/items").json()[0]
    client.patch(f"/api/admin/items/{item['id']}", json={"schedule_key": "lunch"})

    r = client.delete(f"/api/admin/schedules/{schedule.id}")
    assert r.status_code == 409
    assert item["key"] in r.json()["detail"]

    client.patch(f"/api/admin/items/{item['id']}", json={"schedule_key": None})
    assert client.delete(f"/api/admin/schedules/{schedule.id}").status_code == 200


def test_schedule_validation(client, db, venue):
    as_owner(client)
    bad_time = client.post(
        "/api/admin/schedules",
        json={"key": "bad-1", "ranges": [{"days": [1], "from": "25:00", "to": "26:00"}]},
    )
    assert bad_time.status_code == 422
    bad_day = client.post(
        "/api/admin/schedules",
        json={"key": "bad-2", "ranges": [{"days": [9], "from": "10:00", "to": "11:00"}]},
    )
    assert bad_day.status_code == 422


def test_midnight_crossing_schedule_survives_the_round_trip(client, db, venue):
    as_owner(client)
    r = client.post(
        "/api/admin/schedules",
        json={
            "key": "night",
            "label": "Night",
            "ranges": [{"days": [5, 6], "from": "22:00", "to": "01:00"}],
        },
    )
    assert r.status_code == 201
    assert r.json()["ranges"] == [{"days": [5, 6], "from": "22:00", "to": "01:00"}]


def test_section_state_reaches_the_guest_menu(client, db, venue):
    """Розділ має ті самі чотири стани, що й позиція."""
    as_owner(client)
    section = db.scalars(select(MenuSection).where(MenuSection.key == "desserts")).one()

    client.patch(f"/api/admin/sections/{section.id}", json={"state": "off"})
    menu = client.get("/api/menu").json()
    desserts = next(s for s in menu["sections"] if s["key"] == "desserts")
    assert desserts["available"] == {
        "open": False,
        "reason": "sold_out",
        "opens_at": None,
        "schedule": None,
        "hidden": False,
    }

    client.patch(f"/api/admin/sections/{section.id}", json={"state": "auto"})
    menu = client.get("/api/menu").json()
    assert next(s for s in menu["sections"] if s["key"] == "desserts")["available"]["open"] is True


def test_86_from_the_panel_shows_up_in_the_guest_menu(client, db, venue):
    """Критерій спринту з боку API: зміна стану — це запис у Postgres,
    і наступний же запит гостя її бачить."""
    as_owner(client)
    item = next(i for i in client.get("/api/admin/items").json() if i["key"] == "house-lemonade")

    client.patch(f"/api/admin/items/{item['id']}", json={"state": "off"})
    menu = client.get("/api/menu").json()
    lemonade = next(i for i in menu["items"] if i["key"] == "house-lemonade")
    assert lemonade["available"]["open"] is False
    assert lemonade["available"]["reason"] == "sold_out"

    client.patch(f"/api/admin/items/{item['id']}", json={"state": "auto"})
    menu = client.get("/api/menu").json()
    assert next(i for i in menu["items"] if i["key"] == "house-lemonade")["available"]["open"]
