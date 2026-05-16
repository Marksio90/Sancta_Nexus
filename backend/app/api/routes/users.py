"""User profile, privacy settings, and data management routes.

All endpoints require authentication. Users can only access their own data
unless they have an elevated role.

Endpoints:
    GET  /me/profile           — own profile
    PUT  /me/profile           — update own profile
    GET  /me/privacy           — privacy settings
    PUT  /me/privacy           — update privacy settings
    GET  /me/export            — export all personal data (JSON)
    POST /me/ai-history/clear  — clear AI interaction history
    POST /me/delete            — request account deletion (soft-delete)
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import User
from app.services.privacy.privacy_service import privacy_svc

logger = logging.getLogger(__name__)
router = APIRouter()

_VALID_TRADITIONS = {"ignatian", "carmelite", "benedictine", "franciscan", "dominican"}
_VALID_LANGUAGES = {"pl", "en", "de", "fr", "es", "it", "pt", "uk"}


# ── Schemas ───────────────────────────────────────────────────────────────────


class ProfileResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    user_id: str
    email: str
    display_name: str
    role: str
    subscription_tier: str
    is_active: bool
    created_at: str


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(strict=True)

    display_name: str | None = Field(default=None, min_length=1, max_length=100)


class PrivacySettingsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    journal_is_private: bool
    ai_can_read_journal: bool
    ai_history_enabled: bool
    preferred_language: str
    spiritual_tradition: str


class PrivacySettingsUpdate(BaseModel):
    model_config = ConfigDict(strict=True)

    journal_is_private: bool | None = None
    ai_can_read_journal: bool | None = None
    ai_history_enabled: bool | None = None
    preferred_language: str | None = Field(default=None, min_length=2, max_length=5)
    spiritual_tradition: str | None = None


class ClearHistoryResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    deleted_count: int
    message: str


class DeletionResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    message: str


# ── Helpers ───────────────────────────────────────────────────────────────────


def _profile_response(user: User) -> ProfileResponse:
    return ProfileResponse(
        user_id=user.id,
        email=user.email,
        display_name=user.name,
        role=user.role.value,
        subscription_tier=user.subscription_tier.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
    )


# ── GET /me/profile ───────────────────────────────────────────────────────────


@router.get(
    "/me/profile",
    response_model=ProfileResponse,
    summary="Pobierz własny profil",
)
async def get_my_profile(
    current_user: User = require_authenticated,
) -> ProfileResponse:
    """Zwraca profil zalogowanego użytkownika."""
    return _profile_response(current_user)


# ── PUT /me/profile ───────────────────────────────────────────────────────────


@router.put(
    "/me/profile",
    response_model=ProfileResponse,
    summary="Zaktualizuj własny profil",
)
async def update_my_profile(
    update: ProfileUpdate,
    db: DbSession,
    current_user: User = require_authenticated,
) -> ProfileResponse:
    """Aktualizuje edytowalne pola profilu (display_name)."""
    if update.display_name is not None:
        current_user.name = update.display_name

    await db.flush()
    await db.refresh(current_user)
    return _profile_response(current_user)


# ── GET /me/privacy ───────────────────────────────────────────────────────────


@router.get(
    "/me/privacy",
    response_model=PrivacySettingsResponse,
    summary="Pobierz ustawienia prywatności",
)
async def get_privacy_settings(
    db: DbSession,
    current_user: User = require_authenticated,
) -> PrivacySettingsResponse:
    """Zwraca ustawienia prywatności. Tworzy domyślne (privacy-first), jeśli nie istnieją."""
    settings = await privacy_svc.get_or_create_privacy_settings(db, current_user)
    return PrivacySettingsResponse(
        journal_is_private=settings.journal_is_private,
        ai_can_read_journal=settings.ai_can_read_journal,
        ai_history_enabled=settings.ai_history_enabled,
        preferred_language=settings.preferred_language,
        spiritual_tradition=settings.spiritual_tradition,
    )


# ── PUT /me/privacy ───────────────────────────────────────────────────────────


@router.put(
    "/me/privacy",
    response_model=PrivacySettingsResponse,
    summary="Zaktualizuj ustawienia prywatności",
)
async def update_privacy_settings(
    update: PrivacySettingsUpdate,
    db: DbSession,
    current_user: User = require_authenticated,
) -> PrivacySettingsResponse:
    """Aktualizuje wybrane ustawienia prywatności. Pola None są pomijane."""
    if update.preferred_language is not None and update.preferred_language not in _VALID_LANGUAGES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieznany język '{update.preferred_language}'. "
                   f"Dostępne: {sorted(_VALID_LANGUAGES)}",
        )
    if update.spiritual_tradition is not None and update.spiritual_tradition not in _VALID_TRADITIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Nieznana tradycja '{update.spiritual_tradition}'. "
                   f"Dostępne: {sorted(_VALID_TRADITIONS)}",
        )

    priv = await privacy_svc.get_or_create_privacy_settings(db, current_user)

    if update.journal_is_private is not None:
        priv.journal_is_private = update.journal_is_private
    if update.ai_can_read_journal is not None:
        priv.ai_can_read_journal = update.ai_can_read_journal
    if update.ai_history_enabled is not None:
        priv.ai_history_enabled = update.ai_history_enabled
    if update.preferred_language is not None:
        priv.preferred_language = update.preferred_language
    if update.spiritual_tradition is not None:
        priv.spiritual_tradition = update.spiritual_tradition

    await db.flush()
    await db.refresh(priv)

    return PrivacySettingsResponse(
        journal_is_private=priv.journal_is_private,
        ai_can_read_journal=priv.ai_can_read_journal,
        ai_history_enabled=priv.ai_history_enabled,
        preferred_language=priv.preferred_language,
        spiritual_tradition=priv.spiritual_tradition,
    )


# ── GET /me/export ────────────────────────────────────────────────────────────


@router.get(
    "/me/export",
    summary="Eksportuj wszystkie dane osobowe (RODO)",
)
async def export_my_data(
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Zwraca wszystkie dane osobowe użytkownika w formacie JSON (prawo do przenoszenia danych)."""
    return await privacy_svc.export_user_data(db, current_user)


# ── POST /me/ai-history/clear ─────────────────────────────────────────────────


@router.post(
    "/me/ai-history/clear",
    response_model=ClearHistoryResponse,
    summary="Wyczyść historię interakcji z AI",
)
async def clear_ai_history(
    db: DbSession,
    current_user: User = require_authenticated,
) -> ClearHistoryResponse:
    """Usuwa metadane historii interakcji z AI. Treść wiadomości nie jest przechowywana w bazie."""
    deleted_count = await privacy_svc.clear_ai_history(db, current_user)
    return ClearHistoryResponse(
        deleted_count=deleted_count,
        message=f"Usunięto {deleted_count} rekordów historii interakcji z AI.",
    )


# ── POST /me/delete ───────────────────────────────────────────────────────────


@router.post(
    "/me/delete",
    response_model=DeletionResponse,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Zażądaj usunięcia konta (RODO)",
)
async def request_account_deletion(
    db: DbSession,
    current_user: User = require_authenticated,
) -> DeletionResponse:
    """Oznacza konto do usunięcia (soft-delete). Konto zostanie trwale usunięte przez admina
    po upływie okresu retencji. Po wywołaniu tego endpointu konto jest natychmiast dezaktywowane."""
    await privacy_svc.request_deletion(db, current_user, actor_id=current_user.id)
    return DeletionResponse(
        message="Żądanie usunięcia konta zostało przyjęte. "
                "Konto zostało dezaktywowane i będzie trwale usunięte przez administratora.",
    )
