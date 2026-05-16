"""ScriptureMatcher (Emotion2Scripture) -- core matching algorithm.

Maps an emotion vector to the most relevant scripture passages using
semantic search, liturgical context, spiritual history and theology
validation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

from app.services.rag.rag_service import RAGService, ScriptureResult
from app.services.scripture.liturgical_calendar import LiturgicalCalendar

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Static fallback corpus — used when Qdrant is unavailable
# Curated passages mapped to primary spiritual/emotional categories
# ---------------------------------------------------------------------------

_FALLBACK_CORPUS: list[dict] = [
    # joy / gratitude / consolation
    {"book": "Flp", "chapter": 4, "verse": 4, "content": "Radujcie się zawsze w Panu; jeszcze raz powtarzam: radujcie się!", "emotion_tags": ["joy", "gratitude", "consolation"]},
    {"book": "Ps", "chapter": 34, "verse": 9, "content": "Skosztujcie i zobaczcie, jak dobry jest Pan; szczęśliwy człowiek, który się do Niego ucieka.", "emotion_tags": ["joy", "trust", "hope", "consolation"]},
    {"book": "Rz", "chapter": 8, "verse": 28, "content": "Wiemy też, że Bóg z tymi, którzy Go miłują, współdziała we wszystkim dla ich dobra.", "emotion_tags": ["hope", "trust", "consolation", "gratitude"]},
    {"book": "1 Tes", "chapter": 5, "verse": 18, "content": "W każdym położeniu dziękujcie, taka jest bowiem wola Boża w Jezusie Chrystusie względem was.", "emotion_tags": ["gratitude", "joy", "consolation"]},
    # sadness / desolation / grief
    {"book": "Ps", "chapter": 34, "verse": 19, "content": "Pan jest blisko ludzi ze złamanym sercem i ocala tych, których duch jest zgnębiony.", "emotion_tags": ["sadness", "grief", "loneliness", "desolation"]},
    {"book": "Mt", "chapter": 5, "verse": 4, "content": "Błogosławieni, którzy się smucą, albowiem oni będą pocieszeni.", "emotion_tags": ["sadness", "grief", "desolation"]},
    {"book": "Ps", "chapter": 22, "verse": 25, "content": "Bo On nie gardzi ani się nie brzydzi nędzą biedaka, ani nie ukrywa przed nim swego oblicza, ale wysłuchuje go, gdy ten woła do Niego.", "emotion_tags": ["sadness", "loneliness", "desolation", "dark_night"]},
    {"book": "Lm", "chapter": 3, "verse": 25, "content": "Dobry jest Pan dla tych, co w Nim ufają, dla duszy, która Go szuka.", "emotion_tags": ["sadness", "desolation", "seeking", "hope"]},
    # fear / anxiety
    {"book": "Iz", "chapter": 41, "verse": 10, "content": "Nie lękaj się, bo Ja jestem z tobą; nie trwóż się, bom Ja twoim Bogiem.", "emotion_tags": ["fear", "anxiety", "dread"]},
    {"book": "J", "chapter": 14, "verse": 27, "content": "Pokój zostawiam wam, pokój mój daję wam. Nie tak jak daje świat, Ja wam daję. Niech się nie trwoży serce wasze ani się lęka.", "emotion_tags": ["fear", "anxiety", "peace", "serenity"]},
    {"book": "Flp", "chapter": 4, "verse": 7, "content": "A pokój Boży, który przewyższa wszelki umysł, będzie strzegł waszych serc i myśli w Chrystusie Jezusie.", "emotion_tags": ["anxiety", "fear", "peace", "serenity"]},
    {"book": "Ps", "chapter": 23, "verse": 4, "content": "Chociażby chodził ciemną doliną, zła się nie ulęknę, bo Ty jesteś ze mną.", "emotion_tags": ["fear", "dark_night", "trust", "consolation"]},
    # guilt / shame / remorse
    {"book": "1 J", "chapter": 1, "verse": 9, "content": "Jeśli wyznajemy nasze grzechy, Bóg jest wierny i sprawiedliwy, aby nam przebaczyć grzechy.", "emotion_tags": ["guilt", "shame", "remorse"]},
    {"book": "Rz", "chapter": 8, "verse": 1, "content": "Teraz jednak dla tych, którzy są w Chrystusie Jezusie, nie ma już potępienia.", "emotion_tags": ["guilt", "shame", "remorse", "forgiveness"]},
    {"book": "Iz", "chapter": 43, "verse": 25, "content": "Ja, jedynie Ja, przekreślam twe przestępstwa przez wzgląd na siebie i nie wspominam twoich grzechów.", "emotion_tags": ["guilt", "remorse", "forgiveness"]},
    {"book": "Łk", "chapter": 15, "verse": 20, "content": "Jeszcze był daleko, gdy ojciec go ujrzał i wzruszył się głęboko; wybiegł naprzeciw niego, rzucił mu się na szyję i ucałował go.", "emotion_tags": ["guilt", "remorse", "forgiveness", "love"]},
    # longing / seeking
    {"book": "Ps", "chapter": 42, "verse": 2, "content": "Jak łania pragnie wody ze strumieni, tak dusza moja pragnie Ciebie, Boże.", "emotion_tags": ["longing", "seeking", "awe", "reverence"]},
    {"book": "Mt", "chapter": 7, "verse": 7, "content": "Proście, a będzie wam dane; szukajcie, a znajdziecie; kołaczcie, a otworzą wam.", "emotion_tags": ["longing", "hope", "seeking", "trust"]},
    {"book": "Ap", "chapter": 3, "verse": 20, "content": "Oto stoję u drzwi i kołaczę: jeśli kto posłyszy mój głos i drzwi otworzy, wejdę do niego i będę z nim wieczerzał, a on ze Mną.", "emotion_tags": ["longing", "seeking", "love", "consolation"]},
    # peace / serenity / contemplation
    {"book": "J", "chapter": 15, "verse": 5, "content": "Ja jestem krzewem winnym, wy - latoroślami. Kto trwa we Mnie, a Ja w nim, ten przynosi owoc obfity.", "emotion_tags": ["peace", "serenity", "consolation", "love"]},
    {"book": "Mt", "chapter": 11, "verse": 28, "content": "Przyjdźcie do Mnie wszyscy, którzy utrudzeni i obciążeni jesteście, a Ja was pokrzepię.", "emotion_tags": ["peace", "serenity", "sadness", "exhaustion"]},
    {"book": "Ps", "chapter": 46, "verse": 11, "content": "Zatrzymajcie się i wiedzcie, że Ja jestem Bogiem.", "emotion_tags": ["peace", "serenity", "awe", "contemplation"]},
    {"book": "Ps", "chapter": 131, "verse": 2, "content": "Spokojne i ciche jest moje serce, jak niemowlę u matki swojej, jak niemowlę — takie jest moje serce.", "emotion_tags": ["peace", "serenity", "consolation", "humility"]},
    # love / compassion
    {"book": "J", "chapter": 3, "verse": 16, "content": "Tak bowiem Bóg umiłował świat, że Syna swego Jednorodzonego dał.", "emotion_tags": ["love", "awe", "gratitude", "consolation"]},
    {"book": "Rz", "chapter": 8, "verse": 38, "content": "I jestem pewien, że ani śmierć, ani życie, ani aniołowie... nie zdoła nas odłączyć od miłości Boga.", "emotion_tags": ["love", "consolation", "fear", "hope"]},
    {"book": "1 Kor", "chapter": 13, "verse": 8, "content": "Miłość nigdy nie ustaje.", "emotion_tags": ["love", "hope", "consolation"]},
    # hope / dark night
    {"book": "Jr", "chapter": 29, "verse": 11, "content": "Bo Ja wiem, jakie mam względem was zamiary — mówi Pan — zamiary pełne pokoju, a nie zguby, by zapewnić wam przyszłość i nadzieję.", "emotion_tags": ["hope", "desolation", "dark_night", "seeking"]},
    {"book": "Rz", "chapter": 5, "verse": 5, "content": "A nadzieja nie hańbi, bo miłość Boża rozlana jest w sercach naszych przez Ducha Świętego.", "emotion_tags": ["hope", "love", "consolation"]},
    {"book": "Iz", "chapter": 40, "verse": 31, "content": "Lecz ci, co zaufali Panu, odzyskują siły, otrzymują skrzydła jak orły.", "emotion_tags": ["hope", "desolation", "dark_night", "trust"]},
    # doubt / confusion
    {"book": "Mk", "chapter": 9, "verse": 24, "content": "Wierzę, zaradź memu niedowiarstwu!", "emotion_tags": ["doubt", "confusion", "seeking", "trust"]},
    {"book": "J", "chapter": 20, "verse": 27, "content": "Podnieś tutaj swój palec i patrz na moje ręce. Podnieś rękę i włóż w mój bok, i nie bądź niedowiarkiem, lecz wierzącym!", "emotion_tags": ["doubt", "confusion", "trust"]},
]


def _build_fallback_index() -> dict[str, list[dict]]:
    """Build an inverted index from emotion tag to passage list."""
    index: dict[str, list[dict]] = {}
    for passage in _FALLBACK_CORPUS:
        for tag in passage["emotion_tags"]:
            index.setdefault(tag, []).append(passage)
    return index


_FALLBACK_INDEX: dict[str, list[dict]] = _build_fallback_index()


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

TOTAL_BIBLE_VERSES = 31_102  # canonical verse count


class IgnatianState(StrEnum):
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

        # Fallback when Qdrant is offline or collection is empty
        if not candidates:
            logger.info("No Qdrant results — using static fallback corpus.")
            return self._fallback_match(emotion_vector, context)

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

    def _fallback_match(
        self,
        emotion_vector: dict[str, float],
        context: MatchContext,
    ) -> list[ScriptureMatch]:
        """Return passages from the static corpus when Qdrant is offline.

        Scores each passage by summing the emotion intensities for its tags,
        picks the top-3 without repetition.
        """
        scored: list[tuple[float, dict]] = []
        seen_refs: set[str] = set()

        for passage in _FALLBACK_CORPUS:
            score = sum(emotion_vector.get(tag, 0.0) for tag in passage["emotion_tags"])
            ref = f"{passage['book']} {passage['chapter']},{passage['verse']}"
            scored.append((score, passage))

        scored.sort(key=lambda x: x[0], reverse=True)

        results: list[ScriptureMatch] = []
        for score, passage in scored:
            ref = f"{passage['book']} {passage['chapter']},{passage['verse']}"
            if ref in seen_refs:
                continue
            seen_refs.add(ref)

            primary = max(emotion_vector, key=emotion_vector.get) if emotion_vector else "peace"
            match = ScriptureMatch(
                passage=passage["content"],
                reference=ref,
                score=round(score, 4),
                explanation=(
                    f"Fragment wybrany na podstawie dominującego stanu: '{primary}'. "
                    f"Kontekst: {context.liturgical_season or self._calendar.get_season()}."
                ),
                theological_note="",
                book=passage["book"],
                chapter=passage["chapter"],
                verse=passage["verse"],
            )
            results.append(match)
            if len(results) == 3:
                break

        return results

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
        elif context.ignatian_state == IgnatianState.DESOLATION and candidate.book in desolation_books:
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
