from datetime import datetime

from app.services.schedule import availability_of, is_serving_now, venue_now

LATE_BAR = [{"days": [4, 5, 6], "from": "22:00", "to": "01:00"}]
LUNCH = [{"days": [1, 2, 3, 4, 5], "from": "12:00", "to": "17:30"}]


def at(stamp: str):
    return venue_now("Europe/London", datetime.fromisoformat(stamp))


def test_no_schedule_means_always_open():
    assert is_serving_now(None, at("2026-08-01T03:00")) is True


def test_plain_range():
    assert is_serving_now(LUNCH, at("2026-08-03T13:00")) is True  # понеділок
    assert is_serving_now(LUNCH, at("2026-08-03T18:00")) is False
    assert is_serving_now(LUNCH, at("2026-08-02T13:00")) is False  # неділя


def test_range_crossing_midnight():
    # П'ятниця 23:30 — у діапазоні, який почався в п'ятницю
    assert is_serving_now(LATE_BAR, at("2026-08-07T23:30")) is True
    # Субота 00:30 — той самий діапазон, що почався в п'ятницю
    assert is_serving_now(LATE_BAR, at("2026-08-08T00:30")) is True
    # Вівторок 00:30 — понеділка в днях немає
    assert is_serving_now(LATE_BAR, at("2026-08-04T00:30")) is False


def test_time_is_venue_time_not_device_time():
    """Наївний час трактується як час закладу — інакше `?at=` показував би
    не ту годину, ніж просили."""
    assert at("2026-08-01T13:00").minutes == 13 * 60


def test_soon_with_opening_date_opens_itself():
    args = dict(schedule_key=None, hidden_when_closed=False, schedules={}, opens_at="2026-09-01T12:00")
    before = availability_of(state="soon", now=at("2026-08-15T10:00"), **args)
    after = availability_of(state="soon", now=at("2026-09-02T10:00"), **args)
    assert (before.open, before.reason, before.opens_at) == (False, "soon", "2026-09-01T12:00")
    assert after.open is True


def test_soon_with_schedule_reports_hours():
    a = availability_of(
        state="soon",
        schedule_key="lunch",
        opens_at=None,
        hidden_when_closed=False,
        schedules={"lunch": LUNCH},
        now=at("2026-08-03T19:00"),
    )
    assert (a.open, a.reason, a.schedule_key) == (False, "soon", "lunch")


def test_86_is_manual_and_ignores_schedule():
    a = availability_of(
        state="off",
        schedule_key="lunch",
        opens_at=None,
        hidden_when_closed=False,
        schedules={"lunch": LUNCH},
        now=at("2026-08-03T13:00"),
    )
    assert (a.open, a.reason) == (False, "sold_out")


def test_always_on_ignores_schedule():
    a = availability_of(
        state="on",
        schedule_key="lunch",
        opens_at=None,
        hidden_when_closed=False,
        schedules={"lunch": LUNCH},
        now=at("2026-08-03T23:00"),
    )
    assert a.open is True
