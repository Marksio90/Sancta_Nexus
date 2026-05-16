"""JWT authentication and password-hashing utilities for Sancta Nexus.

Provides:
    - ``create_access_token`` / ``create_refresh_token`` — signed JWT helpers
    - ``verify_token`` — decode & validate a JWT, returning its claims
    - ``hash_password`` / ``verify_password`` — bcrypt wrappers via *passlib*
    - ``get_current_user`` — FastAPI dependency that extracts the authenticated
      ``User`` ORM instance from the ``Authorization: Bearer <token>`` header
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db
from app.models.database import User

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(plain: str) -> str:
    """Return a bcrypt hash of *plain*."""
    return _pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    """Return ``True`` when *plain* matches the bcrypt *hashed* value."""
    return _pwd_context.verify(plain, hashed)


# ---------------------------------------------------------------------------
# JWT token creation
# ---------------------------------------------------------------------------

_REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT access token.

    Parameters
    ----------
    data:
        Payload claims.  Must include ``"sub"`` (user id).
    expires_delta:
        Custom lifetime; falls back to ``ACCESS_TOKEN_EXPIRE_MINUTES`` from
        settings.
    """
    to_encode = data.copy()
    expire = datetime.now(UTC) + (
        expires_delta
        if expires_delta is not None
        else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire, "type": "access"})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def create_refresh_token(
    data: dict[str, Any],
    expires_delta: timedelta | None = None,
) -> str:
    """Create a signed JWT refresh token (longer-lived).

    Each token receives a unique ``jti`` (JWT ID) so it can be individually
    revoked in Redis on use, preventing replay attacks.
    """
    to_encode = data.copy()
    lifetime = expires_delta if expires_delta is not None else timedelta(days=_REFRESH_TOKEN_EXPIRE_DAYS)
    expire = datetime.now(UTC) + lifetime
    to_encode.update({"exp": expire, "type": "refresh", "jti": str(uuid4())})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


# ---------------------------------------------------------------------------
# Refresh-token revocation (Redis blocklist)
# ---------------------------------------------------------------------------

_REVOKED_PREFIX = "revoked_jti:"


async def revoke_refresh_token(redis, jti: str, expires_at: datetime) -> None:
    """Store *jti* in Redis until the token naturally expires.

    The TTL is set to the token's remaining lifetime so the blocklist entry
    is automatically cleaned up — we never store stale entries forever.
    """
    remaining = int((expires_at - datetime.now(UTC)).total_seconds())
    if remaining > 0:
        await redis.setex(f"{_REVOKED_PREFIX}{jti}", remaining, "1")


async def is_refresh_token_revoked(redis, jti: str) -> bool:
    """Return True if *jti* has been revoked (already used or explicitly invalidated)."""
    return bool(await redis.exists(f"{_REVOKED_PREFIX}{jti}"))


# ---------------------------------------------------------------------------
# Token verification
# ---------------------------------------------------------------------------


def verify_token(token: str, *, expected_type: str = "access") -> dict[str, Any]:
    """Decode a JWT and return its claims.

    Raises
    ------
    HTTPException (401)
        If the token is invalid, expired, or has the wrong ``type`` claim.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired token.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload: dict[str, Any] = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )
    except JWTError as err:
        raise credentials_exception from err

    if payload.get("type") != expected_type:
        raise credentials_exception

    if payload.get("sub") is None:
        raise credentials_exception

    return payload


# ---------------------------------------------------------------------------
# FastAPI dependency — get_current_user
# ---------------------------------------------------------------------------

_bearer_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Extract and return the authenticated ``User`` from the JWT bearer token.

    Intended for use as a FastAPI dependency::

        @router.get("/protected")
        async def protected(user: User = Depends(get_current_user)):
            ...
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = verify_token(credentials.credentials, expected_type="access")
    user_id: str = payload["sub"]

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user
