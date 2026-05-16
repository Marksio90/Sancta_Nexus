"""ARQ task definitions for Sancta Nexus background workers.

Each async function here is registered with ARQ and executed in a worker
process, not in the HTTP server.  This lets the API return a task_id
immediately (<100 ms) while the LLM pipeline runs in the background.

Context keys available inside task functions (set by arq_settings startup):
    ctx["redis"]   — aioredis.Redis (shared with the worker's Redis pool)

Enqueue from a FastAPI handler:
    pool = await _get_arq_pool()
    job = await pool.enqueue_job("run_lectio_pipeline", user_id=..., ...)
    return {"task_id": job.job_id}
"""
from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Task: run full Lectio Divina LangGraph pipeline
# ---------------------------------------------------------------------------


async def run_lectio_pipeline(
    ctx: dict,
    *,
    user_id: str,
    emotion_text: str,
    tradition: str = "",
) -> dict[str, Any]:
    """Execute the complete Lectio Divina LangGraph pipeline.

    This is the ARQ-compatible wrapper around the same agent called by the
    synchronous ``POST /run`` endpoint.  Running it here means the HTTP
    request completes in < 100 ms (returns task_id) and the 15-40 s LLM
    pipeline runs here instead.

    The result is stored by ARQ in Redis (job_results namespace) and can be
    retrieved via GET /api/v1/tasks/{task_id}.
    """
    logger.info("ARQ: run_lectio_pipeline user=%s tradition=%s", user_id, tradition)

    from app.agents.lectio_divina.lectio_divina_graph import run_session

    try:
        result = await run_session(
            user_id=user_id,
            raw_input=emotion_text,
            tradition=tradition,
        )
    except Exception as exc:
        logger.error("ARQ: run_lectio_pipeline failed: %s", exc, exc_info=True)
        return {"error": str(exc)}

    # Optional: JourneyTrackerAgent post-pipeline
    journey: dict[str, Any] | None = None
    try:
        from app.agents.memory.journey_tracker import JourneyTrackerAgent

        session_data = {
            "emotions": {
                "primary": (result.get("prayer") or {}).get("spiritual_movement", "neutral"),
            },
            "spiritual_state": (result.get("prayer") or {}).get("spiritual_movement", ""),
            "reflection": (result.get("meditation") or {}).get("key_word", ""),
            "scripture": (result.get("scripture") or {}).get("text", ""),
        }
        tracker = JourneyTrackerAgent()
        journey = await tracker.track(user_id, session_data)
    except Exception:
        logger.warning("ARQ: JourneyTrackerAgent failed; journey not tracked.")

    return {
        "scripture": result.get("scripture"),
        "meditation": result.get("meditation"),
        "prayer": result.get("prayer"),
        "contemplation": result.get("contemplation"),
        "action": result.get("action"),
        "tradition": result.get("tradition", ""),
        "kerygmatic_theme": result.get("kerygmatic_theme", ""),
        "journey": journey,
        "error": result.get("error"),
    }


# ---------------------------------------------------------------------------
# Task: send morning push notifications (replaces APScheduler cron job)
# ---------------------------------------------------------------------------


async def send_morning_notifications_task(ctx: dict) -> dict[str, Any]:
    """Send morning push notifications — can be enqueued or run on cron."""
    logger.info("ARQ: send_morning_notifications_task")
    try:
        from app.api.routes.notifications import send_morning_notifications

        return await send_morning_notifications()
    except Exception as exc:
        logger.error("ARQ: morning notifications failed: %s", exc)
        return {"error": str(exc)}


# ---------------------------------------------------------------------------
# Task: pre-fetch tomorrow's scripture
# ---------------------------------------------------------------------------


async def prefetch_tomorrow_scripture_task(ctx: dict) -> dict[str, Any]:
    """Pre-fetch and cache tomorrow's liturgical readings."""
    logger.info("ARQ: prefetch_tomorrow_scripture_task")
    try:
        from datetime import date, timedelta

        from app.services.scripture.saints_calendar import get_saint_today

        tomorrow = date.today() + timedelta(days=1)
        saint = get_saint_today(tomorrow)
        return {"saint": saint["name"]}
    except Exception as exc:
        logger.error("ARQ: scripture prefetch failed: %s", exc)
        return {"error": str(exc)}
