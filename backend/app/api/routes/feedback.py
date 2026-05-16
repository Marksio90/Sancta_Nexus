"""AI response feedback endpoint.

Accepts thumbs up/down ratings and flag reports on AI-generated content.
Currently stores nothing — logs to audit trail and returns 204.
Analytics aggregation and dashboard integration are Phase 2 items.
"""

from __future__ import annotations

import logging
from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel, Field

from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import AuditEventType, User
from app.services.audit.audit_service import audit

logger = logging.getLogger(__name__)

router = APIRouter()


class FeedbackRequest(BaseModel):
    module: str = Field(..., min_length=1, max_length=64)
    content_id: str | None = Field(default=None, max_length=128)
    rating: Literal["up", "down"] | None = None
    flag: Literal["theologically_incorrect", "repetitive_or_generic", "other"] | None = None


@router.post("", status_code=status.HTTP_204_NO_CONTENT, summary="Zapisz opinię o odpowiedzi AI")
async def submit_feedback(
    body: FeedbackRequest,
    db: DbSession,
    current_user: User = require_authenticated,
) -> None:
    """Record user feedback on an AI-generated response.

    Writes to the audit log so the data is available for review.
    A future sprint will aggregate this into a dedicated feedback analytics table.
    """
    desc = (
        f"AI feedback: module={body.module} "
        f"rating={body.rating} flag={body.flag} content_id={body.content_id}"
    )
    await audit.log(
        db,
        event_type=AuditEventType.AI_RESPONSE_GENERATED,
        description=desc,
        user_id=current_user.id,
        payload={
            "module": body.module,
            "content_id": body.content_id,
            "rating": body.rating,
            "flag": body.flag,
        },
    )
    logger.info("Feedback recorded: user=%s module=%s rating=%s flag=%s",
                current_user.id, body.module, body.rating, body.flag)
