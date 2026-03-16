"""Authentication API routes for Sancta Nexus.

Provides JWT-based user registration, login, token refresh, and profile
retrieval backed by the PostgreSQL database via async SQLAlchemy.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from sqlalchemy import select

from app.core.dependencies import DbSession
from app.core.security import (
    create_access_token,
    create_refresh_token,
    get_current_user,
    hash_password,
    verify_password,
    verify_token,
)
from app.core.config import settings
from app.models.database import User

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RegisterRequest(BaseModel):
    """User registration request."""

    model_config = ConfigDict(strict=True)

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., min_length=8, description="Password (min 8 characters).")
    display_name: str = Field(..., min_length=1, max_length=100, description="Display name.")


class UserInfo(BaseModel):
    """User info nested in auth responses."""

    id: str
    email: str
    displayName: str


class RegisterResponse(BaseModel):
    """User registration response."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserInfo


class LoginRequest(BaseModel):
    """User login request."""

    model_config = ConfigDict(strict=True)

    email: EmailStr = Field(..., description="User email address.")
    password: str = Field(..., description="User password.")


class LoginResponse(BaseModel):
    """User login response."""

    model_config = ConfigDict(strict=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token validity in seconds.")
    user: UserInfo


class RefreshRequest(BaseModel):
    """Token refresh request."""

    model_config = ConfigDict(strict=True)

    refresh_token: str = Field(..., description="A valid refresh token.")


class RefreshResponse(BaseModel):
    """Token refresh response."""

    model_config = ConfigDict(strict=True)

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(description="Access-token validity in seconds.")


class UserProfile(BaseModel):
    """Authenticated user profile."""

    model_config = ConfigDict(strict=True)

    user_id: str
    email: str
    display_name: str
    created_at: str


# ---------------------------------------------------------------------------
# POST /register
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
async def register(request: RegisterRequest, db: DbSession) -> RegisterResponse:
    """Register a new user account.

    Creates a new user with the provided email, password, and display name.
    Returns the created user profile.
    """
    # Check if email already taken
    existing = await db.execute(select(User).where(User.email == request.email))
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="A user with this email already exists.",
        )

    user = User(
        email=request.email,
        name=request.display_name,
        hashed_password=hash_password(request.password),
    )
    db.add(user)
    await db.flush()  # populate server defaults (id, created_at)
    await db.refresh(user)

    logger.info("Registered new user: %s (%s)", user.id, user.email)

    token_data = {"sub": user.id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return RegisterResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserInfo(id=user.id, email=user.email, displayName=user.name),
    )


# ---------------------------------------------------------------------------
# POST /login
# ---------------------------------------------------------------------------


@router.post(
    "/login",
    response_model=LoginResponse,
    summary="Authenticate and receive access + refresh tokens",
)
async def login(request: LoginRequest, db: DbSession) -> LoginResponse:
    """Authenticate a user with email and password.

    Returns JWT access and refresh tokens for subsequent authenticated
    requests.
    """
    result = await db.execute(select(User).where(User.email == request.email))
    user = result.scalar_one_or_none()

    if user is None or not verify_password(request.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token_data = {"sub": user.id}
    access_token = create_access_token(token_data)
    refresh_token = create_refresh_token(token_data)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return LoginResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=expires_in,
        user=UserInfo(id=user.id, email=user.email, displayName=user.name),
    )


# ---------------------------------------------------------------------------
# POST /refresh
# ---------------------------------------------------------------------------


@router.post(
    "/refresh",
    response_model=RefreshResponse,
    summary="Refresh an access token",
)
async def refresh(request: RefreshRequest, db: DbSession) -> RefreshResponse:
    """Exchange a valid refresh token for a new access + refresh token pair."""
    payload = verify_token(request.refresh_token, expected_type="refresh")
    user_id: str = payload["sub"]

    # Ensure the user still exists
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found.",
        )

    token_data = {"sub": user.id}
    access_token = create_access_token(token_data)
    new_refresh_token = create_refresh_token(token_data)
    expires_in = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    return RefreshResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=expires_in,
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
    current_user: User = Depends(get_current_user),
) -> UserProfile:
    """Return the profile of the currently authenticated user.

    Requires a valid bearer token in the Authorization header.
    """
    return UserProfile(
        user_id=current_user.id,
        email=current_user.email,
        display_name=current_user.name,
        created_at=current_user.created_at.isoformat(),
    )
