from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models import Booking, Resource, Role, User
from ..schemas import BookingCreate, BookingOut

router = APIRouter(prefix="/bookings", tags=["bookings"])


def _as_utc(value: datetime) -> datetime:
    """SQLite drops timezone information, so re-attach UTC when it comes back naive."""
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


@router.post("", response_model=BookingOut, status_code=status.HTTP_201_CREATED)
def create_booking(
    payload: BookingCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    resource = db.get(Resource, payload.resource_id)
    if resource is None or not resource.is_active:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Resource not found")

    if payload.start_time.tzinfo is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time must include a timezone offset, for example 2026-10-01T09:00:00Z",
        )

    start = payload.start_time.astimezone(timezone.utc).replace(microsecond=0)

    if start <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="start_time must be in the future",
        )

    minutes_into_day = start.hour * 60 + start.minute
    if start.second or minutes_into_day % resource.slot_minutes:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"start_time must fall on a {resource.slot_minutes}-minute slot boundary",
        )

    booking = Booking(resource_id=resource.id, user_id=user.id, start_time=start)
    db.add(booking)

    try:
        db.commit()
    except IntegrityError:
        # The unique index rejected it - another request took this slot first.
        db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="That slot is already booked")

    db.refresh(booking)
    return booking


@router.get("", response_model=list[BookingOut])
def list_my_bookings(
    include_cancelled: bool = False,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    statement = select(Booking).where(Booking.user_id == user.id).order_by(Booking.start_time)
    if not include_cancelled:
        statement = statement.where(Booking.cancelled_at.is_(None))

    return list(db.scalars(statement.limit(limit).offset(offset)))


@router.delete("/{booking_id}", status_code=status.HTTP_204_NO_CONTENT)
def cancel_booking(
    booking_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    booking = db.get(Booking, booking_id)

    # 404 rather than 403 for someone else's booking - don't confirm it exists.
    if booking is None or (booking.user_id != user.id and user.role != Role.ADMIN):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Booking not found")

    if booking.cancelled_at is not None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Booking is already cancelled")

    if _as_utc(booking.start_time) <= datetime.now(timezone.utc):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bookings cannot be cancelled once they have started",
        )

    booking.cancelled_at = datetime.now(timezone.utc)
    db.commit()


