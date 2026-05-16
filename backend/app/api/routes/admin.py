"""Panel administracyjny — Sancta Nexus.

Wszystkie endpointy wymagają roli ADMIN.

Endpoints:
    GET  /admin/users                    — lista użytkowników
    GET  /admin/users/{id}               — profil użytkownika
    PUT  /admin/users/{id}/role          — zmiana roli
    POST /admin/users/{id}/deactivate    — dezaktywacja konta
    GET  /admin/audit-logs               — logi audytu
    GET  /admin/feature-flags            — stan feature flags
    GET  /admin/ai-interactions          — metadane interakcji AI
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import func, select

from app.core.dependencies import DbSession
from app.core.feature_flags import feature_flags
from app.core.rbac import require_admin
from app.models.database import (
    AiInteraction,
    AuditEventType,
    AuditLog,
    User,
    UserRole,
)
from app.services.audit.audit_service import audit
from app.services.community.intention_service import PrayerIntentionService

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Schemas ───────────────────────────────────────────────────────────────────


class AdminUserListItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    email: str
    name: str
    role: str
    subscription_tier: str
    is_active: bool
    created_at: str
    deleted_at: str | None


class AdminUserListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    users: list[AdminUserListItem]
    total: int
    page: int
    page_size: int


class RoleChangeRequest(BaseModel):
    model_config = ConfigDict(strict=True)

    new_role: UserRole = Field(..., description="Nowa rola użytkownika.")


class RoleChangeResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    user_id: str
    old_role: str
    new_role: str
    message: str


class AuditLogItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    event_type: str
    user_id: str | None
    actor_id: str | None
    description: str
    created_at: str


class AuditLogListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    logs: list[AuditLogItem]
    total: int
    page: int
    page_size: int


class FeatureFlagsResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    flags: dict[str, bool]


class AiInteractionItem(BaseModel):
    model_config = ConfigDict(strict=True)

    id: str
    user_id: str | None
    module: str
    risk_category: str
    was_modified: bool
    violations: str | None
    created_at: str


class AiInteractionListResponse(BaseModel):
    model_config = ConfigDict(strict=True)

    interactions: list[AiInteractionItem]
    total: int
    page: int
    page_size: int


# ── GET /admin/users ──────────────────────────────────────────────────────────


@router.get(
    "/users",
    response_model=AdminUserListResponse,
    summary="Lista wszystkich użytkowników",
)
async def list_users(
    db: DbSession,
    admin: User = require_admin,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=50, ge=1, le=200),
    role: UserRole | None = Query(default=None),
    is_active: bool | None = Query(default=None),
) -> AdminUserListResponse:
    """Paginowana lista użytkowników z opcjonalnym filtrem roli i statusu."""
    query = select(User)
    if role is not None:
        query = query.where(User.role == role)
    if is_active is not None:
        query = query.where(User.is_active == is_active)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(User.created_at.desc()))
    users = result.scalars().all()

    return AdminUserListResponse(
        users=[
            AdminUserListItem(
                id=u.id,
                email=u.email,
                name=u.name,
                role=u.role.value,
                subscription_tier=u.subscription_tier.value,
                is_active=u.is_active,
                created_at=u.created_at.isoformat(),
                deleted_at=u.deleted_at.isoformat() if u.deleted_at else None,
            )
            for u in users
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /admin/users/{id} ─────────────────────────────────────────────────────


@router.get(
    "/users/{user_id}",
    response_model=AdminUserListItem,
    summary="Profil użytkownika (widok admina)",
)
async def get_user_admin(
    user_id: str,
    db: DbSession,
    admin: User = require_admin,
) -> AdminUserListItem:
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Użytkownik nie istnieje.")
    return AdminUserListItem(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role.value,
        subscription_tier=user.subscription_tier.value,
        is_active=user.is_active,
        created_at=user.created_at.isoformat(),
        deleted_at=user.deleted_at.isoformat() if user.deleted_at else None,
    )


# ── PUT /admin/users/{id}/role ────────────────────────────────────────────────


@router.put(
    "/users/{user_id}/role",
    response_model=RoleChangeResponse,
    summary="Zmień rolę użytkownika",
)
async def change_user_role(
    user_id: str,
    body: RoleChangeRequest,
    db: DbSession,
    admin: User = require_admin,
) -> RoleChangeResponse:
    """Zmienia rolę użytkownika. Tylko admin może przyznać rolę admin."""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Użytkownik nie istnieje.")

    old_role = user.role.value
    user.role = body.new_role

    await audit.log(
        db,
        event_type=AuditEventType.USER_ROLE_CHANGED,
        user_id=user.id,
        actor_id=admin.id,
        description=f"Rola zmieniona z '{old_role}' na '{body.new_role.value}'",
        payload={"old_role": old_role, "new_role": body.new_role.value},
    )

    await db.flush()
    return RoleChangeResponse(
        user_id=user.id,
        old_role=old_role,
        new_role=body.new_role.value,
        message=f"Rola użytkownika zmieniona na '{body.new_role.value}'.",
    )


# ── POST /admin/users/{id}/deactivate ────────────────────────────────────────


@router.post(
    "/users/{user_id}/deactivate",
    status_code=status.HTTP_200_OK,
    summary="Dezaktywuj konto użytkownika",
)
async def deactivate_user(
    user_id: str,
    db: DbSession,
    admin: User = require_admin,
) -> dict[str, str]:
    """Dezaktywuje konto użytkownika (blokada logowania, soft-delete)."""
    if user_id == admin.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Nie możesz dezaktywować własnego konta przez panel admina.",
        )
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Użytkownik nie istnieje.")

    user.is_active = False
    await audit.log(
        db,
        event_type=AuditEventType.USER_DELETED,
        user_id=user.id,
        actor_id=admin.id,
        description=f"Konto użytkownika {user.id} dezaktywowane przez admina",
    )
    await db.flush()
    return {"message": f"Konto użytkownika {user_id} zostało dezaktywowane."}


# ── GET /admin/audit-logs ─────────────────────────────────────────────────────


@router.get(
    "/audit-logs",
    response_model=AuditLogListResponse,
    summary="Lista logów audytu",
)
async def list_audit_logs(
    db: DbSession,
    admin: User = require_admin,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    event_type: AuditEventType | None = Query(default=None),
    user_id: str | None = Query(default=None),
) -> AuditLogListResponse:
    """Paginowana lista logów audytu z filtrowaniem po typie zdarzenia i użytkowniku."""
    query = select(AuditLog)
    if event_type is not None:
        query = query.where(AuditLog.event_type == event_type)
    if user_id is not None:
        query = query.where(AuditLog.user_id == user_id)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(query.offset(offset).limit(page_size).order_by(AuditLog.created_at.desc()))
    logs = result.scalars().all()

    return AuditLogListResponse(
        logs=[
            AuditLogItem(
                id=log.id,
                event_type=log.event_type.value,
                user_id=log.user_id,
                actor_id=log.actor_id,
                description=log.description,
                created_at=log.created_at.isoformat(),
            )
            for log in logs
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── GET /admin/feature-flags ──────────────────────────────────────────────────


@router.get(
    "/feature-flags",
    response_model=FeatureFlagsResponse,
    summary="Stan wszystkich feature flags",
)
async def get_feature_flags(
    admin: User = require_admin,
) -> FeatureFlagsResponse:
    """Zwraca aktualny stan wszystkich feature flags odczytanych z konfiguracji."""
    return FeatureFlagsResponse(flags=feature_flags.all_flags())


# ── GET /admin/ai-interactions ────────────────────────────────────────────────


@router.get(
    "/ai-interactions",
    response_model=AiInteractionListResponse,
    summary="Metadane interakcji AI (safety review)",
)
async def list_ai_interactions(
    db: DbSession,
    admin: User = require_admin,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=100, ge=1, le=500),
    was_modified: bool | None = Query(default=None, description="Filtruj po interwencji safety layer"),
    module: str | None = Query(default=None),
) -> AiInteractionListResponse:
    """Lista metadanych interakcji AI do przeglądu bezpieczeństwa. Treść wiadomości nie jest przechowywana."""
    query = select(AiInteraction)
    if was_modified is not None:
        query = query.where(AiInteraction.was_modified == was_modified)
    if module is not None:
        query = query.where(AiInteraction.module == module)

    count_result = await db.execute(select(func.count()).select_from(query.subquery()))
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        query.offset(offset).limit(page_size).order_by(AiInteraction.created_at.desc())
    )
    records = result.scalars().all()

    return AiInteractionListResponse(
        interactions=[
            AiInteractionItem(
                id=r.id,
                user_id=r.user_id,
                module=r.module,
                risk_category=r.risk_category,
                was_modified=r.was_modified,
                violations=r.violations,
                created_at=r.created_at.isoformat(),
            )
            for r in records
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


# ── Intention moderation ──────────────────────────────────────────────────────


class RejectIntentionBody(BaseModel):
    model_config = ConfigDict(strict=True)

    reason: str = Field(..., min_length=1, max_length=500, description="Reason for rejection.")


@router.get(
    "/intentions/pending",
    summary="Lista intencji oczekujących na moderację",
)
async def list_pending_intentions(
    db: DbSession,
    admin: User = require_admin,
) -> dict[str, Any]:
    """Return all prayer intentions with PENDING_MODERATION status. Admin only."""
    svc = PrayerIntentionService()
    intentions = await svc.list_pending_moderation(db)
    return {"intentions": intentions, "count": len(intentions)}


@router.post(
    "/intentions/{intention_id}/approve",
    summary="Zatwierdź intencję modlitewną",
)
async def approve_intention(
    intention_id: str,
    db: DbSession,
    admin: User = require_admin,
) -> dict[str, Any]:
    """Approve a pending prayer intention — sets status to ACTIVE. Admin only."""
    svc = PrayerIntentionService()
    result = await svc.approve(db, intention_id, admin.id)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intention not found or already moderated.",
        )
    await audit.log(
        db,
        event_type=AuditEventType.INTENTION_MODERATED,
        user_id=result.get("user_id"),
        actor_id=admin.id,
        description=f"Intention {intention_id} approved by admin {admin.id}",
        payload={"intention_id": intention_id, "action": "approved"},
    )
    return result


@router.post(
    "/intentions/{intention_id}/reject",
    summary="Odrzuć intencję modlitewną",
)
async def reject_intention(
    intention_id: str,
    body: RejectIntentionBody,
    db: DbSession,
    admin: User = require_admin,
) -> dict[str, Any]:
    """Reject a pending prayer intention with a reason. Admin only."""
    svc = PrayerIntentionService()
    result = await svc.reject(db, intention_id, admin.id, body.reason)
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intention not found or already moderated.",
        )
    await audit.log(
        db,
        event_type=AuditEventType.INTENTION_MODERATED,
        user_id=result.get("user_id"),
        actor_id=admin.id,
        description=f"Intention {intention_id} rejected by admin {admin.id}",
        payload={"intention_id": intention_id, "action": "rejected"},
    )
    return result
