from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy.exc import IntegrityError

from booking_api.models import Booking, Resource, User
from tests.conftest import auth


def test_booking_a_free_slot_succeeds(client, user_token, resource_id, future_slot):
    response = client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_time": future_slot},
        headers=auth(user_token),
    )

    assert response.status_code == 201
    assert response.json()["cancelled_at"] is None


def test_booking_the_same_slot_twice_conflicts(client, user_token, resource_id, future_slot):
    payload = {"resource_id": resource_id, "start_time": future_slot}

    assert client.post("/bookings", json=payload, headers=auth(user_token)).status_code == 201
    assert client.post("/bookings", json=payload, headers=auth(user_token)).status_code == 409


def test_start_time_must_align_to_the_slot_boundary(client, user_token, resource_id, future_slot):
    misaligned = future_slot.replace("00:00Z", "30:00Z")

    response = client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_time": misaligned},
        headers=auth(user_token),
    )
    assert response.status_code == 422


def test_past_bookings_are_rejected(client, user_token, resource_id):
    response = client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_time": "2020-01-01T09:00:00Z"},
        headers=auth(user_token),
    )
    assert response.status_code == 422


def test_naive_start_time_is_rejected(client, user_token, resource_id):
    response = client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_time": "2030-01-01T09:00:00"},
        headers=auth(user_token),
    )
    assert response.status_code == 422


def test_cancelling_frees_the_slot(client, user_token, resource_id, future_slot):
    payload = {"resource_id": resource_id, "start_time": future_slot}
    booking_id = client.post("/bookings", json=payload, headers=auth(user_token)).json()["id"]

    assert client.delete(f"/bookings/{booking_id}", headers=auth(user_token)).status_code == 204
    assert client.post("/bookings", json=payload, headers=auth(user_token)).status_code == 201


def test_cancelling_twice_conflicts(client, user_token, resource_id, future_slot):
    booking_id = client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_time": future_slot},
        headers=auth(user_token),
    ).json()["id"]

    client.delete(f"/bookings/{booking_id}", headers=auth(user_token))
    assert client.delete(f"/bookings/{booking_id}", headers=auth(user_token)).status_code == 409


def test_users_cannot_cancel_other_peoples_bookings(
    client, user_token, admin_token, resource_id, future_slot
):
    booking_id = client.post(
        "/bookings",
        json={"resource_id": resource_id, "start_time": future_slot},
        headers=auth(admin_token),
    ).json()["id"]

    assert client.delete(f"/bookings/{booking_id}", headers=auth(user_token)).status_code == 404


def test_database_constraint_blocks_concurrent_bookings(session_factory):
    """Two sessions insert the same slot; the unique index must reject the second."""
    with session_factory() as setup:
        user = User(email="race@example.com", hashed_password="x")
        resource = Resource(name="Contended Room")
        setup.add_all([user, resource])
        setup.commit()
        user_id, resource_id = user.id, resource.id

    start = (datetime.now(timezone.utc) + timedelta(days=2)).replace(
        minute=0, second=0, microsecond=0
    )

    first, second = session_factory(), session_factory()
    try:
        first.add(Booking(resource_id=resource_id, user_id=user_id, start_time=start))
        second.add(Booking(resource_id=resource_id, user_id=user_id, start_time=start))

        first.commit()

        with pytest.raises(IntegrityError):
            second.commit()
    finally:
        first.close()
        second.close()


