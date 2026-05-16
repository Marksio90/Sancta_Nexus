"""ARQ WorkerSettings — configuration for the background worker process.

Start a worker with:
    arq app.workers.arq_settings.WorkerSettings

The worker connects to the same Redis instance as the API server.
Cron jobs here can eventually replace the APScheduler jobs in main.py.
"""
from __future__ import annotations

import logging

from arq import cron
from arq.connections import RedisSettings

from app.core.config import settings
from app.workers.tasks import (
    prefetch_tomorrow_scripture_task,
    run_lectio_pipeline,
    send_morning_notifications_task,
)

logger = logging.getLogger(__name__)

# Parse Redis URL into ARQ RedisSettings.
# ARQ uses its own settings class (not aioredis ConnectionPool).
_redis_settings = RedisSettings.from_dsn(settings.REDIS_URL)


async def startup(ctx: dict) -> None:
    """Worker startup — log readiness."""
    logger.info("ARQ worker started")


async def shutdown(ctx: dict) -> None:
    """Worker shutdown — clean up."""
    logger.info("ARQ worker stopped")


class WorkerSettings:
    """ARQ worker configuration.

    ``functions`` — task functions available for ``pool.enqueue_job()``.
    ``cron_jobs`` — scheduled tasks (run on cron instead of APScheduler).
    """

    redis_settings = _redis_settings
    functions = [
        run_lectio_pipeline,
        send_morning_notifications_task,
        prefetch_tomorrow_scripture_task,
    ]
    cron_jobs = [
        # Morning push: daily 07:00 Warsaw → UTC 06:00 (UTC+1 winter, UTC+2 summer)
        # Use 05:00 UTC as a safe default (catches both DST states).
        cron(send_morning_notifications_task, hour=5, minute=0),
        # Pre-fetch tomorrow's readings: 22:30 UTC (≈23:30 Warsaw winter, 00:30+1 summer)
        cron(prefetch_tomorrow_scripture_task, hour=22, minute=30),
    ]
    on_startup = startup
    on_shutdown = shutdown
    max_jobs = 10
    job_timeout = 120  # seconds — enough for the slowest LLM pipeline
    keep_result = 3600  # store results in Redis for 1 hour
    max_tries = 3
    retry_jobs = True
    health_check_interval = 30
