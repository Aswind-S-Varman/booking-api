# booking-api

Book shared resources without double-booking them. FastAPI, SQLAlchemy, JWT auth, and a
server-rendered booking interface.

![tests](https://github.com/Aswind-S-Varman/booking-api/actions/workflows/tests.yml/badge.svg)

## The problem

Any shared-resource booking system has one requirement that must never fail: two people
cannot hold the same slot. That sounds trivial until two requests arrive at the same
moment. The obvious implementation — check whether the slot is free, then insert — looks
correct and is wrong. Between the check and the insert, another request can claim it.

This project solves that at the database level and proves it with a test.

## Features

- Registration and login with bcrypt-hashed passwords and JWT access tokens
- Role-based access: only admins create or modify resources
- Booking, listing, and cancellation with slot-boundary and future-date validation
- Guaranteed conflict-free slots, enforced by a partial unique index
- Cancellation preserves history rather than deleting rows
- Server-rendered UI (Jinja2) alongside the JSON API
- Interactive OpenAPI docs at `/docs`

## Quick start

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -e ".[dev]"
alembic upgrade head
python scripts/seed.py
uvicorn booking_api.main:app --reload
```

- UI: http://127.0.0.1:8000/ — log in as `user@example.com` / `password123`
- API docs: http://127.0.0.1:8000/docs

## How double-booking is prevented

`bookings` carries a partial unique index:

```sql
CREATE UNIQUE INDEX uq_active_booking_slot
ON bookings (resource_id, start_time)
WHERE cancelled_at IS NULL;
```

The endpoint does not check availability before inserting. It attempts the insert and
translates the resulting `IntegrityError` into `409 Conflict`. The database arbitrates
atomically: one request wins, the other gets a clean conflict.

`tests/test_bookings.py::test_database_constraint_blocks_concurrent_bookings` opens two
independent sessions, has both insert the same slot, and asserts the second is rejected.

## Design decisions

**Correctness lives in the database.** Application-level checks cannot close a race window;
a constraint can. The endpoint's job is translating a constraint violation into a sensible
HTTP status.

**Bookings are discrete slots, not arbitrary ranges.** Storing a `start_time` plus a
per-resource `slot_minutes` means a plain unique index prevents overlap. Arbitrary
start/end ranges would require a PostgreSQL exclusion constraint over a range type — more
flexible, but tied to one database engine.

**Cancellation sets a timestamp.** Deleting would lose the audit trail. The index's
`WHERE cancelled_at IS NULL` clause means cancelled rows stay without blocking the slot.

**Deactivate rather than delete resources.** A hard delete would cascade to bookings and
destroy history.

**Cookies for the UI, headers for the API.** Same JWT, two transports. The cookie is
`httponly` so JavaScript cannot read it, which limits the damage an XSS bug could do.

**Someone else's booking returns 404, not 403.** A 403 confirms the record exists. The same
reasoning makes login return one error for both unknown emails and wrong passwords.

## Known limitations

- Role changes do not take effect until the user logs in again, because the role is carried
  in the JWT. Production systems address this with short-lived tokens plus refresh tokens,
  or a revocation list.
- SQLite by default. `DATABASE_URL` accepts PostgreSQL, but SQLite stores datetimes without
  timezone information, which is why the code re-attaches UTC on read.
- No password reset, email verification, or login rate limiting.
- The API owns `/resources`, so the UI lives under `/ui`. Serving the API from `/api/v1`
  would be cleaner and leave room for versioning.
- `scripts/set_password.py` is a local development convenience and bypasses the checks a
  real reset flow would need.

## Tests

```bash
pytest -v
```

Covers authentication, role enforcement, booking validation rules, cancellation behaviour,
slot generation, and the concurrency constraint.

## License

MIT


