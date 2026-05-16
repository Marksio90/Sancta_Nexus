"""Tests for auth security improvements: jti revocation, login_failed audit."""

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

import pytest

from app.models.database import AuditEventType


class TestAuditEventTypeLoginFailed:
    def test_login_failed_exists(self):
        assert hasattr(AuditEventType, "LOGIN_FAILED")

    def test_login_failed_value(self):
        assert AuditEventType.LOGIN_FAILED == "login_failed"

    def test_all_original_events_still_present(self):
        required = {
            "USER_REGISTERED", "USER_ROLE_CHANGED", "USER_DELETED",
            "AI_RESPONSE_GENERATED", "AI_RESPONSE_REWRITTEN", "AI_CRISIS_DETECTED",
            "CONTENT_CREATED", "MODULE_TOGGLED", "ROLE_PERMISSION_DENIED",
            "JOURNAL_ENTRY_DELETED", "ACCOUNT_DELETION_REQUESTED", "LOGIN_FAILED",
        }
        names = {e.name for e in AuditEventType}
        assert required <= names, f"Missing: {required - names}"


class TestRefreshTokenJti:
    def test_create_refresh_token_contains_jti(self):
        from unittest.mock import MagicMock

        mock_jwt = MagicMock()
        mock_jwt.encode.return_value = "mocked_token"
        with patch("app.core.security.jwt", mock_jwt):
            from app.core.security import create_refresh_token

            create_refresh_token({"sub": "user-123"})

        call_kwargs = mock_jwt.encode.call_args
        payload = call_kwargs[0][0]
        assert "jti" in payload, "Refresh token must contain a jti claim"
        assert payload["type"] == "refresh"

    def test_access_token_has_no_jti(self):
        mock_jwt = MagicMock()
        mock_jwt.encode.return_value = "mocked_access"
        with patch("app.core.security.jwt", mock_jwt):
            from app.core.security import create_access_token

            create_access_token({"sub": "user-123"})

        payload = mock_jwt.encode.call_args[0][0]
        assert "jti" not in payload, "Access token should not have jti"
        assert payload["type"] == "access"


class TestTokenRevocation:
    @pytest.mark.asyncio
    async def test_revoke_sets_redis_key(self):
        from datetime import UTC, datetime, timedelta

        from app.core.security import revoke_refresh_token

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        future = datetime.now(UTC) + timedelta(days=7)
        await revoke_refresh_token(mock_redis, "test-jti-123", future)

        mock_redis.setex.assert_awaited_once()
        args = mock_redis.setex.call_args[0]
        assert "test-jti-123" in args[0]
        assert args[1] > 0  # TTL > 0

    @pytest.mark.asyncio
    async def test_revoke_skips_expired_tokens(self):
        from datetime import UTC, datetime, timedelta

        from app.core.security import revoke_refresh_token

        mock_redis = AsyncMock()
        mock_redis.setex = AsyncMock()

        past = datetime.now(UTC) - timedelta(seconds=1)
        await revoke_refresh_token(mock_redis, "expired-jti", past)

        mock_redis.setex.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_is_revoked_true(self):
        from app.core.security import is_refresh_token_revoked

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=1)

        result = await is_refresh_token_revoked(mock_redis, "some-jti")
        assert result is True

    @pytest.mark.asyncio
    async def test_is_revoked_false(self):
        from app.core.security import is_refresh_token_revoked

        mock_redis = AsyncMock()
        mock_redis.exists = AsyncMock(return_value=0)

        result = await is_refresh_token_revoked(mock_redis, "unused-jti")
        assert result is False
