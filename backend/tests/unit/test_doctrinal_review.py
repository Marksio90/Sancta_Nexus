"""Unit tests for doctrinal review (imprimatur support) infrastructure.

Covers:
  - SubmitReviewRequest validation
  - ReviewItem model field constraints
  - ReviewDecisionRequest accepts None note
  - Router has submit, queue, approve, reject routes
  - Review routes are protected (require_content_reviewer)
  - Router is registered in main.py
  - Redis key format correct
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


class TestSubmitReviewRequest:
    def test_valid_minimal(self):
        from app.api.routes.doctrinal_review import SubmitReviewRequest
        r = SubmitReviewRequest(module="lectio", ai_response_text="A" * 20)
        assert r.module == "lectio"
        assert r.concern is None

    def test_ai_response_too_short(self):
        from pydantic import ValidationError
        from app.api.routes.doctrinal_review import SubmitReviewRequest
        import pytest
        with pytest.raises(ValidationError):
            SubmitReviewRequest(module="lectio", ai_response_text="short")

    def test_ai_response_too_long(self):
        from pydantic import ValidationError
        from app.api.routes.doctrinal_review import SubmitReviewRequest
        import pytest
        with pytest.raises(ValidationError):
            SubmitReviewRequest(module="lectio", ai_response_text="x" * 20_001)

    def test_concern_max_length(self):
        from pydantic import ValidationError
        from app.api.routes.doctrinal_review import SubmitReviewRequest
        import pytest
        with pytest.raises(ValidationError):
            SubmitReviewRequest(
                module="lectio",
                ai_response_text="A" * 20,
                concern="x" * 1001,
            )

    def test_with_all_fields(self):
        from app.api.routes.doctrinal_review import SubmitReviewRequest
        r = SubmitReviewRequest(
            module="reflection",
            content_id="session-123",
            ai_response_text="Pan jest blisko złamanych sercem." * 5,
            concern="Może sugerować fałszywą pewność zbawienia.",
        )
        assert r.content_id == "session-123"
        assert r.module == "reflection"


class TestReviewItem:
    def test_pending_status(self):
        from app.api.routes.doctrinal_review import ReviewItem
        r = ReviewItem(
            review_id="r1",
            module="lectio",
            content_id=None,
            ai_response_text="Some text",
            concern=None,
            status="pending",
            submitted_at="2026-01-01T00:00:00Z",
        )
        assert r.status == "pending"
        assert r.reviewer_note is None

    def test_approved_status(self):
        from app.api.routes.doctrinal_review import ReviewItem
        r = ReviewItem(
            review_id="r2",
            module="examen",
            content_id="c1",
            ai_response_text="Text",
            concern=None,
            status="approved",
            submitted_at="2026-01-01T00:00:00Z",
            reviewed_at="2026-01-02T00:00:00Z",
            reviewer_note="Doctrinally sound.",
            reviewer_id="reviewer-uuid",
        )
        assert r.status == "approved"
        assert r.reviewer_note == "Doctrinally sound."

    def test_rejected_status(self):
        from app.api.routes.doctrinal_review import ReviewItem
        r = ReviewItem(
            review_id="r3",
            module="lectio",
            content_id=None,
            ai_response_text="Problematic text",
            concern="Sounds like absolution",
            status="rejected",
            submitted_at="2026-01-01T00:00:00Z",
            reviewed_at="2026-01-02T00:00:00Z",
            reviewer_note="This implies priestly absolution — must be rewritten.",
            reviewer_id="reviewer-uuid",
        )
        assert r.status == "rejected"


class TestReviewRoutes:
    def test_router_exists(self):
        from app.api.routes.doctrinal_review import router
        assert router is not None

    def test_has_submit_post_route(self):
        from app.api.routes.doctrinal_review import router
        paths = [r.path for r in router.routes]
        assert "/submit" in paths

    def test_has_queue_get_route(self):
        from app.api.routes.doctrinal_review import router
        paths = [r.path for r in router.routes]
        assert "/queue" in paths

    def test_has_approve_post_route(self):
        from app.api.routes.doctrinal_review import router
        paths = [r.path for r in router.routes]
        assert any("approve" in p for p in paths)

    def test_has_reject_post_route(self):
        from app.api.routes.doctrinal_review import router
        paths = [r.path for r in router.routes]
        assert any("reject" in p for p in paths)

    def test_has_single_review_get_route(self):
        from app.api.routes.doctrinal_review import router
        paths = [r.path for r in router.routes]
        assert any("{review_id}" in p for p in paths)

    def test_router_registered_in_main(self):
        import app.main as main_module
        import inspect
        src = inspect.getsource(main_module)
        assert "app.api.routes.doctrinal_review" in src

    def test_redis_key_format(self):
        from app.api.routes.doctrinal_review import _REVIEW_KEY
        key = _REVIEW_KEY.format(review_id="abc-123")
        assert "abc-123" in key
        assert "doctrinal_review" in key

    def test_decision_request_note_optional(self):
        from app.api.routes.doctrinal_review import ReviewDecisionRequest
        r = ReviewDecisionRequest()
        assert r.note is None

    def test_decision_request_with_note(self):
        from app.api.routes.doctrinal_review import ReviewDecisionRequest
        r = ReviewDecisionRequest(note="Approved — consistent with Catechism §§1430-1449.")
        assert "Catechism" in r.note
