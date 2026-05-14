"""Role-Based Access Control (RBAC) for Sancta Nexus.

Role hierarchy (ascending privilege):
    user < premium_user < moderator < editor
    < spiritual_content_reviewer < group_leader
    < organization_admin < admin

Usage in routes::

    from app.core.rbac import require_role, require_admin
    from app.models.database import UserRole

    @router.get("/admin/users")
    async def list_users(user: User = require_admin):
        ...

    @router.post("/content")
    async def create_content(user: User = require_role(UserRole.EDITOR)):
        ...
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, status

from app.core.security import get_current_user
from app.models.database import User, UserRole

# ── Role ordering ─────────────────────────────────────────────────────────────

_ROLE_LEVEL: dict[UserRole, int] = {
    UserRole.USER: 0,
    UserRole.PREMIUM_USER: 10,
    UserRole.MODERATOR: 20,
    UserRole.EDITOR: 30,
    UserRole.SPIRITUAL_CONTENT_REVIEWER: 40,
    UserRole.GROUP_LEADER: 50,
    UserRole.ORGANIZATION_ADMIN: 60,
    UserRole.ADMIN: 100,
}


def has_role(user: User, minimum_role: UserRole) -> bool:
    """Return True when *user* has at least *minimum_role* privilege level."""
    user_level = _ROLE_LEVEL.get(user.role, 0)
    required_level = _ROLE_LEVEL.get(minimum_role, 0)
    return user_level >= required_level


# ── Dependency factory ────────────────────────────────────────────────────────


def require_role(minimum_role: UserRole):
    """FastAPI dependency that enforces a minimum role.

    Raises HTTP 403 when the authenticated user's role is insufficient.

    Example::

        @router.delete("/content/{id}")
        async def delete_content(
            content_id: str,
            user: User = Depends(require_role(UserRole.EDITOR)),
        ):
            ...
    """

    async def _check(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is inactive.",
            )
        if not has_role(current_user, minimum_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires at least the '{minimum_role.value}' role.",
            )
        return current_user

    return Depends(_check)


# ── Convenience shortcuts ─────────────────────────────────────────────────────

require_admin = require_role(UserRole.ADMIN)
require_organization_admin = require_role(UserRole.ORGANIZATION_ADMIN)
require_group_leader = require_role(UserRole.GROUP_LEADER)
require_content_reviewer = require_role(UserRole.SPIRITUAL_CONTENT_REVIEWER)
require_editor = require_role(UserRole.EDITOR)
require_moderator = require_role(UserRole.MODERATOR)
require_premium = require_role(UserRole.PREMIUM_USER)

# Active authenticated user (any role)
require_authenticated = require_role(UserRole.USER)
