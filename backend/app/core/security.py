import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


# --- Robot API keys ---------------------------------------------------------
# API keys are high-entropy (32 random bytes), so a fast deterministic SHA-256
# is sufficient and — unlike a salted password hash — lets us look the key up
# with an indexed equality query. Only the hash is ever stored; the raw key is
# shown to the operator exactly once, at creation/rotation time.

def generate_api_key() -> str:
    """Return a fresh, URL-safe raw API key (~43 chars)."""
    return secrets.token_urlsafe(32)


def hash_api_key(raw: str) -> str:
    """Deterministic SHA-256 hex digest used for storage and lookup."""
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def api_key_prefix(raw: str, length: int = 8) -> str:
    """Short, non-secret identifier shown in listings (e.g. 'x7Qk9aB2')."""
    return raw[:length]


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(subject: str | int, extra: dict[str, Any] | None = None) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload: dict[str, Any] = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "access",
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(subject: str | int) -> str:
    now = datetime.now(timezone.utc)
    expires = now + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": str(subject),
        "iat": int(now.timestamp()),
        "exp": int(expires.timestamp()),
        "type": "refresh",
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def decode_token(token: str) -> dict[str, Any]:
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        raise ValueError("invalid token") from exc
