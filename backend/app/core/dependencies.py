"""FastAPI dependency-injection providers for shared infrastructure clients.

Each generator yields a ready-to-use client and guarantees cleanup on request
teardown.  All clients are configured from the central ``Settings`` object.
"""

from collections.abc import AsyncGenerator
from typing import Annotated

import redis.asyncio as aioredis
from fastapi import Depends
from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession as Neo4jAsyncSession
from qdrant_client import AsyncQdrantClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings

# ── SQLAlchemy async engine (module-level singleton) ─────────────────────────
_async_engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=20,
    max_overflow=10,
    pool_pre_ping=True,
)

_async_session_factory = async_sessionmaker(
    bind=_async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

# ── Neo4j async driver (module-level singleton) ─────────────────────────────
_neo4j_driver: AsyncDriver = AsyncGraphDatabase.driver(
    settings.NEO4J_URI,
    auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD),
)

# ── Redis async pool (module-level singleton) ────────────────────────────────
_redis_pool = aioredis.ConnectionPool.from_url(
    settings.REDIS_URL,
    decode_responses=True,
)


# ── Dependency providers ─────────────────────────────────────────────────────


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a transactional async SQLAlchemy session.

    The session is committed on success and rolled back on unhandled exceptions.
    """
    async with _async_session_factory() as session:
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


async def get_neo4j_driver() -> AsyncGenerator[Neo4jAsyncSession, None]:
    """Yield an async Neo4j session from the shared driver."""
    async with _neo4j_driver.session() as session:
        yield session


async def get_redis_client() -> AsyncGenerator[aioredis.Redis, None]:
    """Yield an async Redis client backed by the shared connection pool."""
    client = aioredis.Redis(connection_pool=_redis_pool)
    try:
        yield client
    finally:
        await client.aclose()


# ── Annotated shortcuts for cleaner router signatures ────────────────────────
DbSession = Annotated[AsyncSession, Depends(get_db)]
QdrantDep = Annotated[AsyncQdrantClient, Depends(get_qdrant_client)]
Neo4jDep = Annotated[Neo4jAsyncSession, Depends(get_neo4j_driver)]
RedisDep = Annotated[aioredis.Redis, Depends(get_redis_client)]


# ── Lifecycle helpers (called from main.py lifespan) ─────────────────────────


async def close_all_connections() -> None:
    """Gracefully shut down all infrastructure connections."""
    await _async_engine.dispose()
    await _neo4j_driver.close()
    await _redis_pool.disconnect()
