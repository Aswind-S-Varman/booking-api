from sqlalchemy import select

from booking_api.database import SessionLocal
from booking_api.models import Resource, Role, User
from booking_api.security import hash_password

ACCOUNTS = [
    ("admin@example.com", Role.ADMIN),
    ("user@example.com", Role.USER),
]
RESOURCES = [
    ("Meeting Room A", "Seats 8, projector", 60),
    ("Meeting Room B", "Seats 4", 30),
    ("Company Car", "Bookable by the hour", 60),
]


def main() -> None:
    with SessionLocal() as db:
        for email, role in ACCOUNTS:
            if db.scalar(select(User).where(User.email == email)):
                continue
            db.add(User(email=email, hashed_password=hash_password("password123"), role=role))

        for name, description, slot_minutes in RESOURCES:
            if db.scalar(select(Resource).where(Resource.name == name)):
                continue
            db.add(Resource(name=name, description=description, slot_minutes=slot_minutes))

        db.commit()

    print("Seeded. Log in as admin@example.com or user@example.com with password123")


if __name__ == "__main__":
    main()


