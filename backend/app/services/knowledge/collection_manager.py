"""Qdrant collection manager for the Church knowledge base.

Responsibilities:
  - Create / ensure all knowledge base collections exist with correct config
  - Define vector dimension and distance metric per collection
  - Create payload indices for fast filtered search
  - Provide async upsert and batch-upsert helpers
  - Track collection statistics

Collections (all use text-embedding-3-small → 1536 dims):
  biblia_pl   — Polish Bible
  biblia_la   — Latin Vulgate + Greek NT + Hebrew OT
  biblia_en   — English Douay-Rheims
  katechizm   — CCC paragraphs
  sobory      — Council documents
  magisterium — Encyclicals + apostolic exhortations
  patrystyka  — Church Fathers
  liturgia    — Liturgical texts
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import (
    Distance,
    FieldCondition,
    Filter,
    MatchValue,
    PayloadSchemaType,
    PointStruct,
    VectorParams,
)

from app.services.knowledge.corpus_registry import QdrantCollection

logger = logging.getLogger(__name__)

# Vector dimension for text-embedding-3-small (OpenAI)
VECTOR_DIM = 1536
DISTANCE = Distance.COSINE

# Payload fields to index for efficient filtered queries
_PAYLOAD_INDICES: dict[QdrantCollection, list[tuple[str, PayloadSchemaType]]] = {
    QdrantCollection.BIBLIA_PL: [
        ("book", PayloadSchemaType.KEYWORD),
        ("chapter", PayloadSchemaType.INTEGER),
        ("translation", PayloadSchemaType.KEYWORD),
        ("language", PayloadSchemaType.KEYWORD),
    ],
    QdrantCollection.BIBLIA_LA: [
        ("book", PayloadSchemaType.KEYWORD),
        ("chapter", PayloadSchemaType.INTEGER),
        ("translation", PayloadSchemaType.KEYWORD),
    ],
    QdrantCollection.BIBLIA_EN: [
        ("book", PayloadSchemaType.KEYWORD),
        ("chapter", PayloadSchemaType.INTEGER),
        ("translation", PayloadSchemaType.KEYWORD),
    ],
    QdrantCollection.KATECHIZM: [
        ("part", PayloadSchemaType.INTEGER),
        ("section_ref", PayloadSchemaType.KEYWORD),
    ],
    QdrantCollection.SOBORY: [
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("author", PayloadSchemaType.KEYWORD),
        ("doc_type", PayloadSchemaType.KEYWORD),
        ("year", PayloadSchemaType.INTEGER),
    ],
    QdrantCollection.MAGISTERIUM: [
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("author", PayloadSchemaType.KEYWORD),
        ("doc_type", PayloadSchemaType.KEYWORD),
        ("year", PayloadSchemaType.INTEGER),
    ],
    QdrantCollection.PATRYSTYKA: [
        ("doc_id", PayloadSchemaType.KEYWORD),
        ("author", PayloadSchemaType.KEYWORD),
        ("tradition_tags", PayloadSchemaType.KEYWORD),
    ],
    QdrantCollection.LITURGIA: [
        ("rite", PayloadSchemaType.KEYWORD),
        ("liturgical_season", PayloadSchemaType.KEYWORD),
    ],
}

# Common payload fields indexed for all collections
_COMMON_INDICES: list[tuple[str, PayloadSchemaType]] = [
    ("source_type", PayloadSchemaType.KEYWORD),
    ("language", PayloadSchemaType.KEYWORD),
    ("theology_tags", PayloadSchemaType.KEYWORD),
    ("tradition_tags", PayloadSchemaType.KEYWORD),
]


class CollectionManager:
    """Manages Qdrant collections for the Church knowledge base."""

    def __init__(self, host: str = "localhost", port: int = 6333, api_key: str | None = None) -> None:
        self._host = host
        self._port = port
        self._api_key = api_key
        self._sync_client: QdrantClient | None = None

    def _get_sync_client(self) -> QdrantClient:
        if self._sync_client is None:
            self._sync_client = QdrantClient(
                host=self._host, port=self._port, api_key=self._api_key
            )
        return self._sync_client

    def _get_async_client(self) -> AsyncQdrantClient:
        return AsyncQdrantClient(
            host=self._host, port=self._port, api_key=self._api_key
        )

    # ── Collection setup ──────────────────────────────────────────────────────

    def ensure_collection(self, collection: QdrantCollection) -> bool:
        """Create collection if it does not exist. Returns True if created."""
        client = self._get_sync_client()
        name = collection.value

        existing = {c.name for c in client.get_collections().collections}
        if name in existing:
            return False

        client.create_collection(
            collection_name=name,
            vectors_config=VectorParams(size=VECTOR_DIM, distance=DISTANCE),
        )
        logger.info("Created Qdrant collection: %s", name)

        # Create payload indices for fast filtered queries
        all_indices = _COMMON_INDICES + _PAYLOAD_INDICES.get(collection, [])
        for field_name, schema_type in all_indices:
            try:
                client.create_payload_index(
                    collection_name=name,
                    field_name=field_name,
                    field_schema=schema_type,
                )
            except Exception as exc:
                logger.debug("Index %s.%s already exists or failed: %s", name, field_name, exc)

        return True

    def ensure_all_collections(self) -> dict[str, bool]:
        """Ensure all knowledge base collections exist. Returns {name: created} map."""
        return {c.value: self.ensure_collection(c) for c in QdrantCollection}

    # ── Upsert helpers ────────────────────────────────────────────────────────

    def upsert_chunks(
        self,
        collection: QdrantCollection,
        chunks: list[dict[str, Any]],  # {"id": str, "vector": list[float], "payload": dict}
        batch_size: int = 100,
    ) -> int:
        """Batch upsert chunks into a collection. Returns total upserted count."""
        client = self._get_sync_client()
        name = collection.value
        total = 0

        for i in range(0, len(chunks), batch_size):
            batch = chunks[i:i + batch_size]
            points = [
                PointStruct(id=c["id"], vector=c["vector"], payload=c["payload"])
                for c in batch
            ]
            client.upsert(collection_name=name, points=points)
            total += len(batch)
            logger.debug("Upserted %d/%d chunks into %s", total, len(chunks), name)

        return total

    async def async_upsert_chunks(
        self,
        collection: QdrantCollection,
        chunks: list[dict[str, Any]],
        batch_size: int = 100,
    ) -> int:
        """Async batch upsert."""
        async with self._get_async_client() as client:
            total = 0
            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]
                points = [
                    PointStruct(id=c["id"], vector=c["vector"], payload=c["payload"])
                    for c in batch
                ]
                await client.upsert(collection_name=collection.value, points=points)
                total += len(batch)
            return total

    # ── Statistics ────────────────────────────────────────────────────────────

    def collection_stats(self) -> dict[str, dict[str, Any]]:
        """Return point count and status for each collection."""
        client = self._get_sync_client()
        stats: dict[str, dict[str, Any]] = {}

        for col in QdrantCollection:
            try:
                info = client.get_collection(col.value)
                stats[col.value] = {
                    "points": info.points_count,
                    "status": info.status.value if info.status else "unknown",
                    "vectors_count": info.vectors_count,
                }
            except Exception:
                stats[col.value] = {"points": 0, "status": "missing"}

        return stats

    def search(
        self,
        collection: QdrantCollection,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """Synchronous vector search with optional payload filtering."""
        client = self._get_sync_client()

        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        results = client.search(
            collection_name=collection.value,
            query_vector=query_vector,
            limit=limit,
            query_filter=qdrant_filter,
            score_threshold=score_threshold,
            with_payload=True,
        )

        return [
            {"id": r.id, "score": r.score, "payload": r.payload}
            for r in results
        ]

    async def async_search(
        self,
        collection: QdrantCollection,
        query_vector: list[float],
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float = 0.35,
    ) -> list[dict[str, Any]]:
        """Async vector search."""
        qdrant_filter = None
        if filters:
            conditions = [
                FieldCondition(key=k, match=MatchValue(value=v))
                for k, v in filters.items()
            ]
            qdrant_filter = Filter(must=conditions)

        async with self._get_async_client() as client:
            results = await client.search(
                collection_name=collection.value,
                query_vector=query_vector,
                limit=limit,
                query_filter=qdrant_filter,
                score_threshold=score_threshold,
                with_payload=True,
            )

        return [
            {"id": r.id, "score": r.score, "payload": r.payload}
            for r in results
        ]
