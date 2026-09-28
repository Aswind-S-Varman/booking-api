from datetime import datetime, timedelta, timezone

from booking_api.availability import BUSINESS_END_HOUR, BUSINESS_START_HOUR, upcoming_slots


def test_slots_stay_within_business_hours():
    now = datetime(2026, 10, 1, 6, 0, tzinfo=timezone.utc)

    for slot in upcoming_slots(60, now):
        assert BUSINESS_START_HOUR <= slot.hour < BUSINESS_END_HOUR


def test_past_slots_are_excluded():
    now = datetime(2026, 10, 1, 13, 30, tzinfo=timezone.utc)

    slots = upcoming_slots(60, now, days=1)

    assert all(slot > now for slot in slots)
    assert slots[0] == datetime(2026, 10, 1, 14, 0, tzinfo=timezone.utc)


def test_slot_length_controls_the_spacing():
    now = datetime(2026, 10, 1, 0, 0, tzinfo=timezone.utc)

    hourly = upcoming_slots(60, now, days=1)
    half_hourly = upcoming_slots(30, now, days=1)

    assert len(hourly) == BUSINESS_END_HOUR - BUSINESS_START_HOUR
    assert len(half_hourly) == 2 * len(hourly)
    assert half_hourly[1] - half_hourly[0] == timedelta(minutes=30)


