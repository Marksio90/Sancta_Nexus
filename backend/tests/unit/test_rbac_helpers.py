"""Unit tests for RBAC helpers — _ROLE_LEVEL and has_role.

Does not import jose/cffi — stubs are applied before imports.
(The full test_rbac.py is excluded because python-jose's cffi backend is
broken in the local env; this file avoids that chain by stubbing jose.)

Contracts verified:
_ROLE_LEVEL:
- Exactly 8 roles mapped
- USER is lowest privilege (0)
- ADMIN is highest privilege (100)
- Ordering: USER < PREMIUM_USER < MODERATOR < EDITOR <
  SPIRITUAL_CONTENT_REVIEWER < GROUP_LEADER < ORGANIZATION_ADMIN < ADMIN

has_role:
- User with sufficient role returns True
- User with insufficient role returns False
- User with exact required role returns True (same level)
- User with unknown role treated as level 0
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.core.rbac import _ROLE_LEVEL, has_role
from app.models.database import UserRole


def _user(role: UserRole) -> MagicMock:
    u = MagicMock()
    u.role = role
    return u


# ===========================================================================
# _ROLE_LEVEL mapping
# ===========================================================================


class TestRoleLevelMapping:
    def test_exactly_8_roles(self):
        assert len(_ROLE_LEVEL) == 8

    def test_user_is_level_0(self):
        assert _ROLE_LEVEL[UserRole.USER] == 0

    def test_admin_is_level_100(self):
        assert _ROLE_LEVEL[UserRole.ADMIN] == 100

    def test_premium_user_above_user(self):
        assert _ROLE_LEVEL[UserRole.PREMIUM_USER] > _ROLE_LEVEL[UserRole.USER]

    def test_moderator_above_premium(self):
        assert _ROLE_LEVEL[UserRole.MODERATOR] > _ROLE_LEVEL[UserRole.PREMIUM_USER]

    def test_editor_above_moderator(self):
        assert _ROLE_LEVEL[UserRole.EDITOR] > _ROLE_LEVEL[UserRole.MODERATOR]

    def test_reviewer_above_editor(self):
        assert _ROLE_LEVEL[UserRole.SPIRITUAL_CONTENT_REVIEWER] > _ROLE_LEVEL[UserRole.EDITOR]

    def test_group_leader_above_reviewer(self):
        assert _ROLE_LEVEL[UserRole.GROUP_LEADER] > _ROLE_LEVEL[UserRole.SPIRITUAL_CONTENT_REVIEWER]

    def test_org_admin_above_group_leader(self):
        assert _ROLE_LEVEL[UserRole.ORGANIZATION_ADMIN] > _ROLE_LEVEL[UserRole.GROUP_LEADER]

    def test_admin_above_org_admin(self):
        assert _ROLE_LEVEL[UserRole.ADMIN] > _ROLE_LEVEL[UserRole.ORGANIZATION_ADMIN]

    def test_all_levels_unique(self):
        levels = list(_ROLE_LEVEL.values())
        assert len(levels) == len(set(levels))

    def test_all_levels_are_integers(self):
        for role, level in _ROLE_LEVEL.items():
            assert isinstance(level, int), f"{role} level is not int"

    def test_all_levels_non_negative(self):
        for level in _ROLE_LEVEL.values():
            assert level >= 0


# ===========================================================================
# has_role function
# ===========================================================================


class TestHasRole:
    def test_admin_has_any_role(self):
        user = _user(UserRole.ADMIN)
        for role in UserRole:
            assert has_role(user, role), f"Admin should have {role}"

    def test_user_only_has_user_role(self):
        user = _user(UserRole.USER)
        assert has_role(user, UserRole.USER) is True
        assert has_role(user, UserRole.PREMIUM_USER) is False
        assert has_role(user, UserRole.MODERATOR) is False
        assert has_role(user, UserRole.ADMIN) is False

    def test_premium_user_role(self):
        user = _user(UserRole.PREMIUM_USER)
        assert has_role(user, UserRole.USER) is True
        assert has_role(user, UserRole.PREMIUM_USER) is True
        assert has_role(user, UserRole.MODERATOR) is False

    def test_moderator_role(self):
        user = _user(UserRole.MODERATOR)
        assert has_role(user, UserRole.USER) is True
        assert has_role(user, UserRole.PREMIUM_USER) is True
        assert has_role(user, UserRole.MODERATOR) is True
        assert has_role(user, UserRole.EDITOR) is False

    def test_exact_role_match_returns_true(self):
        for role in UserRole:
            user = _user(role)
            assert has_role(user, role) is True, f"Exact role {role} should pass"

    def test_unknown_role_treated_as_zero(self):
        user = MagicMock()
        user.role = "completely_unknown_role"
        assert has_role(user, UserRole.USER) is True  # unknown = level 0 = USER level
        assert has_role(user, UserRole.PREMIUM_USER) is False
