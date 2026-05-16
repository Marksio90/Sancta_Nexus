"""Shared ARQ connection pool for enqueueing background tasks from the API.

Usage in FastAPI route handlers:
    from app.workers.pool import enqueue

    job = await enqueue("run_lectio_pipeline",
                        user_id=current_user.id,
                        emotion_text=request.emotion_text)
    return {"task_id": job.job_id}
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

_arq_pool = None


async def _get_pool():
    """Return the shared ArqRedis pool, creating it on first call."""
    global _arq_pool
    if _arq_pool is None:
        try:
            from arq import create_pool
            from arq.connections import RedisSettings

            from app.core.config import settings

            _arq_pool = await create_pool(RedisSettings.from_dsn(settings.REDIS_URL))
        except Exception as exc:
            logger.error("ARQ pool creation failed: %s", exc)
            raise
    return _arq_pool


async def enqueue(function_name: str, **kwargs: Any):
    """Enqueue a background task and return the ARQ Job object.

    Returns None if ARQ is unavailable (graceful degradation).
    """
    try:
        pool = await _get_pool()
        job = await pool.enqueue_job(function_name, **kwargs)
        logger.info("Enqueued ARQ job: function=%s job_id=%s", function_name, job.job_id if job else None)
        return job
    except Exception as exc:
        logger.error("ARQ enqueue failed for %s: %s", function_name, exc)
        return None


async def close_pool() -> None:
    """Close the shared ARQ pool on application shutdown."""
    global _arq_pool
    if _arq_pool is not None:
        await _arq_pool.aclose()
        _arq_pool = None
