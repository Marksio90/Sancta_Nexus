"""Sancta Nexus API -- FastAPI application entry point.

Initialises middleware, routers, and infrastructure connections via an async
lifespan context manager.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.dependencies import close_all_connections, create_tables
from app.core.middleware import RateLimitMiddleware
from app.middleware.langsmith_context import LangSmithContextMiddleware
from app.middleware.timing import TimingMiddleware

logger = logging.getLogger(__name__)


# ── Background scheduler ──────────────────────────────────────────────────────


def _build_scheduler():
    """Buduje APScheduler z cron-jobami platformy.

    Importowany leniwie żeby serwer startował nawet bez apscheduler w środowisku.
    Zwraca None jeśli apscheduler nie jest zainstalowany.
    """
    try:
        from apscheduler.schedulers.asyncio import AsyncIOScheduler
        from apscheduler.triggers.cron import CronTrigger
    except ImportError:
        logger.warning("apscheduler not installed — cron jobs disabled. Run: pip install apscheduler")
        return None

    scheduler = AsyncIOScheduler(timezone="Europe/Warsaw")

    async def _morning_push_job() -> None:
        try:
            from app.api.routes.notifications import send_morning_notifications
            result = await send_morning_notifications()
            logger.info("Morning push sent: %s", result)
        except Exception as exc:
            logger.error("Morning push job failed: %s", exc)

    async def _prefetch_tomorrow_scripture() -> None:
        try:
            from datetime import date, timedelta

            from app.services.scripture.saints_calendar import get_saint_today
            tomorrow = date.today() + timedelta(days=1)
            saint = get_saint_today(tomorrow)
            logger.info("Pre-fetched tomorrow's saint: %s", saint["name"])
        except Exception as exc:
            logger.error("Scripture prefetch job failed: %s", exc)

    # Poranne powiadomienia — codziennie o 07:00 Warsaw
    scheduler.add_job(
        _morning_push_job,
        trigger=CronTrigger(hour=7, minute=0, timezone="Europe/Warsaw"),
        id="morning_push",
        name="Poranne powiadomienia z patronem dnia",
        replace_existing=True,
    )

    # Pre-fetch jutrzejszej liturgii — codziennie o 23:30 Warsaw
    scheduler.add_job(
        _prefetch_tomorrow_scripture,
        trigger=CronTrigger(hour=23, minute=30, timezone="Europe/Warsaw"),
        id="prefetch_scripture",
        name="Pre-fetch jutrzejszej liturgii",
        replace_existing=True,
    )

    return scheduler


# ── Lifespan ─────────────────────────────────────────────────────────────────


@asynccontextmanager
async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
    """Manage startup and shutdown of shared infrastructure connections.

    On startup the dependency-module singletons (engine, driver, pool) are
    already created at import time; we simply log readiness here.  On shutdown
    we close every connection pool gracefully.
    """
    logger.info(
        "Starting %s v%s",
        settings.APP_NAME,
        settings.VERSION,
    )

    # ── LangSmith tracing ────────────────────────────────────────────────
    # LangChain reads LANGCHAIN_* env vars automatically. We set them here
    # from our Settings object so the app works even if env vars are not
    # exported directly (e.g. in Docker when injected via config files).
    if settings.LANGCHAIN_TRACING_V2 and settings.LANGCHAIN_API_KEY:
        import os
        os.environ.setdefault("LANGCHAIN_TRACING_V2", "true")
        os.environ.setdefault("LANGCHAIN_API_KEY", settings.LANGCHAIN_API_KEY)
        os.environ.setdefault("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT)
        os.environ.setdefault("LANGCHAIN_ENDPOINT", settings.LANGCHAIN_ENDPOINT)
        logger.info(
            "LangSmith tracing enabled — project=%s endpoint=%s",
            settings.LANGCHAIN_PROJECT,
            settings.LANGCHAIN_ENDPOINT,
        )
    else:
        logger.info("LangSmith tracing disabled (set LANGCHAIN_TRACING_V2=true + LANGCHAIN_API_KEY to enable)")

    # Create database tables if they don't exist yet
    try:
        await create_tables()
        logger.info("Database tables verified / created")
    except Exception as exc:
        logger.warning("Could not create tables (will retry on first request): %s", exc)

    # Start background scheduler (cron jobs)
    scheduler = _build_scheduler()
    if scheduler is not None:
        scheduler.start()
        logger.info("Background scheduler started (2 jobs: morning push + scripture prefetch)")

    yield

    # Graceful shutdown
    if scheduler is not None:
        scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")

    # Close ARQ pool if it was opened during this process lifetime
    try:
        from app.workers.pool import close_pool
        await close_pool()
    except Exception:
        pass

    logger.info("Shutting down -- releasing infrastructure connections")
    await close_all_connections()


# ── Application factory ─────────────────────────────────────────────────────

app = FastAPI(
    title="Sancta Nexus API",
    description=(
        "Katolicka platforma modlitwy i formacji duchowej. "
        "Wspiera Lectio Divina, dziennik duchowy, Asystenta refleksji i programy formacyjne. "
        "Nie zastępuje kapłana, spowiednika ani kierownika duchowego."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── Observability ────────────────────────────────────────────────────────────

app.add_middleware(TimingMiddleware)
app.add_middleware(LangSmithContextMiddleware)

# ── Rate limiting ─────────────────────────────────────────────────────────────

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
    ai_max_requests=settings.AI_RATE_LIMIT_REQUESTS,
    ai_window_seconds=settings.AI_RATE_LIMIT_WINDOW,
)

# ── CORS ─────────────────────────────────────────────────────────────────────

_allowed_origins = [o.strip() for o in settings.ALLOWED_ORIGINS.split(",") if o.strip()]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
# Each router module is expected to expose an ``router`` APIRouter instance.
# Imports are deferred so the app still boots even when route modules are not
# yet implemented -- they simply will not be registered.

_ROUTERS: list[tuple[str, str, list[str]]] = [
    # stable
    ("app.api.routes.lectio_divina", "/api/v1/lectio-divina", ["lectio-divina"]),
    ("app.api.routes.examen", "/api/v1/examen", ["examen"]),
    ("app.api.routes.bible", "/api/v1/bible", ["bible"]),
    # beta
    ("app.api.routes.breviary", "/api/v1/breviary", ["breviary"]),
    ("app.api.routes.notifications", "/api/v1/notifications", ["notifications"]),
    # experimental
    # experimental (renamed from spiritual_director in Phase 2)
    ("app.api.routes.reflection_assistant", "/api/v1/reflection-assistant", ["reflection-assistant"]),
    ("app.api.routes.sacraments", "/api/v1/sacramental-prep", ["sacramental-prep"]),
    ("app.api.routes.community", "/api/v1/community", ["community"]),
    # core infrastructure (always active)
    ("app.api.routes.journal", "/api/v1/journal", ["journal"]),
    ("app.api.routes.auth", "/api/v1/auth", ["auth"]),
    ("app.api.routes.users", "/api/v1/users", ["users"]),
    ("app.api.routes.admin", "/api/v1/admin", ["admin"]),
    ("app.api.routes.orchestrate", "/api/v1/orchestrate", ["orchestrate"]),
    ("app.api.routes.knowledge", "/api/v1/knowledge", ["knowledge"]),
    # voice — experimental, behind feature flag
    ("app.api.routes.voice", "/api/v1/voice", ["voice"]),
    # WebSocket — Różaniec Wspólnotowy real-time sync
    ("app.api.routes.ws_rosary", "/ws", ["websocket"]),
    # Billing — Stripe subskrypcje
    ("app.api.routes.billing", "/api/v1/billing", ["billing"]),
    # User data sync — replaces localStorage-only stores
    ("app.api.routes.notes", "/api/v1/notes", ["notes"]),
    ("app.api.routes.progress", "/api/v1/progress", ["progress"]),
    # AI response quality feedback
    ("app.api.routes.feedback", "/api/v1/feedback", ["feedback"]),
    # Background task status polling (ARQ)
    ("app.api.routes.tasks", "/api/v1/tasks", ["tasks"]),
    # Guest mode — one free Lectio Divina without registration
    ("app.api.routes.guest", "/api/v1/guest", ["guest"]),
]

for _module_path, _prefix, _tags in _ROUTERS:
    try:
        import importlib

        _module = importlib.import_module(_module_path)
        app.include_router(_module.router, prefix=_prefix, tags=_tags)
        logger.info("Registered router %s", _module_path)
    except (ImportError, AttributeError):
        logger.debug(
            "Router %s not available yet -- skipping",
            _module_path,
        )


# ── Health check ─────────────────────────────────────────────────────────────


@app.get("/health", tags=["system"])
async def health_check() -> dict[str, str]:
    """Lightweight liveness probe for load-balancers and orchestrators."""
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "version": settings.VERSION,
    }


@app.get("/health/llm", tags=["system"])
async def llm_health() -> dict[str, object]:
    """LLM observability status — reports LangSmith tracing configuration.

    Does NOT make a live LangSmith API call (avoids latency in health checks).
    Use this to verify tracing is configured correctly in each environment.
    """
    import os

    tracing_active = bool(
        os.environ.get("LANGCHAIN_TRACING_V2") == "true"
        and os.environ.get("LANGCHAIN_API_KEY")
    )
    return {
        "status": "healthy",
        "langsmith_tracing": tracing_active,
        "langsmith_project": os.environ.get("LANGCHAIN_PROJECT", settings.LANGCHAIN_PROJECT),
        "langsmith_endpoint": os.environ.get("LANGCHAIN_ENDPOINT", settings.LANGCHAIN_ENDPOINT),
        "llm_provider": settings.LLM_PROVIDER,
        "llm_primary_model": settings.LLM_PRIMARY_MODEL,
        "llm_fast_model": settings.LLM_FAST_MODEL,
    }
