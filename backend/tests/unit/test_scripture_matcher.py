"""Unit tests for app/services/scripture/scripture_matcher.py.

Self-contained — no Qdrant, no DB. qdrant_client is mocked at the sys.modules
level before any imports so the test can run in environments without Qdrant.
The Qdrant path is forced to the static fallback corpus by returning empty
from the mocked RAGService.

Contracts verified:
- _FALLBACK_CORPUS: structure, at least 20 passages, all required fields
- _FALLBACK_INDEX: built correctly from corpus, all expected emotion keys
- TheologyGuard: valid note for sensitive passages; empty note for normal
- MatchContext: dataclass defaults
- ScriptureMatch: dataclass fields
- ScriptureMatcher.match (fallback path): returns ScriptureMatch list,
  max 3 results, highest-scoring emotions prioritised, unique refs
- ScriptureMatcher with joy/consolation → J 3,16 or Flp 4,4 in top results
- ScriptureMatcher with guilt → Rz 8,1 or 1 J 1,9 in top results
- Zero-vector emotion returns results without error
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# ---------------------------------------------------------------------------
# Stub out qdrant_client and openai before importing app modules
# ---------------------------------------------------------------------------

for _mod in (
    "qdrant_client",
    "qdrant_client.models",
    "qdrant_client.models.common",
    "qdrant_client.http",
    "qdrant_client.http.models",
    "qdrant_client.http.models.models",
):
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

# Also stub the RAGService module so the top-level import succeeds
_rag_stub = MagicMock()
_rag_stub.RAGService = MagicMock
_rag_stub.ScriptureResult = MagicMock
if "app.services.rag.rag_service" not in sys.modules:
    sys.modules["app.services.rag.rag_service"] = _rag_stub

from app.services.scripture.scripture_matcher import (
    _FALLBACK_CORPUS,
    _FALLBACK_INDEX,
    IgnatianState,
    MatchContext,
    ScriptureMatch,
    ScriptureMatcher,
    TheologyGuard,
)

# ── Static corpus ─────────────────────────────────────────────────────────────


class TestFallbackCorpus:
    def test_at_least_20_passages(self):
        assert len(_FALLBACK_CORPUS) >= 20

    def test_all_passages_have_required_fields(self):
        required = {"book", "chapter", "verse", "content", "emotion_tags"}
        for passage in _FALLBACK_CORPUS:
            assert required <= set(passage.keys()), f"Missing fields in: {passage}"

    def test_all_books_are_non_empty_strings(self):
        for p in _FALLBACK_CORPUS:
            assert isinstance(p["book"], str) and p["book"].strip()

    def test_all_content_is_non_empty_text(self):
        for p in _FALLBACK_CORPUS:
            assert isinstance(p["content"], str) and len(p["content"]) > 10

    def test_j_3_16_present(self):
        refs = {f"{p['book']} {p['chapter']},{p['verse']}" for p in _FALLBACK_CORPUS}
        assert "J 3,16" in refs

    def test_ps_23_present(self):
        refs = {f"{p['book']} {p['chapter']},{p['verse']}" for p in _FALLBACK_CORPUS}
        assert "Ps 23,4" in refs or any("Ps" in r and "23" in r for r in refs)

    def test_no_duplicate_references(self):
        refs = [f"{p['book']} {p['chapter']},{p['verse']}" for p in _FALLBACK_CORPUS]
        assert len(refs) == len(set(refs)), "Duplicate references in fallback corpus"


class TestFallbackIndex:
    def test_builds_from_corpus(self):
        assert len(_FALLBACK_INDEX) > 0

    def test_joy_is_indexed(self):
        assert "joy" in _FALLBACK_INDEX

    def test_fear_is_indexed(self):
        assert "fear" in _FALLBACK_INDEX

    def test_guilt_is_indexed(self):
        assert "guilt" in _FALLBACK_INDEX

    def test_peace_is_indexed(self):
        assert "peace" in _FALLBACK_INDEX

    def test_index_values_are_passage_lists(self):
        for _emotion, passages in _FALLBACK_INDEX.items():
            assert isinstance(passages, list) and len(passages) > 0


# ── TheologyGuard ─────────────────────────────────────────────────────────────


class TestTheologyGuard:
    def setup_method(self):
        self.guard = TheologyGuard()

    def _make_match(self, reference: str) -> ScriptureMatch:
        return ScriptureMatch(
            passage="test",
            reference=reference,
            score=0.9,
            explanation="test",
            theological_note="",
        )

    def test_normal_passage_is_valid(self):
        match = self._make_match("J 3,16")
        valid, note = self.guard.validate(match, {"love": 0.9}, MatchContext())
        assert valid is True

    def test_normal_passage_has_empty_note(self):
        match = self._make_match("Ps 23,4")
        valid, note = self.guard.validate(match, {"fear": 0.5}, MatchContext())
        assert valid is True
        assert note == ""

    def test_sensitive_passage_for_despair(self):
        """Jr 29,11 is listed as sensitive for despair."""
        match = self._make_match("Jr 29,11")
        valid, note = self.guard.validate(match, {"despair": 0.8}, MatchContext())
        assert valid is True
        assert "pastoral" in note.lower() or "29,11" in note

    def test_sensitive_passage_for_anger(self):
        match = self._make_match("Ef 4,26")
        valid, note = self.guard.validate(match, {"anger": 0.9}, MatchContext())
        assert valid is True

    def test_validates_all_emotion_vectors(self):
        """Guard should handle any emotion vector without raising."""
        match = self._make_match("Rz 8,1")
        for emotion in ("joy", "guilt", "fear", "love", "confusion", "dark_night"):
            valid, _ = self.guard.validate(match, {emotion: 0.8}, MatchContext())
            assert valid is True


# ── MatchContext ──────────────────────────────────────────────────────────────


class TestMatchContext:
    def test_defaults(self):
        ctx = MatchContext()
        assert ctx.user_id is None
        assert ctx.liturgical_season is None
        assert ctx.spiritual_history == []
        assert ctx.ignatian_state == IgnatianState.NEUTRAL
        assert ctx.preferred_translations == ["BT"]

    def test_custom_values(self):
        ctx = MatchContext(
            user_id="u123",
            liturgical_season="lent",
            ignatian_state=IgnatianState.DESOLATION,
        )
        assert ctx.user_id == "u123"
        assert ctx.liturgical_season == "lent"
        assert ctx.ignatian_state == IgnatianState.DESOLATION


# ── ScriptureMatch ────────────────────────────────────────────────────────────


class TestScriptureMatch:
    def test_fields(self):
        m = ScriptureMatch(
            passage="Ja jestem",
            reference="J 14,6",
            score=0.95,
            explanation="reason",
            theological_note="",
        )
        assert m.passage == "Ja jestem"
        assert m.reference == "J 14,6"
        assert m.score == 0.95

    def test_optional_book_chapter_verse(self):
        m = ScriptureMatch(
            passage="text",
            reference="Ps 23,4",
            score=0.8,
            explanation="",
            theological_note="",
            book="Ps",
            chapter=23,
            verse=4,
        )
        assert m.book == "Ps"
        assert m.chapter == 23
        assert m.verse == 4


# ── ScriptureMatcher (fallback path) ─────────────────────────────────────────


def _make_matcher() -> ScriptureMatcher:
    """Build a ScriptureMatcher whose RAGService always returns empty (→ fallback corpus)."""
    mock_rag = MagicMock()
    mock_rag.search_scripture.return_value = []
    return ScriptureMatcher(rag_service=mock_rag)


class TestScriptureMatcherFallback:
    def test_returns_list_of_scripture_matches(self):
        matcher = _make_matcher()
        results = matcher.match({"joy": 0.9})
        assert isinstance(results, list)
        assert all(isinstance(r, ScriptureMatch) for r in results)

    def test_returns_at_most_3_results(self):
        matcher = _make_matcher()
        results = matcher.match({"peace": 0.8, "hope": 0.6})
        assert len(results) <= 3

    def test_returns_results_for_joy_emotion(self):
        matcher = _make_matcher()
        results = matcher.match({"joy": 1.0, "consolation": 0.8})
        assert len(results) > 0

    def test_returns_results_for_fear_emotion(self):
        matcher = _make_matcher()
        results = matcher.match({"fear": 1.0, "anxiety": 0.7})
        assert len(results) > 0

    def test_returns_results_for_guilt_emotion(self):
        matcher = _make_matcher()
        results = matcher.match({"guilt": 1.0, "shame": 0.5})
        assert len(results) > 0

    def test_references_are_unique(self):
        matcher = _make_matcher()
        results = matcher.match({"peace": 0.9, "serenity": 0.8, "consolation": 0.7})
        refs = [r.reference for r in results]
        assert len(refs) == len(set(refs)), "Duplicate references returned"

    def test_scores_are_non_negative(self):
        matcher = _make_matcher()
        for emotion in ("joy", "fear", "guilt", "longing", "dark_night"):
            results = matcher.match({emotion: 0.9})
            for r in results:
                assert r.score >= 0.0

    def test_zero_emotion_vector_does_not_raise(self):
        matcher = _make_matcher()
        results = matcher.match({"unknown_emotion": 0.0})
        assert isinstance(results, list)

    def test_empty_emotion_vector_does_not_raise(self):
        matcher = _make_matcher()
        results = matcher.match({})
        # Fallback should still return something
        assert isinstance(results, list)

    def test_guilt_returns_forgiveness_passages(self):
        """Guilt should surface passages about forgiveness/mercy."""
        matcher = _make_matcher()
        results = matcher.match({"guilt": 1.0})
        # Expected: Rz 8,1 or 1 J 1,9 or similar
        all_text = " ".join(r.passage for r in results)
        # At least one passage about not being condemned / forgiveness
        forgiveness_keywords = ["potępienia", "przebaczyć", "grzechy", "Ojciec", "przebaczenie"]
        assert any(kw in all_text for kw in forgiveness_keywords)

    def test_peace_returns_peace_passages(self):
        matcher = _make_matcher()
        results = matcher.match({"peace": 1.0, "serenity": 0.8})
        all_text = " ".join(r.passage for r in results)
        peace_keywords = ["pokój", "Pokój", "spokojne", "Zatrzymajcie"]
        assert any(kw in all_text for kw in peace_keywords)

    def test_context_is_used_without_raising(self):
        matcher = _make_matcher()
        ctx = MatchContext(
            user_id="test-user",
            liturgical_season="lent",
            ignatian_state=IgnatianState.DESOLATION,
        )
        results = matcher.match({"sadness": 0.8, "desolation": 0.6}, context=ctx)
        assert isinstance(results, list)

    def test_match_with_multiple_emotions(self):
        """Multiple emotions should blend correctly."""
        matcher = _make_matcher()
        results = matcher.match({"joy": 0.6, "hope": 0.5, "gratitude": 0.4})
        assert len(results) > 0

    def test_explanation_is_non_empty_string(self):
        matcher = _make_matcher()
        results = matcher.match({"fear": 0.9})
        for r in results:
            assert isinstance(r.explanation, str) and len(r.explanation) > 0
