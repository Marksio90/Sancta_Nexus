"""
MagisteriumValidator (A-016) - RAG-based validation against Magisterium sources.

Validates content against the Catechism of the Catholic Church, Vatican II
documents, and papal encyclicals using vector similarity search in Qdrant.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from qdrant_client import AsyncQdrantClient
from qdrant_client.models import Filter, FieldCondition, MatchValue

logger = logging.getLogger(__name__)

ALIGNMENT_THRESHOLD = 0.82
COLLECTION_NAME = "magisterium"


@dataclass(frozen=True, slots=True)
class ValidationResult:
    """Result of Magisterium validation."""

    is_valid: bool
    confidence: float
    issues: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)


class MagisteriumValidator:
    """
    A-016: Validates theological content against the Catholic Magisterium.

    Performs RAG-based similarity search against authoritative Church documents
    including the Catechism, Vatican II constitutions/decrees, and papal
    encyclicals stored in a Qdrant vector collection.
    """

    AGENT_ID = "A-016"
    AGENT_NAME = "MagisteriumValidator"

    # Source categories for filtering
    SOURCE_CATEGORIES = (
        "catechism",
        "vatican_ii",
        "papal_encyclical",
        "apostolic_constitution",
        "apostolic_exhortation",
    )

    def __init__(
        self,
        qdrant_client: AsyncQdrantClient,
        embed_fn: Any,
        *,
        collection: str = COLLECTION_NAME,
        threshold: float = ALIGNMENT_THRESHOLD,
        top_k: int = 10,
    ) -> None:
        """
        Args:
            qdrant_client: Async Qdrant client instance.
            embed_fn: Async callable that converts text to an embedding vector.
            collection: Qdrant collection name.
            threshold: Minimum cosine similarity for alignment.
            top_k: Number of nearest neighbours to retrieve.
        """
        self._client = qdrant_client
        self._embed = embed_fn
        self._collection = collection
        self._threshold = threshold
        self._top_k = top_k

    async def validate(self, content: str) -> ValidationResult:
        """
        Validate content against the Magisterium corpus.

        Embeds the input content and searches for the closest matches in the
        magisterium vector store. If the top matches exceed the alignment
        threshold the content is considered valid.

        Args:
            content: The theological content to validate.

        Returns:
            ValidationResult with alignment score, any issues, and references.
        """
        logger.info(
            "[%s] Starting Magisterium validation (threshold=%.2f)",
            self.AGENT_ID,
            self._threshold,
        )

        try:
            embedding = await self._embed(content)
        except Exception:
            logger.exception("[%s] Embedding generation failed", self.AGENT_ID)
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=["Embedding generation failed; cannot validate content."],
            )

        try:
            search_results = await self._client.search(
                collection_name=self._collection,
                query_vector=embedding,
                limit=self._top_k,
                score_threshold=0.0,
            )
        except Exception:
            logger.exception("[%s] Qdrant search failed", self.AGENT_ID)
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=["Vector search failed; cannot validate content."],
            )

        if not search_results:
            logger.warning("[%s] No results returned from Qdrant", self.AGENT_ID)
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=["No matching documents found in the Magisterium corpus."],
            )

        # Compute alignment metrics
        scores = [hit.score for hit in search_results]
        top_score = scores[0]
        avg_score = sum(scores) / len(scores)
        aligned_count = sum(1 for s in scores if s >= self._threshold)

        # Collect references from payload
        references: list[str] = []
        for hit in search_results:
            payload = hit.payload or {}
            source = payload.get("source", "Unknown source")
            paragraph = payload.get("paragraph", "")
            ref_label = f"{source}"
            if paragraph:
                ref_label += f", {paragraph}"
            if hit.score >= self._threshold:
                references.append(ref_label)

        # Determine validity
        is_valid = top_score >= self._threshold and aligned_count >= 1
        confidence = round(min(top_score, 1.0), 4)

        issues: list[str] = []
        if not is_valid:
            issues.append(
                f"Top similarity score {top_score:.4f} is below "
                f"threshold {self._threshold}."
            )
        if aligned_count == 0:
            issues.append(
                "No retrieved documents exceed the alignment threshold; "
                "content may diverge from Magisterium teaching."
            )
        if avg_score < self._threshold * 0.8:
            issues.append(
                f"Average similarity ({avg_score:.4f}) is significantly "
                f"below threshold; content may contain novel claims."
            )

        logger.info(
            "[%s] Validation complete: valid=%s confidence=%.4f "
            "aligned=%d/%d references=%d",
            self.AGENT_ID,
            is_valid,
            confidence,
            aligned_count,
            len(scores),
            len(references),
        )

        return ValidationResult(
            is_valid=is_valid,
            confidence=confidence,
            issues=issues,
            references=references,
        )

    async def validate_with_category(
        self,
        content: str,
        category: str,
    ) -> ValidationResult:
        """
        Validate content against a specific Magisterium source category.

        Args:
            content: The theological content to validate.
            category: One of SOURCE_CATEGORIES to filter by.

        Returns:
            ValidationResult scoped to the requested category.
        """
        if category not in self.SOURCE_CATEGORIES:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[
                    f"Unknown category '{category}'. "
                    f"Valid categories: {', '.join(self.SOURCE_CATEGORIES)}"
                ],
            )

        embedding = await self._embed(content)

        search_results = await self._client.search(
            collection_name=self._collection,
            query_vector=embedding,
            query_filter=Filter(
                must=[
                    FieldCondition(
                        key="category",
                        match=MatchValue(value=category),
                    )
                ]
            ),
            limit=self._top_k,
            score_threshold=0.0,
        )

        if not search_results:
            return ValidationResult(
                is_valid=False,
                confidence=0.0,
                issues=[f"No documents found in category '{category}'."],
            )

        scores = [hit.score for hit in search_results]
        top_score = scores[0]
        is_valid = top_score >= self._threshold

        references = [
            (hit.payload or {}).get("source", "Unknown")
            for hit in search_results
            if hit.score >= self._threshold
        ]

        issues = []
        if not is_valid:
            issues.append(
                f"Content does not align with '{category}' sources "
                f"(top score: {top_score:.4f})."
            )

        return ValidationResult(
            is_valid=is_valid,
            confidence=round(min(top_score, 1.0), 4),
            issues=issues,
            references=references,
        )
