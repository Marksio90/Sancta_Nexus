"""Lectio Divina API routes.

5-etapowe rozważanie Pisma Świętego (Lectio → Meditatio → Oratio → Contemplatio → Actio).

Wszystkie endpointy chronione JWT. user_id pochodzi z tokenu — nigdy z body requestu.

Nowe w Phase 3:
- POST /session/{id}/complete   — zamknij sesję i zapisz do PostgreSQL
- POST /favorites               — dodaj ulubiony fragment
- GET  /favorites               — lista ulubionych
- DELETE /favorites/{id}        — usuń ulubiony
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.dependencies import DbSession, RedisDep
from app.core.rbac import require_authenticated
from app.models.database import (
    AuditEventType,
    FavoritePassage,
    Prayer,
    ScriptureEncounter,
    Session as DbSession_model,
    SessionType,
    User,
)
from app.services.audit.audit_service import audit
from app.services.cache.session_store import SessionStore

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class StartSessionRequest(BaseModel):
    """Request body for starting a new Lectio Divina session."""

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


class CompleteSessionRequest(BaseModel):
    """Zamknij sesję i zapisz do bazy danych."""

    fruit_of_day: str | None = Field(default=None, description="Owoc dnia — konkretne postanowienie.")
    final_note: str | None = Field(default=None, description="Końcowa notatka do dziennika.")


class CompleteSessionResponse(BaseModel):
    session_id: str
    db_session_id: str
    message: str


class FavoritePassageRequest(BaseModel):
    book: str = Field(..., min_length=1, max_length=64)
    chapter: int = Field(..., ge=1)
    verse_start: int = Field(..., ge=1)
    verse_end: int = Field(..., ge=1)
    reference: str = Field(..., min_length=1, max_length=128)
    excerpt: str | None = Field(default=None, max_length=512)
    note: str | None = None


class FavoritePassageResponse(BaseModel):
    id: str
    book: str
    chapter: int
    verse_start: int
    verse_end: int
    reference: str
    excerpt: str | None
    note: str | None
    created_at: str


class EmotionInputRequest(BaseModel):
    """Request body for submitting emotion data during a session."""

    session_id: str
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


class RunPipelineRequest(BaseModel):
    """Request body for running the full Lectio Divina AI pipeline."""

    emotion_text: str
    tradition: str = ""


class RunPipelineResponse(BaseModel):
    """Full AI-generated session content returned by the pipeline."""

    scripture: dict[str, Any] | None = None
    meditation: dict[str, Any] | None = None
    prayer: dict[str, Any] | None = None
    contemplation: dict[str, Any] | None = None
    action: dict[str, Any] | None = None
    tradition: str = ""
    kerygmatic_theme: str = ""
    journey: dict[str, Any] | None = None
    error: str | None = None


_STAGE_ORDER = ["lectio", "meditatio", "oratio", "contemplatio", "actio"]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/session", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def start_session(
    request: StartSessionRequest,
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> SessionResponse:
    """Rozpocznij nową sesję Lectio Divina.

    Tworzy sesję w Redis (aktywna przez 24h). Po zakończeniu wywołaj
    POST /session/{id}/complete, aby utrwalić w PostgreSQL.
    """
    from app.services.scripture.liturgical_calendar import LiturgicalCalendar

    session_id = str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    calendar = LiturgicalCalendar()
    today = calendar.get_today()

    scripture_info: dict[str, Any] = {
        "season": today.season,
        "feast": today.feast,
        "readings": [str(r) for r in today.readings],
    }

    session_data = {
        "session_id": session_id,
        "user_id": current_user.id,
        "status": "active",
        "created_at": now.isoformat(),
        "tradition": request.tradition,
        "scripture": scripture_info,
        "stage": "lectio",
        "reflections": {},
        "emotions": [],
    }

    store = SessionStore(redis, namespace="lectio")
    await store.create(session_id, session_data)

    logger.info("Started Lectio Divina session %s for user %s", session_id, current_user.id)

    return SessionResponse(
        session_id=session_id,
        user_id=current_user.id,
        status="active",
        created_at=now.isoformat(),
        scripture=scripture_info,
        stage="lectio",
    )


@router.post("/session/{session_id}/complete", response_model=CompleteSessionResponse)
async def complete_session(
    session_id: str,
    body: CompleteSessionRequest,
    redis: RedisDep,
    db: DbSession,
    current_user: User = require_authenticated,
) -> CompleteSessionResponse:
    """Zamknij sesję Lectio Divina i zapisz do PostgreSQL.

    Tworzy rekordy: Session, ScriptureEncounter (jeśli był fragment),
    Prayer (jeśli był etap oratio).
    """
    store = SessionStore(redis, namespace="lectio")
    session = await store.get(session_id)
    if not session:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sesja nie istnieje lub wygasła.")
    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="To nie jest Twoja sesja.")

    now = datetime.now(timezone.utc)
    started_at = datetime.fromisoformat(session["created_at"])

    # Zapis sesji do DB
    db_session = DbSession_model(
        user_id=current_user.id,
        session_type=SessionType.LECTIO_DIVINA,
        scripture_reference=session.get("scripture", {}).get("readings", [""])[0] if session.get("scripture") else None,
        started_at=started_at,
        ended_at=now,
        notes=body.final_note,
    )
    db.add(db_session)
    await db.flush()

    # Zapis napotkania z Pismem
    scripture = session.get("scripture", {})
    readings = scripture.get("readings", [])
    if readings:
        reflection_text = session.get("reflections", {}).get("meditatio", {}).get("text")
        encounter = ScriptureEncounter(
            user_id=current_user.id,
            session_id=db_session.id,
            book=readings[0].split(" ")[0] if readings else "unknown",
            chapter=1,
            verse_start=1,
            verse_end=1,
            user_reflection=reflection_text,
        )
        db.add(encounter)

    # Zapis modlitwy z etapu oratio
    oratio = session.get("reflections", {}).get("oratio", {})
    if oratio.get("text"):
        prayer = Prayer(
            user_id=current_user.id,
            session_id=db_session.id,
            content=oratio["text"],
            prayer_type="oratio",
            tradition=session.get("tradition", "ignatian"),
        )
        db.add(prayer)

    # Owoc dnia — zapisz jako modlitwę actio
    if body.fruit_of_day:
        actio_prayer = Prayer(
            user_id=current_user.id,
            session_id=db_session.id,
            content=body.fruit_of_day,
            prayer_type="actio",
            tradition=session.get("tradition", "ignatian"),
        )
        db.add(actio_prayer)

    # Oznacz sesję Redis jako zakończoną
    session["status"] = "completed"
    session["ended_at"] = now.isoformat()
    session["db_session_id"] = db_session.id
    await store.update(session_id, session)

    await audit.log(
        db,
        event_type=AuditEventType.CONTENT_CREATED,
        user_id=current_user.id,
        actor_id=current_user.id,
        description=f"Lectio Divina session completed and saved to DB. session_id={db_session.id}",
        payload={"redis_session_id": session_id, "db_session_id": db_session.id},
    )

    logger.info("Session %s completed and saved to DB as %s", session_id, db_session.id)
    return CompleteSessionResponse(
        session_id=session_id,
        db_session_id=db_session.id,
        message="Sesja Lectio Divina została zakończona i zapisana do dziennika.",
    )


@router.post("/emotion", response_model=EmotionResponse)
async def analyze_emotion(
    request: EmotionInputRequest,
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> EmotionResponse:
    """Analyse emotion input (text or audio) within a session.

    Returns the detected emotion vector, spiritual state and
    suggested scripture passages.
    """
    from app.services.emotion.emotion_service import EmotionService
    from app.services.scripture.scripture_matcher import MatchContext, ScriptureMatcher

    store = SessionStore(redis, namespace="lectio")
    session = await store.get(request.session_id)
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
    await store.update(request.session_id, session)

    # Get suggested scripture
    matcher = ScriptureMatcher()
    context = MatchContext(
        user_id=current_user.id,
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
    from app.services.scripture.liturgical_calendar import LiturgicalCalendar

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
async def submit_reflection(
    request: ReflectionRequest,
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> ReflectionResponse:
    """Zapisz refleksję dla bieżącego etapu Lectio Divina."""
    store = SessionStore(redis, namespace="lectio")
    session = await store.get(request.session_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session {request.session_id} not found",
        )

    if session["user_id"] != current_user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="To nie jest Twoja sesja.")

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

    await store.update(request.session_id, session)

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


_JOURNEY_CACHE_TTL = 3_600   # 1 hour
_PATTERNS_CACHE_TTL = 3_600  # 1 hour


@router.get("/journey/me")
async def get_spiritual_journey(
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    user_id = current_user.id
    """Return the user's current spiritual journey stage via JourneyTrackerAgent (A-036).

    Analyses all stored sessions for the user and returns purgation /
    illumination / union stage, percentage progress, milestones, and the
    next growth area.  Results are cached in Redis for 1 hour.
    """
    from app.agents.memory.journey_tracker import JourneyTrackerAgent

    # --- Redis cache check ---
    cache_key = f"journey_cache:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        logger.debug("Journey cache HIT for user=%s", user_id)
        return json.loads(cached)

    store = SessionStore(redis, namespace="lectio")
    user_sessions = await store.list_by_user(user_id)

    latest = (
        sorted(user_sessions, key=lambda s: s.get("created_at", ""), reverse=True)[0]
        if user_sessions
        else {}
    )
    session_data = {
        "emotions": {
            "primary": (
                latest.get("emotions", [{}])[-1].get("primary", "neutral")
                if latest.get("emotions")
                else "neutral"
            ),
        },
        "spiritual_state": "",
        "reflection": "",
        "scripture": "",
        "total_sessions": len(user_sessions),
    }

    tracker = JourneyTrackerAgent()
    journey = await tracker.track(user_id, session_data)

    # --- Cache result ---
    await redis.setex(cache_key, _JOURNEY_CACHE_TTL, json.dumps(journey))
    logger.debug("Journey cached for user=%s (TTL=%ds)", user_id, _JOURNEY_CACHE_TTL)
    return journey


@router.get("/patterns/me")
async def get_spiritual_patterns(
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> list[dict[str, Any]]:
    user_id = current_user.id
    """Discover recurring spiritual patterns via PatternDiscoveryAgent (A-037).

    Analyses session history (up to last 30 sessions) to identify
    recurring themes, cyclical crises, grace moments, and growth
    trajectories.  Results are cached in Redis for 1 hour.
    """
    from app.agents.memory.pattern_discovery import PatternDiscoveryAgent

    # --- Redis cache check ---
    cache_key = f"patterns_cache:{user_id}"
    cached = await redis.get(cache_key)
    if cached:
        logger.debug("Patterns cache HIT for user=%s", user_id)
        return json.loads(cached)

    store = SessionStore(redis, namespace="lectio")
    user_sessions = await store.list_by_user(user_id)

    sessions_for_analysis = [
        {
            "date": s.get("created_at", ""),
            "primary_emotion": (
                s.get("emotions", [{}])[-1].get("primary", "neutral")
                if s.get("emotions")
                else "neutral"
            ),
            "spiritual_state": (
                s.get("emotions", [{}])[-1].get("state", "")
                if s.get("emotions")
                else ""
            ),
            "scripture_ref": (s.get("scripture") or {}).get("readings", [""])[0]
            if isinstance((s.get("scripture") or {}).get("readings"), list)
            else "",
        }
        for s in sorted(user_sessions, key=lambda s: s.get("created_at", ""), reverse=True)
    ]

    agent = PatternDiscoveryAgent()
    patterns = await agent.discover(user_id, sessions_for_analysis)

    # --- Cache result ---
    await redis.setex(cache_key, _PATTERNS_CACHE_TTL, json.dumps(patterns))
    logger.debug("Patterns cached for user=%s (TTL=%ds)", user_id, _PATTERNS_CACHE_TTL)
    return patterns


@router.get("/history/me", response_model=list[SessionHistoryItem])
async def get_session_history(
    redis: RedisDep,
    current_user: User = require_authenticated,
) -> list[SessionHistoryItem]:
    user_id = current_user.id
    """Get session history for a user."""
    store = SessionStore(redis, namespace="lectio")
    user_sessions = await store.list_by_user(user_id)

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


@router.post("/run", response_model=RunPipelineResponse)
async def run_lectio_pipeline(
    request: RunPipelineRequest,
    current_user: User = require_authenticated,
) -> RunPipelineResponse:
    """Run the full Lectio Divina AI pipeline for a given emotion text.

    Executes the complete LangGraph flow:
    emotion_analysis → scripture_selection → lectio → meditatio
    → oratio → contemplatio → actio

    Returns all AI-generated content (scripture, meditation questions,
    prayer, contemplation guidance, and daily challenge).
    """
    from app.agents.lectio_divina.lectio_divina_graph import run_session

    result = await run_session(
        user_id=current_user.id,
        raw_input=request.emotion_text,
        tradition=request.tradition,
    )

    # --- A-036: JourneyTrackerAgent — track spiritual progress after each session ---
    journey: dict[str, Any] | None = None
    try:
        from app.agents.memory.journey_tracker import JourneyTrackerAgent

        session_data = {
            "emotions": {
                "primary": (result.get("prayer") or {}).get("spiritual_movement", "neutral"),
            },
            "spiritual_state": (result.get("prayer") or {}).get("spiritual_movement", ""),
            "reflection": (result.get("meditation") or {}).get("key_word", ""),
            "scripture": (result.get("scripture") or {}).get("text", ""),
        }
        tracker = JourneyTrackerAgent()
        journey = await tracker.track(current_user.id, session_data)
        logger.info(
            "JourneyTrackerAgent (A-036): user=%s stage=%s progress=%s%%",
            current_user.id,
            journey.get("current_stage"),
            journey.get("progress_percentage"),
        )
    except Exception:
        logger.warning("JourneyTrackerAgent (A-036) failed; journey not tracked.")

    return RunPipelineResponse(
        scripture=result.get("scripture"),
        meditation=result.get("meditation"),
        prayer=result.get("prayer"),
        contemplation=result.get("contemplation"),
        action=result.get("action"),
        tradition=result.get("tradition", ""),
        kerygmatic_theme=result.get("kerygmatic_theme", ""),
        journey=journey,
        error=result.get("error"),
    )


# ── Ulubione fragmenty ────────────────────────────────────────────────────────


@router.post("/favorites", response_model=FavoritePassageResponse, status_code=status.HTTP_201_CREATED)
async def add_favorite(
    body: FavoritePassageRequest,
    db: DbSession,
    current_user: User = require_authenticated,
) -> FavoritePassageResponse:
    """Dodaj fragment Pisma do ulubionych."""
    passage = FavoritePassage(
        user_id=current_user.id,
        book=body.book,
        chapter=body.chapter,
        verse_start=body.verse_start,
        verse_end=body.verse_end,
        reference=body.reference,
        excerpt=body.excerpt,
        note=body.note,
    )
    db.add(passage)
    try:
        await db.flush()
        await db.refresh(passage)
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ten fragment jest już w ulubionych.",
        )
    return FavoritePassageResponse(
        id=passage.id,
        book=passage.book,
        chapter=passage.chapter,
        verse_start=passage.verse_start,
        verse_end=passage.verse_end,
        reference=passage.reference,
        excerpt=passage.excerpt,
        note=passage.note,
        created_at=passage.created_at.isoformat(),
    )


@router.get("/favorites", response_model=list[FavoritePassageResponse])
async def list_favorites(
    db: DbSession,
    current_user: User = require_authenticated,
) -> list[FavoritePassageResponse]:
    """Lista ulubionych fragmentów Pisma zalogowanego użytkownika."""
    result = await db.execute(
        select(FavoritePassage)
        .where(FavoritePassage.user_id == current_user.id)
        .order_by(FavoritePassage.created_at.desc())
    )
    passages = result.scalars().all()
    return [
        FavoritePassageResponse(
            id=p.id,
            book=p.book,
            chapter=p.chapter,
            verse_start=p.verse_start,
            verse_end=p.verse_end,
            reference=p.reference,
            excerpt=p.excerpt,
            note=p.note,
            created_at=p.created_at.isoformat(),
        )
        for p in passages
    ]


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_favorite(
    favorite_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> None:
    """Usuń fragment z ulubionych."""
    result = await db.execute(
        select(FavoritePassage).where(
            FavoritePassage.id == favorite_id,
            FavoritePassage.user_id == current_user.id,
        )
    )
    passage = result.scalar_one_or_none()
    if passage is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ulubiony fragment nie istnieje.")
    await db.delete(passage)
    await db.flush()
