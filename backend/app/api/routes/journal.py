"""Dziennik duchowy — Sancta Nexus.

Prywatny dziennik refleksji, modlitw i owoców Lectio Divina.

Zasady prywatności:
- Wpisy są prywatne domyślnie.
- Treść nie jest przesyłana do AI bez zgody użytkownika
  (privacy_settings.ai_can_read_journal).
- Soft-delete: wpis oznaczany deleted_at, nie usuwany natychmiast.
- Użytkownik może wyeksportować wszystkie wpisy przez GET /me/export.

Endpoints:
    POST   /journal/entries           — nowy wpis
    GET    /journal/entries           — lista wpisów (paginacja + szukaj)
    GET    /journal/entries/{id}      — pojedynczy wpis
    PUT    /journal/entries/{id}      — aktualizuj wpis
    DELETE /journal/entries/{id}      — soft-delete wpisu
    GET    /journal/insights          — analiza drogi duchowej (AI, opt-in)
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import or_, select

from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import AuditEventType, JournalEntry, User, UserPrivacySettings
from app.services.audit.audit_service import audit
from app.services.memory.journal_insights_service import JournalInsightsService

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_MOODS = {
    "spokój", "radość", "wdzięczność", "smutek", "niepokój",
    "nadzieja", "zagubienie", "miłość", "tęsknota", "pokuta",
}


# ── Schemas ───────────────────────────────────────────────────────────────────


class JournalEntryCreate(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str | None = Field(default=None, max_length=256)
    content: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list, description="Tagi, np. ['modlitwa', 'Ewangelia']")
    mood: str | None = Field(default=None, description=f"Nastrój. Dozwolone: {sorted(_VALID_MOODS)}")
    scripture_reference: str | None = Field(default=None, max_length=128)
    lectio_session_id: str | None = None
    program_id: str | None = None


class JournalEntryUpdate(BaseModel):
    model_config = ConfigDict(strict=True)

    title: str | None = Field(default=None, max_length=256)
    content: str | None = Field(default=None, min_length=1)
    tags: list[str] | None = None
    mood: str | None = None
    scripture_reference: str | None = Field(default=None, max_length=128)


class JournalEntryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    title: str | None
    content: str
    tags: list[str]
    mood: str | None
    scripture_reference: str | None
    lectio_session_id: str | None
    program_id: str | None
    created_at: str
    updated_at: str


class JournalListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    entries: list[JournalEntryResponse]
    total: int
    page: int
    page_size: int


# ── Helpers ───────────────────────────────────────────────────────────────────


def _tags_to_str(tags: list[str]) -> str:
    return ",".join(t.strip()[:64] for t in tags[:20])


def _str_to_tags(tags_str: str | None) -> list[str]:
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


def _entry_response(entry: JournalEntry) -> JournalEntryResponse:
    return JournalEntryResponse(
        id=entry.id,
        title=entry.title,
        content=entry.content,
        tags=_str_to_tags(entry.tags),
        mood=entry.mood,
        scripture_reference=entry.scripture_reference,
        lectio_session_id=entry.lectio_session_id,
        program_id=entry.program_id,
        created_at=entry.created_at.isoformat(),
        updated_at=entry.updated_at.isoformat(),
    )


def _get_active_entries_query(user_id: str):
    return select(JournalEntry).where(
        JournalEntry.user_id == user_id,
        JournalEntry.deleted_at.is_(None),
    )


# ── POST /journal/entries ─────────────────────────────────────────────────────


@router.post(
    "/entries",
    response_model=JournalEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Nowy wpis w dzienniku duchowym",
)
async def create_entry(
    body: JournalEntryCreate,
    db: DbSession,
    current_user: User = require_authenticated,
) -> JournalEntryResponse:
    """Tworzy nowy wpis w dzienniku duchowym. Prywatny domyślnie."""
    if body.mood and body.mood not in _VALID_MOODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieprawidłowy nastrój '{body.mood}'. Dostępne: {sorted(_VALID_MOODS)}",
        )

    entry = JournalEntry(
        user_id=current_user.id,
        title=body.title,
        content=body.content,
        tags=_tags_to_str(body.tags),
        mood=body.mood,
        scripture_reference=body.scripture_reference,
        lectio_session_id=body.lectio_session_id,
        program_id=body.program_id,
    )
    db.add(entry)
    await db.flush()
    await db.refresh(entry)

    logger.info("Journal entry created: %s by user %s", entry.id, current_user.id)
    return _entry_response(entry)


# ── GET /journal/entries ──────────────────────────────────────────────────────


@router.get(
    "/entries",
    response_model=JournalListResponse,
    summary="Lista wpisów w dzienniku (paginacja + wyszukiwanie)",
)
async def list_entries(
    db: DbSession,
    current_user: User = require_authenticated,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    search: str | None = Query(default=None, description="Szukaj w tytule i treści"),
    tag: str | None = Query(default=None, description="Filtruj po tagu"),
    mood: str | None = Query(default=None, description="Filtruj po nastroju"),
) -> JournalListResponse:
    """Zwraca paginowaną listę wpisów zalogowanego użytkownika."""
    from sqlalchemy import func

    query = _get_active_entries_query(current_user.id)

    if search:
        term = f"%{search}%"
        query = query.where(or_(JournalEntry.title.ilike(term), JournalEntry.content.ilike(term)))
    if tag:
        query = query.where(JournalEntry.tags.ilike(f"%{tag}%"))
    if mood:
        query = query.where(JournalEntry.mood == mood)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.order_by(JournalEntry.created_at.desc()).offset(offset).limit(page_size)
    )
    entries = result.scalars().all()

    return JournalListResponse(
        entries=[_entry_response(e) for e in entries],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /journal/entries/{id} ─────────────────────────────────────────────────


@router.get(
    "/entries/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Pobierz pojedynczy wpis",
)
async def get_entry(
    entry_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> JournalEntryResponse:
    """Zwraca jeden wpis. Tylko właściciel może go odczytać."""
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
            JournalEntry.deleted_at.is_(None),
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wpis nie istnieje.")
    return _entry_response(entry)


# ── PUT /journal/entries/{id} ─────────────────────────────────────────────────


@router.put(
    "/entries/{entry_id}",
    response_model=JournalEntryResponse,
    summary="Zaktualizuj wpis",
)
async def update_entry(
    entry_id: str,
    body: JournalEntryUpdate,
    db: DbSession,
    current_user: User = require_authenticated,
) -> JournalEntryResponse:
    """Aktualizuje edytowalne pola wpisu. Pola None są pomijane."""
    if body.mood and body.mood not in _VALID_MOODS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieprawidłowy nastrój '{body.mood}'. Dostępne: {sorted(_VALID_MOODS)}",
        )

    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
            JournalEntry.deleted_at.is_(None),
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wpis nie istnieje.")

    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    if body.tags is not None:
        entry.tags = _tags_to_str(body.tags)
    if body.mood is not None:
        entry.mood = body.mood
    if body.scripture_reference is not None:
        entry.scripture_reference = body.scripture_reference

    await db.flush()
    await db.refresh(entry)
    return _entry_response(entry)


# ── DELETE /journal/entries/{id} ──────────────────────────────────────────────


@router.delete(
    "/entries/{entry_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Usuń wpis (soft-delete)",
)
async def delete_entry(
    entry_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> None:
    """Soft-delete wpisu. Dane są zachowane przez okres retencji, potem usuwane przez admina."""
    result = await db.execute(
        select(JournalEntry).where(
            JournalEntry.id == entry_id,
            JournalEntry.user_id == current_user.id,
            JournalEntry.deleted_at.is_(None),
        )
    )
    entry = result.scalar_one_or_none()
    if entry is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Wpis nie istnieje.")

    entry.deleted_at = datetime.now(timezone.utc)

    await audit.log(
        db,
        event_type=AuditEventType.JOURNAL_ENTRY_DELETED,
        user_id=current_user.id,
        actor_id=current_user.id,
        description=f"Journal entry soft-deleted: {entry_id}",
        payload={"entry_id": entry_id},
    )
    await db.flush()


# ── GET /journal/insights ─────────────────────────────────────────────────────


class InsightsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    journey: dict
    patterns: list[dict]
    entry_count: int
    generated_at: str
    disclaimer: str
    ai_enabled: bool


@router.get(
    "/insights",
    response_model=InsightsResponse,
    summary="Analiza drogi duchowej na podstawie dziennika",
)
async def get_insights(
    db: DbSession,
    current_user: User = require_authenticated,
    entries_limit: int = Query(default=30, ge=5, le=100, description="Liczba ostatnich wpisów do analizy"),
) -> InsightsResponse:
    """
    Analizuje ostatnie wpisy w dzienniku przez JourneyTrackerAgent i PatternDiscoveryAgent.

    Wymaga: privacy_settings.ai_can_read_journal == True.
    Jeśli zgoda nie jest udzielona, zwraca ai_enabled=False bez analizy.
    """
    # Check privacy consent
    privacy_result = await db.execute(
        select(UserPrivacySettings).where(UserPrivacySettings.user_id == current_user.id)
    )
    privacy = privacy_result.scalar_one_or_none()
    ai_enabled = privacy.ai_can_read_journal if privacy else True

    if not ai_enabled:
        return InsightsResponse(
            journey={
                "current_stage": "unknown",
                "stage_name_pl": "Analiza wyłączona",
                "stage_description": "Włącz analizę AI w ustawieniach prywatności.",
                "progress_percentage": 0,
                "milestones": [],
                "next_growth_area": "",
            },
            patterns=[],
            entry_count=0,
            generated_at=datetime.now(timezone.utc).isoformat(),
            disclaimer=(
                "Analiza AI dziennika jest wyłączona w ustawieniach prywatności. "
                "Możesz ją włączyć w sekcji Ustawienia → Prywatność."
            ),
            ai_enabled=False,
        )

    # Fetch recent entries
    entries_result = await db.execute(
        _get_active_entries_query(current_user.id)
        .order_by(JournalEntry.created_at.desc())
        .limit(entries_limit)
    )
    entries = list(entries_result.scalars().all())

    if not entries:
        from app.services.memory.journal_insights_service import DISCLAIMER
        return InsightsResponse(
            journey={
                "current_stage": "purgation",
                "stage_name_pl": "Oczyszczenie",
                "stage_description": "Dodaj pierwsze wpisy do dziennika, aby zobaczyć analizę.",
                "progress_percentage": 0,
                "milestones": [],
                "next_growth_area": "Zacznij od codziennego wpisu po modlitwie lub Lectio Divina.",
            },
            patterns=[],
            entry_count=0,
            generated_at=datetime.now(timezone.utc).isoformat(),
            disclaimer=DISCLAIMER,
            ai_enabled=True,
        )

    service = JournalInsightsService()
    result = await service.generate(current_user.id, entries)

    return InsightsResponse(
        journey=result["journey"],
        patterns=result["patterns"],
        entry_count=result["entry_count"],
        generated_at=result["generated_at"],
        disclaimer=result["disclaimer"],
        ai_enabled=True,
    )
