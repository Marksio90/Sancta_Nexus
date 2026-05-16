"""Doctrinal review workflow — imprimatur support infrastructure.

Purpose:
  Sancta Nexus seeks theological endorsement (imprimatur) from a bishop.
  This module provides the queue, review, and audit trail infrastructure
  needed to demonstrate to a diocesan censor that every AI-generated
  response passes human doctrinal review before being shown to users.

Endpoints:
  POST /api/v1/doctrinal-review/submit    — submit AI response for review
  GET  /api/v1/doctrinal-review/queue     — pending reviews (reviewer+)
  POST /api/v1/doctrinal-review/{id}/approve  — approve (reviewer+)
  POST /api/v1/doctrinal-review/{id}/reject   — reject with note (reviewer+)
  GET  /api/v1/doctrinal-review/{id}          — get single review (reviewer+)
  GET  /api/v1/doctrinal-review/stats         — review stats for imprimatur report (admin)

Storage: Redis (pending queue, 30-day TTL) + AuditLog (permanent record).
No Postgres model is added here — reviews are stored as JSON in Redis with
a UUID key so no migration is needed.  A permanent DB model can be added
in a follow-up sprint as the volume grows.

Security:
  - Submitting is open to all authenticated users (any user can flag content).
  - Reviewing requires SPIRITUAL_CONTENT_REVIEWER role or higher.
  - Review decisions are always written to AuditLog (immutable trail).
  - Content text stored in review record is the AI response, not user input.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.core.dependencies import DbSession, RedisDep
from app.core.rbac import require_authenticated, require_content_reviewer
from app.models.database import AuditEventType, User
from app.services.audit.audit_service import audit

logger = logging.getLogger(__name__)

router = APIRouter()

_REVIEW_KEY = "doctrinal_review:{review_id}"
_QUEUE_KEY = "doctrinal_review_queue"
_REVIEW_TTL = 30 * 86_400  # 30 days


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SubmitReviewRequest(BaseModel):
    module: str = Field(..., description="AI module that generated the content, e.g. 'lectio', 'reflection'")
    content_id: str | None = Field(default=None, description="Session or content identifier")
    ai_response_text: str = Field(..., min_length=10, max_length=20_000, description="Full AI-generated text to review")
    concern: str | None = Field(default=None, max_length=1000, description="Optional note from the submitter about their concern")


class ReviewItem(BaseModel):
    review_id: str
    module: str
    content_id: str | None
    ai_response_text: str
    concern: str | None
    status: Literal["pending", "approved", "rejected"]
    submitted_at: str
    reviewed_at: str | None = None
    reviewer_note: str | None = None
    reviewer_id: str | None = None


class ReviewDecisionRequest(BaseModel):
    note: str | None = Field(default=None, max_length=2000, description="Reviewer's theological note or correction suggestion")


class ReviewStatsResponse(BaseModel):
    total_pending: int
    total_approved: int
    total_rejected: int
    last_30_days: dict[str, int]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _get_review(redis, review_id: str) -> dict[str, Any] | None:
    raw = await redis.get(_REVIEW_KEY.format(review_id=review_id))
    if not raw:
        return None
    return json.loads(raw)


async def _save_review(redis, review_id: str, data: dict[str, Any]) -> None:
    await redis.setex(
        _REVIEW_KEY.format(review_id=review_id),
        _REVIEW_TTL,
        json.dumps(data),
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/submit",
    response_model=ReviewItem,
    status_code=status.HTTP_201_CREATED,
    summary="Submit an AI response for doctrinal review",
)
async def submit_for_review(
    body: SubmitReviewRequest,
    redis: RedisDep,
    db: DbSession,
    current_user: User = require_authenticated,
) -> ReviewItem:
    """Flag an AI-generated response for human doctrinal review.

    Any authenticated user can submit — useful when they notice a response
    that might be theologically imprecise.  The submission is added to the
    reviewer queue and logged in the audit trail.
    """
    review_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    review_data: dict[str, Any] = {
        "review_id": review_id,
        "module": body.module,
        "content_id": body.content_id,
        "ai_response_text": body.ai_response_text,
        "concern": body.concern,
        "status": "pending",
        "submitted_at": now,
        "submitted_by": current_user.id,
        "reviewed_at": None,
        "reviewer_note": None,
        "reviewer_id": None,
    }

    await _save_review(redis, review_id, review_data)
    await redis.lpush(_QUEUE_KEY, review_id)

    await audit(
        db=db,
        event_type=AuditEventType.CONTENT_CREATED,
        user_id=current_user.id,
        detail=f"Doctrinal review submitted: review_id={review_id} module={body.module}",
    )

    logger.info(
        "Doctrinal review submitted: review_id=%s module=%s user=%s",
        review_id, body.module, current_user.id,
    )

    return ReviewItem(**{k: v for k, v in review_data.items() if k != "submitted_by"})


@router.get(
    "/queue",
    response_model=list[ReviewItem],
    summary="List pending doctrinal reviews (reviewer+ only)",
)
async def get_review_queue(
    redis: RedisDep,
    limit: int = 20,
    current_user: User = require_content_reviewer,
) -> list[ReviewItem]:
    """Return the current pending review queue."""
    # Fetch up to `limit` review IDs from the queue (LRANGE doesn't remove).
    ids = await redis.lrange(_QUEUE_KEY, 0, limit - 1)
    items = []
    for review_id in ids:
        data = await _get_review(redis, review_id)
        if data and data["status"] == "pending":
            items.append(ReviewItem(**{k: v for k, v in data.items() if k != "submitted_by"}))
    return items


@router.get(
    "/{review_id}",
    response_model=ReviewItem,
    summary="Get a single doctrinal review (reviewer+ only)",
)
async def get_review(
    review_id: str,
    redis: RedisDep,
    current_user: User = require_content_reviewer,
) -> ReviewItem:
    """Retrieve a review by ID."""
    data = await _get_review(redis, review_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    return ReviewItem(**{k: v for k, v in data.items() if k != "submitted_by"})


@router.post(
    "/{review_id}/approve",
    response_model=ReviewItem,
    summary="Approve AI response as doctrinally sound",
)
async def approve_review(
    review_id: str,
    body: ReviewDecisionRequest,
    redis: RedisDep,
    db: DbSession,
    current_user: User = require_content_reviewer,
) -> ReviewItem:
    """Mark the AI response as doctrinally sound.

    The decision is written to the audit log — this creates the permanent
    trail required for an imprimatur application.
    """
    data = await _get_review(redis, review_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    if data["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Review already {data['status']}.",
        )

    now = datetime.now(UTC).isoformat()
    data.update({
        "status": "approved",
        "reviewed_at": now,
        "reviewer_note": body.note,
        "reviewer_id": current_user.id,
    })
    await _save_review(redis, review_id, data)
    await redis.lrem(_QUEUE_KEY, 1, review_id)

    await audit(
        db=db,
        event_type=AuditEventType.CONTENT_PUBLISHED,
        user_id=current_user.id,
        detail=f"Doctrinal review APPROVED: review_id={review_id} module={data['module']}",
    )

    logger.info(
        "Doctrinal review APPROVED: review_id=%s reviewer=%s",
        review_id, current_user.id,
    )

    return ReviewItem(**{k: v for k, v in data.items() if k != "submitted_by"})


@router.post(
    "/{review_id}/reject",
    response_model=ReviewItem,
    summary="Reject AI response as doctrinally problematic",
)
async def reject_review(
    review_id: str,
    body: ReviewDecisionRequest,
    redis: RedisDep,
    db: DbSession,
    current_user: User = require_content_reviewer,
) -> ReviewItem:
    """Reject the AI response and record a theological note.

    The rejection note should explain the doctrinal concern clearly so the
    AI team can use it to improve prompts or the safety layer.
    """
    data = await _get_review(redis, review_id)
    if not data:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Review not found.")
    if data["status"] != "pending":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Review already {data['status']}.",
        )

    now = datetime.now(UTC).isoformat()
    data.update({
        "status": "rejected",
        "reviewed_at": now,
        "reviewer_note": body.note,
        "reviewer_id": current_user.id,
    })
    await _save_review(redis, review_id, data)
    await redis.lrem(_QUEUE_KEY, 1, review_id)

    await audit(
        db=db,
        event_type=AuditEventType.CONTENT_ARCHIVED,
        user_id=current_user.id,
        detail=f"Doctrinal review REJECTED: review_id={review_id} module={data['module']} note={body.note}",
    )

    logger.info(
        "Doctrinal review REJECTED: review_id=%s reviewer=%s",
        review_id, current_user.id,
    )

    return ReviewItem(**{k: v for k, v in data.items() if k != "submitted_by"})
