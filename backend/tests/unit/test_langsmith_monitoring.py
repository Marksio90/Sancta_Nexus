"""Unit tests for LangSmith observability integration.

Covers:
  - Settings include LangSmith config keys
  - Defaults are safe (tracing off, empty API key)
  - JWT user_id extraction from Bearer token (no verification)
  - LangSmithContextMiddleware is registered in main.py
  - /health/llm endpoint is defined
  - LangSmith env var initialization in lifespan
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


class TestLangSmithSettings:
    def test_langsmith_tracing_default_false(self):
        from app.core.config import settings
        assert settings.LANGCHAIN_TRACING_V2 is False

    def test_langsmith_api_key_default_empty(self):
        from app.core.config import settings
        assert settings.LANGCHAIN_API_KEY == ""

    def test_langsmith_project_default(self):
        from app.core.config import settings
        assert settings.LANGCHAIN_PROJECT == "sancta-nexus"

    def test_langsmith_endpoint_default(self):
        from app.core.config import settings
        assert "smith.langchain.com" in settings.LANGCHAIN_ENDPOINT

    def test_langsmith_settings_present(self):
        from app.core.config import Settings
        fields = Settings.model_fields
        assert "LANGCHAIN_TRACING_V2" in fields
        assert "LANGCHAIN_API_KEY" in fields
        assert "LANGCHAIN_PROJECT" in fields
        assert "LANGCHAIN_ENDPOINT" in fields


class TestJwtUserIdExtraction:
    def _make_token(self, payload: dict) -> str:
        """Create a fake (unsigned) JWT with given payload."""
        import base64
        import json
        header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256"}).encode()).rstrip(b"=")
        body = base64.urlsafe_b64encode(json.dumps(payload).encode()).rstrip(b"=")
        return f"{header.decode()}.{body.decode()}.fakesig"

    def test_extracts_sub_from_valid_token(self):
        from app.middleware.langsmith_context import _extract_user_id_from_bearer
        token = self._make_token({"sub": "user-abc-123", "type": "access"})
        result = _extract_user_id_from_bearer(f"Bearer {token}")
        assert result == "user-abc-123"

    def test_returns_none_for_no_header(self):
        from app.middleware.langsmith_context import _extract_user_id_from_bearer
        assert _extract_user_id_from_bearer(None) is None

    def test_returns_none_for_non_bearer(self):
        from app.middleware.langsmith_context import _extract_user_id_from_bearer
        assert _extract_user_id_from_bearer("Basic dXNlcjpwYXNz") is None

    def test_returns_none_for_malformed_token(self):
        from app.middleware.langsmith_context import _extract_user_id_from_bearer
        assert _extract_user_id_from_bearer("Bearer not.a.valid.jwt.token") is None

    def test_returns_none_when_no_sub(self):
        from app.middleware.langsmith_context import _extract_user_id_from_bearer
        token = self._make_token({"exp": 9999999999})  # no sub
        result = _extract_user_id_from_bearer(f"Bearer {token}")
        assert result is None


class TestLangSmithMiddlewareRegistration:
    def test_middleware_importable(self):
        from app.middleware.langsmith_context import LangSmithContextMiddleware
        assert LangSmithContextMiddleware is not None

    def test_middleware_registered_in_main(self):
        import app.main as main_module
        import inspect
        src = inspect.getsource(main_module)
        assert "LangSmithContextMiddleware" in src

    def test_health_llm_endpoint_defined(self):
        import app.main as main_module
        import inspect
        src = inspect.getsource(main_module)
        assert "/health/llm" in src

    def test_langsmith_env_init_in_lifespan(self):
        import app.main as main_module
        import inspect
        src = inspect.getsource(main_module)
        assert "LANGCHAIN_TRACING_V2" in src
        assert "LANGCHAIN_API_KEY" in src
        assert "LANGCHAIN_PROJECT" in src
