import sys

from sqlalchemy import select  # type: ignore[reportMissingImports]

from booking_api.database import SessionLocal
from booking_api.models import Role, User


def main() -> None:
    if len(sys.argv) != 2:
        raise SystemExit("Usage: python scripts/promote_admin.py <email>")

    email = sys.argv[1]

    with SessionLocal() as db:
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            raise SystemExit(f"No user found with email {email}")

        user.role = Role.ADMIN
        db.commit()
        print(f"{email} is now an admin")


if __name__ == "__main__":
    main()


