"""Unit tests for route-level validation sets.

No HTTP, no DB, no LLM — pure data-layer testing.

Contracts verified:
_VALID_MOODS (app/api/routes/journal.py):
- Exactly 10 Polish spiritual moods
- Specific moods present: spokój, radość, wdzięczność, smutek, niepokój,
  nadzieja, zagubienie, miłość, tęsknota, pokuta
- All are non-empty strings
- All are lowercase Polish

_VALID_TRADITIONS (app/api/routes/users.py):
- Exactly 5 spiritual traditions
- Expected: ignatian, carmelite, benedictine, franciscan, dominican
- No duplicates, all lowercase

_VALID_LANGUAGES (app/api/routes/users.py):
- Exactly 8 language codes
- Polish (pl) always present
- Common European languages present: en, de, fr, es, it, pt
- Ukrainian (uk) present — pastoral outreach
- All 2-letter ISO 639-1 codes
- No duplicates
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

for _mod in ["neo4j", "qdrant_client", "qdrant_client.models",
             "jose", "jose.jwt", "jose.exceptions"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.api.routes.journal import _VALID_MOODS
from app.api.routes.users import _VALID_LANGUAGES, _VALID_TRADITIONS

_EXPECTED_MOODS = {
    "spokój", "radość", "wdzięczność", "smutek", "niepokój",
    "nadzieja", "zagubienie", "miłość", "tęsknota", "pokuta",
}
_EXPECTED_TRADITIONS = {"ignatian", "carmelite", "benedictine", "franciscan", "dominican"}
_EXPECTED_LANGUAGES = {"pl", "en", "de", "fr", "es", "it", "pt", "uk"}


# ===========================================================================
# _VALID_MOODS
# ===========================================================================


class TestValidMoods:
    def test_exactly_10_moods(self):
        assert len(_VALID_MOODS) == 10

    def test_all_expected_moods_present(self):
        assert _EXPECTED_MOODS == _VALID_MOODS

    def test_spokój_present(self):
        assert "spokój" in _VALID_MOODS

    def test_radość_present(self):
        assert "radość" in _VALID_MOODS

    def test_wdzięczność_present(self):
        assert "wdzięczność" in _VALID_MOODS

    def test_smutek_present(self):
        assert "smutek" in _VALID_MOODS

    def test_niepokój_present(self):
        assert "niepokój" in _VALID_MOODS

    def test_nadzieja_present(self):
        assert "nadzieja" in _VALID_MOODS

    def test_zagubienie_present(self):
        assert "zagubienie" in _VALID_MOODS

    def test_miłość_present(self):
        assert "miłość" in _VALID_MOODS

    def test_tęsknota_present(self):
        assert "tęsknota" in _VALID_MOODS

    def test_pokuta_present(self):
        # Penance/repentance — essential for Catholic spiritual diary
        assert "pokuta" in _VALID_MOODS

    def test_is_set(self):
        assert isinstance(_VALID_MOODS, (set, frozenset))

    def test_no_duplicates(self):
        assert len(_VALID_MOODS) == len(set(_VALID_MOODS))

    def test_all_are_strings(self):
        for mood in _VALID_MOODS:
            assert isinstance(mood, str), f"Mood {mood!r} is not a string"

    def test_all_non_empty(self):
        for mood in _VALID_MOODS:
            assert mood.strip(), "Empty mood found"

    def test_all_lowercase(self):
        for mood in _VALID_MOODS:
            assert mood == mood.lower(), f"Mood {mood!r} not lowercase"


# ===========================================================================
# _VALID_TRADITIONS
# ===========================================================================


class TestValidTraditions:
    def test_exactly_5_traditions(self):
        assert len(_VALID_TRADITIONS) == 5

    def test_all_expected_traditions(self):
        assert _EXPECTED_TRADITIONS == _VALID_TRADITIONS

    def test_ignatian_present(self):
        assert "ignatian" in _VALID_TRADITIONS

    def test_carmelite_present(self):
        assert "carmelite" in _VALID_TRADITIONS

    def test_benedictine_present(self):
        assert "benedictine" in _VALID_TRADITIONS

    def test_franciscan_present(self):
        assert "franciscan" in _VALID_TRADITIONS

    def test_dominican_present(self):
        assert "dominican" in _VALID_TRADITIONS

    def test_is_set(self):
        assert isinstance(_VALID_TRADITIONS, (set, frozenset))

    def test_no_duplicates(self):
        assert len(_VALID_TRADITIONS) == len(set(_VALID_TRADITIONS))

    def test_all_lowercase(self):
        for t in _VALID_TRADITIONS:
            assert t == t.lower(), f"Tradition {t!r} not lowercase"


# ===========================================================================
# _VALID_LANGUAGES
# ===========================================================================


class TestValidLanguages:
    def test_exactly_8_languages(self):
        assert len(_VALID_LANGUAGES) == 8

    def test_all_expected_languages(self):
        assert _EXPECTED_LANGUAGES == _VALID_LANGUAGES

    def test_polish_present(self):
        assert "pl" in _VALID_LANGUAGES

    def test_english_present(self):
        assert "en" in _VALID_LANGUAGES

    def test_german_present(self):
        assert "de" in _VALID_LANGUAGES

    def test_french_present(self):
        assert "fr" in _VALID_LANGUAGES

    def test_spanish_present(self):
        assert "es" in _VALID_LANGUAGES

    def test_italian_present(self):
        assert "it" in _VALID_LANGUAGES

    def test_portuguese_present(self):
        assert "pt" in _VALID_LANGUAGES

    def test_ukrainian_present(self):
        # Pastoral outreach for Ukrainian users
        assert "uk" in _VALID_LANGUAGES

    def test_is_set(self):
        assert isinstance(_VALID_LANGUAGES, (set, frozenset))

    def test_no_duplicates(self):
        assert len(_VALID_LANGUAGES) == len(set(_VALID_LANGUAGES))

    def test_all_are_2_char_codes(self):
        for lang in _VALID_LANGUAGES:
            assert len(lang) == 2, f"Language code {lang!r} is not 2 characters"

    def test_all_lowercase(self):
        for lang in _VALID_LANGUAGES:
            assert lang == lang.lower(), f"Language code {lang!r} not lowercase"
