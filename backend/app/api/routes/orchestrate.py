"""Orchestrate API route.

Exposes OrchestratorSupremus (A-001) as a single POST endpoint that
accepts user context and routes to the appropriate LangGraph sub-graph:
lectio_divina, free_reflection, interactive_bible, spiritual_direction,
community, or crisis.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


class OrchestrateRequest(BaseModel):
    """Request body for orchestrating a spiritual guidance session."""

    user_id: str = "anonymous"
    emotion_vector: dict[str, float] = Field(default_factory=dict)
    spiritual_state: dict[str, Any] = Field(default_factory=dict)
    intent: str | None = None  # if set, intent routing is skipped
    tradition: str = ""
    session_history: list[dict[str, Any]] = Field(default_factory=list)


class OrchestrateResponse(BaseModel):
    """Response from the OrchestratorSupremus pipeline."""

    user_id: str
    intent: str = ""
    scripture: dict[str, Any] | None = None
    meditation: dict[str, Any] | None = None
    prayer: dict[str, Any] | None = None
    contemplation: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    theological_validation: dict[str, Any] | None = None
    error: str | None = None


@router.post("", response_model=OrchestrateResponse, status_code=status.HTTP_200_OK)
async def orchestrate(request: OrchestrateRequest) -> OrchestrateResponse:
    """Run the full OrchestratorSupremus (A-001) pipeline.

    The orchestrator classifies user intent via LLM and dispatches to the
    appropriate sub-graph (Lectio Divina supervisor, etc.).  A QualityGate
    agent validates the final output before returning.

    Valid intents: ``lectio_divina``, ``free_reflection``,
    ``interactive_bible``, ``spiritual_direction``, ``community``,
    ``crisis``.
    """
    from app.agents.orchestration.orchestrator_supremus import OrchestratorSupremus

    orchestrator = OrchestratorSupremus()

    initial_state: dict[str, Any] = {
        "user_id": request.user_id,
        "emotion_vector": request.emotion_vector,
        "spiritual_state": request.spiritual_state,
        "session_history": request.session_history,
    }
    if request.intent:
        initial_state["intent"] = request.intent

    try:
        result = await orchestrator.run(initial_state)
    except Exception as exc:
        logger.exception(
            "OrchestratorSupremus failed for user=%s", request.user_id
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Orchestration pipeline failed: {exc}",
        ) from exc

    logger.info(
        "Orchestration complete: user=%s intent=%s",
        request.user_id,
        result.get("intent", "unknown"),
    )

    return OrchestrateResponse(
        user_id=request.user_id,
        intent=result.get("intent", ""),
        scripture=result.get("scripture"),
        meditation=result.get("meditation"),
        prayer=result.get("prayer"),
        contemplation=result.get("contemplation"),
        action=result.get("action"),
        theological_validation=result.get("theological_validation"),
        error=result.get("error"),
    )
