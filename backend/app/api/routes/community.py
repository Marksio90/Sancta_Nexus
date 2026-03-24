"""Community & Social Features API — /api/v1/community

Endpoints
---------
Intencje modlitewne:
  GET  /intentions              – list public intentions (filterable by category)
  POST /intentions              – create new intention
  POST /intentions/{id}/pray    – increment intercession count
  POST /intentions/{id}/answered – mark own intention as answered

Grupy modlitewne:
  GET  /groups                  – list public groups
  GET  /groups/{id}             – get group details
  POST /groups                  – create a group
  POST /groups/{id}/join        – join a group
  POST /groups/{id}/leave       – leave a group
  GET  /groups/my               – groups the current user belongs to

Różaniec:
  GET  /rosary/mysteries        – all mystery types + content
  GET  /rosary/today            – today's recommended mystery type
  GET  /rosary/community        – list open community sessions
  POST /rosary/community        – create a community session
  POST /rosary/community/{id}/join    – join a session
  POST /rosary/participation/{id}/decade – mark a decade complete
  POST /rosary/meditate/stream  – stream AI meditation for a mystery

Nowenny:
  GET  /novenas                 – novena library catalogue
  GET  /novenas/{id}            – full novena content
  GET  /novenas/{id}/day/{day}  – content for a specific day
  GET  /novenas/{id}/meditation/{day} – AI meditation for a day
  POST /novenas/{id}/start      – start tracking a novena (requires auth)
  POST /novenas/tracking/{id}/complete-day – mark a day as done
  GET  /novenas/my              – user's active/completed novenas

Overview:
  GET  /overview                – community feature overview
"""
from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

router = APIRouter()


# ── DB session dependency ─────────────────────────────────────────────────────

async def get_db():
    from app.core.dependencies import DbSession
    async with DbSession() as session:
        yield session


# ── Optional current user (returns None if no valid token) ───────────────────

async def optional_user(
    authorization: Optional[str] = None,
) -> Optional[str]:
    """Return user_id if bearer token present and valid, else None."""
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.replace("Bearer ", "")
    try:
        from app.core.security import verify_token
        payload = verify_token(token)
        return payload.get("sub") if payload else None
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
    category: str = Query(default="all"),
    limit: int = Query(default=30, le=100),
    offset: int = Query(default=0),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _intentions()
    items = await svc.list_public(
        db, category=category if category != "all" else None,
        limit=limit, offset=offset,
    )
    return {
        "intentions": items,
        "categories": svc.INTENTION_CATEGORIES if hasattr(svc, "INTENTION_CATEGORIES") else [],
    }


@router.post("/intentions", status_code=status.HTTP_201_CREATED)
async def create_intention(
    req: IntentionCreate,
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _intentions()
    return await svc.create(
        db,
        content=req.content,
        is_public=req.is_public,
        category=req.category,
        author_display=req.author_display,
        user_id=None,  # anonymous for now — auth token optional
    )


@router.post("/intentions/{intention_id}/pray")
async def pray_for_intention(
    intention_id: str,
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _intentions()
    result = await svc.intercede(db, intention_id)
    if not result:
        raise HTTPException(status_code=404, detail="Intention not found.")
    return result


@router.post("/intentions/{intention_id}/answered")
async def mark_intention_answered(
    intention_id: str,
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _intentions()
    result = await svc.mark_answered(db, intention_id, user_id)
    if not result:
        raise HTTPException(status_code=404, detail="Intention not found or not yours.")
    return result


# ── Prayer groups ─────────────────────────────────────────────────────────────

@router.get("/groups")
async def list_groups(
    category: str = Query(default="all"),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _groups()
    groups = await svc.list_groups(
        db, category=category if category != "all" else None
    )
    from app.services.community.prayer_group_service import GROUP_CATEGORIES
    return {"groups": groups, "categories": GROUP_CATEGORIES}


@router.get("/groups/my")
async def get_my_groups(
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _groups()
    return {"groups": await svc.get_user_groups(db, user_id)}


@router.get("/groups/{group_id}")
async def get_group(group_id: str, db=Depends(get_db)) -> dict[str, Any]:
    svc = _groups()
    group = await svc.get_group(db, group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found.")
    return group


@router.post("/groups", status_code=status.HTTP_201_CREATED)
async def create_group(
    req: GroupCreate,
    user_id: str = Query(default=None),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _groups()
    return await svc.create_group(
        db,
        name=req.name,
        description=req.description,
        category=req.category,
        schedule=req.schedule,
        parish=req.parish,
        leader_user_id=user_id,
    )


@router.post("/groups/{group_id}/join")
async def join_group(
    group_id: str,
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _groups()
    return await svc.join_group(db, group_id, user_id)


@router.post("/groups/{group_id}/leave")
async def leave_group(
    group_id: str,
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _groups()
    return await svc.leave_group(db, group_id, user_id)


# ── Rosary ────────────────────────────────────────────────────────────────────

@router.get("/rosary/mysteries")
async def get_mysteries() -> dict[str, Any]:
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
    svc = _rosary()
    mystery_type = svc.get_today_mystery()
    return {
        "mystery_type": mystery_type,
        "mysteries": svc.get_mysteries(mystery_type),
    }


@router.get("/rosary/community")
async def list_community_rosaries(db=Depends(get_db)) -> dict[str, Any]:
    svc = _rosary()
    sessions = await svc.list_open_sessions(db)
    return {"sessions": sessions}


@router.post("/rosary/community", status_code=status.HTTP_201_CREATED)
async def create_community_rosary(
    req: RosarySessionCreate,
    user_id: str = Query(default=None),
    db=Depends(get_db),
) -> dict[str, Any]:
    valid = {"radosne", "bolesne", "chwalebne", "swietlne"}
    if req.mystery_type not in valid:
        raise HTTPException(status_code=400, detail=f"Invalid mystery_type. Valid: {valid}")
    svc = _rosary()
    return await svc.create_session(db, req.mystery_type, req.intention, user_id)


@router.post("/rosary/community/{rosary_id}/join")
async def join_community_rosary(
    rosary_id: str,
    user_id: str = Query(default=None),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _rosary()
    return await svc.join_session(db, rosary_id, user_id)


@router.post("/rosary/participation/{participation_id}/decade")
async def complete_rosary_decade(
    participation_id: str,
    req: DecadeComplete,
    db=Depends(get_db),
) -> dict[str, Any]:
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
    svc = _novena()
    return {
        "title": "Biblioteka Nowenn",
        "novenas": svc.get_all_novenas(),
    }


@router.get("/novenas/my")
async def get_my_novenas(
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _novena()
    return {"novenas": await svc.get_user_novenas(db, user_id)}


@router.get("/novenas/{novena_id}")
async def get_novena(novena_id: str) -> dict[str, Any]:
    svc = _novena()
    novena = svc.get_novena(novena_id)
    if not novena:
        raise HTTPException(status_code=404, detail=f"Novena '{novena_id}' not found.")
    return novena


@router.get("/novenas/{novena_id}/day/{day}")
async def get_novena_day(novena_id: str, day: int) -> dict[str, Any]:
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
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _novena()
    result = await svc.start_novena(db, user_id, novena_id, req.intention)
    if "error" in result:
        raise HTTPException(status_code=404, detail=result["error"])
    return result


@router.post("/novenas/tracking/{tracking_id}/complete-day")
async def complete_novena_day(
    tracking_id: str,
    req: NovenaCompleteDay,
    user_id: str = Query(...),
    db=Depends(get_db),
) -> dict[str, Any]:
    svc = _novena()
    result = await svc.complete_day(db, tracking_id, user_id, req.day)
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
