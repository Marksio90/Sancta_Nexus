"""
PatristicAgent (A-017) - Cross-references content with the Church Fathers.

Searches the 'patrystyka' Qdrant collection for relevant passages from
Augustine, Aquinas, John of the Cross, Teresa of Avila, and other Fathers
and Doctors of the Church.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchAny

logger = logging.getLogger(__name__)

COLLECTION_NAME = "patrystyka"
DEFAULT_MIN_RELEVANCE = 0.70


@dataclass(frozen=True, slots=True)
class PatristicReference:
    """A single cross-reference to a Church Father's writing."""

    father_name: str
    work: str
    quote: str
    relevance_score: float


class PatristicAgent:
    """
    A-017: Finds patristic cross-references for scripture and theological content.

    Searches a vector store of Church Fathers' writings to locate passages
    that illuminate or corroborate a given scripture reference or piece of
    theological content.
    """

    AGENT_ID = "A-017"
    AGENT_NAME = "PatristicAgent"

    # Canonical list of Fathers/Doctors supported by default
    SUPPORTED_FATHERS = (
        "Augustine of Hippo",
        "Thomas Aquinas",
        "John of the Cross",
        "Teresa of Avila",
        "John Chrysostom",
        "Basil the Great",
        "Gregory of Nazianzus",
        "Ambrose of Milan",
        "Jerome",
        "Gregory the Great",
        "Athanasius of Alexandria",
        "Cyril of Alexandria",
        "Irenaeus of Lyon",
        "Clement of Alexandria",
        "Origen",
        "Bernard of Clairvaux",
        "Catherine of Siena",
        "Therese of Lisieux",
    )

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embed_fn: Any,
        *,
        collection: str = COLLECTION_NAME,
        min_relevance: float = DEFAULT_MIN_RELEVANCE,
        top_k: int = 10,
    ) -> None:
        """
        Args:
            qdrant_client: Async Qdrant client instance.
            embed_fn: Async callable that converts text to an embedding vector.
            collection: Qdrant collection name for patristic writings.
            min_relevance: Minimum similarity score to include a reference.
            top_k: Maximum number of references to return.
        """
        self._client = qdrant_client
        self._embed = embed_fn
        self._collection = collection
        self._min_relevance = min_relevance
        self._top_k = top_k

    async def find_patristic_references(
        self,
        scripture_ref: str,
        content: str,
    ) -> list[PatristicReference]:
        """
        Find relevant patristic writings for a scripture passage and content.

        Combines the scripture reference with the content to build a query,
        then performs vector search against the patrystyka collection.

        Args:
            scripture_ref: Scripture reference, e.g. "John 14:6".
            content: Theological content or commentary to cross-reference.

        Returns:
            List of PatristicReference objects sorted by relevance.
        """
        query_text = f"Scripture: {scripture_ref}\n\n{content}"

        logger.info(
            "[%s] Searching patristic references for '%s'",
            self.AGENT_ID,
            scripture_ref,
        )

        try:
            embedding = await self._embed(query_text)
        except Exception:
            logger.exception("[%s] Embedding generation failed", self.AGENT_ID)
            return []

        try:
            search_results = await self._client.search(
                collection_name=self._collection,
                query_vector=embedding,
                limit=self._top_k,
                score_threshold=self._min_relevance,
            )
        except Exception:
            logger.exception("[%s] Qdrant search failed", self.AGENT_ID)
            return []

        references: list[PatristicReference] = []
        for hit in search_results:
            payload = hit.payload or {}
            references.append(
                PatristicReference(
                    father_name=payload.get("father_name", "Unknown Father"),
                    work=payload.get("work", "Unknown Work"),
                    quote=payload.get("text", payload.get("quote", "")),
                    relevance_score=round(hit.score, 4),
                )
            )

        logger.info(
            "[%s] Found %d patristic references (min_relevance=%.2f)",
            self.AGENT_ID,
            len(references),
            self._min_relevance,
        )

        return references

    async def find_by_father(
        self,
        father_name: str,
        content: str,
        *,
        top_k: int | None = None,
    ) -> list[PatristicReference]:
        """
        Search for references from a specific Church Father.

        Args:
            father_name: Name of the Father/Doctor to filter by.
            content: Content to search against.
            top_k: Override default top_k for this query.

        Returns:
            List of PatristicReference objects from the specified Father.
        """
        embedding = await self._embed(content)
        limit = top_k or self._top_k

        try:
            search_results = await self._client.search(
                collection_name=self._collection,
                query_vector=embedding,
                query_filter=Filter(
                    must=[
                        FieldCondition(
                            key="father_name",
                            match=MatchAny(any=[father_name]),
                        )
                    ]
                ),
                limit=limit,
                score_threshold=self._min_relevance,
            )
        except Exception:
            logger.exception(
                "[%s] Filtered search for '%s' failed",
                self.AGENT_ID,
                father_name,
            )
            return []

        return [
            PatristicReference(
                father_name=(hit.payload or {}).get("father_name", father_name),
                work=(hit.payload or {}).get("work", "Unknown Work"),
                quote=(hit.payload or {}).get(
                    "text", (hit.payload or {}).get("quote", "")
                ),
                relevance_score=round(hit.score, 4),
            )
            for hit in search_results
        ]

    async def find_consensus_patrum(
        self,
        content: str,
    ) -> list[PatristicReference]:
        """
        Search across multiple Fathers to establish consensus patrum.

        Retrieves references from at least 3 different Fathers to demonstrate
        patristic consensus on a given topic.

        Args:
            content: Theological content to check for consensus.

        Returns:
            List of PatristicReference objects from diverse Fathers.
        """
        embedding = await self._embed(content)

        # Request more results to increase diversity of Fathers
        search_results = await self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            limit=self._top_k * 3,
            score_threshold=self._min_relevance,
        )

        # Deduplicate by Father, keeping the best score per Father
        best_by_father: dict[str, Any] = {}
        for hit in search_results:
            payload = hit.payload or {}
            name = payload.get("father_name", "Unknown")
            if name not in best_by_father or hit.score > best_by_father[name].score:
                best_by_father[name] = hit

        references = [
            PatristicReference(
                father_name=(hit.payload or {}).get("father_name", "Unknown"),
                work=(hit.payload or {}).get("work", "Unknown Work"),
                quote=(hit.payload or {}).get(
                    "text", (hit.payload or {}).get("quote", "")
                ),
                relevance_score=round(hit.score, 4),
            )
            for hit in sorted(
                best_by_father.values(), key=lambda h: h.score, reverse=True
            )
        ]

        logger.info(
            "[%s] Consensus patrum: found references from %d distinct Fathers",
            self.AGENT_ID,
            len(references),
        )

        return references
