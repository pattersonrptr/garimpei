"""JWT access tokens: the claims of a user and how long a token lasts."""

from datetime import UTC, datetime, timedelta
from typing import Any

from jose import jwt

from src.app.accounts.entities import User
from src.config import settings


def create_access_token(user: User) -> str:
    """A signed token for ``user`` that expires after ACCESS_TOKEN_EXPIRE_MINUTES."""
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    claims = {
        "sub": user.username,
        "user_id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
        "is_superuser": user.is_superuser,
        "exp": expire,
    }
    return jwt.encode(claims, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """The token's claims; raises ``jose.JWTError`` when it is invalid or expired."""
    return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
