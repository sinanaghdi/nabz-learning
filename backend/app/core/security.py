from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from app.core.config import settings

password_hash = PasswordHash.recommended()


def hash_password(password: str) -> str:
    """Hash a password using the recommended Argon2 configuration."""
    return password_hash.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Compare a submitted password with its stored Argon2 hash."""
    return password_hash.verify(plain_password, hashed_password)


def create_access_token(subject: str) -> str:
    """Issue a short-lived signed bearer token for an authenticated user."""
    now = datetime.now(UTC)
    expires_at = now + timedelta(minutes=settings.jwt_access_token_minutes)
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "iat": now,
        "exp": expires_at,
    }
    return jwt.encode(claims, settings.jwt_secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict[str, object]:
    """Verify token signature, expiry, and issuer before returning its claims."""
    return jwt.decode(
        token,
        settings.jwt_secret_key,
        algorithms=["HS256"],
        issuer=settings.jwt_issuer,
        options={"require": ["sub", "iss", "iat", "exp"]},
    )
