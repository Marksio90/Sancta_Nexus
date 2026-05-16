"""Diocese licensing API — B2B SaaS for dioceses.

Business model:
  A diocese signs an annual contract (handled via Stripe).  Once activated,
  all priests and lay leaders in the diocese get DISCIPLE-tier access.
  The diocese IT contact manages member activation via this API.

Endpoints:
  POST /api/v1/diocese/register          — create diocese license (admin only)
  GET  /api/v1/diocese/{code}             — get diocese info (admin only)
  POST /api/v1/diocese/{code}/activate    — activate a user under a diocese license
  GET  /api/v1/diocese/{code}/stats       — member count, active sessions (admin)
  POST /api/v1/diocese/{code}/deactivate  — remove a user from diocese (admin)
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import func, select

from app.core.dependencies import DbSession
from app.core.rbac import require_admin
from app.models.database import DioceseLicense, SubscriptionTier, User
from app.models.database import AuditEventType
from app.services.audit.audit_service import audit

logger = logging.getLogger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class RegisterDioceseRequest(BaseModel):
    name: str = Field(..., min_length=3, max_length=300)
    country: str = Field(default="PL", min_length=2, max_length=2)
    diocese_code: str = Field(..., min_length=2, max_length=50, description="Unique short code, e.g. 'krakow-archdiocese'")
    contact_email: EmailStr
    max_users: int = Field(default=0, ge=0, description="0 = unlimited")
    stripe_subscription_id: str | None = None
    license_starts_at: str | None = None
    license_expires_at: str | None = None


class DioceseResponse(BaseModel):
    id: str
    name: str
    country: str
    diocese_code: str
    contact_email: str
    max_users: int
    is_active: bool
    stripe_subscription_id: str | None
    license_starts_at: str | None
    license_expires_at: str | None
    created_at: str


class ActivateUserRequest(BaseModel):
    user_email: EmailStr


class DioceseStatsResponse(BaseModel):
    diocese_id: str
    diocese_name: str
    total_members: int
    max_users: int
    is_within_limit: bool
    is_active: bool


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _diocese_to_response(d: DioceseLicense) -> DioceseResponse:
    return DioceseResponse(
        id=d.id,
        name=d.name,
        country=d.country,
        diocese_code=d.diocese_code,
        contact_email=d.contact_email,
        max_users=d.max_users,
        is_active=d.is_active,
        stripe_subscription_id=d.stripe_subscription_id,
        license_starts_at=d.license_starts_at.isoformat() if d.license_starts_at else None,
        license_expires_at=d.license_expires_at.isoformat() if d.license_expires_at else None,
        created_at=d.created_at.isoformat(),
    )


async def _get_diocese_by_code(db: DbSession, code: str) -> DioceseLicense:
    result = await db.execute(
        select(DioceseLicense).where(DioceseLicense.diocese_code == code)
    )
    diocese = result.scalar_one_or_none()
    if diocese is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Diocese '{code}' not found.",
        )
    return diocese


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/register",
    response_model=DioceseResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new diocese license (admin only)",
)
async def register_diocese(
    body: RegisterDioceseRequest,
    db: DbSession,
    admin_user: User = require_admin,
) -> DioceseResponse:
    """Create a diocese license record.

    Called by the Sancta Nexus sales team after the diocese signs a contract.
    The ``diocese_code`` becomes the identifier used in all subsequent API calls.
    """
    from sqlalchemy.exc import IntegrityError

    diocese = DioceseLicense(
        name=body.name,
        country=body.country.upper(),
        diocese_code=body.diocese_code.lower().replace(" ", "-"),
        contact_email=body.contact_email,
        max_users=body.max_users,
        stripe_subscription_id=body.stripe_subscription_id,
        license_starts_at=(
            datetime.fromisoformat(body.license_starts_at) if body.license_starts_at else None
        ),
        license_expires_at=(
            datetime.fromisoformat(body.license_expires_at) if body.license_expires_at else None
        ),
    )
    db.add(diocese)
    try:
        await db.flush()
        await db.refresh(diocese)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Diocese code '{body.diocese_code}' already exists.",
        )

    await audit(
        db=db,
        event_type=AuditEventType.CONTENT_CREATED,
        user_id=admin_user.id,
        detail=f"Diocese license registered: code={diocese.diocese_code} name={diocese.name}",
    )

    logger.info("Diocese registered: code=%s name=%s", diocese.diocese_code, diocese.name)
    return _diocese_to_response(diocese)


@router.get(
    "/{diocese_code}",
    response_model=DioceseResponse,
    summary="Get diocese license details (admin only)",
)
async def get_diocese(
    diocese_code: str,
    db: DbSession,
    admin_user: User = require_admin,  # noqa: ARG001
) -> DioceseResponse:
    """Retrieve a diocese license by code."""
    diocese = await _get_diocese_by_code(db, diocese_code)
    return _diocese_to_response(diocese)


@router.post(
    "/{diocese_code}/activate",
    response_model=dict,
    summary="Activate a user under a diocese license",
)
async def activate_user_for_diocese(
    diocese_code: str,
    body: ActivateUserRequest,
    db: DbSession,
    admin_user: User = require_admin,
) -> dict:
    """Grant diocese-level access to a user.

    Sets the user's ``diocese_id`` and upgrades their subscription to
    ``DISCIPLE`` tier.  If the license has a ``max_users`` limit and it
    has been reached, the request is rejected.
    """
    diocese = await _get_diocese_by_code(db, diocese_code)

    if not diocese.is_active:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Diocese license is not active.",
        )

    # Check if license has expired
    if diocese.license_expires_at and diocese.license_expires_at < datetime.now(UTC):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail="Diocese license has expired.",
        )

    # Check user limit
    if diocese.max_users > 0:
        count_result = await db.execute(
            select(func.count()).where(User.diocese_id == diocese.id)
        )
        current_count = count_result.scalar() or 0
        if current_count >= diocese.max_users:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Diocese license limit reached ({diocese.max_users} users).",
            )

    # Find user by email
    user_result = await db.execute(select(User).where(User.email == body.user_email))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_email}' not found.",
        )

    if user.diocese_id == diocese.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is already activated under this diocese.",
        )

    user.diocese_id = diocese.id
    user.subscription_tier = SubscriptionTier.DISCIPLE
    await db.flush()

    await audit(
        db=db,
        event_type=AuditEventType.USER_ROLE_CHANGED,
        user_id=admin_user.id,
        detail=f"Diocese activation: user={body.user_email} diocese={diocese_code} tier=disciple",
    )

    logger.info(
        "Diocese activation: user=%s diocese=%s", body.user_email, diocese_code
    )

    return {
        "message": f"User '{body.user_email}' activated under diocese '{diocese.name}'.",
        "user_email": body.user_email,
        "diocese_code": diocese_code,
        "subscription_tier": SubscriptionTier.DISCIPLE.value,
    }


@router.get(
    "/{diocese_code}/stats",
    response_model=DioceseStatsResponse,
    summary="Diocese membership statistics (admin only)",
)
async def get_diocese_stats(
    diocese_code: str,
    db: DbSession,
    admin_user: User = require_admin,  # noqa: ARG001
) -> DioceseStatsResponse:
    """Return membership count and limit status for a diocese."""
    diocese = await _get_diocese_by_code(db, diocese_code)

    count_result = await db.execute(
        select(func.count()).where(User.diocese_id == diocese.id)
    )
    total_members = count_result.scalar() or 0

    is_within = diocese.max_users == 0 or total_members <= diocese.max_users

    return DioceseStatsResponse(
        diocese_id=diocese.id,
        diocese_name=diocese.name,
        total_members=total_members,
        max_users=diocese.max_users,
        is_within_limit=is_within,
        is_active=diocese.is_active,
    )


@router.post(
    "/{diocese_code}/deactivate",
    response_model=dict,
    summary="Remove a user from diocese license",
)
async def deactivate_user_for_diocese(
    diocese_code: str,
    body: ActivateUserRequest,
    db: DbSession,
    admin_user: User = require_admin,
) -> dict:
    """Remove diocese access from a user.

    Clears ``diocese_id`` and downgrades subscription back to ``FREE``.
    """
    diocese = await _get_diocese_by_code(db, diocese_code)

    user_result = await db.execute(select(User).where(User.email == body.user_email))
    user = user_result.scalar_one_or_none()
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{body.user_email}' not found.",
        )

    if user.diocese_id != diocese.id:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User is not a member of this diocese.",
        )

    user.diocese_id = None
    user.subscription_tier = SubscriptionTier.FREE
    await db.flush()

    await audit(
        db=db,
        event_type=AuditEventType.USER_ROLE_CHANGED,
        user_id=admin_user.id,
        detail=f"Diocese deactivation: user={body.user_email} diocese={diocese_code}",
    )

    return {
        "message": f"User '{body.user_email}' removed from diocese '{diocese.name}'.",
        "user_email": body.user_email,
        "diocese_code": diocese_code,
    }
