"""Community & Social Features API — /api/v1/community

Endpoints
---------
Intencje modlitewne:
  GET  /intentions              – list public active intentions (filterable by category)
  POST /intentions              – create new intention (optional auth; links user if authed)
  POST /intentions/{id}/pray    – increment intercession count (public)
  POST /intentions/{id}/answered – mark own intention as answered (require auth, verify ownership)
  DELETE /intentions/{id}       – delete intention (require auth, verify ownership or admin)
  GET  /intentions/mine         – authenticated user's own intentions (all statuses)
  GET  /groups/{id}/intentions  – active public intentions for a group
  POST /groups/{id}/intentions  – create intention linked to a group (require auth)

Grupy modlitewne:
  GET  /groups                  – list public groups
  GET  /groups/{id}             – get group details
  POST /groups                  – create a group (require auth)
  POST /groups/{id}/join        – join a group (require auth)
  POST /groups/{id}/leave       – leave a group (require auth)
  GET  /groups/my               – groups the current user belongs to (require auth)

Różaniec:
  GET  /rosary/mysteries        – all mystery types + content
  GET  /rosary/today            – today's recommended mystery type
  GET  /rosary/community        – list open community sessions
  POST /rosary/community        – create a community session (optional auth)
  POST /rosary/community/{id}/join    – join a session (optional auth)
  POST /rosary/participation/{id}/decade – mark a decade complete
  POST /rosary/meditate/stream  – stream AI meditation for a mystery

Nowenny:
  GET  /novenas                 – novena library catalogue
  GET  /novenas/{id}            – full novena content
  GET  /novenas/{id}/day/{day}  – content for a specific day
  GET  /novenas/{id}/meditation/{day} – AI meditation for a day
  POST /novenas/{id}/start      – start tracking a novena (require auth)
  POST /novenas/tracking/{id}/complete-day – mark a day as done (require auth)
  GET  /novenas/my              – user's active/completed novenas (require auth)

Overview:
  GET  /overview                – community feature overview
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, Field

from app.core.dependencies import DbSession
from app.core.rbac import require_authenticated
from app.models.database import User, UserRole

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Optional auth dependency ──────────────────────────────────────────────────

_optional_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_optional_bearer),
) -> Optional[User]:
    """Return the authenticated User if a valid Bearer token is present, else None."""
    if credentials is None:
        return None
    try:
        from app.core.security import verify_token
        from sqlalchemy import select
        from app.models.database import User as UserModel
        from app.core.dependencies import _get_session_factory

        payload = verify_token(credentials.credentials, expected_type="access")
        user_id: str = payload["sub"]

        factory = _get_session_factory()
        async with factory() as session:
            result = await session.execute(select(UserModel).where(UserModel.id == user_id))
            return result.scalar_one_or_none()
    except Exception:
        return None


# ── Lazy service loaders ──────────────────────────────────────────────────────

def _intentions():
    from app.services.community.intention_service import PrayerIntentionService
    return PrayerIntentionService()


def _groups():
    from app.services.community.prayer_group_service import PrayerGroupService
    return PrayerGroupService()


def _rosary():
    from app.services.community.rosary_service import RosaryService
    return RosaryService()


def _novena():
    from app.services.community.novena_service import NovenaService
    return NovenaService()


# ── Pydantic request models ───────────────────────────────────────────────────

class IntentionCreate(BaseModel):
    content: str = Field(..., min_length=5, max_length=500)
    is_public: bool = Field(default=True)
    category: str = Field(default="general")
    author_display: Optional[str] = Field(default=None, max_length=100)


class GroupCreate(BaseModel):
    name: str = Field(..., min_length=3, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    category: str = Field(default="ogólna")
    schedule: Optional[str] = Field(default=None, max_length=200)
    parish: Optional[str] = Field(default=None, max_length=200)


class RosarySessionCreate(BaseModel):
    mystery_type: str = Field(..., description="radosne|bolesne|chwalebne|swietlne")
    intention: Optional[str] = Field(default=None, max_length=300)


class RosaryMeditationRequest(BaseModel):
    mystery_type: str
    mystery_number: int = Field(..., ge=1, le=5)


class DecadeComplete(BaseModel):
    decade_number: int = Field(..., ge=1, le=5)


class NovenaStart(BaseModel):
    intention: Optional[str] = Field(default=None, max_length=500)


class NovenaCompleteDay(BaseModel):
    day: int = Field(..., ge=1, le=9)


# ── Intentions ────────────────────────────────────────────────────────────────

@router.get("/intentions")
async def list_intentions(
    db: DbSession,
    category: str = Query(default="all"),
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0),
) -> dict[str, Any]:
    """List public active prayer intentions. No authentication required."""
    from app.services.community.intention_service import INTENTION_CATEGORIES
    svc = _intentions()
    items = await svc.list_public(
        db, category=category if category != "all" else None,
        limit=limit, offset=offset,
    )
    return {
        "intentions": items,
        "categories": INTENTION_CATEGORIES,
    }


@router.post("/intentions", status_code=status.HTTP_201_CREATED)
async def create_intention(
    req: IntentionCreate,
    db: DbSession,
    current_user: Optional[User] = Depends(get_optional_user),
) -> dict[str, Any]:
    """Create a prayer intention. Auth is optional — anonymous submissions allowed.

    Public intentions are placed in PENDING_MODERATION until approved by a moderator.
    Private intentions are immediately ACTIVE.
    """
    svc = _intentions()
    return await svc.create(
        db,
        content=req.content,
        is_public=req.is_public,
        category=req.category,
        author_display=req.author_display,
        user_id=current_user.id if current_user else None,
    )


@router.post("/intentions/{intention_id}/pray")
async def pray_for_intention(
    intention_id: str,
    db: DbSession,
) -> dict[str, Any]:
    """Increment the intercession counter for an intention. No authentication required."""
    svc = _intentions()
    result = await svc.intercede(db, intention_id)
    if not result:
        raise HTTPException(status_code=404, detail="Intention not found.")
    return result


@router.post("/intentions/{intention_id}/answered")
async def mark_intention_answered(
    intention_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Mark own intention as answered. Requires authentication and ownership."""
    svc = _intentions()
    result = await svc.mark_answered(db, intention_id, current_user.id)
    if not result:
        raise HTTPException(status_code=404, detail="Intention not found or not yours.")
    return result


@router.delete("/intentions/{intention_id}", status_code=status.HTTP_200_OK)
async def delete_intention(
    intention_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Delete an intention. Requires ownership or admin role."""
    from sqlalchemy import select
    from sqlalchemy import delete as sa_delete
    from app.models.database import PrayerIntention

    result = await db.execute(
        select(PrayerIntention).where(PrayerIntention.id == intention_id)
    )
    intention = result.scalar_one_or_none()

    if intention is None:
        raise HTTPException(status_code=404, detail="Intention not found.")

    is_admin = current_user.role == UserRole.ADMIN
    if intention.user_id != current_user.id and not is_admin:
        raise HTTPException(status_code=403, detail="Not authorised to delete this intention.")

    await db.execute(
        sa_delete(PrayerIntention).where(PrayerIntention.id == intention_id)
    )
    await db.commit()
    return {"deleted": True, "intention_id": intention_id}


@router.get("/intentions/mine")
async def get_my_intentions(
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Return all intentions belonging to the authenticated user (all statuses)."""
    svc = _intentions()
    return {"intentions": await svc.list_by_user(db, current_user.id)}


# ── Prayer groups ─────────────────────────────────────────────────────────────

@router.get("/groups")
async def list_groups(
    db: DbSession,
    category: str = Query(default="all"),
) -> dict[str, Any]:
    """List public prayer groups. No authentication required."""
    from app.services.community.prayer_group_service import GROUP_CATEGORIES
    svc = _groups()
    groups = await svc.list_groups(
        db, category=category if category != "all" else None
    )
    return {"groups": groups, "categories": GROUP_CATEGORIES}


@router.get("/groups/my")
async def get_my_groups(
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Return groups the authenticated user belongs to."""
    svc = _groups()
    return {"groups": await svc.get_user_groups(db, current_user.id)}


@router.get("/groups/{group_id}")
async def get_group(group_id: str, db: DbSession) -> dict[str, Any]:
    """Get prayer group details. No authentication required."""
    svc = _groups()
    group = await svc.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found.")
    return group


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_group(
    req: GroupCreate,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Create a prayer group. Requires authentication."""
    svc = _groups()
    return await svc.create_group(
        db,
        name=req.name,
        description=req.description,
        category=req.category,
        schedule=req.schedule,
        parish=req.parish,
        leader_user_id=current_user.id,
    )


@router.post("/groups/{group_id}/join")
async def join_group(
    group_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Join a prayer group. Requires authentication."""
    svc = _groups()
    return await svc.join_group(db, group_id, current_user.id)


@router.post("/groups/{group_id}/leave")
async def leave_group(
    group_id: str,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Leave a prayer group. Requires authentication."""
    svc = _groups()
    return await svc.leave_group(db, group_id, current_user.id)


@router.get("/groups/{group_id}/intentions")
async def list_group_intentions(
    group_id: str,
    db: DbSession,
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0),
) -> dict[str, Any]:
    """List active public intentions for a prayer group. No authentication required."""
    svc = _intentions()
    items = await svc.list_by_group(db, group_id, limit=limit, offset=offset)
    return {"intentions": items, "group_id": group_id}


@router.post("/groups/{group_id}/intentions", status_code=status.HTTP_201_CREATED)
async def create_group_intention(
    group_id: str,
    req: IntentionCreate,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Create an intention linked to a specific prayer group. Requires authentication."""
    svc = _intentions()
    return await svc.create(
        db,
        content=req.content,
        is_public=req.is_public,
        category=req.category,
        author_display=req.author_display,
        user_id=current_user.id,
        group_id=group_id,
    )


# ── Rosary ────────────────────────────────────────────────────────────────────

@router.get("/rosary/mysteries")
async def get_mysteries() -> dict[str, Any]:
    """Return all Rosary mystery types with full content. No authentication required."""
    svc = _rosary()
    result = {}
    for mt in svc.get_all_mystery_types():
        result[mt["id"]] = {
            **mt,
            "mysteries": svc.get_mysteries(mt["id"]),
        }
    return {
        "mystery_types": result,
        "today": svc.get_today_mystery(),
    }


@router.get("/rosary/today")
async def get_today_mystery() -> dict[str, Any]:
    """Return today's recommended Rosary mystery type. No authentication required."""
    svc = _rosary()
    mystery_type = svc.get_today_mystery()
    return {
        "mystery_type": mystery_type,
        "mysteries": svc.get_mysteries(mystery_type),
    }


@router.get("/rosary/community")
async def list_community_rosaries(db: DbSession) -> dict[str, Any]:
    """List open community Rosary sessions. No authentication required."""
    svc = _rosary()
    sessions = await svc.list_open_sessions(db)
    return {"sessions": sessions}


@router.post("/rosary/community", status_code=status.HTTP_201_CREATED)
async def create_community_rosary(
    req: RosarySessionCreate,
    db: DbSession,
    current_user: Optional[User] = Depends(get_optional_user),
) -> dict[str, Any]:
    """Create a community Rosary session. Auth is optional."""
    valid = {"radosne", "bolesne", "chwalebne", "swietlne"}
    if req.mystery_type not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid mystery_type. Valid: {valid}")
    svc = _rosary()
    user_id = current_user.id if current_user else None
    return await svc.create_session(db, req.mystery_type, req.intention, user_id)


@router.post("/rosary/community/{rosary_id}/join")
async def join_community_rosary(
    rosary_id: str,
    db: DbSession,
    current_user: Optional[User] = Depends(get_optional_user),
) -> dict[str, Any]:
    """Join a community Rosary session. Auth is optional."""
    svc = _rosary()
    user_id = current_user.id if current_user else None
    return await svc.join_session(db, rosary_id, user_id)


@router.post("/rosary/participation/{participation_id}/decade")
async def complete_rosary_decade(
    participation_id: str,
    req: DecadeComplete,
    db: DbSession,
) -> dict[str, Any]:
    """Mark a Rosary decade as complete."""
    svc = _rosary()
    result = await svc.complete_decade(db, participation_id, req.decade_number)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/rosary/meditate/stream")
async def stream_rosary_meditation(req: RosaryMeditationRequest) -> StreamingResponse:
    """Stream AI meditation for a Rosary mystery."""
    async def _gen() -> AsyncIterator[bytes]:
        try:
            svc = _rosary()
            async for chunk in svc.stream_mystery_meditation(
                req.mystery_type, req.mystery_number
            ):
                yield chunk.encode("utf-8")
        except Exception as exc:
            logger.error("Rosary meditation stream error: %s", exc)
            yield b"[Blad generowania medytacji]"

    return StreamingResponse(
        _gen(),
        media_type="text/plain; charset=utf-8",
        headers={"X-Content-Type-Options": "nosniff"},
    )


# ── Novenas ───────────────────────────────────────────────────────────────────

@router.get("/novenas")
async def list_novenas() -> dict[str, Any]:
    """Return novena library catalogue. No authentication required."""
    svc = _novena()
    return {
        "title": "Biblioteka Nowenn",
        "novenas": svc.get_all_novenas(),
    }


@router.get("/novenas/my")
async def get_my_novenas(
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Return the authenticated user's active and completed novenas."""
    svc = _novena()
    return {"novenas": await svc.get_user_novenas(db, current_user.id)}


@router.get("/novenas/{novena_id}")
async def get_novena(novena_id: str) -> dict[str, Any]:
    """Return full novena content. No authentication required."""
    svc = _novena()
    novena = svc.get_novena(novena_id)
    if not novena:
        raise HTTPException(status_code=404, detail=f"Novena '{novena_id}' not found.")
    return novena


@router.get("/novenas/{novena_id}/day/{day}")
async def get_novena_day(novena_id: str, day: int) -> dict[str, Any]:
    """Return content for a specific novena day. No authentication required."""
    svc = _novena()
    content = svc.get_day(novena_id, day)
    if not content:
        raise HTTPException(status_code=404, detail="Day not found.")
    return content


@router.get("/novenas/{novena_id}/meditation/{day}")
async def get_novena_meditation(
    novena_id: str,
    day: int,
    intention: Optional[str] = Query(default=None),
) -> dict[str, Any]:
    """Return AI-generated meditation for a novena day. No authentication required."""
    try:
        svc = _novena()
        meditation = await svc.generate_day_meditation(novena_id, day, intention)
        return {"novena_id": novena_id, "day": day, "meditation": meditation}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/novenas/{novena_id}/start", status_code=status.HTTP_201_CREATED)
async def start_novena(
    novena_id: str,
    req: NovenaStart,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Start tracking a novena. Requires authentication."""
    svc = _novena()
    result = await svc.start_novena(db, current_user.id, novena_id, req.intention)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/novenas/tracking/{tracking_id}/complete-day")
async def complete_novena_day(
    tracking_id: str,
    req: NovenaCompleteDay,
    db: DbSession,
    current_user: User = require_authenticated,
) -> dict[str, Any]:
    """Mark a novena day as completed. Requires authentication."""
    svc = _novena()
    result = await svc.complete_day(db, tracking_id, current_user.id, req.day)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


# ── Overview ──────────────────────────────────────────────────────────────────

@router.get("/overview")
async def community_overview() -> dict[str, Any]:
    return {
        "features": [
            {
                "id": "intentions",
                "title": "Intencje modlitewne",
                "description": "Dziel się swoimi intencjami z wspólnotą i módl się za innych.",
                "icon": "🙏",
                "url_prefix": "/api/v1/community/intentions",
            },
            {
                "id": "groups",
                "title": "Grupy modlitewne",
                "description": "Dołącz do parafialnych grup modlitewnych lub stwórz własną.",
                "icon": "👥",
                "url_prefix": "/api/v1/community/groups",
            },
            {
                "id": "rosary",
                "title": "Różaniec wspólnotowy",
                "description": "Odmawiaj Różaniec razem z innymi — tajemnice z medytacją AI.",
                "icon": "📿",
                "url_prefix": "/api/v1/community/rosary",
            },
            {
                "id": "novenas",
                "title": "Nowenny z trackingiem",
                "description": "8 nowenn z biblioteką modlitw i śledzeniem postępu przez 9 dni.",
                "icon": "🕯",
                "url_prefix": "/api/v1/community/novenas",
            },
        ]
    }
