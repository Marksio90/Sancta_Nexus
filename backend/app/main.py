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

logger = logging.getLogger(__name__)


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
    yield
    logger.info("Shutting down -- releasing infrastructure connections")
    await close_all_connections()


# ── Application factory ─────────────────────────────────────────────────────

app = FastAPI(
    title="Sancta Nexus API",
    description=(
        "AI-powered prayer and spiritual direction platform featuring 47 "
        "specialised agents for Lectio Divina, emotional discernment, and "
        "theological scholarship."
    ),
    version=settings.VERSION,
    lifespan=lifespan,
)

# ── Observability ────────────────────────────────────────────────────────────

app.add_middleware(TimingMiddleware)

# ── CORS ─────────────────────────────────────────────────────────────────────

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # tighten in production via env var
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────────────────────────
# Each router module is expected to expose an ``router`` APIRouter instance.
# Imports are deferred so the app still boots even when route modules are not
# yet implemented -- they simply will not be registered.

_ROUTERS: list[tuple[str, str, list[str]]] = [
    ("app.api.routes.lectio_divina", "/api/v1/lectio-divina", ["lectio-divina"]),
    ("app.api.routes.bible", "/api/v1/bible", ["bible"]),
    ("app.api.routes.spiritual_director", "/api/v1/spiritual-director", ["spiritual-director"]),
    ("app.api.routes.orchestrate", "/api/v1/orchestrate", ["orchestrate"]),
    ("app.api.routes.auth", "/api/v1/auth", ["auth"]),
    ("app.api.routes.users", "/api/v1/users", ["users"]),
    ("app.api.routes.breviary", "/api/v1/breviary", ["breviary"]),
    ("app.api.routes.voice", "/api/v1/voice", ["voice"]),
    ("app.api.routes.notifications", "/api/v1/notifications", ["notifications"]),
    ("app.api.routes.knowledge", "/api/v1/knowledge", ["knowledge"]),
    ("app.api.routes.sacraments", "/api/v1/sacraments", ["sacraments"]),
    ("app.api.routes.community", "/api/v1/community", ["community"]),
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
