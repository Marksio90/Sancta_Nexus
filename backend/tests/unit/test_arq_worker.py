"""Unit tests for ARQ worker infrastructure.

All tests are self-contained — no Redis, no LLM, no real ARQ worker.
Covers:
  - WorkerSettings has required attributes
  - task functions are registered
  - run_lectio_pipeline task signature and structure
  - tasks route is registered in main.py
  - EnqueuedTaskResponse model
"""
import importlib
import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from unittest.mock import MagicMock as UnitMock

# --- Stub heavy deps so imports work without installed packages -------------

for _mod in [
    "arq", "arq.connections", "arq.jobs",
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = UnitMock()

# Provide arq.cron as a no-op function so arq_settings imports cleanly.
sys.modules["arq"].cron = lambda fn, **_: fn


# ---------------------------------------------------------------------------
# WorkerSettings
# ---------------------------------------------------------------------------


class TestWorkerSettings:
    def test_worker_settings_importable(self):
        """WorkerSettings class exists and is importable."""
        from app.workers.arq_settings import WorkerSettings
        assert WorkerSettings is not None

    def test_functions_list_not_empty(self):
        from app.workers.arq_settings import WorkerSettings
        assert len(WorkerSettings.functions) >= 1

    def test_run_lectio_pipeline_registered(self):
        from app.workers.arq_settings import WorkerSettings
        from app.workers.tasks import run_lectio_pipeline
        assert run_lectio_pipeline in WorkerSettings.functions

    def test_keep_result_positive(self):
        from app.workers.arq_settings import WorkerSettings
        assert WorkerSettings.keep_result > 0

    def test_job_timeout_positive(self):
        from app.workers.arq_settings import WorkerSettings
        assert WorkerSettings.job_timeout > 0

    def test_max_tries_positive(self):
        from app.workers.arq_settings import WorkerSettings
        assert WorkerSettings.max_tries >= 1

    def test_on_startup_callable(self):
        from app.workers.arq_settings import WorkerSettings
        assert callable(WorkerSettings.on_startup)

    def test_on_shutdown_callable(self):
        from app.workers.arq_settings import WorkerSettings
        assert callable(WorkerSettings.on_shutdown)


# ---------------------------------------------------------------------------
# Task function signatures
# ---------------------------------------------------------------------------


class TestTaskFunctions:
    def test_run_lectio_pipeline_importable(self):
        from app.workers.tasks import run_lectio_pipeline
        assert callable(run_lectio_pipeline)

    def test_send_morning_notifications_task_importable(self):
        from app.workers.tasks import send_morning_notifications_task
        assert callable(send_morning_notifications_task)

    def test_prefetch_tomorrow_scripture_task_importable(self):
        from app.workers.tasks import prefetch_tomorrow_scripture_task
        assert callable(prefetch_tomorrow_scripture_task)

    @pytest.mark.asyncio
    async def test_run_lectio_pipeline_returns_dict_on_error(self):
        """When the LangGraph agent raises, task returns error dict (not re-raises)."""
        from app.workers.tasks import run_lectio_pipeline

        ctx = {}
        mock_module = MagicMock()
        mock_module.run_session = AsyncMock(side_effect=RuntimeError("LLM unavailable"))
        with patch.dict("sys.modules", {"app.agents.lectio_divina.lectio_divina_graph": mock_module}):
            result = await run_lectio_pipeline(
                ctx,
                user_id="user-123",
                emotion_text="czuję się zagubiony",
            )
        assert isinstance(result, dict)
        assert "error" in result

    @pytest.mark.asyncio
    async def test_run_lectio_pipeline_returns_full_structure_on_success(self):
        """Successful task returns all expected keys."""
        from app.workers.tasks import run_lectio_pipeline

        fake_result = {
            "scripture": {"text": "Ps 23"},
            "meditation": {"key_word": "pasterz"},
            "prayer": {"spiritual_movement": "peace"},
            "contemplation": {},
            "action": {},
            "tradition": "ignatian",
            "kerygmatic_theme": "mercy",
        }

        ctx = {}
        mock_module = MagicMock()
        mock_module.run_session = AsyncMock(return_value=fake_result)

        with patch.dict("sys.modules", {"app.agents.lectio_divina.lectio_divina_graph": mock_module}):
            with patch.dict("sys.modules", {"app.agents.memory.journey_tracker": MagicMock(
                JourneyTrackerAgent=MagicMock(return_value=MagicMock(
                    track=AsyncMock(return_value={"current_stage": "purgativa", "progress_percentage": 10})
                ))
            )}):
                result = await run_lectio_pipeline(
                    ctx,
                    user_id="user-123",
                    emotion_text="czuję spokój",
                )

        assert "scripture" in result
        assert "meditation" in result
        assert "prayer" in result
        assert "error" in result  # may be None — key must exist


# ---------------------------------------------------------------------------
# Route registration
# ---------------------------------------------------------------------------


class TestTasksRouteRegistration:
    def test_tasks_router_exists(self):
        from app.api.routes.tasks import router
        assert router is not None

    def test_tasks_router_has_get_route(self):
        from app.api.routes.tasks import router
        paths = [r.path for r in router.routes]
        assert any("{task_id}" in p for p in paths)

    def test_tasks_router_in_main_routers(self):
        import app.main as main_module
        import ast, inspect, textwrap
        src = inspect.getsource(main_module)
        assert "app.api.routes.tasks" in src

    def test_enqueued_task_response_model(self):
        from app.api.routes.lectio_divina import EnqueuedTaskResponse
        r = EnqueuedTaskResponse(task_id="abc", status="queued", poll_url="/api/v1/tasks/abc")
        assert r.task_id == "abc"
        assert r.poll_url == "/api/v1/tasks/abc"

    def test_lectio_router_has_run_async_route(self):
        from app.api.routes.lectio_divina import router
        paths = [r.path for r in router.routes]
        assert "/run/async" in paths
