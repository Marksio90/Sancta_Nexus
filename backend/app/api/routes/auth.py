"""Authentication API routes for Sancta Nexus.

Provides placeholder endpoints for user registration, login, and
profile retrieval. A production implementation would integrate with
a proper authentication backend (e.g. Firebase Auth, Auth0, or
a custom JWT solution).
"""

from __future__ import annotations

import hashlib
import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, EmailStr, Field

logger = logging.getLogger(__name__)

router = APIRouter()

security = HTTPBearer(auto_error=False)

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """User registration request."""

    model_config = ConfigDict(strict=True)

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., min_length=8, description="Password (min 8 characters).")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name.")


class RegisterResponse(BaseModel):
    """User registration response."""

    model_config = ConfigDict(strict=True)

    user_id: str
    email: str
    display_name: str
    created_at: str


class LoginRequest(BaseModel):
    """User login request."""

    model_config = ConfigDict(strict=True)

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., description="User password.")


class LoginResponse(BaseModel):
    """User login response."""

    model_config = ConfigDict(strict=True)

    access_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Token validity in seconds.")
    user_id: str


class UserProfile(BaseModel):
    """Authenticated user profile."""

    model_config = ConfigDict(strict=True)

    user_id: str
    email: str
    display_name: str
    created_at: str


# ---------------------------------------------------------------------------
# In-memory user store (MVP placeholder)
# ---------------------------------------------------------------------------

_users: dict[str, dict[str, Any]] = {}
_tokens: dict[str, str] = {}  # token -> user_id


def _hash_password(password: str) -> str:
    """Create a simple hash of the password (placeholder, not production-safe)."""
    return hashlib.sha256(password.encode()).hexdigest()


def _generate_token(user_id: str) -> str:
    """Generate a placeholder bearer token."""
    token = str(uuid.uuid4())
    _tokens[token] = user_id
    return token


async def _get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> dict[str, Any]:
    """Extract the current user from the bearer token."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = _tokens.get(credentials.credentials)
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = _users.get(user_id)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(request: RegisterRequest) -> RegisterResponse:
    """Register a new user account.

    Creates a new user with the provided email, password, and display name.
    Returns the created user profile.
    """
    # Check if email already exists
    for user in _users.values():
        if user["email"] == request.email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="A user with this email already exists.",
            )

    user_id = str(uuid.uuid4())
    now = datetime.utcnow().isoformat()

    _users[user_id] = {
        "user_id": user_id,
        "email": request.email,
        "display_name": request.display_name,
        "password_hash": _hash_password(request.password),
        "created_at": now,
    }

    logger.info("Registered new user: %s (%s)", user_id, request.email)

    return RegisterResponse(
        user_id=user_id,
        email=request.email,
        display_name=request.display_name,
        created_at=now,
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and receive an access token",
)
async def login(request: LoginRequest) -> LoginResponse:
    """Authenticate a user with email and password.

    Returns a bearer token for subsequent authenticated requests.
    """
    password_hash = _hash_password(request.password)

    matched_user: dict[str, Any] | None = None
    for user in _users.values():
        if user["email"] == request.email and user["password_hash"] == password_hash:
            matched_user = user
            break

    if matched_user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = _generate_token(matched_user["user_id"])
    expires_in = int(timedelta(hours=24).total_seconds())

    return LoginResponse(
        access_token=token,
        expires_in=expires_in,
        user_id=matched_user["user_id"],
    )


# ---------------------------------------------------------------------------
# GET /me
# ---------------------------------------------------------------------------


@router.get(
    "/me",
    response_model=UserProfile,
    summary="Get the current authenticated user's profile",
)
async def get_me(
    current_user: dict[str, Any] = Depends(_get_current_user),
) -> UserProfile:
    """Return the profile of the currently authenticated user.

    Requires a valid bearer token in the Authorization header.
    """
    return UserProfile(
        user_id=current_user["user_id"],
        email=current_user["email"],
        display_name=current_user["display_name"],
        created_at=current_user["created_at"],
    )
