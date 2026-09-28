from datetime import datetime, timedelta

BUSINESS_START_HOUR = 9
BUSINESS_END_HOUR = 17


def upcoming_slots(slot_minutes: int, now: datetime, days: int = 3) -> list[datetime]:
    """Bookable start times within business hours over the next few days."""
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    slots: list[datetime] = []

    for offset in range(days):
        cursor = midnight + timedelta(days=offset, hours=BUSINESS_START_HOUR)
        day_end = midnight + timedelta(days=offset, hours=BUSINESS_END_HOUR)

        while cursor < day_end:
            if cursor > now:
                slots.append(cursor)
            cursor += timedelta(minutes=slot_minutes)

    return slots


