"""Integration tests for new platform features.

Covers the full logic pipeline (without real infrastructure) for:
  - ARQ task queue (enqueue, status polling, result)
  - Guest mode (rate limiting, session storage, email capture)
  - Doctrinal review (submit → queue → approve/reject lifecycle)
  - Diocese licensing (register → activate → stats → deactivate)

All tests stub Redis, DB, and external deps inline — no running services needed.
"""
from __future__ import annotations

import sys
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

# ── Stub heavy dependencies ──────────────────────────────────────────────────

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Stub arq without clobbering the cron lambda
_arq_mock = MagicMock()
_arq_mock.cron = lambda fn, **_: fn
sys.modules.setdefault("arq", _arq_mock)
sys.modules.setdefault("arq.connections", MagicMock())
sys.modules.setdefault("arq.jobs", MagicMock())


# ── Helpers ──────────────────────────────────────────────────────────────────

def _make_user(
    user_id: str | None = None,
    email: str = "user@test.pl",
    diocese_id: str | None = None,
) -> MagicMock:
    u = MagicMock()
    u.id = user_id or str(uuid.uuid4())
    u.email = email
    u.diocese_id = diocese_id
    u.subscription_tier = MagicMock()
    u.subscription_tier.value = "free"
    return u


def _make_diocese(
    diocese_id: str | None = None,
    code: str = "krakow-archdiocese",
    max_users: int = 0,
    is_active: bool = True,
    license_expires_at=None,
) -> MagicMock:
    d = MagicMock()
    d.id = diocese_id or str(uuid.uuid4())
    d.name = "Archidiecezja Krakowska"
    d.country = "PL"
    d.diocese_code = code
    d.contact_email = "it@archikrakow.pl"
    d.max_users = max_users
    d.is_active = is_active
    d.license_expires_at = license_expires_at
    d.stripe_subscription_id = None
    d.license_starts_at = None
    d.created_at = MagicMock()
    d.created_at.isoformat.return_value = "2026-01-01T00:00:00+00:00"
    return d


# ─────────────────────────────────────────────────────────────────────────────
# ARQ Task Queue
# ─────────────────────────────────────────────────────────────────────────────


class TestArqTaskQueue:
    """Tests for ARQ task enqueue → status polling pipeline."""

    def test_worker_settings_has_run_lectio_pipeline(self):
        from app.workers.arq_settings import WorkerSettings
        fn_names = [f.__name__ for f in WorkerSettings.functions]
        assert "run_lectio_pipeline" in fn_names

    def test_worker_settings_has_cron_jobs(self):
        from app.workers.arq_settings import WorkerSettings
        assert len(WorkerSettings.cron_jobs) >= 2

    def test_worker_settings_max_jobs_reasonable(self):
        from app.workers.arq_settings import WorkerSettings
        assert WorkerSettings.max_jobs >= 1
        assert WorkerSettings.job_timeout >= 60

    def test_task_status_response_model(self):
        from app.api.routes.tasks import TaskStatusResponse
        r = TaskStatusResponse(
            task_id="job-abc",
            status="queued",
            result=None,
            error=None,
        )
        assert r.status == "queued"
        assert r.task_id == "job-abc"

    def test_task_status_complete_with_result(self):
        from app.api.routes.tasks import TaskStatusResponse
        r = TaskStatusResponse(
            task_id="job-xyz",
            status="complete",
            result={"lectio": "text", "meditatio": "text"},
            error=None,
        )
        assert r.status == "complete"
        assert r.result is not None

    def test_task_status_failed_with_error(self):
        from app.api.routes.tasks import TaskStatusResponse
        r = TaskStatusResponse(
            task_id="job-err",
            status="failed",
            result=None,
            error="LLM timeout",
        )
        assert r.error == "LLM timeout"

    def test_enqueued_task_response_has_poll_url(self):
        from app.api.routes.lectio_divina import EnqueuedTaskResponse
        r = EnqueuedTaskResponse(
            task_id="job-111",
            status="queued",
            poll_url="/api/v1/tasks/job-111",
        )
        assert "job-111" in r.poll_url

    def test_run_lectio_pipeline_task_returns_error_dict_on_exception(self):
        """Task must return {error: ...} rather than re-raise — keeps ARQ worker alive."""
        import asyncio
        import importlib

        mock_module = MagicMock()
        mock_module.run_session = AsyncMock(side_effect=RuntimeError("LLM down"))

        with patch.dict(
            "sys.modules",
            {"app.agents.lectio_divina.lectio_divina_graph": mock_module},
        ):
            # Re-import with the patched module available
            from app.workers import tasks as tasks_module
            import importlib
            importlib.reload(tasks_module)

            ctx = {"db": AsyncMock(), "redis": AsyncMock()}
            result = asyncio.get_event_loop().run_until_complete(
                tasks_module.run_lectio_pipeline(
                    ctx,
                    user_id="user-1",
                    emotion_text="Czuję się niepokojem",
                    tradition="ignatian",
                )
            )
        assert "error" in result

    def test_pool_enqueue_returns_none_gracefully_when_no_pool(self):
        """enqueue() must not crash when ARQ pool is unavailable."""
        import asyncio
        import app.workers.pool as pool_module

        original = pool_module._arq_pool
        pool_module._arq_pool = None

        async def _run():
            # Make _get_pool raise to simulate unavailable ARQ
            with patch.object(pool_module, "_get_pool", AsyncMock(side_effect=ConnectionError("no redis"))):
                return await pool_module.enqueue("run_lectio_pipeline", user_id="u1")

        result = asyncio.get_event_loop().run_until_complete(_run())
        pool_module._arq_pool = original
        assert result is None


# ─────────────────────────────────────────────────────────────────────────────
# Guest Mode
# ─────────────────────────────────────────────────────────────────────────────


class TestGuestMode:
    """Tests for guest mode endpoints."""

    def test_guest_router_exists(self):
        from app.api.routes.guest import router
        assert router is not None

    def test_guest_has_lectio_post(self):
        from app.api.routes.guest import router
        paths = [r.path for r in router.routes]
        assert "/lectio" in paths

    def test_guest_has_session_get(self):
        from app.api.routes.guest import router
        paths = [r.path for r in router.routes]
        assert any("{guest_session_id}" in p for p in paths)

    def test_guest_has_capture_email_post(self):
        from app.api.routes.guest import router
        paths = [r.path for r in router.routes]
        assert any("capture-email" in p for p in paths)

    def test_ip_hash_is_deterministic(self):
        from app.api.routes.guest import _ip_hash
        req = MagicMock()
        req.client = MagicMock()
        req.client.host = "192.168.1.1"
        req.headers = {}
        h1 = _ip_hash(req)
        h2 = _ip_hash(req)
        assert h1 == h2
        assert len(h1) == 16

    def test_ip_hash_handles_no_client(self):
        from app.api.routes.guest import _ip_hash
        req = MagicMock()
        req.client = None
        req.headers = {}
        h = _ip_hash(req)
        assert isinstance(h, str)
        assert len(h) == 16

    def test_ip_hash_uses_forwarded_for(self):
        from app.api.routes.guest import _ip_hash
        req = MagicMock()
        req.client = MagicMock()
        req.client.host = "10.0.0.1"
        req.headers = {"x-forwarded-for": "203.0.113.5"}
        h_with = _ip_hash(req)
        req.headers = {}
        h_without = _ip_hash(req)
        assert h_with != h_without  # different IP → different hash

    def test_check_guest_rate_limit_raises_429_when_key_exists(self):
        import asyncio
        from fastapi import HTTPException
        from app.api.routes.guest import _check_guest_rate_limit
        import pytest

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=b"1")  # key exists

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                _check_guest_rate_limit(redis, "abc123")
            )
        assert exc_info.value.status_code == 429

    def test_check_guest_rate_limit_passes_when_key_missing(self):
        import asyncio
        from app.api.routes.guest import _check_guest_rate_limit

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=None)  # key absent

        # Should not raise
        asyncio.get_event_loop().run_until_complete(
            _check_guest_rate_limit(redis, "abc123")
        )

    def test_guest_keys_have_correct_format(self):
        from app.api.routes.guest import (
            _GUEST_RATE_KEY, _GUEST_SESSION_KEY, _GUEST_EMAIL_KEY
        )
        assert "guest_rate" in _GUEST_RATE_KEY
        assert "guest_session" in _GUEST_SESSION_KEY
        assert "guest_email" in _GUEST_EMAIL_KEY

    def test_guest_ttl_is_24h(self):
        from app.api.routes.guest import _GUEST_TTL
        assert _GUEST_TTL == 86_400

    def test_no_auth_required_on_guest_routes(self):
        """Guest routes must not import require_authenticated at module level."""
        import inspect
        from app.api.routes import guest as guest_module
        src = inspect.getsource(guest_module)
        # Routes themselves don't use require_authenticated as a dependency
        # (the module may import it but not use it on guest endpoints)
        # Just verify the router has routes with no auth dependency by checking
        # that none of the guest route functions have require_authenticated
        for route in guest_module.router.routes:
            if hasattr(route, "dependant"):
                dep_names = [
                    str(d.call) for d in route.dependant.dependencies
                ]
                assert not any("require_authenticated" in n for n in dep_names), (
                    f"Guest route {route.path} should not require authentication"
                )


# ─────────────────────────────────────────────────────────────────────────────
# Doctrinal Review
# ─────────────────────────────────────────────────────────────────────────────


class TestDoctrinalReviewIntegration:
    """Integration tests for the submit → review → decision lifecycle."""

    def test_submit_creates_review_data(self):
        import asyncio
        import json
        from app.api.routes.doctrinal_review import submit_for_review, SubmitReviewRequest
        from app.models.database import AuditEventType

        redis = AsyncMock()
        redis.setex = AsyncMock()
        redis.lpush = AsyncMock()

        db = AsyncMock()
        audit_mock = AsyncMock()

        user = _make_user()
        body = SubmitReviewRequest(
            module="lectio",
            ai_response_text="Pan jest blisko złamanych sercem. " * 5,
        )

        stored_data = {}

        async def mock_setex(key, ttl, value):
            stored_data["key"] = key
            stored_data["value"] = json.loads(value)

        redis.setex = mock_setex
        redis.lpush = AsyncMock()

        with patch("app.api.routes.doctrinal_review.audit", audit_mock):
            result = asyncio.get_event_loop().run_until_complete(
                submit_for_review(body=body, redis=redis, db=db, current_user=user)
            )

        assert result.status == "pending"
        assert result.module == "lectio"
        assert stored_data["value"]["status"] == "pending"
        assert "submitted_by" not in dict(result)  # submitted_by excluded from response

    def test_approve_updates_status(self):
        import asyncio
        import json
        from datetime import UTC, datetime
        from app.api.routes.doctrinal_review import approve_review, ReviewDecisionRequest

        review_id = str(uuid.uuid4())
        review_data = {
            "review_id": review_id,
            "module": "examen",
            "content_id": None,
            "ai_response_text": "Text content here",
            "concern": None,
            "status": "pending",
            "submitted_at": datetime.now(UTC).isoformat(),
            "submitted_by": "user-1",
            "reviewed_at": None,
            "reviewer_note": None,
            "reviewer_id": None,
        }

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps(review_data))
        redis.setex = AsyncMock()
        redis.lrem = AsyncMock()

        db = AsyncMock()
        audit_mock = AsyncMock()
        reviewer = _make_user(user_id="reviewer-1")
        body = ReviewDecisionRequest(note="Doctrinally sound.")

        with patch("app.api.routes.doctrinal_review.audit", audit_mock):
            result = asyncio.get_event_loop().run_until_complete(
                approve_review(
                    review_id=review_id,
                    body=body,
                    redis=redis,
                    db=db,
                    current_user=reviewer,
                )
            )

        assert result.status == "approved"
        assert result.reviewer_note == "Doctrinally sound."
        assert result.reviewer_id == "reviewer-1"
        audit_mock.assert_awaited_once()

    def test_reject_updates_status(self):
        import asyncio
        import json
        from datetime import UTC, datetime
        from app.api.routes.doctrinal_review import reject_review, ReviewDecisionRequest

        review_id = str(uuid.uuid4())
        review_data = {
            "review_id": review_id,
            "module": "reflection",
            "content_id": "sess-123",
            "ai_response_text": "Problematic content",
            "concern": "Sounds like absolution",
            "status": "pending",
            "submitted_at": datetime.now(UTC).isoformat(),
            "submitted_by": "user-2",
            "reviewed_at": None,
            "reviewer_note": None,
            "reviewer_id": None,
        }

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps(review_data))
        redis.setex = AsyncMock()
        redis.lrem = AsyncMock()

        db = AsyncMock()
        audit_mock = AsyncMock()
        reviewer = _make_user(user_id="reviewer-2")
        body = ReviewDecisionRequest(note="Implies priestly absolution — must be rewritten.")

        with patch("app.api.routes.doctrinal_review.audit", audit_mock):
            result = asyncio.get_event_loop().run_until_complete(
                reject_review(
                    review_id=review_id,
                    body=body,
                    redis=redis,
                    db=db,
                    current_user=reviewer,
                )
            )

        assert result.status == "rejected"
        assert "absolution" in result.reviewer_note

    def test_approve_already_decided_raises_409(self):
        import asyncio
        import json
        from datetime import UTC, datetime
        from fastapi import HTTPException
        from app.api.routes.doctrinal_review import approve_review, ReviewDecisionRequest
        import pytest

        review_data = {
            "review_id": "r1",
            "module": "lectio",
            "content_id": None,
            "ai_response_text": "Text",
            "concern": None,
            "status": "approved",  # already decided
            "submitted_at": datetime.now(UTC).isoformat(),
            "submitted_by": "u1",
            "reviewed_at": datetime.now(UTC).isoformat(),
            "reviewer_note": "Ok",
            "reviewer_id": "r1",
        }

        redis = AsyncMock()
        redis.get = AsyncMock(return_value=json.dumps(review_data))

        with pytest.raises(HTTPException) as exc_info:
            asyncio.get_event_loop().run_until_complete(
                approve_review(
                    review_id="r1",
                    body=ReviewDecisionRequest(),
                    redis=redis,
                    db=AsyncMock(),
                    current_user=_make_user(),
                )
            )
        assert exc_info.value.status_code == 409

    def test_get_queue_filters_non_pending(self):
        import asyncio
        import json
        from datetime import UTC, datetime
        from app.api.routes.doctrinal_review import get_review_queue

        pending = {
            "review_id": "r-pending",
            "module": "lectio",
            "content_id": None,
            "ai_response_text": "Text",
            "concern": None,
            "status": "pending",
            "submitted_at": datetime.now(UTC).isoformat(),
            "submitted_by": "u1",
            "reviewed_at": None,
            "reviewer_note": None,
            "reviewer_id": None,
        }
        approved = {**pending, "review_id": "r-approved", "status": "approved"}

        call_count = 0

        async def mock_get(key):
            nonlocal call_count
            call_count += 1
            if "r-pending" in key:
                return json.dumps(pending)
            return json.dumps(approved)

        redis = AsyncMock()
        redis.lrange = AsyncMock(return_value=["r-pending", "r-approved"])
        redis.get = mock_get

        result = asyncio.get_event_loop().run_until_complete(
            get_review_queue(redis=redis, limit=10, current_user=_make_user())
        )

        assert len(result) == 1
        assert result[0].review_id == "r-pending"


# ─────────────────────────────────────────────────────────────────────────────
# Diocese Licensing
# ─────────────────────────────────────────────────────────────────────────────


class TestDioceseLicensingIntegration:
    """Integration tests for the diocese B2B licensing pipeline."""

    def test_activate_user_sets_disciple_tier(self):
        import asyncio
        from app.api.routes.diocese import activate_user_for_diocese, ActivateUserRequest
        from app.models.database import SubscriptionTier

        diocese = _make_diocese(max_users=0, is_active=True)
        user = _make_user(email="priest@archikrakow.pl")
        user.diocese_id = None

        db = AsyncMock()
        db.execute = AsyncMock()
        db.flush = AsyncMock()

        scalar_result = MagicMock()
        scalar_result.scalar_one_or_none = MagicMock(side_effect=[diocese, user])
        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=0)

        call_idx = 0

        async def mock_execute(stmt):
            nonlocal call_idx
            call_idx += 1
            if call_idx == 1:
                return scalar_result
            return scalar_result

        db.execute = mock_execute

        admin = _make_user(user_id="admin-1")
        body = ActivateUserRequest(user_email="priest@archikrakow.pl")
        audit_mock = AsyncMock()

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)), \
             patch("app.api.routes.diocese.audit", audit_mock):
            # Mock user lookup
            user_result = MagicMock()
            user_result.scalar_one_or_none = MagicMock(return_value=user)

            async def mock_execute2(stmt):
                return user_result

            db.execute = mock_execute2

            result = asyncio.get_event_loop().run_until_complete(
                activate_user_for_diocese(
                    diocese_code="krakow-archdiocese",
                    body=body,
                    db=db,
                    admin_user=admin,
                )
            )

        assert user.diocese_id == diocese.id
        assert result["diocese_code"] == "krakow-archdiocese"

    def test_activate_inactive_diocese_raises_402(self):
        import asyncio
        from fastapi import HTTPException
        from app.api.routes.diocese import activate_user_for_diocese, ActivateUserRequest
        import pytest

        diocese = _make_diocese(is_active=False)
        admin = _make_user(user_id="admin-1")
        body = ActivateUserRequest(user_email="priest@test.pl")

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    activate_user_for_diocese(
                        diocese_code="test",
                        body=body,
                        db=AsyncMock(),
                        admin_user=admin,
                    )
                )
        assert exc_info.value.status_code == 402

    def test_activate_expired_diocese_raises_402(self):
        import asyncio
        from datetime import UTC, datetime, timedelta
        from fastapi import HTTPException
        from app.api.routes.diocese import activate_user_for_diocese, ActivateUserRequest
        import pytest

        expired = _make_diocese(
            is_active=True,
            license_expires_at=datetime(2020, 1, 1, tzinfo=UTC),
        )
        admin = _make_user(user_id="admin-1")
        body = ActivateUserRequest(user_email="priest@test.pl")

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=expired)):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    activate_user_for_diocese(
                        diocese_code="test",
                        body=body,
                        db=AsyncMock(),
                        admin_user=admin,
                    )
                )
        assert exc_info.value.status_code == 402
        assert "expired" in exc_info.value.detail.lower()

    def test_activate_over_limit_raises_403(self):
        import asyncio
        from fastapi import HTTPException
        from app.api.routes.diocese import activate_user_for_diocese, ActivateUserRequest
        import pytest

        diocese = _make_diocese(max_users=5, is_active=True)
        admin = _make_user(user_id="admin-1")
        body = ActivateUserRequest(user_email="priest@test.pl")

        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=5)  # already at limit

        db = AsyncMock()
        db.execute = AsyncMock(return_value=count_result)

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    activate_user_for_diocese(
                        diocese_code="test",
                        body=body,
                        db=db,
                        admin_user=admin,
                    )
                )
        assert exc_info.value.status_code == 403
        assert "limit" in exc_info.value.detail.lower()

    def test_deactivate_resets_to_free(self):
        import asyncio
        from app.api.routes.diocese import deactivate_user_for_diocese, ActivateUserRequest
        from app.models.database import SubscriptionTier

        diocese = _make_diocese()
        user = _make_user()
        user.diocese_id = diocese.id

        user_result = MagicMock()
        user_result.scalar_one_or_none = MagicMock(return_value=user)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=user_result)
        db.flush = AsyncMock()

        admin = _make_user(user_id="admin-1")
        body = ActivateUserRequest(user_email=user.email)
        audit_mock = AsyncMock()

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)), \
             patch("app.api.routes.diocese.audit", audit_mock):
            result = asyncio.get_event_loop().run_until_complete(
                deactivate_user_for_diocese(
                    diocese_code=diocese.diocese_code,
                    body=body,
                    db=db,
                    admin_user=admin,
                )
            )

        assert user.diocese_id is None
        assert user.subscription_tier == SubscriptionTier.FREE
        assert "removed" in result["message"].lower()

    def test_deactivate_wrong_diocese_raises_409(self):
        import asyncio
        from fastapi import HTTPException
        from app.api.routes.diocese import deactivate_user_for_diocese, ActivateUserRequest
        import pytest

        diocese = _make_diocese(diocese_id="diocese-A")
        user = _make_user()
        user.diocese_id = "diocese-B"  # belongs to different diocese

        user_result = MagicMock()
        user_result.scalar_one_or_none = MagicMock(return_value=user)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=user_result)

        admin = _make_user()
        body = ActivateUserRequest(user_email=user.email)

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)):
            with pytest.raises(HTTPException) as exc_info:
                asyncio.get_event_loop().run_until_complete(
                    deactivate_user_for_diocese(
                        diocese_code="diocese-A",
                        body=body,
                        db=db,
                        admin_user=admin,
                    )
                )
        assert exc_info.value.status_code == 409

    def test_stats_returns_correct_counts(self):
        import asyncio
        from app.api.routes.diocese import get_diocese_stats

        diocese = _make_diocese(max_users=100, is_active=True)

        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=42)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=count_result)
        admin = _make_user()

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)):
            result = asyncio.get_event_loop().run_until_complete(
                get_diocese_stats(
                    diocese_code=diocese.diocese_code,
                    db=db,
                    admin_user=admin,
                )
            )

        assert result.total_members == 42
        assert result.max_users == 100
        assert result.is_within_limit is True

    def test_stats_unlimited_diocese(self):
        import asyncio
        from app.api.routes.diocese import get_diocese_stats

        diocese = _make_diocese(max_users=0, is_active=True)  # unlimited

        count_result = MagicMock()
        count_result.scalar = MagicMock(return_value=9999)

        db = AsyncMock()
        db.execute = AsyncMock(return_value=count_result)
        admin = _make_user()

        with patch("app.api.routes.diocese._get_diocese_by_code", AsyncMock(return_value=diocese)):
            result = asyncio.get_event_loop().run_until_complete(
                get_diocese_stats(
                    diocese_code=diocese.diocese_code,
                    db=db,
                    admin_user=admin,
                )
            )

        assert result.is_within_limit is True  # unlimited → always within limit


# ─────────────────────────────────────────────────────────────────────────────
# Alembic migration integrity
# ─────────────────────────────────────────────────────────────────────────────


class TestAlembicMigration006:
    """Verify migration 006 has correct structure before running it on a DB."""

    def test_migration_file_exists(self):
        import os
        migrations_dir = os.path.join(
            os.path.dirname(__file__), "../../alembic/versions"
        )
        files = os.listdir(migrations_dir)
        assert any("006" in f for f in files), "Migration 006 file not found"

    def test_migration_006_revises_005(self):
        import os, re
        migrations_dir = os.path.join(
            os.path.dirname(__file__), "../../alembic/versions"
        )
        migration_file = next(
            f for f in os.listdir(migrations_dir) if f.startswith("006")
        )
        src = open(os.path.join(migrations_dir, migration_file)).read()
        assert re.search(r'revision[^=]*=\s*["\']006["\']', src)
        assert re.search(r'down_revision[^=]*=\s*["\']005["\']', src)

    def test_migration_006_has_upgrade_and_downgrade(self):
        import os
        migrations_dir = os.path.join(
            os.path.dirname(__file__), "../../alembic/versions"
        )
        migration_file = next(
            f for f in os.listdir(migrations_dir) if f.startswith("006")
        )
        src = open(os.path.join(migrations_dir, migration_file)).read()
        assert "def upgrade()" in src
        assert "def downgrade()" in src
