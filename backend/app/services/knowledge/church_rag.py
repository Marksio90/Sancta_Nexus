"""Church Knowledge RAG — enhanced retrieval across all magisterial collections.

Core capabilities
-----------------
1. Query routing  — maps a question to the most relevant collection(s)
2. Multi-collection search — parallel async search across selected collections
3. Re-ranking   — theological relevance scoring (Magisterium > Patristic > Bible)
4. Citation generation — returns structured citations with document metadata
5. Tradition filtering — narrows results to a specific spiritual tradition

Usage::

    rag = ChurchRAG()
    results = await rag.search("co mówi Kościół o modlitwie kontemplacyjnej?")
    results = await rag.search("Łk 15 – przypowieść", collections=["biblia_pl"])
    results = await rag.search_for_tradition("rozeznawanie duchowe", "ignatian")
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from app.services.rag.embedding_service import EmbeddingService
from app.services.knowledge.collection_manager import CollectionManager
from app.services.knowledge.corpus_registry import (
    QdrantCollection,
    CORPUS_BY_ID,
)

logger = logging.getLogger(__name__)


# ─────────────────────────────────────────────────────────────────────────────
# Result model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class KnowledgeResult:
    content: str
    score: float
    source_type: str          # bible | catechism | encyclical | council | patristic
    collection: str
    section_ref: str          # "§ 2697", "Łk 15,11", "n. 14"
    document_title: str = ""
    document_title_pl: str = ""
    author: str = ""
    year: int = 0
    language: str = "la"
    book: str = ""            # Bible only
    chapter: int = 0          # Bible only
    verse_start: int = 0      # Bible only
    verse_end: int = 0        # Bible only
    translation: str = ""     # Bible only
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def citation(self) -> str:
        """Human-readable citation string."""
        if self.source_type == "bible":
            return f"{self.book} {self.chapter},{self.verse_start}" + (
                f"-{self.verse_end}" if self.verse_end != self.verse_start else ""
            ) + f" ({self.translation})"
        if self.section_ref:
            doc = self.document_title_pl or self.document_title
            return f"{doc}, {self.section_ref}" if doc else self.section_ref
        return self.document_title or "Nieznane źródło"


# ─────────────────────────────────────────────────────────────────────────────
# Query routing
# ─────────────────────────────────────────────────────────────────────────────

# Keywords that steer towards specific collections
_ROUTING_HINTS: dict[QdrantCollection, list[str]] = {
    QdrantCollection.BIBLIA_PL: [
        "fragment", "werset", "psalm", "ewangelia", "listy", "apokalipsa",
        "stary testament", "nowy testament", "księga", "biblia", "pismo",
    ],
    QdrantCollection.BIBLIA_LA: ["vulgate", "vulgata", "latin", "latina", "hebraeum", "graecum"],
    QdrantCollection.KATECHIZM: [
        "katechizm", "kkk", "§", "katolicka nauka", "dogmat", "sakrament",
        "grzech", "cnota", "dekalog", "modlitwa pańska",
    ],
    QdrantCollection.SOBORY: [
        "sobór", "vaticanum", "konstytucja", "dekret", "lumen gentium",
        "gaudium et spes", "dei verbum", "sacrosanctum concilium",
    ],
    QdrantCollection.MAGISTERIUM: [
        "encyklika", "adhortacja", "papież", "nauczanie", "magisterium",
        "rerum novarum", "evangelium", "laudato", "franciszek", "jan paweł",
    ],
    QdrantCollection.PATRYSTYKA: [
        "ojcowie kościoła", "augustyn", "tomasz", "teresa", "jan od krzyża",
        "ignacy", "benedykt", "tradycja", "mistycyzm", "kontemplacja",
    ],
}

def _route_query(query: str, limit: int = 3) -> list[QdrantCollection]:
    """Return the top-N most relevant collections for a query."""
    query_lower = query.lower()
    scores: dict[QdrantCollection, int] = {}

    for collection, hints in _ROUTING_HINTS.items():
        score = sum(1 for h in hints if h in query_lower)
        if score:
            scores[collection] = score

    if scores:
        ranked = sorted(scores, key=lambda c: scores[c], reverse=True)
        return ranked[:limit]

    # Default: search all main text collections
    return [
        QdrantCollection.BIBLIA_PL,
        QdrantCollection.KATECHIZM,
        QdrantCollection.MAGISTERIUM,
        QdrantCollection.SOBORY,
        QdrantCollection.PATRYSTYKA,
    ]


# ─────────────────────────────────────────────────────────────────────────────
# Re-ranking weights
# ─────────────────────────────────────────────────────────────────────────────

# Magisterium and CCC carry higher authority weight in theological context
_AUTHORITY_WEIGHT: dict[str, float] = {
    "sobory":      1.15,
    "katechizm":   1.12,
    "magisterium": 1.10,
    "patrystyka":  1.05,
    "biblia_pl":   1.08,
    "biblia_la":   1.06,
    "biblia_en":   1.04,
    "liturgia":    1.03,
}


def _rerank(results: list[KnowledgeResult]) -> list[KnowledgeResult]:
    """Apply authority weighting and deduplicate by content similarity."""
    for r in results:
        weight = _AUTHORITY_WEIGHT.get(r.collection, 1.0)
        r.score = r.score * weight

    # Simple deduplication: remove near-duplicates (same content start)
    seen: set[str] = set()
    unique: list[KnowledgeResult] = []
    for r in sorted(results, key=lambda x: x.score, reverse=True):
        key = r.content[:80].strip().lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)

    return unique


# ─────────────────────────────────────────────────────────────────────────────
# Church RAG
# ─────────────────────────────────────────────────────────────────────────────

class ChurchRAG:
    """Multi-collection retrieval over the Church knowledge base."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 6333,
        api_key: str | None = None,
    ) -> None:
        self._embedder = EmbeddingService(backend="openai")
        self._cm = CollectionManager(host=host, port=port, api_key=api_key)
        self._available_collections: set[str] = set()

    # ── Public API ────────────────────────────────────────────────────────────

    async def search(
        self,
        query: str,
        *,
        collections: list[str] | None = None,
        limit: int = 8,
        score_threshold: float = 0.35,
        filters: dict[str, Any] | None = None,
        language: str | None = None,
    ) -> list[KnowledgeResult]:
        """Search across one or more collections and return ranked results.

        Args:
            query: Natural language question in Polish, Latin, or English.
            collections: Explicit collection names; if None, auto-routed.
            limit: Total results to return after re-ranking.
            score_threshold: Minimum cosine similarity.
            filters: Extra payload filters applied to every collection.
            language: Filter to a specific language (pl|la|en).
        """
        # Build query vector
        try:
            vector = await self._embedder.aembed_text(query)
        except Exception as exc:
            logger.error("Embedding failed: %s", exc)
            return []

        # Resolve collections
        if collections:
            target = [QdrantCollection(c) for c in collections if c in [q.value for q in QdrantCollection]]
        else:
            target = _route_query(query)

        # Add language filter
        effective_filters = dict(filters or {})
        if language:
            effective_filters["language"] = language

        # Parallel search
        tasks = [
            self._search_collection(col, vector, limit=limit, filters=effective_filters, threshold=score_threshold)
            for col in target
        ]
        per_collection = await asyncio.gather(*tasks, return_exceptions=True)

        # Flatten, filter exceptions
        all_results: list[KnowledgeResult] = []
        for batch in per_collection:
            if isinstance(batch, list):
                all_results.extend(batch)

        # Re-rank and trim
        ranked = _rerank(all_results)
        return ranked[:limit]

    async def search_scripture(
        self,
        query: str,
        translation: str = "BG",
        limit: int = 5,
    ) -> list[KnowledgeResult]:
        """Search the Bible (Polish Biblia Gdańska by default)."""
        col = QdrantCollection.BIBLIA_PL
        return await self.search(
            query,
            collections=[col.value],
            filters={"translation": translation},
            limit=limit,
        )

    async def search_catechism(self, query: str, limit: int = 5) -> list[KnowledgeResult]:
        """Search the Catechism of the Catholic Church."""
        return await self.search(query, collections=[QdrantCollection.KATECHIZM.value], limit=limit)

    async def search_magisterium(self, query: str, limit: int = 5) -> list[KnowledgeResult]:
        """Search encyclicals and apostolic exhortations."""
        return await self.search(query, collections=[QdrantCollection.MAGISTERIUM.value], limit=limit)

    async def search_councils(self, query: str, limit: int = 5) -> list[KnowledgeResult]:
        """Search Vatican I and Vatican II documents."""
        return await self.search(query, collections=[QdrantCollection.SOBORY.value], limit=limit)

    async def search_patristic(self, query: str, limit: int = 5) -> list[KnowledgeResult]:
        """Search Church Fathers and Saints."""
        return await self.search(query, collections=[QdrantCollection.PATRYSTYKA.value], limit=limit)

    async def search_for_tradition(
        self,
        query: str,
        tradition: str,
        limit: int = 8,
    ) -> list[KnowledgeResult]:
        """Search all collections filtered by spiritual tradition tag."""
        return await self.search(
            query,
            filters={"tradition_tags": tradition},
            limit=limit,
        )

    async def search_by_document(
        self,
        query: str,
        doc_id: str,
        limit: int = 5,
    ) -> list[KnowledgeResult]:
        """Search within a specific document (e.g. 'lumen-gentium')."""
        doc = CORPUS_BY_ID.get(doc_id)
        if not doc:
            return []
        return await self.search(
            query,
            collections=[doc.collection.value],
            filters={"doc_id": doc_id},
            limit=limit,
        )

    async def cross_reference(
        self,
        scripture_ref: str,
        limit: int = 6,
    ) -> list[KnowledgeResult]:
        """Find magisterial/patristic texts that reference a scripture passage.

        Searches CCC, encyclicals, and patristics for mentions of the passage.
        """
        results = await self.search(
            scripture_ref,
            collections=[
                QdrantCollection.KATECHIZM.value,
                QdrantCollection.MAGISTERIUM.value,
                QdrantCollection.PATRYSTYKA.value,
                QdrantCollection.SOBORY.value,
            ],
            limit=limit,
        )
        return results

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _search_collection(
        self,
        collection: QdrantCollection,
        vector: list[float],
        limit: int,
        filters: dict[str, Any],
        threshold: float,
    ) -> list[KnowledgeResult]:
        try:
            raw = await self._cm.async_search(
                collection, vector, limit=limit,
                filters=filters or None,
                score_threshold=threshold,
            )
            return [self._to_result(r, collection) for r in raw]
        except Exception as exc:
            logger.debug("Collection %s search failed: %s", collection.value, exc)
            return []

    @staticmethod
    def _to_result(raw: dict[str, Any], collection: QdrantCollection) -> KnowledgeResult:
        p = raw.get("payload", {})
        doc_meta = CORPUS_BY_ID.get(p.get("doc_id", ""))

        return KnowledgeResult(
            content=p.get("content", ""),
            score=raw.get("score", 0.0),
            source_type=p.get("source_type", collection.value),
            collection=collection.value,
            section_ref=p.get("section_ref", ""),
            document_title=p.get("document_title") or (doc_meta.title if doc_meta else ""),
            document_title_pl=p.get("document_title_pl") or (doc_meta.title_pl if doc_meta else ""),
            author=p.get("author") or (doc_meta.author if doc_meta else ""),
            year=p.get("year") or (doc_meta.year if doc_meta else 0),
            language=p.get("language", "la"),
            book=p.get("book", ""),
            chapter=p.get("chapter", 0),
            verse_start=p.get("verse_start", 0),
            verse_end=p.get("verse_end", 0),
            translation=p.get("translation", ""),
            metadata=p,
        )


# ─────────────────────────────────────────────────────────────────────────────
# Module-level singleton (lazy init)
# ─────────────────────────────────────────────────────────────────────────────

_church_rag: ChurchRAG | None = None


def get_church_rag() -> ChurchRAG:
    global _church_rag
    if _church_rag is None:
        from app.core.config import settings
        _church_rag = ChurchRAG(
            host=settings.QDRANT_HOST,
            port=settings.QDRANT_PORT,
            api_key=settings.QDRANT_API_KEY,
        )
    return _church_rag
