from datetime import datetime, timezone
from pathlib import Path

import jwt
from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from .availability import upcoming_slots
from .database import get_db
from .models import Booking, Resource, User
from .security import create_access_token, decode_access_token, hash_password, verify_password

router = APIRouter(prefix="/ui", tags=["web"])
templates = Jinja2Templates(directory=str(Path(__file__).parent / "templates"))

COOKIE_NAME = "access_token"


def _as_utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def current_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Web pages authenticate by cookie; the JSON API still uses the Authorization header."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        return None

    try:
        payload = decode_access_token(token)
    except jwt.PyJWTError:
        return None

    user = db.get(User, int(payload.get("sub", 0)))
    return user if user and user.is_active else None


def _login_redirect() -> RedirectResponse:
    return RedirectResponse("/ui/login", status_code=303)


@router.get("/login", response_class=HTMLResponse)
def login_form(request: Request):
    return templates.TemplateResponse(request, "login.html", {"error": None})


@router.post("/login")
def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = db.scalar(select(User).where(User.email == email.lower()))

    if user is None or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse(
            request, "login.html", {"error": "Incorrect email or password"}, status_code=401
        )

    response = RedirectResponse("/ui/resources", status_code=303)
    response.set_cookie(
        COOKIE_NAME,
        create_access_token(str(user.id), user.role),
        httponly=True,  # JavaScript cannot read it, which blunts XSS token theft
        samesite="lax",
    )
    return response


@router.get("/register", response_class=HTMLResponse)
def register_form(request: Request):
    return templates.TemplateResponse(request, "register.html", {"error": None})


@router.post("/register")
def register_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    if len(password) < 8:
        return templates.TemplateResponse(
            request, "register.html", {"error": "Password must be at least 8 characters"}, status_code=422
        )

    if db.scalar(select(User).where(User.email == email.lower())):
        return templates.TemplateResponse(
            request, "register.html", {"error": "That email is already registered"}, status_code=409
        )

    db.add(User(email=email.lower(), hashed_password=hash_password(password)))
    db.commit()
    return RedirectResponse("/ui/login", status_code=303)


@router.post("/logout")
def logout():
    response = RedirectResponse("/ui/login", status_code=303)
    response.delete_cookie(COOKIE_NAME)
    return response


@router.get("/resources", response_class=HTMLResponse)
def resource_list(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    if user is None:
        return _login_redirect()

    resources = db.scalars(
        select(Resource).where(Resource.is_active.is_(True)).order_by(Resource.name)
    ).all()

    return templates.TemplateResponse(request, "resources.html", {"user": user, "resources": resources})


@router.get("/resources/{resource_id}", response_class=HTMLResponse)
def resource_detail(
    request: Request,
    resource_id: int,
    error: str | None = None,
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    if user is None:
        return _login_redirect()

    resource = db.get(Resource, resource_id)
    if resource is None:
        return RedirectResponse("/ui/resources", status_code=303)

    now = datetime.now(timezone.utc)
    slots = upcoming_slots(resource.slot_minutes, now)

    taken = {
        _as_utc(booking.start_time)
        for booking in db.scalars(
            select(Booking).where(
                Booking.resource_id == resource_id,
                Booking.cancelled_at.is_(None),
            )
        )
    }

    return templates.TemplateResponse(
        request,
        "resource.html",
        {
            "user": user,
            "resource": resource,
            "slots": [(slot, slot in taken) for slot in slots],
            "error": error,
        },
    )


@router.post("/resources/{resource_id}/book")
def book_slot(
    resource_id: int,
    start_time: str = Form(...),
    db: Session = Depends(get_db),
    user=Depends(current_user),
):
    if user is None:
        return _login_redirect()

    start = datetime.fromisoformat(start_time)
    db.add(Booking(resource_id=resource_id, user_id=user.id, start_time=start))

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        return RedirectResponse(
            f"/ui/resources/{resource_id}?error=That+slot+was+just+taken", status_code=303
        )

    return RedirectResponse("/ui/bookings", status_code=303)


@router.get("/bookings", response_class=HTMLResponse)
def my_bookings(request: Request, db: Session = Depends(get_db), user=Depends(current_user)):
    if user is None:
        return _login_redirect()

    bookings = db.scalars(
        select(Booking)
        .where(Booking.user_id == user.id, Booking.cancelled_at.is_(None))
        .order_by(Booking.start_time)
    ).all()

    return templates.TemplateResponse(request, "bookings.html", {"user": user, "bookings": bookings})


@router.post("/bookings/{booking_id}/cancel")
def cancel(booking_id: int, db: Session = Depends(get_db), user=Depends(current_user)):
    if user is None:
        return _login_redirect()

    booking = db.get(Booking, booking_id)
    if booking is not None and booking.user_id == user.id and booking.cancelled_at is None:
        booking.cancelled_at = datetime.now(timezone.utc)
        db.commit()

    return RedirectResponse("/ui/bookings", status_code=303)


