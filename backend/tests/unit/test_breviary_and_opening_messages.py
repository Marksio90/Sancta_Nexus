"""Unit tests for breviary constants and reflection assistant opening messages.

No HTTP calls, no DB, no LLM — pure data-layer testing.

Contracts verified:
_HOURS (breviary):
- Exactly 3 canonical hours: lauds, vespers, compline
- All have: name, latin, time, opening, psalm_ref, psalm_text, reading,
  reading_ref, responsory, canticle, canticle_ref, closing
- All openings use the Ps 70,2 Deus in Adiutorium formula
- Lauds uses Benedictus canticle, Vespers uses Magnificat, Compline uses Nunc Dimittis
- All psalm texts are non-empty multi-line strings

_SEASON_LABELS (breviary):
- Exactly 5 seasons: advent, christmas, lent, easter, ordinary
- All values are non-empty Polish strings
- Specific Polish labels correct

_OPENING_MESSAGES (reflection_assistant):
- Exactly 5 traditions: ignatian, carmelite, benedictine, franciscan, dominican
- All are non-empty strings ending with a question mark
- Tradition-specific vocabulary present
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

for _mod in ["neo4j", "qdrant_client", "qdrant_client.models",
             "jose", "jose.jwt", "jose.exceptions"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.api.routes.breviary import _HOURS, _SEASON_LABELS
from app.api.routes.reflection_assistant import _OPENING_MESSAGES

_REQUIRED_HOUR_FIELDS = {
    "name", "latin", "time", "opening",
    "psalm_ref", "psalm_text", "reading", "reading_ref",
    "responsory", "canticle", "canticle_ref", "closing",
}

_DEU_IN_ADJ = "Boże, wejrzyj ku wspomożeniu memu"


# ===========================================================================
# _HOURS catalog
# ===========================================================================


class TestHoursCatalog:
    def test_exactly_3_hours(self):
        assert len(_HOURS) == 3

    def test_lauds_present(self):
        assert "lauds" in _HOURS

    def test_vespers_present(self):
        assert "vespers" in _HOURS

    def test_compline_present(self):
        assert "compline" in _HOURS

    def test_all_have_required_fields(self):
        for hour, data in _HOURS.items():
            missing = _REQUIRED_HOUR_FIELDS - set(data.keys())
            assert not missing, f"{hour} missing: {missing}"

    def test_all_openings_use_deus_in_adiutorium(self):
        for hour, data in _HOURS.items():
            assert _DEU_IN_ADJ in data["opening"], f"{hour} missing Deus in Adiutorium"

    def test_lauds_polish_name(self):
        assert _HOURS["lauds"]["name"] == "Jutrznia"

    def test_vespers_polish_name(self):
        assert _HOURS["vespers"]["name"] == "Nieszpory"

    def test_compline_polish_name(self):
        assert _HOURS["compline"]["name"] == "Kompleta"

    def test_lauds_latin_is_laudes(self):
        assert _HOURS["lauds"]["latin"] == "Laudes"

    def test_vespers_latin_is_vesperae(self):
        assert "Vesper" in _HOURS["vespers"]["latin"]

    def test_compline_latin_is_completorium(self):
        assert "Complet" in _HOURS["compline"]["latin"]

    def test_lauds_canticle_is_benedictus(self):
        assert "Benedictus" in _HOURS["lauds"]["canticle_ref"]

    def test_vespers_canticle_is_magnificat(self):
        assert "Magnificat" in _HOURS["vespers"]["canticle_ref"]

    def test_compline_canticle_is_nunc_dimittis(self):
        assert "Nunc Dimittis" in _HOURS["compline"]["canticle_ref"]

    def test_lauds_psalm_ref_is_ps63(self):
        assert "Ps 63" in _HOURS["lauds"]["psalm_ref"]

    def test_vespers_psalm_ref_is_ps141(self):
        assert "Ps 141" in _HOURS["vespers"]["psalm_ref"]

    def test_compline_psalm_ref_is_ps91(self):
        assert "Ps 91" in _HOURS["compline"]["psalm_ref"]

    def test_all_psalm_texts_are_multiline(self):
        for hour, data in _HOURS.items():
            assert "\n" in data["psalm_text"], f"{hour} psalm_text not multiline"

    def test_all_psalm_texts_non_empty(self):
        for _hour, data in _HOURS.items():
            assert len(data["psalm_text"].strip()) > 50

    def test_vespers_magnificat_canticle_text(self):
        assert "Wielbi dusza moja Pana" in _HOURS["vespers"]["canticle"]

    def test_compline_nunc_dimittis_canticle_text(self):
        assert "pokoju" in _HOURS["compline"]["canticle"].lower()

    def test_lauds_benedictus_canticle_text(self):
        assert "Błogosławiony" in _HOURS["lauds"]["canticle"]

    def test_all_closings_non_empty(self):
        for _hour, data in _HOURS.items():
            assert len(data["closing"].strip()) > 20

    def test_all_readings_non_empty(self):
        for _hour, data in _HOURS.items():
            assert len(data["reading"].strip()) > 10

    def test_compline_reading_ref_is_1p58(self):
        assert "1 P" in _HOURS["compline"]["reading_ref"] or "1P" in _HOURS["compline"]["reading_ref"]


# ===========================================================================
# _SEASON_LABELS catalog
# ===========================================================================


class TestSeasonLabels:
    def test_exactly_5_seasons(self):
        assert len(_SEASON_LABELS) == 5

    def test_advent_present(self):
        assert "advent" in _SEASON_LABELS

    def test_christmas_present(self):
        assert "christmas" in _SEASON_LABELS

    def test_lent_present(self):
        assert "lent" in _SEASON_LABELS

    def test_easter_present(self):
        assert "easter" in _SEASON_LABELS

    def test_ordinary_present(self):
        assert "ordinary" in _SEASON_LABELS

    def test_advent_label(self):
        assert _SEASON_LABELS["advent"] == "Adwent"

    def test_christmas_label(self):
        assert _SEASON_LABELS["christmas"] == "Boże Narodzenie"

    def test_lent_label(self):
        assert _SEASON_LABELS["lent"] == "Wielki Post"

    def test_easter_label(self):
        assert _SEASON_LABELS["easter"] == "Wielkanoc"

    def test_ordinary_label(self):
        assert _SEASON_LABELS["ordinary"] == "Zwykły"

    def test_all_labels_are_strings(self):
        for season, label in _SEASON_LABELS.items():
            assert isinstance(label, str), f"{season} label is not a string"

    def test_all_labels_non_empty(self):
        for season, label in _SEASON_LABELS.items():
            assert label.strip(), f"{season} label is empty"


# ===========================================================================
# _OPENING_MESSAGES
# ===========================================================================


class TestOpeningMessages:
    def test_exactly_5_traditions(self):
        assert len(_OPENING_MESSAGES) == 5

    def test_ignatian_present(self):
        assert "ignatian" in _OPENING_MESSAGES

    def test_carmelite_present(self):
        assert "carmelite" in _OPENING_MESSAGES

    def test_benedictine_present(self):
        assert "benedictine" in _OPENING_MESSAGES

    def test_franciscan_present(self):
        assert "franciscan" in _OPENING_MESSAGES

    def test_dominican_present(self):
        assert "dominican" in _OPENING_MESSAGES

    def test_all_are_strings(self):
        for tradition, msg in _OPENING_MESSAGES.items():
            assert isinstance(msg, str), f"{tradition} message is not a string"

    def test_all_non_empty(self):
        for tradition, msg in _OPENING_MESSAGES.items():
            assert len(msg.strip()) > 20, f"{tradition} message too short"

    def test_all_end_with_question_mark(self):
        for tradition, msg in _OPENING_MESSAGES.items():
            assert msg.strip().endswith("?"), f"{tradition} message doesn't end with ?"

    def test_ignatian_mentions_ignacy(self):
        assert "ignacjanskiej" in _OPENING_MESSAGES["ignatian"].lower() or "ignacjan" in _OPENING_MESSAGES["ignatian"].lower()

    def test_carmelite_mentions_teresa_or_jan(self):
        msg = _OPENING_MESSAGES["carmelite"]
        assert "Teresa" in msg or "teresa" in msg.lower() or "Jana" in msg or "Krzyza" in msg

    def test_benedictine_mentions_benedykt(self):
        msg = _OPENING_MESSAGES["benedictine"]
        assert "Benedykt" in msg or "benedykt" in msg.lower()

    def test_franciscan_mentions_franciszek(self):
        assert "Franciszka" in _OPENING_MESSAGES["franciscan"]

    def test_dominican_mentions_prawda(self):
        msg = _OPENING_MESSAGES["dominican"]
        assert "Prawda" in msg or "Prawdy" in msg or "prawdy" in msg.lower()

    def test_franciscan_has_pokoj_i_dobro(self):
        assert "Pokoj i Dobro" in _OPENING_MESSAGES["franciscan"] or "Pokój i Dobro" in _OPENING_MESSAGES["franciscan"]
