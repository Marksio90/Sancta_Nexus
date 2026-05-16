"""Unit tests for the RBAC system."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.core.rbac import has_role, require_role
from app.models.database import User, UserRole


def _make_user(role: UserRole, is_active: bool = True) -> User:
    user = MagicMock(spec=User)
    user.role = role
    user.is_active = is_active
    return user


class TestHasRole:
    def test_admin_has_all_roles(self):
        admin = _make_user(UserRole.ADMIN)
        for role in UserRole:
            assert has_role(admin, role) is True

    def test_user_has_only_user_role(self):
        user = _make_user(UserRole.USER)
        assert has_role(user, UserRole.USER) is True
        assert has_role(user, UserRole.PREMIUM_USER) is False
        assert has_role(user, UserRole.MODERATOR) is False
        assert has_role(user, UserRole.ADMIN) is False

    def test_moderator_hierarchy(self):
        moderator = _make_user(UserRole.MODERATOR)
        assert has_role(moderator, UserRole.USER) is True
        assert has_role(moderator, UserRole.PREMIUM_USER) is True
        assert has_role(moderator, UserRole.MODERATOR) is True
        assert has_role(moderator, UserRole.EDITOR) is False
        assert has_role(moderator, UserRole.ADMIN) is False

    def test_editor_hierarchy(self):
        editor = _make_user(UserRole.EDITOR)
        assert has_role(editor, UserRole.MODERATOR) is True
        assert has_role(editor, UserRole.EDITOR) is True
        assert has_role(editor, UserRole.SPIRITUAL_CONTENT_REVIEWER) is False

    def test_content_reviewer_hierarchy(self):
        reviewer = _make_user(UserRole.SPIRITUAL_CONTENT_REVIEWER)
        assert has_role(reviewer, UserRole.EDITOR) is True
        assert has_role(reviewer, UserRole.SPIRITUAL_CONTENT_REVIEWER) is True
        assert has_role(reviewer, UserRole.GROUP_LEADER) is False

    def test_organization_admin_below_admin(self):
        org_admin = _make_user(UserRole.ORGANIZATION_ADMIN)
        assert has_role(org_admin, UserRole.GROUP_LEADER) is True
        assert has_role(org_admin, UserRole.ORGANIZATION_ADMIN) is True
        assert has_role(org_admin, UserRole.ADMIN) is False


class TestRequireRole:
    @pytest.mark.asyncio
    async def test_sufficient_role_returns_user(self):
        admin = _make_user(UserRole.ADMIN)
        dep = require_role(UserRole.ADMIN)
        inner = dep.dependency
        with patch("app.core.rbac.get_current_user", return_value=admin):
            result = await inner(current_user=admin)
        assert result is admin

    @pytest.mark.asyncio
    async def test_insufficient_role_raises_403(self):
        user = _make_user(UserRole.USER)
        dep = require_role(UserRole.ADMIN)
        inner = dep.dependency
        with pytest.raises(HTTPException) as exc_info:
            await inner(current_user=user)
        assert exc_info.value.status_code == 403
        assert "admin" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_inactive_user_raises_403(self):
        inactive_admin = _make_user(UserRole.ADMIN, is_active=False)
        dep = require_role(UserRole.USER)
        inner = dep.dependency
        with pytest.raises(HTTPException) as exc_info:
            await inner(current_user=inactive_admin)
        assert exc_info.value.status_code == 403
        assert "inactive" in exc_info.value.detail.lower()

    @pytest.mark.asyncio
    async def test_premium_user_can_access_premium_endpoint(self):
        premium = _make_user(UserRole.PREMIUM_USER)
        dep = require_role(UserRole.PREMIUM_USER)
        inner = dep.dependency
        result = await inner(current_user=premium)
        assert result is premium
