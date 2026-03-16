"""User profile and spiritual journey API routes for Sancta Nexus.

Provides endpoints for viewing and updating user profiles, and
retrieving a user's spiritual journey summary.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class UserProfileResponse(BaseModel):
    """Public user profile data."""

    model_config = ConfigDict(strict=True)

    user_id: str
    display_name: str
    spiritual_tradition: str = Field(
        default="ignatian",
        description="Preferred spiritual tradition.",
    )
    preferred_language: str = Field(default="pl", description="Preferred language code.")
    created_at: str
    sessions_count: int = Field(default=0, description="Total spiritual direction sessions.")


class UserProfileUpdate(BaseModel):
    """Fields that can be updated on a user profile."""

    model_config = ConfigDict(strict=True)

    display_name: str | None = Field(default=None, max_length=100)
    spiritual_tradition: str | None = Field(default=None)
    preferred_language: str | None = Field(default=None, max_length=5)


class SpiritualJourneyResponse(BaseModel):
    """Summary of a user's spiritual journey."""

    model_config = ConfigDict(strict=True)

    user_id: str
    total_sessions: int
    current_spiritual_state: str
    dominant_themes: list[str]
    recent_scriptures: list[str]
    ignatian_movement: str = Field(
        description="Overall movement direction: towards_consolation, towards_desolation, or stable.",
    )
    journey_start: str | None = Field(default=None, description="Date of first session.")
    milestones: list[dict[str, str]]


# ---------------------------------------------------------------------------
# In-memory store (MVP placeholder)
# ---------------------------------------------------------------------------

_profiles: dict[str, dict[str, Any]] = {}


def _get_or_create_profile(user_id: str) -> dict[str, Any]:
    """Retrieve a user profile, creating a default if none exists."""
    if user_id not in _profiles:
        _profiles[user_id] = {
            "user_id": user_id,
            "display_name": f"User {user_id[:8]}",
            "spiritual_tradition": "ignatian",
            "preferred_language": "pl",
            "created_at": datetime.utcnow().isoformat(),
            "sessions_count": 0,
        }
    return _profiles[user_id]


# ---------------------------------------------------------------------------
# GET /{user_id}/profile
# ---------------------------------------------------------------------------


@router.get(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    summary="Get a user's profile",
)
async def get_profile(user_id: str) -> UserProfileResponse:
    """Retrieve the profile for a given user.

    If no profile exists yet, a default one is created automatically.
    """
    profile = _get_or_create_profile(user_id)

    return UserProfileResponse(
        user_id=profile["user_id"],
        display_name=profile["display_name"],
        spiritual_tradition=profile["spiritual_tradition"],
        preferred_language=profile["preferred_language"],
        created_at=profile["created_at"],
        sessions_count=profile["sessions_count"],
    )


# ---------------------------------------------------------------------------
# PUT /{user_id}/profile
# ---------------------------------------------------------------------------


@router.put(
    "/{user_id}/profile",
    response_model=UserProfileResponse,
    summary="Update a user's profile",
)
async def update_profile(user_id: str, update: UserProfileUpdate) -> UserProfileResponse:
    """Update the profile for a given user.

    Only provided (non-null) fields are updated; omitted fields retain
    their current values.
    """
    profile = _get_or_create_profile(user_id)

    if update.display_name is not None:
        profile["display_name"] = update.display_name
    if update.spiritual_tradition is not None:
        valid_traditions = {"ignatian", "carmelite", "benedictine", "franciscan"}
        if update.spiritual_tradition.lower() not in valid_traditions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid tradition '{update.spiritual_tradition}'. "
                       f"Must be one of: {sorted(valid_traditions)}",
            )
        profile["spiritual_tradition"] = update.spiritual_tradition.lower()
    if update.preferred_language is not None:
        profile["preferred_language"] = update.preferred_language

    return UserProfileResponse(
        user_id=profile["user_id"],
        display_name=profile["display_name"],
        spiritual_tradition=profile["spiritual_tradition"],
        preferred_language=profile["preferred_language"],
        created_at=profile["created_at"],
        sessions_count=profile["sessions_count"],
    )


# ---------------------------------------------------------------------------
# GET /{user_id}/spiritual-journey
# ---------------------------------------------------------------------------


@router.get(
    "/{user_id}/spiritual-journey",
    response_model=SpiritualJourneyResponse,
    summary="Get a user's spiritual journey summary",
)
async def get_spiritual_journey(user_id: str) -> SpiritualJourneyResponse:
    """Retrieve a summary of the user's spiritual journey.

    Aggregates data from past sessions to provide an overview of
    spiritual themes, emotional patterns, scripture encounters,
    and overall Ignatian movement direction.
    """
    profile = _get_or_create_profile(user_id)

    # MVP placeholder: return a representative journey summary
    return SpiritualJourneyResponse(
        user_id=user_id,
        total_sessions=profile["sessions_count"],
        current_spiritual_state="peace",
        dominant_themes=[
            "Trust in God's providence",
            "Finding peace in uncertainty",
            "Growing in prayer",
        ],
        recent_scriptures=[
            "Ps 23:1-6",
            "Phil 4:6-7",
            "Is 41:10",
        ],
        ignatian_movement="stable",
        journey_start=profile["created_at"] if profile["sessions_count"] > 0 else None,
        milestones=[
            {
                "type": "first_session",
                "description": "First spiritual direction session completed",
                "date": profile["created_at"],
            },
        ] if profile["sessions_count"] > 0 else [],
    )
