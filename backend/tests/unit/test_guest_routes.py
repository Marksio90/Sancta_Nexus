"""Unit tests for guest mode routes.

Covers:
  - IP hash is deterministic and 16 chars
  - Rate-limit key format
  - GuestRunRequest validation
  - GuestEmailCaptureRequest requires valid email
  - GuestSessionResponse always includes cta
  - Router exists and has correct endpoints
  - Guest routes registered in main.py
"""
import sys
from unittest.mock import MagicMock

import pytest

# Stub heavy deps
for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


class TestIpHash:
    def test_hash_is_16_chars(self):
        """_ip_hash produces a 16-character string."""
        from app.api.routes.guest import _ip_hash
        from unittest.mock import MagicMock

        req = MagicMock()
        req.client.host = "192.168.1.1"
        result = _ip_hash(req)
        assert len(result) == 16

    def test_hash_is_deterministic(self):
        from app.api.routes.guest import _ip_hash
        from unittest.mock import MagicMock

        req = MagicMock()
        req.client.host = "10.0.0.1"
        assert _ip_hash(req) == _ip_hash(req)

    def test_different_ips_different_hashes(self):
        from app.api.routes.guest import _ip_hash
        from unittest.mock import MagicMock

        req1 = MagicMock()
        req1.client.host = "1.1.1.1"
        req2 = MagicMock()
        req2.client.host = "2.2.2.2"
        assert _ip_hash(req1) != _ip_hash(req2)

    def test_none_client_handled(self):
        from app.api.routes.guest import _ip_hash
        from unittest.mock import MagicMock

        req = MagicMock()
        req.client = None
        result = _ip_hash(req)
        assert isinstance(result, str)
        assert len(result) == 16


class TestGuestSchemas:
    def test_guest_run_request_min_length(self):
        from pydantic import ValidationError
        from app.api.routes.guest import GuestRunRequest

        with pytest.raises(ValidationError):
            GuestRunRequest(emotion_text="")

    def test_guest_run_request_max_length(self):
        from pydantic import ValidationError
        from app.api.routes.guest import GuestRunRequest

        with pytest.raises(ValidationError):
            GuestRunRequest(emotion_text="x" * 2001)

    def test_guest_run_request_valid(self):
        from app.api.routes.guest import GuestRunRequest

        r = GuestRunRequest(emotion_text="czuję spokój")
        assert r.emotion_text == "czuję spokój"
        assert r.tradition == ""

    def test_guest_email_capture_requires_valid_email(self):
        from pydantic import ValidationError
        from app.api.routes.guest import GuestEmailCaptureRequest

        with pytest.raises(ValidationError):
            GuestEmailCaptureRequest(guest_session_id="abc", email="not-an-email")

    def test_guest_email_capture_valid(self):
        from app.api.routes.guest import GuestEmailCaptureRequest

        r = GuestEmailCaptureRequest(
            guest_session_id="123",
            email="test@example.com",
        )
        assert r.email == "test@example.com"

    def test_guest_session_response_has_cta(self):
        from app.api.routes.guest import GuestSessionResponse

        r = GuestSessionResponse(guest_session_id="x")
        assert len(r.cta) > 10

    def test_guest_email_capture_response_registered_default_false(self):
        from app.api.routes.guest import GuestEmailCaptureResponse

        r = GuestEmailCaptureResponse(message="ok")
        assert r.registered is False


class TestGuestRouteRegistration:
    def test_guest_router_exists(self):
        from app.api.routes.guest import router
        assert router is not None

    def test_has_lectio_post_route(self):
        from app.api.routes.guest import router
        paths = [r.path for r in router.routes]
        assert "/lectio" in paths

    def test_has_session_get_route(self):
        from app.api.routes.guest import router
        paths = [r.path for r in router.routes]
        assert any("{guest_session_id}" in p for p in paths)

    def test_has_capture_email_post_route(self):
        from app.api.routes.guest import router
        paths = [r.path for r in router.routes]
        assert "/capture-email" in paths

    def test_guest_router_in_main_routers(self):
        import app.main as main_module
        import inspect
        src = inspect.getsource(main_module)
        assert "app.api.routes.guest" in src

    def test_rate_limit_key_format(self):
        from app.api.routes.guest import _GUEST_RATE_KEY
        key = _GUEST_RATE_KEY.format(ip_hash="abcdef1234567890")
        assert "abcdef1234567890" in key
        assert "guest_rate" in key
