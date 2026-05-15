"""Unit tests for Bible route helper functions (4 senses of Scripture).

No HTTP, no DB, no LLM — pure function testing.

The four senses follow the patristic exegesis tradition:
  literal (historical) → allegorical (typological) →
  moral (tropological) → anagogical (eschatological)

Contracts verified for each _generate_*_sense helper:
- With context: returns a non-empty Polish string starting with
  the correct sense name
- Without context: returns a Polish error/fallback message
- Question is embedded in the literal sense output
- All return strings (not None)
- Fallback strings mention brak kontekstu
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

for _mod in ["neo4j", "qdrant_client", "qdrant_client.models",
             "jose", "jose.jwt", "jose.exceptions"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.api.routes.bible import (
    _generate_allegorical_sense,
    _generate_anagogical_sense,
    _generate_literal_sense,
    _generate_moral_sense,
)

_QUESTION = "Co oznacza Psalm 23 dla wierzącego?"
_CONTEXT = "Pan jest moim pasterzem, nie brak mi niczego."


# ===========================================================================
# _generate_literal_sense
# ===========================================================================


class TestLiteralSense:
    def test_with_context_returns_string(self):
        result = _generate_literal_sense(_QUESTION, _CONTEXT)
        assert isinstance(result, str)

    def test_with_context_non_empty(self):
        result = _generate_literal_sense(_QUESTION, _CONTEXT)
        assert len(result.strip()) > 20

    def test_with_context_starts_with_sens_literalny(self):
        result = _generate_literal_sense(_QUESTION, _CONTEXT)
        assert result.lower().startswith("sens literalny")

    def test_with_context_contains_question(self):
        result = _generate_literal_sense(_QUESTION, _CONTEXT)
        assert _QUESTION in result

    def test_without_context_returns_fallback(self):
        result = _generate_literal_sense(_QUESTION, "")
        assert isinstance(result, str)
        assert len(result.strip()) > 10

    def test_without_context_mentions_brak(self):
        result = _generate_literal_sense(_QUESTION, "")
        assert "brak" in result.lower() or "kontekst" in result.lower()


# ===========================================================================
# _generate_allegorical_sense
# ===========================================================================


class TestAllegoricalSense:
    def test_with_context_returns_string(self):
        result = _generate_allegorical_sense(_QUESTION, _CONTEXT)
        assert isinstance(result, str)

    def test_with_context_non_empty(self):
        result = _generate_allegorical_sense(_QUESTION, _CONTEXT)
        assert len(result.strip()) > 20

    def test_with_context_starts_with_sens_alegoryczny(self):
        result = _generate_allegorical_sense(_QUESTION, _CONTEXT)
        assert result.lower().startswith("sens alegoryczny")

    def test_with_context_mentions_chrystusa(self):
        # Allegorical sense references Christ and the Church
        result = _generate_allegorical_sense(_QUESTION, _CONTEXT)
        assert "Chrystus" in result or "chrystus" in result.lower()

    def test_without_context_returns_fallback(self):
        result = _generate_allegorical_sense(_QUESTION, "")
        assert isinstance(result, str)
        assert "brak" in result.lower() or "kontekst" in result.lower()


# ===========================================================================
# _generate_moral_sense
# ===========================================================================


class TestMoralSense:
    def test_with_context_returns_string(self):
        result = _generate_moral_sense(_QUESTION, _CONTEXT)
        assert isinstance(result, str)

    def test_with_context_non_empty(self):
        result = _generate_moral_sense(_QUESTION, _CONTEXT)
        assert len(result.strip()) > 20

    def test_with_context_starts_with_sens_moralny(self):
        result = _generate_moral_sense(_QUESTION, _CONTEXT)
        assert result.lower().startswith("sens moralny")

    def test_with_context_mentions_nawrocenie(self):
        # Moral sense calls to conversion/transformation
        result = _generate_moral_sense(_QUESTION, _CONTEXT)
        assert "nawróc" in result.lower() or "nawroceni" in result.lower() or "przemian" in result.lower()

    def test_without_context_returns_fallback(self):
        result = _generate_moral_sense(_QUESTION, "")
        assert isinstance(result, str)
        assert "brak" in result.lower() or "kontekst" in result.lower()


# ===========================================================================
# _generate_anagogical_sense
# ===========================================================================


class TestAnagogicalSense:
    def test_with_context_returns_string(self):
        result = _generate_anagogical_sense(_QUESTION, _CONTEXT)
        assert isinstance(result, str)

    def test_with_context_non_empty(self):
        result = _generate_anagogical_sense(_QUESTION, _CONTEXT)
        assert len(result.strip()) > 20

    def test_with_context_starts_with_sens_anagogiczny(self):
        result = _generate_anagogical_sense(_QUESTION, _CONTEXT)
        assert result.lower().startswith("sens anagogiczny")

    def test_with_context_mentions_eschatologia(self):
        # Anagogical sense points to eschatological realities
        result = _generate_anagogical_sense(_QUESTION, _CONTEXT)
        assert "eschatolog" in result.lower() or "zbawieni" in result.lower() or "wieczn" in result.lower()

    def test_without_context_returns_fallback(self):
        result = _generate_anagogical_sense(_QUESTION, "")
        assert isinstance(result, str)
        assert "brak" in result.lower() or "kontekst" in result.lower()


# ===========================================================================
# Cross-sense contract: all return distinct values with same inputs
# ===========================================================================


class TestFourSensesDistinct:
    def test_all_four_senses_differ_with_same_context(self):
        results = [
            _generate_literal_sense(_QUESTION, _CONTEXT),
            _generate_allegorical_sense(_QUESTION, _CONTEXT),
            _generate_moral_sense(_QUESTION, _CONTEXT),
            _generate_anagogical_sense(_QUESTION, _CONTEXT),
        ]
        assert len(set(results)) == 4, "All four senses must produce distinct output"

    def test_all_four_fallbacks_differ_without_context(self):
        results = [
            _generate_literal_sense(_QUESTION, ""),
            _generate_allegorical_sense(_QUESTION, ""),
            _generate_moral_sense(_QUESTION, ""),
            _generate_anagogical_sense(_QUESTION, ""),
        ]
        assert len(set(results)) == 4, "All four fallbacks must be distinct"
