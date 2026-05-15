"""Sancta Nexus API -- FastAPI application entry point.

Initialises middleware, routers, and infrastructure connections via an async
lifespan context manager.
"""

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.dependencies import close_all_connections, create_tables
from app.middleware.timing import TimingMiddleware
from app.core.middleware import RateLimitMiddleware

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

# ── Rate limiting ─────────────────────────────────────────────────────────────

app.add_middleware(
    RateLimitMiddleware,
    max_requests=settings.RATE_LIMIT_REQUESTS,
    window_seconds=settings.RATE_LIMIT_WINDOW,
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
