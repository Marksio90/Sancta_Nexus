"""Prayer progress tracking API.

Exposes computed progress stats (streak, journey stages, themes) from the
existing ``Session`` table, supplemented by lightweight theme data stored in
``User.spiritual_profile_json``.

No schema migration required: all new data fits in the existing JSON column.

Streak algorithm: consecutive days with at least one completed session,
counting backwards from today.
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, date, datetime, timedelta
from typing import Any

from fastapi import APIRouter, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import Session as DbSession_model, SessionType, User

logger = logging.getLogger(__name__)

router = APIRouter()

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------


class SessionRecord(BaseModel):
    id: str
    date: str
    passage_ref: str = ""
    emotion: str = ""
    duration_minutes: int = 0


class ThemeItem(BaseModel):
    name: str
    count: int


class JourneyProgress(BaseModel):
    purgativa: float
    illuminativa: float
    unitiva: float


class ProgressStats(BaseModel):
    prayer_streak: int
    total_sessions: int
    last_prayer_date: str | None
    themes: list[ThemeItem]
    journey_progress: JourneyProgress


class RecordSessionRequest(BaseModel):
    date: str = Field(..., description="ISO date string YYYY-MM-DD")
    passage_ref: str = Field(default="", max_length=128)
    emotion: str = Field(default="", max_length=64)
    duration_minutes: int = Field(default=0, ge=0, le=1440)
    theme: str | None = Field(default=None, max_length=64)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _compute_streak(session_dates: list[date]) -> int:
    if not session_dates:
        return 0
    unique_days = sorted(set(session_dates), reverse=True)
    today = date.today()
    streak = 0
    expected = today
    for d in unique_days:
        if d == expected:
            streak += 1
            expected = expected - timedelta(days=1)
        elif d < expected:
            break
    return streak


def _compute_journey(total: int) -> JourneyProgress:
    return JourneyProgress(
        purgativa=min(100.0, total * 5.0),
        illuminativa=min(100.0, max(0.0, (total - 20) * 5.0)) if total >= 20 else 0.0,
        unitiva=min(100.0, max(0.0, (total - 40) * 5.0)) if total >= 40 else 0.0,
    )


def _load_themes(user: User) -> list[dict[str, Any]]:
    if not user.spiritual_profile_json:
        return []
    try:
        return json.loads(user.spiritual_profile_json).get("progress_themes", [])
    except (ValueError, TypeError):
        return []


def _save_themes(user: User, themes: list[dict[str, Any]]) -> None:
    try:
        profile = json.loads(user.spiritual_profile_json) if user.spiritual_profile_json else {}
    except (ValueError, TypeError):
        profile = {}
    profile["progress_themes"] = themes
    user.spiritual_profile_json = json.dumps(profile, ensure_ascii=False)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get("", response_model=ProgressStats, summary="Pobierz statystyki modlitwy")
async def get_progress(
    db: DbSession,
    current_user: User = require_authenticated,
) -> ProgressStats:
    """Return prayer streak, journey progress, and theme breakdown.

    Streak and total sessions are computed from the ``sessions`` table.
    Themes are stored in ``User.spiritual_profile_json``.
    """
    result = await db.execute(
        select(DbSession_model.started_at)
        .where(
            DbSession_model.user_id == current_user.id,
            DbSession_model.session_type == SessionType.LECTIO_DIVINA,
            DbSession_model.ended_at.isnot(None),
        )
        .order_by(DbSession_model.started_at.desc())
    )
    session_rows = result.scalars().all()

    session_dates = [row.date() for row in session_rows]
    total = len(session_dates)
    streak = _compute_streak(session_dates)
    last_prayer = session_dates[0].isoformat() if session_dates else None

    # Load themes from JSON profile
    raw_themes = _load_themes(current_user)
    themes = [ThemeItem(name=t["name"], count=t["count"]) for t in raw_themes if "name" in t]

    return ProgressStats(
        prayer_streak=streak,
        total_sessions=total,
        last_prayer_date=last_prayer,
        themes=themes,
        journey_progress=_compute_journey(total),
    )


@router.post(
    "/session",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Zarejestruj sesję modlitwy w historii postępu",
)
async def record_session(
    body: RecordSessionRequest,
    db: DbSession,
    current_user: User = require_authenticated,
) -> None:
    """Record a completed prayer session for streak and theme tracking.

    This creates a lightweight ``Session`` DB row and optionally increments
    a theme counter in the user profile JSON.
    """
    try:
        session_date = datetime.fromisoformat(body.date).replace(tzinfo=UTC)
    except ValueError:
        session_date = datetime.now(UTC)

    db_session = DbSession_model(
        user_id=current_user.id,
        session_type=SessionType.LECTIO_DIVINA,
        scripture_reference=body.passage_ref or None,
        started_at=session_date,
        ended_at=session_date + timedelta(minutes=max(1, body.duration_minutes)),
    )
    db.add(db_session)

    if body.theme:
        result = await db.execute(select(User).where(User.id == current_user.id))
        user = result.scalar_one_or_none()
        if user:
            themes = _load_themes(user)
            existing = next((t for t in themes if t.get("name") == body.theme), None)
            if existing:
                existing["count"] = existing.get("count", 0) + 1
            else:
                themes.append({"name": body.theme, "count": 1})
            # Keep top 10 themes
            themes.sort(key=lambda t: t.get("count", 0), reverse=True)
            _save_themes(user, themes[:10])
            db.add(user)

    await db.flush()
    logger.info("Progress session recorded for user=%s date=%s", current_user.id, body.date)
