"""Task status polling endpoint.

Clients that cannot use SSE (mobile background, Capacitor offline fetch)
enqueue a pipeline via POST /api/v1/lectio-divina/run/async and poll here
for the result.

GET /api/v1/tasks/{task_id}
→ TaskStatusResponse

Status values (mirror ARQ JobStatus):
    queued       — task waiting in queue
    in_progress  — worker is executing the task
    complete     — result is ready (check `result` field)
    failed       — task raised an exception (check `error` field)
    not_found    — unknown task_id or result expired (1 h TTL)
"""
from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel

from app.core.rbac import require_authenticated
from app.models.database import User

logger = logging.getLogger(__name__)

router = APIRouter()


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str  # queued | in_progress | complete | failed | not_found
    result: dict[str, Any] | None = None
    error: str | None = None


@router.get("/{task_id}", response_model=TaskStatusResponse)
async def get_task_status(
    task_id: str,
    current_user: User = require_authenticated,  # noqa: ARG001 — auth enforced
) -> TaskStatusResponse:
    """Poll the status and result of a background task.

    The ``task_id`` is obtained from the response of a ``POST /run/async``
    endpoint (e.g. ``/api/v1/lectio-divina/run/async``).

    Results expire after 1 hour (``keep_result=3600`` in WorkerSettings).
    """
    try:
        from arq.jobs import Job, JobStatus

        from app.workers.pool import _get_pool

        pool = await _get_pool()
        job = Job(task_id, pool)
        job_status = await job.status()

        if job_status == JobStatus.not_found:
            return TaskStatusResponse(task_id=task_id, status="not_found")

        if job_status in (JobStatus.queued, JobStatus.deferred):
            return TaskStatusResponse(task_id=task_id, status="queued")

        if job_status == JobStatus.in_progress:
            return TaskStatusResponse(task_id=task_id, status="in_progress")

        # complete or failed — retrieve result info
        info = await job.result_info()
        if info is None:
            return TaskStatusResponse(task_id=task_id, status="not_found")

        if info.success:
            return TaskStatusResponse(
                task_id=task_id,
                status="complete",
                result=info.result,
            )
        else:
            return TaskStatusResponse(
                task_id=task_id,
                status="failed",
                error=str(info.result),
            )

    except ImportError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Background task queue (ARQ) not available.",
        )
    except Exception as exc:
        logger.error("Task status check failed for %s: %s", task_id, exc)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve task status.",
        )
