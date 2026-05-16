"""Unit tests for the /api/v1/feedback endpoint."""

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

from app.api.routes.feedback import FeedbackRequest


class TestFeedbackSchema:
    def test_rating_up_valid(self):
        req = FeedbackRequest(module="lectio", rating="up")
        assert req.rating == "up"

    def test_rating_down_valid(self):
        req = FeedbackRequest(module="lectio", rating="down")
        assert req.rating == "down"

    def test_flag_valid_values(self):
        for flag in ("theologically_incorrect", "repetitive_or_generic", "other"):
            req = FeedbackRequest(module="lectio", flag=flag)
            assert req.flag == flag

    def test_all_fields_optional_except_module(self):
        req = FeedbackRequest(module="reflection")
        assert req.rating is None
        assert req.flag is None
        assert req.content_id is None

    def test_module_required(self):
        import pydantic
        try:
            FeedbackRequest()
            assert False, "Should have raised"
        except (pydantic.ValidationError, TypeError):
            pass


class TestFeedbackRouteRegistration:
    def test_feedback_router_exists(self):
        from app.api.routes.feedback import router
        assert router is not None

    def test_has_post_route(self):
        from app.api.routes.feedback import router
        methods = set()
        for route in router.routes:
            if hasattr(route, "methods"):
                methods.update(route.methods)
        assert "POST" in methods
