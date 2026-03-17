"""FastAPI dependency-injection providers for shared infrastructure clients.

Each generator yields a ready-to-use client and guarantees cleanup on request
teardown.  All clients are configured from the central ``Settings`` object.

Connections are created lazily on first use (not at import time) to avoid
crashes when databases are not yet ready during container startup.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession as Neo4jAsyncSession
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# ── Lazy singletons (created on first access) ───────────────────────────────

_async_engine = None
_async_session_factory = None
_neo4j_driver: AsyncDriver | None = None
_redis_pool = None


def _get_engine():
    global _async_engine
    if _async_engine is None:
        _async_engine = create_async_engine(
            settings.DATABASE_URL,
            echo=settings.DEBUG,
            pool_size=20,
            max_overflow=10,
            pool_pre_ping=True,
        )
    return _async_engine


def _get_session_factory():
    global _async_session_factory
    if _async_session_factory is None:
        _async_session_factory = async_sessionmaker(
            bind=_get_engine(),
            class_=AsyncSession,
            expire_on_commit=False,
        )
    return _async_session_factory


def _get_neo4j_driver() -> AsyncDriver:
    global _neo4j_driver
    if _neo4j_driver is None:
        _neo4j_driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
        )
    return _neo4j_driver


def _get_redis_pool():
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.ConnectionPool.from_url(
            settings.REDIS_URL,
            decode_responses=True,
        )
    return _redis_pool


# ── Dependency providers ─────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async SQLAlchemy session."""
    factory = _get_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_qdrant_client() -> AsyncGenerator[AsyncQdrantClient, None]:
    """Yield an async Qdrant client, closed after the request."""
    client = AsyncQdrantClient(
        host=settings.QDRANT_HOST,
        port=settings.QDRANT_PORT,
        api_key=settings.QDRANT_API_KEY,
    )
    try:
        yield client
    finally:
        await client.close()


async def get_neo4j_session() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Yield an async Neo4j session from the shared driver."""
    driver = _get_neo4j_driver()
    async with driver.session() as session:
        yield session


async def get_redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Yield an async Redis client backed by the shared connection pool."""
    pool = _get_redis_pool()
    client = aioredis.Redis(connection_pool=pool)
    try:
        yield client
    finally:
        await client.aclose()


# ── Annotated shortcuts for cleaner router signatures ────────────────────────
DbSession = Annotated[AsyncSession, Depends(get_db)]
QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]
Neo4jDep = Annotated[Neo4jAsyncSession, Depends(get_neo4j_session)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis_client)]


# ── Lifecycle helpers (called from main.py lifespan) ─────────────────────────


async def create_tables() -> None:
    """Create all ORM tables if they do not exist yet (dev convenience)."""
    from app.models.database import Base  # noqa: F401 — ensure all models loaded

    engine = _get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_all_connections() -> None:
    """Gracefully shut down all infrastructure connections."""
    global _async_engine, _neo4j_driver, _redis_pool

    if _async_engine is not None:
        await _async_engine.dispose()
        _async_engine = None

    if _neo4j_driver is not None:
        await _neo4j_driver.close()
        _neo4j_driver = None

    if _redis_pool is not None:
        await _redis_pool.disconnect()
        _redis_pool = None
