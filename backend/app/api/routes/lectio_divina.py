"""Lectio Divina API routes.

Provides endpoints for managing Lectio Divina prayer sessions,
emotion analysis within sessions, scripture retrieval and
reflection submission.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/lectio-divina", tags=["Lectio Divina"])

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    """Request body for starting a new Lectio Divina session."""

    user_id: str
    tradition: str = "ignatian"
    preferred_translation: str = "BT"
    intention: str | None = None


class SessionResponse(BaseModel):
    """Response after creating or retrieving a session."""

    session_id: str
    user_id: str
    status: str
    created_at: str
    scripture: dict[str, Any] | None = None
    stage: str = "lectio"  # lectio | meditatio | oratio | contemplatio | actio


class EmotionInputRequest(BaseModel):
    """Request body for submitting emotion data during a session."""

    session_id: str
    user_id: str
    text: str | None = None
    audio_url: str | None = None


class EmotionResponse(BaseModel):
    """Response with emotion analysis results."""

    session_id: str
    primary_emotion: str
    secondary_emotions: list[str] = Field(default_factory=list)
    vector: dict[str, float] = Field(default_factory=dict)
    confidence: float
    spiritual_state: str
    suggested_scripture: list[dict[str, Any]] = Field(default_factory=list)


class ReflectionRequest(BaseModel):
    """Request body for submitting a session reflection."""

    session_id: str
    user_id: str
    stage: str  # which stage of lectio divina
    reflection_text: str
    grace_notes: list[str] = Field(default_factory=list)


class ReflectionResponse(BaseModel):
    """Response after saving a reflection."""

    session_id: str
    stage: str
    saved: bool
    next_stage: str | None = None
    guidance: str = ""


class ScriptureForDateResponse(BaseModel):
    """Response with scripture readings for a given date."""

    date: str
    season: str
    feast: str | None = None
    readings: list[dict[str, Any]] = Field(default_factory=list)


class SessionHistoryItem(BaseModel):
    """A single historical session summary."""

    session_id: str
    created_at: str
    primary_emotion: str | None = None
    spiritual_state: str | None = None
    stages_completed: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# In-memory session store (production: use Redis / DB)
# ---------------------------------------------------------------------------

_sessions: dict[str, dict[str, Any]] = {}

_STAGE_ORDER = ["lectio", "meditatio", "oratio", "contemplatio", "actio"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(request: StartSessionRequest) -> SessionResponse:
    """Start a new Lectio Divina session.

    Creates a session, determines liturgical context and selects an
    initial scripture passage.
    """
    from backend.app.services.scripture.liturgical_calendar import LiturgicalCalendar

    session_id = str(uuid.uuid4())
    now = datetime.utcnow()

    calendar = LiturgicalCalendar()
    today = calendar.get_today()

    scripture_info: dict[str, Any] = {
        "season": today.season,
        "feast": today.feast,
        "readings": [str(r) for r in today.readings],
    }

    session_data = {
        "session_id": session_id,
        "user_id": request.user_id,
        "status": "active",
        "created_at": now.isoformat(),
        "tradition": request.tradition,
        "scripture": scripture_info,
        "stage": "lectio",
        "reflections": {},
        "emotions": [],
    }
    _sessions[session_id] = session_data

    logger.info("Started Lectio Divina session %s for user %s", session_id, request.user_id)

    return SessionResponse(
        session_id=session_id,
        user_id=request.user_id,
        status="active",
        created_at=now.isoformat(),
        scripture=scripture_info,
        stage="lectio",
    )


@router.post("/emotion", response_model=EmotionResponse)
async def analyze_emotion(request: EmotionInputRequest) -> EmotionResponse:
    """Analyse emotion input (text or audio) within a session.

    Returns the detected emotion vector, spiritual state and
    suggested scripture passages.
    """
    from backend.app.services.emotion.emotion_service import EmotionService
    from backend.app.services.scripture.scripture_matcher import MatchContext, ScriptureMatcher

    session = _sessions.get(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    emotion_svc = EmotionService()

    if request.text:
        analysis = emotion_svc.analyze_text(request.text)
    elif request.audio_url:
        analysis = emotion_svc.analyze_voice(request.audio_url)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Either 'text' or 'audio_url' must be provided",
        )

    # Store emotion in session
    session.setdefault("emotions", []).append({
        "timestamp": datetime.utcnow().isoformat(),
        "primary": analysis.primary_emotion,
        "vector": analysis.vector,
    })

    # Get suggested scripture
    matcher = ScriptureMatcher()
    context = MatchContext(
        user_id=request.user_id,
        liturgical_season=session.get("scripture", {}).get("season"),
    )
    matches = matcher.match(analysis.vector, context)

    suggested = [
        {
            "reference": m.reference,
            "passage": m.passage,
            "score": m.score,
            "explanation": m.explanation,
        }
        for m in matches
    ]

    return EmotionResponse(
        session_id=request.session_id,
        primary_emotion=analysis.primary_emotion,
        secondary_emotions=analysis.secondary_emotions,
        vector=analysis.vector,
        confidence=analysis.confidence,
        spiritual_state=analysis.spiritual_state.value,
        suggested_scripture=suggested,
    )


@router.get("/scripture/{date}", response_model=ScriptureForDateResponse)
async def get_scripture_for_date(date: str) -> ScriptureForDateResponse:
    """Get scripture readings for a specific date (YYYY-MM-DD)."""
    from backend.app.services.scripture.liturgical_calendar import LiturgicalCalendar

    calendar = LiturgicalCalendar()
    try:
        day = calendar.get_today(today=__import__("datetime").date.fromisoformat(date))
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid date format: {date}. Use YYYY-MM-DD.",
        ) from exc

    return ScriptureForDateResponse(
        date=date,
        season=day.season,
        feast=day.feast,
        readings=[
            {
                "label": r.label,
                "reference": str(r),
                "book": r.book,
                "chapter": r.chapter,
                "verse_start": r.verse_start,
                "verse_end": r.verse_end,
            }
            for r in day.readings
        ],
    )


@router.post("/reflection", response_model=ReflectionResponse)
async def submit_reflection(request: ReflectionRequest) -> ReflectionResponse:
    """Submit a reflection for the current Lectio Divina stage."""
    session = _sessions.get(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    if request.stage not in _STAGE_ORDER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid stage '{request.stage}'. Must be one of {_STAGE_ORDER}",
        )

    session.setdefault("reflections", {})[request.stage] = {
        "text": request.reflection_text,
        "grace_notes": request.grace_notes,
        "timestamp": datetime.utcnow().isoformat(),
    }

    # Advance to next stage
    current_idx = _STAGE_ORDER.index(request.stage)
    next_stage = _STAGE_ORDER[current_idx + 1] if current_idx + 1 < len(_STAGE_ORDER) else None
    if next_stage:
        session["stage"] = next_stage

    guidance_map = {
        "lectio": "Przeczytaj tekst ponownie. Co slowo lub fraza przyciaga Twoja uwage?",
        "meditatio": "Rozważ, co Bog mówi do Ciebie przez ten tekst. Jakie mysli sie rodza?",
        "oratio": "Odpowiedz Bogu modlitwa. Co chcesz Mu powiedziec?",
        "contemplatio": "Trwaj w ciszy przed Bogiem. Pozwól Mu dzialac.",
        "actio": "Jak ten tekst zmienia Twoje zycie dzisiaj? Jakie postanowienie podejmujesz?",
    }

    return ReflectionResponse(
        session_id=request.session_id,
        stage=request.stage,
        saved=True,
        next_stage=next_stage,
        guidance=guidance_map.get(next_stage or "", "Sesja Lectio Divina zakonczona. Chwala Bogu!"),
    )


@router.get("/history/{user_id}", response_model=list[SessionHistoryItem])
async def get_session_history(user_id: str) -> list[SessionHistoryItem]:
    """Get session history for a user."""
    user_sessions = [
        s for s in _sessions.values() if s.get("user_id") == user_id
    ]

    return [
        SessionHistoryItem(
            session_id=s["session_id"],
            created_at=s["created_at"],
            primary_emotion=(
                s["emotions"][-1]["primary"] if s.get("emotions") else None
            ),
            spiritual_state=None,
            stages_completed=list(s.get("reflections", {}).keys()),
        )
        for s in sorted(user_sessions, key=lambda x: x["created_at"], reverse=True)
    ]
