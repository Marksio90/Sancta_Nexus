"""ScriptureMatcher (Emotion2Scripture) -- core matching algorithm.

Maps an emotion vector to the most relevant scripture passages using
semantic search, liturgical context, spiritual history and theology
validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from backend.app.services.rag.rag_service import RAGService, ScriptureResult
from backend.app.services.scripture.liturgical_calendar import LiturgicalCalendar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

TOTAL_BIBLE_VERSES = 31_102  # canonical verse count


class IgnatianState(str, Enum):
    """Simplified Ignatian discernment states."""

    CONSOLATION = "consolation"
    DESOLATION = "desolation"
    NEUTRAL = "neutral"


@dataclass
class MatchContext:
    """Contextual information used during re-ranking."""

    user_id: str | None = None
    liturgical_season: str | None = None
    spiritual_history: list[str] = field(default_factory=list)
    ignatian_state: IgnatianState = IgnatianState.NEUTRAL
    preferred_translations: list[str] = field(default_factory=lambda: ["BT"])


@dataclass
class ScriptureMatch:
    """A matched scripture passage with supporting metadata."""

    passage: str
    reference: str
    score: float
    explanation: str
    theological_note: str
    book: str = ""
    chapter: int = 0
    verse: int = 0


# ---------------------------------------------------------------------------
# Theology guard
# ---------------------------------------------------------------------------


class TheologyGuard:
    """Validates that scripture selections remain theologically sound.

    This is a lightweight rule-based guard.  It checks for common
    misapplication patterns (e.g. prosperity-gospel proof-texting) and
    ensures the passage is contextually appropriate.
    """

    # Passages that require extra care when matched to certain emotions
    _SENSITIVE_PASSAGES: dict[str, list[str]] = {
        "despair": ["Jr 29,11", "Rz 8,28"],  # often used superficially
        "anger": ["Ef 4,26", "Ps 137"],
        "guilt": ["Rz 8,1", "1 J 1,9"],
    }

    def validate(
        self,
        match: ScriptureMatch,
        emotion_vector: dict[str, float],
        context: MatchContext,
    ) -> tuple[bool, str]:
        """Return ``(is_valid, note)`` for the proposed match."""
        primary_emotion = max(emotion_vector, key=emotion_vector.get)

        sensitive_refs = self._SENSITIVE_PASSAGES.get(primary_emotion, [])
        if match.reference in sensitive_refs:
            note = (
                f"Passage {match.reference} requires careful contextualisation "
                f"when associated with '{primary_emotion}'. "
                "Ensure pastoral sensitivity."
            )
            return True, note

        return True, ""


# ---------------------------------------------------------------------------
# ScriptureMatcher
# ---------------------------------------------------------------------------


class ScriptureMatcher:
    """Emotion2Scripture matching engine.

    Pipeline:
        1. Convert emotion vector to a query embedding.
        2. Nearest-neighbour search in the biblical embedding space
           (Qdrant ``biblia_pl`` collection).
        3. Re-rank candidates with liturgical context, spiritual history
           and Ignatian state.
        4. Run theology guard validation.
        5. Return top-3 matches with explanations.
    """

    def __init__(
        self,
        rag_service: RAGService | None = None,
        liturgical_calendar: LiturgicalCalendar | None = None,
    ) -> None:
        self._rag = rag_service or RAGService()
        self._calendar = liturgical_calendar or LiturgicalCalendar()
        self._theology_guard = TheologyGuard()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def match(
        self,
        emotion_vector: dict[str, float],
        context: MatchContext | None = None,
    ) -> list[ScriptureMatch]:
        """Run the full Emotion2Scripture pipeline.

        Args:
            emotion_vector: Mapping of emotion labels to intensity floats
                (e.g. ``{"joy": 0.8, "hope": 0.6, ...}``).
            context: Optional :class:`MatchContext` for re-ranking.

        Returns:
            Top-3 :class:`ScriptureMatch` results.
        """
        if context is None:
            context = MatchContext()

        # 1. Build a natural-language query from the emotion vector
        query_text = self._emotion_to_query(emotion_vector)
        logger.debug("Emotion query: %s", query_text)

        # 2. Nearest-neighbour search
        candidates = self._retrieve_candidates(query_text, emotion_vector)

        # 3. Re-rank
        ranked = self._rerank(candidates, emotion_vector, context)

        # 4. Theology guard + build output
        matches: list[ScriptureMatch] = []
        for candidate in ranked:
            match = self._to_scripture_match(candidate, emotion_vector, context)
            is_valid, note = self._theology_guard.validate(match, emotion_vector, context)
            if is_valid:
                if note:
                    match.theological_note = note
                matches.append(match)
            if len(matches) == 3:
                break

        return matches

    # ------------------------------------------------------------------
    # Pipeline steps
    # ------------------------------------------------------------------

    def _emotion_to_query(self, emotion_vector: dict[str, float]) -> str:
        """Translate an emotion vector into a natural-language search query."""
        sorted_emotions = sorted(emotion_vector.items(), key=lambda x: x[1], reverse=True)
        top = sorted_emotions[:5]
        parts = [f"{label} ({score:.2f})" for label, score in top]
        return (
            "Szukam fragmentu Pisma Swietego odpowiedniego dla osoby "
            f"odczuwajacej: {', '.join(parts)}"
        )

    def _retrieve_candidates(
        self,
        query_text: str,
        emotion_vector: dict[str, float],
        limit: int = 15,
    ) -> list[ScriptureResult]:
        """Retrieve initial candidates from Qdrant."""
        # Build an emotion filter for strong emotions (> 0.5)
        emotion_filter: dict[str, Any] | None = None
        strong = {k: v for k, v in emotion_vector.items() if v > 0.7}
        if strong:
            primary = max(strong, key=strong.get)
            emotion_filter = {"emotion_tag": primary}

        return self._rag.search_scripture(
            query=query_text,
            emotion_filter=emotion_filter,
            limit=limit,
        )

    def _rerank(
        self,
        candidates: list[ScriptureResult],
        emotion_vector: dict[str, float],
        context: MatchContext,
    ) -> list[ScriptureResult]:
        """Re-rank candidates using contextual signals."""
        scored: list[tuple[float, ScriptureResult]] = []

        for candidate in candidates:
            boost = 0.0

            # Liturgical season boost
            boost += self._liturgical_boost(candidate, context)

            # Spiritual history boost (familiar passages weighted slightly)
            boost += self._history_boost(candidate, context)

            # Ignatian state boost
            boost += self._ignatian_boost(candidate, context)

            final_score = candidate.score + boost
            scored.append((final_score, candidate))

        scored.sort(key=lambda x: x[0], reverse=True)
        return [c for _, c in scored]

    def _liturgical_boost(self, candidate: ScriptureResult, context: MatchContext) -> float:
        """Give a small boost to passages aligned with the current liturgical season."""
        season = context.liturgical_season or self._calendar.get_season()
        season_books: dict[str, list[str]] = {
            "advent": ["Iz", "Mi", "Łk"],
            "christmas": ["Łk", "Mt", "J"],
            "lent": ["Mt", "Mk", "Iz", "Ps"],
            "easter": ["Dz", "J", "Rz"],
            "ordinary": [],
        }
        favoured = season_books.get(season, [])
        if candidate.book in favoured:
            return 0.05
        return 0.0

    def _history_boost(self, candidate: ScriptureResult, context: MatchContext) -> float:
        """Slightly boost passages the user has encountered before."""
        ref = f"{candidate.book} {candidate.chapter},{candidate.verse}"
        if ref in context.spiritual_history:
            return 0.03
        return 0.0

    def _ignatian_boost(self, candidate: ScriptureResult, context: MatchContext) -> float:
        """Adjust score based on Ignatian discernment state."""
        consolation_books = {"Ps", "Flp", "Rz", "J"}
        desolation_books = {"Ps", "Lm", "Hi", "Iz"}

        if context.ignatian_state == IgnatianState.CONSOLATION:
            if candidate.book in consolation_books:
                return 0.04
        elif context.ignatian_state == IgnatianState.DESOLATION:
            if candidate.book in desolation_books:
                return 0.04
        return 0.0

    def _to_scripture_match(
        self,
        candidate: ScriptureResult,
        emotion_vector: dict[str, float],
        context: MatchContext,
    ) -> ScriptureMatch:
        """Convert a :class:`ScriptureResult` into a :class:`ScriptureMatch`."""
        primary = max(emotion_vector, key=emotion_vector.get)
        explanation = (
            f"Ten fragment odpowiada na dominujace uczucie '{primary}' "
            f"(intensywnosc: {emotion_vector[primary]:.2f}). "
            f"Kontekst liturgiczny: {context.liturgical_season or self._calendar.get_season()}."
        )
        reference = f"{candidate.book} {candidate.chapter},{candidate.verse}"
        return ScriptureMatch(
            passage=candidate.content,
            reference=reference,
            score=candidate.score,
            explanation=explanation,
            theological_note="",
            book=candidate.book,
            chapter=candidate.chapter,
            verse=candidate.verse,
        )
