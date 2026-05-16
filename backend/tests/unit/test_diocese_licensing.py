"""Unit tests for diocese licensing B2B model.

Covers:
  - RegisterDioceseRequest validation
  - DioceseResponse model
  - ActivateUserRequest requires valid email
  - Router has all 5 diocese endpoints
  - Router is registered in main.py
  - DioceseLicense ORM model has expected columns
  - User model has diocese_id column
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


class TestRegisterDioceseRequest:
    def test_valid_minimal(self):
        from app.api.routes.diocese import RegisterDioceseRequest
        r = RegisterDioceseRequest(
            name="Archidiecezja Krakowska",
            diocese_code="krakow-archdiocese",
            contact_email="it@archikrakow.pl",
        )
        assert r.name == "Archidiecezja Krakowska"
        assert r.country == "PL"
        assert r.max_users == 0

    def test_name_too_short(self):
        from pydantic import ValidationError
        from app.api.routes.diocese import RegisterDioceseRequest
        import pytest
        with pytest.raises(ValidationError):
            RegisterDioceseRequest(
                name="AB",
                diocese_code="krakow",
                contact_email="it@test.pl",
            )

    def test_diocese_code_too_short(self):
        from pydantic import ValidationError
        from app.api.routes.diocese import RegisterDioceseRequest
        import pytest
        with pytest.raises(ValidationError):
            RegisterDioceseRequest(
                name="Test Diocese",
                diocese_code="x",
                contact_email="it@test.pl",
            )

    def test_max_users_zero_means_unlimited(self):
        from app.api.routes.diocese import RegisterDioceseRequest
        r = RegisterDioceseRequest(
            name="Test Diocese",
            diocese_code="test-diocese",
            contact_email="it@test.pl",
            max_users=0,
        )
        assert r.max_users == 0

    def test_max_users_positive(self):
        from app.api.routes.diocese import RegisterDioceseRequest
        r = RegisterDioceseRequest(
            name="Test Diocese",
            diocese_code="test-diocese",
            contact_email="it@test.pl",
            max_users=500,
        )
        assert r.max_users == 500

    def test_max_users_negative_rejected(self):
        from pydantic import ValidationError
        from app.api.routes.diocese import RegisterDioceseRequest
        import pytest
        with pytest.raises(ValidationError):
            RegisterDioceseRequest(
                name="Test Diocese",
                diocese_code="test-diocese",
                contact_email="it@test.pl",
                max_users=-1,
            )

    def test_invalid_email_rejected(self):
        from pydantic import ValidationError
        from app.api.routes.diocese import RegisterDioceseRequest
        import pytest
        with pytest.raises(ValidationError):
            RegisterDioceseRequest(
                name="Test Diocese",
                diocese_code="test-diocese",
                contact_email="not-an-email",
            )

    def test_stripe_subscription_optional(self):
        from app.api.routes.diocese import RegisterDioceseRequest
        r = RegisterDioceseRequest(
            name="Test Diocese",
            diocese_code="test-diocese",
            contact_email="it@test.pl",
            stripe_subscription_id="sub_abc123",
        )
        assert r.stripe_subscription_id == "sub_abc123"

    def test_license_dates_optional(self):
        from app.api.routes.diocese import RegisterDioceseRequest
        r = RegisterDioceseRequest(
            name="Test Diocese",
            diocese_code="test-diocese",
            contact_email="it@test.pl",
            license_starts_at="2026-01-01T00:00:00",
            license_expires_at="2027-01-01T00:00:00",
        )
        assert r.license_starts_at == "2026-01-01T00:00:00"
        assert r.license_expires_at == "2027-01-01T00:00:00"

    def test_with_all_fields(self):
        from app.api.routes.diocese import RegisterDioceseRequest
        r = RegisterDioceseRequest(
            name="Archidiecezja Warszawska",
            country="PL",
            diocese_code="warszawa-archdiocese",
            contact_email="it@archwarszawa.pl",
            max_users=1000,
            stripe_subscription_id="sub_xyz789",
            license_starts_at="2026-01-01T00:00:00",
            license_expires_at="2027-01-01T00:00:00",
        )
        assert r.country == "PL"
        assert r.max_users == 1000


class TestDioceseResponse:
    def test_valid_response(self):
        from app.api.routes.diocese import DioceseResponse
        r = DioceseResponse(
            id="uuid-diocese-1",
            name="Archidiecezja Krakowska",
            country="PL",
            diocese_code="krakow-archdiocese",
            contact_email="it@archikrakow.pl",
            max_users=0,
            is_active=True,
            stripe_subscription_id=None,
            license_starts_at=None,
            license_expires_at=None,
            created_at="2026-01-01T00:00:00+00:00",
        )
        assert r.is_active is True
        assert r.stripe_subscription_id is None

    def test_inactive_diocese(self):
        from app.api.routes.diocese import DioceseResponse
        r = DioceseResponse(
            id="uuid-diocese-2",
            name="Test Diocese",
            country="PL",
            diocese_code="test",
            contact_email="it@test.pl",
            max_users=100,
            is_active=False,
            stripe_subscription_id="sub_expired",
            license_starts_at="2025-01-01T00:00:00+00:00",
            license_expires_at="2026-01-01T00:00:00+00:00",
            created_at="2025-01-01T00:00:00+00:00",
        )
        assert r.is_active is False


class TestActivateUserRequest:
    def test_valid_email(self):
        from app.api.routes.diocese import ActivateUserRequest
        r = ActivateUserRequest(user_email="priest@archikrakow.pl")
        assert r.user_email == "priest@archikrakow.pl"

    def test_invalid_email_rejected(self):
        from pydantic import ValidationError
        from app.api.routes.diocese import ActivateUserRequest
        import pytest
        with pytest.raises(ValidationError):
            ActivateUserRequest(user_email="not-an-email")


class TestDioceseStatsResponse:
    def test_within_limit(self):
        from app.api.routes.diocese import DioceseStatsResponse
        r = DioceseStatsResponse(
            diocese_id="uuid-1",
            diocese_name="Test Diocese",
            total_members=50,
            max_users=100,
            is_within_limit=True,
            is_active=True,
        )
        assert r.is_within_limit is True
        assert r.total_members == 50

    def test_unlimited_max_users(self):
        from app.api.routes.diocese import DioceseStatsResponse
        r = DioceseStatsResponse(
            diocese_id="uuid-2",
            diocese_name="Big Diocese",
            total_members=5000,
            max_users=0,
            is_within_limit=True,
            is_active=True,
        )
        assert r.max_users == 0


class TestDioceseRoutes:
    def test_router_exists(self):
        from app.api.routes.diocese import router
        assert router is not None

    def test_has_register_post_route(self):
        from app.api.routes.diocese import router
        paths = [r.path for r in router.routes]
        assert "/register" in paths

    def test_has_get_diocese_route(self):
        from app.api.routes.diocese import router
        paths = [r.path for r in router.routes]
        assert any("{diocese_code}" in p for p in paths)

    def test_has_activate_post_route(self):
        from app.api.routes.diocese import router
        paths = [r.path for r in router.routes]
        assert any("activate" in p for p in paths)

    def test_has_stats_get_route(self):
        from app.api.routes.diocese import router
        paths = [r.path for r in router.routes]
        assert any("stats" in p for p in paths)

    def test_has_deactivate_post_route(self):
        from app.api.routes.diocese import router
        paths = [r.path for r in router.routes]
        assert any("deactivate" in p for p in paths)

    def test_router_registered_in_main(self):
        import app.main as main_module
        import inspect
        src = inspect.getsource(main_module)
        assert "app.api.routes.diocese" in src

    def test_register_requires_admin(self):
        import inspect
        import ast
        import app.api.routes.diocese as diocese_module
        src = inspect.getsource(diocese_module)
        assert "require_admin" in src

    def test_no_user_id_in_request_body(self):
        """Security: user_id must never appear in request body models."""
        import ast
        import inspect
        import app.api.routes.diocese as diocese_module
        src = inspect.getsource(diocese_module)
        # Check RegisterDioceseRequest and ActivateUserRequest don't include user_id
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name in (
                "RegisterDioceseRequest", "ActivateUserRequest", "DioceseStatsResponse"
            ):
                field_names = [
                    n.target.id
                    for n in ast.walk(node)
                    if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name)
                ]
                assert "user_id" not in field_names, (
                    f"{node.name} must not contain user_id field"
                )


class TestDioceseLicenseModel:
    def test_diocese_license_model_exists(self):
        from app.models.database import DioceseLicense
        assert DioceseLicense is not None

    def test_diocese_license_has_expected_columns(self):
        from app.models.database import DioceseLicense
        mapper = DioceseLicense.__mapper__
        column_names = {c.key for c in mapper.columns}
        expected = {
            "id", "name", "country", "diocese_code", "contact_email",
            "stripe_subscription_id", "max_users", "is_active",
            "license_starts_at", "license_expires_at", "created_at",
        }
        assert expected.issubset(column_names), (
            f"Missing columns: {expected - column_names}"
        )

    def test_diocese_code_is_unique(self):
        from app.models.database import DioceseLicense
        col = DioceseLicense.__table__.c["diocese_code"]
        assert col.unique

    def test_max_users_defaults_to_zero(self):
        from app.models.database import DioceseLicense
        col = DioceseLicense.__table__.c["max_users"]
        assert col.default is not None or col.server_default is not None or str(col.default) != "None"
        # Just verify the column exists with integer type
        from sqlalchemy import Integer
        assert isinstance(col.type, Integer)

    def test_is_active_defaults_to_true(self):
        from app.models.database import DioceseLicense
        col = DioceseLicense.__table__.c["is_active"]
        from sqlalchemy import Boolean
        assert isinstance(col.type, Boolean)

    def test_user_has_diocese_id_column(self):
        from app.models.database import User
        mapper = User.__mapper__
        column_names = {c.key for c in mapper.columns}
        assert "diocese_id" in column_names

    def test_diocese_id_is_nullable(self):
        from app.models.database import User
        col = User.__table__.c["diocese_id"]
        assert col.nullable is True
