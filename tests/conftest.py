from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from booking_api.database import Base, get_db
from booking_api.main import app
from booking_api.models import Role, User


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture()
def session_factory(tmp_path):
    engine = create_engine(
        f"sqlite:///{tmp_path / 'test.db'}",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(engine)
    yield sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    engine.dispose()


@pytest.fixture()
def client(session_factory):
    def override_get_db():
        db = session_factory()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


def _register_and_login(client, email: str) -> str:
    client.post("/auth/register", json={"email": email, "password": "password123"})
    response = client.post("/auth/login", data={"username": email, "password": "password123"})
    return response.json()["access_token"]


@pytest.fixture()
def user_token(client) -> str:
    return _register_and_login(client, "user@example.com")


@pytest.fixture()
def admin_token(client, session_factory) -> str:
    client.post("/auth/register", json={"email": "admin@example.com", "password": "password123"})

    with session_factory() as db:
        admin = db.scalar(select(User).where(User.email == "admin@example.com"))
        admin.role = Role.ADMIN
        db.commit()

    response = client.post(
        "/auth/login", data={"username": "admin@example.com", "password": "password123"}
    )
    return response.json()["access_token"]


@pytest.fixture()
def resource_id(client, admin_token) -> int:
    response = client.post(
        "/resources",
        json={"name": "Room A", "description": "Seats 8", "slot_minutes": 60},
        headers=auth(admin_token),
    )
    return response.json()["id"]


@pytest.fixture()
def future_slot() -> str:
    start = (datetime.now(timezone.utc) + timedelta(days=1)).replace(
        minute=0, second=0, microsecond=0
    )
    return start.isoformat().replace("+00:00", "Z")


