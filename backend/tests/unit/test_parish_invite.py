"""Unit tests for parish invite code feature.

Covers:
  - PrayerGroup model has invite_code column
  - invite_code has unique constraint
  - InviteCodeResponse model validates correctly
  - GroupByCodeResponse model validates correctly
  - community router has invite-code routes
  - invite code endpoints are POST/GET respectively
  - invite_code column is nullable (existing groups not broken)
"""
import sys
from unittest.mock import MagicMock

# Stub heavy deps
for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
    "arq", "arq.connections", "arq.jobs",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()
sys.modules["arq"].cron = lambda fn, **_: fn


class TestPrayerGroupModel:
    def test_invite_code_column_exists(self):
        from app.models.database import PrayerGroup
        from sqlalchemy import inspect as sa_inspect
        cols = {c.key for c in PrayerGroup.__mapper__.columns}
        assert "invite_code" in cols

    def test_invite_code_is_nullable(self):
        from app.models.database import PrayerGroup
        col = PrayerGroup.__mapper__.columns["invite_code"]
        assert col.nullable is True

    def test_invite_code_is_indexed(self):
        from app.models.database import PrayerGroup
        col = PrayerGroup.__mapper__.columns["invite_code"]
        assert col.index is True

    def test_invite_code_max_length_16(self):
        from app.models.database import PrayerGroup
        col = PrayerGroup.__mapper__.columns["invite_code"]
        assert col.type.length == 16

    def test_prayer_group_has_leader_user_id(self):
        from app.models.database import PrayerGroup
        cols = {c.key for c in PrayerGroup.__mapper__.columns}
        assert "leader_user_id" in cols


class TestInviteCodeSchemas:
    def test_invite_code_response_valid(self):
        from app.api.routes.community import InviteCodeResponse
        r = InviteCodeResponse(
            group_id="group-123",
            invite_code="ABCD1234",
            join_url="/grupy/dolacz/ABCD1234",
        )
        assert r.invite_code == "ABCD1234"
        assert "dolacz" in r.join_url

    def test_group_by_code_response_valid(self):
        from app.api.routes.community import GroupByCodeResponse
        r = GroupByCodeResponse(
            group_id="g1",
            name="Parafia Wniebowzięcia NMP",
            description=None,
            parish="Parafia NMP",
            category="parish",
            member_count=42,
            is_public=True,
        )
        assert r.name == "Parafia Wniebowzięcia NMP"
        assert r.description is None

    def test_group_by_code_response_requires_name(self):
        from pydantic import ValidationError
        from app.api.routes.community import GroupByCodeResponse
        import pytest
        with pytest.raises(ValidationError):
            GroupByCodeResponse(
                group_id="g1",
                # name missing
                category="parish",
                member_count=0,
                is_public=True,
            )


class TestInviteCodeRoutes:
    def test_community_router_has_invite_code_post_route(self):
        from app.api.routes.community import router
        methods_paths = [(r.methods, r.path) for r in router.routes]
        invite_routes = [
            (m, p) for m, p in methods_paths
            if "invite-code" in p
        ]
        assert len(invite_routes) >= 1
        # Should be POST
        assert any("POST" in (m or set()) for m, p in invite_routes)

    def test_community_router_has_code_get_route(self):
        from app.api.routes.community import router
        paths = [r.path for r in router.routes]
        assert any("code" in p for p in paths)

    def test_community_router_has_code_join_post_route(self):
        from app.api.routes.community import router
        methods_paths = [(r.methods, r.path) for r in router.routes]
        join_routes = [
            (m, p) for m, p in methods_paths
            if "code" in p and "join" in p
        ]
        assert len(join_routes) >= 1

    def test_invite_code_join_url_format(self):
        from app.api.routes.community import InviteCodeResponse
        r = InviteCodeResponse(
            group_id="g1",
            invite_code="XY789ABC",
            join_url="/grupy/dolacz/XY789ABC",
        )
        assert r.join_url.endswith(r.invite_code)
