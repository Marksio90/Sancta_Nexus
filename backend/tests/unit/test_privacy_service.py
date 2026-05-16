"""Unit tests for the privacy service."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.database import SubscriptionTier, User, UserPrivacySettings, UserRole
from app.services.privacy.privacy_service import PrivacyService


def _make_user(user_id: str = "test-user-123") -> User:
    user = MagicMock(spec=User)
    user.id = user_id
    user.email = "test@example.com"
    user.name = "Jan Kowalski"
    user.role = UserRole.USER
    user.subscription_tier = SubscriptionTier.FREE
    user.is_active = True
    user.deleted_at = None
    user.created_at = datetime(2026, 1, 1, tzinfo=UTC)
    user.updated_at = datetime(2026, 1, 1, tzinfo=UTC)
    return user


def _make_privacy_settings(user_id: str) -> UserPrivacySettings:
    ps = MagicMock(spec=UserPrivacySettings)
    ps.user_id = user_id
    ps.journal_is_private = True
    ps.ai_can_read_journal = True
    ps.ai_history_enabled = True
    ps.preferred_language = "pl"
    ps.spiritual_tradition = "ignatian"
    ps.deletion_requested_at = None
    return ps


@pytest.fixture
def svc():
    return PrivacyService()


class TestGetOrCreatePrivacySettings:
    @pytest.mark.asyncio
    async def test_returns_existing_settings(self, svc):
        user = _make_user()
        existing = _make_privacy_settings(user.id)

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing
        db.execute = AsyncMock(return_value=mock_result)

        result = await svc.get_or_create_privacy_settings(db, user)
        assert result is existing
        db.add.assert_not_called()

    @pytest.mark.asyncio
    async def test_creates_default_settings_when_none(self, svc):
        user = _make_user()

        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=mock_result)
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        await svc.get_or_create_privacy_settings(db, user)
        db.add.assert_called_once()
        db.flush.assert_called_once()


class TestRequestDeletion:
    @pytest.mark.asyncio
    async def test_sets_inactive_and_deleted_at(self, svc):
        user = _make_user()
        db = AsyncMock()

        # Mock get_or_create_privacy_settings
        ps = _make_privacy_settings(user.id)
        with patch.object(svc, "get_or_create_privacy_settings", return_value=ps):
            with patch("app.services.privacy.privacy_service.audit") as mock_audit:
                mock_audit.log = AsyncMock()
                await svc.request_deletion(db, user, actor_id=user.id)

        assert user.is_active is False
        assert user.deleted_at is not None
        assert ps.deletion_requested_at is not None

    @pytest.mark.asyncio
    async def test_audit_logged_on_deletion(self, svc):
        user = _make_user()
        db = AsyncMock()
        ps = _make_privacy_settings(user.id)

        with patch.object(svc, "get_or_create_privacy_settings", return_value=ps):
            with patch("app.services.privacy.privacy_service.audit") as mock_audit:
                mock_audit.log = AsyncMock()
                await svc.request_deletion(db, user, actor_id=user.id)
                mock_audit.log.assert_called_once()
                call_kwargs = mock_audit.log.call_args
                assert "account_deletion_requested" in str(call_kwargs)


class TestExportUserData:
    @pytest.mark.asyncio
    async def test_export_contains_required_sections(self, svc):
        user = _make_user()
        db = AsyncMock()

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        empty_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=empty_result)
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        with patch("app.services.privacy.privacy_service.audit") as mock_audit:
            mock_audit.log = AsyncMock()
            export = await svc.export_user_data(db, user)

        assert "account" in export
        assert "privacy_settings" in export
        assert "sessions" in export
        assert "prayers" in export
        assert "scripture_encounters" in export
        assert "spiritual_insights" in export
        assert "ai_interactions_metadata" in export
        assert "export_generated_at" in export

    @pytest.mark.asyncio
    async def test_account_data_correct(self, svc):
        user = _make_user("abc-123")
        db = AsyncMock()

        empty_result = MagicMock()
        empty_result.scalars.return_value.all.return_value = []
        empty_result.scalar_one_or_none.return_value = None
        db.execute = AsyncMock(return_value=empty_result)
        db.add = MagicMock()
        db.flush = AsyncMock()
        db.refresh = AsyncMock()

        with patch("app.services.privacy.privacy_service.audit") as mock_audit:
            mock_audit.log = AsyncMock()
            export = await svc.export_user_data(db, user)

        assert export["account"]["id"] == "abc-123"
        assert export["account"]["email"] == "test@example.com"
        assert export["account"]["role"] == "user"
