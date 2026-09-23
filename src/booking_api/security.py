from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from .config import settings

ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_access_token(subject: str, role: str) -> str:
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_minutes)
    return jwt.encode(
        {"sub": subject, "role": role, "exp": expires_at},
        settings.secret_key,
        algorithm=ALGORITHM,
    )


def decode_access_token(token: str) -> dict:
    return jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])


