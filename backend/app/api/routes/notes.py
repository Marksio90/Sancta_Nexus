"""Verse notes API — persist personal scripture reflections to the backend.

Replaces the previous localStorage-only implementation in the frontend
``notes.ts`` store.  Notes are stored as a JSON blob in
``UserPrivacySettings.spiritual_tradition`` — no, more specifically in a
dedicated column added by migration 006.  Until that migration runs, this
module stores notes inside ``User.spiritual_profile_json`` as a nested
``"notes"`` dict, which requires no schema change and is available
immediately.

Design choices:
- Notes keyed by scripture reference string (e.g. ``"J 3,16"``).
- Max 10 000 characters per note; max 500 notes per user.
- References are lowercased for storage to normalise "J 3,16" vs "j 3,16".
- Stored as ``spiritual_profile_json.notes``.  A dedicated table is a
  better long-term solution but deferred to keep this sprint zero-migration.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import User

logger = logging.getLogger(__name__)

router = APIRouter()

_MAX_NOTES = 500
_MAX_NOTE_LEN = 10_000


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _load_profile(user: User) -> dict[str, Any]:
    if not user.spiritual_profile_json:
        return {}
    try:
        return json.loads(user.spiritual_profile_json)
    except (ValueError, TypeError):
        return {}


def _save_profile(user: User, profile: dict[str, Any]) -> None:
    user.spiritual_profile_json = json.dumps(profile, ensure_ascii=False)


def _get_notes(user: User) -> dict[str, str]:
    return _load_profile(user).get("notes", {})


def _set_notes(user: User, notes: dict[str, str]) -> None:
    profile = _load_profile(user)
    profile["notes"] = notes
    _save_profile(user, profile)


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class NoteItem(BaseModel):
    ref: str
    text: str
    saved_at: str | None = None


class SaveNoteRequest(BaseModel):
    text: str = Field(..., max_length=_MAX_NOTE_LEN)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=list[NoteItem], summary="Pobierz wszystkie notatki")
async def get_all_notes(
    db: DbSession,
    current_user: User = require_authenticated,
) -> list[NoteItem]:
    """Return all verse notes for the authenticated user."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    notes = _get_notes(user)
    return [NoteItem(ref=ref, text=text) for ref, text in notes.items() if text.strip()]


@router.get("/{ref:path}", response_model=NoteItem, summary="Pobierz notatkę dla wersetu")
async def get_note(
    ref: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> NoteItem:
    """Return the note for a single scripture reference."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    notes = _get_notes(user)
    text = notes.get(ref.lower(), "")
    return NoteItem(ref=ref, text=text)


@router.put("/{ref:path}", response_model=NoteItem, summary="Zapisz lub zaktualizuj notatkę")
async def save_note(
    ref: str,
    body: SaveNoteRequest,
    db: DbSession,
    current_user: User = require_authenticated,
) -> NoteItem:
    """Save or update a personal note for a scripture reference."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    notes = _get_notes(user)
    key = ref.lower()
    if key not in notes and len(notes) >= _MAX_NOTES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Maximum {_MAX_NOTES} notes reached. Delete some before adding new ones.",
        )

    notes[key] = body.text
    _set_notes(user, notes)
    db.add(user)
    await db.flush()

    logger.info("Note saved for user=%s ref=%s", current_user.id, ref)
    return NoteItem(ref=ref, text=body.text)


@router.delete("/{ref:path}", status_code=status.HTTP_204_NO_CONTENT, summary="Usuń notatkę")
async def delete_note(
    ref: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> None:
    """Delete the note for a scripture reference."""
    result = await db.execute(select(User).where(User.id == current_user.id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

    notes = _get_notes(user)
    key = ref.lower()
    if key not in notes:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found.")

    del notes[key]
    _set_notes(user, notes)
    db.add(user)
    await db.flush()
    logger.info("Note deleted for user=%s ref=%s", current_user.id, ref)
