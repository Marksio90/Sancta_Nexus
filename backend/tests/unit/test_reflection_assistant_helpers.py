"""Unit tests for reflection_assistant route helpers and TRADITIONS catalog.

No HTTP calls, no LLM, no DB — pure function and data layer testing.

Contracts verified:
TRADITIONS:
- Exactly 5 traditions present
- All have id, name, description, key_practices
- All key_practices lists non-empty
- Known tradition IDs: ignatian, carmelite, benedictine, franciscan, dominican
- Each name is non-empty Polish string

_generate_director_response:
- Always includes primary_emotion in output
- Tradition-specific closing appended
- Scripture suggestion included when matches provided
- No matches → scripture part omitted
- Unknown tradition → falls back to ignatian closing

_generate_follow_up_questions:
- Returns list of strings
- Length ≤ 3
- Emotion-specific questions prepended for known emotions
  (sadness, joy, fear, guilt, longing)
- Unknown emotion → only base questions
- Base questions always present in output
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub unavailable packages before import
for _mod in ["neo4j", "qdrant_client", "qdrant_client.models",
             "jose", "jose.jwt", "jose.exceptions"]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.api.routes.reflection_assistant import (
    TRADITIONS,
    _generate_director_response,
    _generate_follow_up_questions,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _analysis(primary_emotion: str = "peace") -> MagicMock:
    a = MagicMock()
    a.primary_emotion = primary_emotion
    return a


def _spiritual_state(description: str = "") -> MagicMock:
    s = MagicMock()
    s.description = description
    return s


def _match(reference: str = "Ps 23", passage: str = "Pan jest moim pasterzem") -> MagicMock:
    m = MagicMock()
    m.reference = reference
    m.passage = passage
    return m


# ===========================================================================
# TRADITIONS catalog
# ===========================================================================


class TestTraditionsCatalog:
    def test_exactly_5_traditions(self):
        assert len(TRADITIONS) == 5

    def test_all_have_required_fields(self):
        required = {"id", "name", "description", "key_practices"}
        for t in TRADITIONS:
            assert required <= set(t.keys()), f"Missing field in {t.get('id')}"

    def test_ignatian_present(self):
        ids = {t["id"] for t in TRADITIONS}
        assert "ignatian" in ids

    def test_carmelite_present(self):
        ids = {t["id"] for t in TRADITIONS}
        assert "carmelite" in ids

    def test_benedictine_present(self):
        ids = {t["id"] for t in TRADITIONS}
        assert "benedictine" in ids

    def test_franciscan_present(self):
        ids = {t["id"] for t in TRADITIONS}
        assert "franciscan" in ids

    def test_dominican_present(self):
        ids = {t["id"] for t in TRADITIONS}
        assert "dominican" in ids

    def test_all_have_non_empty_names(self):
        for t in TRADITIONS:
            assert t["name"].strip()

    def test_all_have_non_empty_descriptions(self):
        for t in TRADITIONS:
            assert t["description"].strip()

    def test_all_have_key_practices(self):
        for t in TRADITIONS:
            assert len(t["key_practices"]) >= 3

    def test_ignatian_has_examen(self):
        ign = next(t for t in TRADITIONS if t["id"] == "ignatian")
        practices = " ".join(ign["key_practices"]).lower()
        assert "examen" in practices or "rachunek" in practices

    def test_benedictine_has_ora_et_labora(self):
        ben = next(t for t in TRADITIONS if t["id"] == "benedictine")
        practices = " ".join(ben["key_practices"])
        assert "Ora et Labora" in practices

    def test_dominican_has_rozaniec(self):
        dom = next(t for t in TRADITIONS if t["id"] == "dominican")
        practices = " ".join(dom["key_practices"])
        assert "Rozaniec" in practices or "Różaniec" in practices

    def test_carmelite_mentions_jan_od_krzyza(self):
        car = next(t for t in TRADITIONS if t["id"] == "carmelite")
        assert "Jan" in car["description"] or "Krzyza" in car["description"]

    def test_all_ids_unique(self):
        ids = [t["id"] for t in TRADITIONS]
        assert len(ids) == len(set(ids))


# ===========================================================================
# _generate_director_response
# ===========================================================================


class TestGenerateDirectorResponse:
    def test_includes_primary_emotion(self):
        result = _generate_director_response(
            "Czuję się zagubiony",
            "ignatian",
            _analysis("sadness"),
            _spiritual_state(),
            [],
        )
        assert "sadness" in result

    def test_ignatian_closing(self):
        result = _generate_director_response(
            "msg", "ignatian", _analysis("joy"), _spiritual_state(), []
        )
        assert "Bog" in result or "Boga" in result or "doswiadczeniu" in result

    def test_carmelite_closing(self):
        result = _generate_director_response(
            "msg", "carmelite", _analysis("peace"), _spiritual_state(), []
        )
        assert "ciszy" in result or "trwania" in result

    def test_benedictine_closing(self):
        result = _generate_director_response(
            "msg", "benedictine", _analysis("peace"), _spiritual_state(), []
        )
        assert "serca" in result or "Sluchaj" in result

    def test_franciscan_closing(self):
        result = _generate_director_response(
            "msg", "franciscan", _analysis("joy"), _spiritual_state(), []
        )
        assert "Franciszka" in result or "prostoty" in result

    def test_dominican_closing(self):
        result = _generate_director_response(
            "msg", "dominican", _analysis("hope"), _spiritual_state(), []
        )
        assert "prawdy" in result or "doswiadczeniu" in result

    def test_unknown_tradition_falls_back_to_ignatian(self):
        result = _generate_director_response(
            "msg", "unknown_tradition", _analysis("peace"), _spiritual_state(), []
        )
        # ignatian closing: "gdzie w tym doswiadczeniu jest Bog?"
        assert "Bog" in result or "doswiadczeniu" in result

    def test_scripture_included_when_matches_provided(self):
        match = _match("Ps 23", "Pan jest moim pasterzem")
        result = _generate_director_response(
            "msg", "ignatian", _analysis("peace"), _spiritual_state(), [match]
        )
        assert "Ps 23" in result

    def test_scripture_passage_included(self):
        match = _match("J 14,27", "Pokój zostawiam wam")
        result = _generate_director_response(
            "msg", "ignatian", _analysis("peace"), _spiritual_state(), [match]
        )
        assert "Pokój zostawiam wam" in result

    def test_no_scripture_when_no_matches(self):
        result = _generate_director_response(
            "msg", "ignatian", _analysis("peace"), _spiritual_state(), []
        )
        # The scripture suggestion phrase
        assert "rozważenia" not in result

    def test_spiritual_description_included_when_non_empty(self):
        state = _spiritual_state(description="Jesteś w stanie pocieszenia.")
        result = _generate_director_response(
            "msg", "ignatian", _analysis("joy"), state, []
        )
        assert "pocieszenia" in result

    def test_empty_spiritual_description_not_added(self):
        state = _spiritual_state(description="")
        result = _generate_director_response(
            "msg", "ignatian", _analysis("joy"), state, []
        )
        # Should still produce valid output without the description part
        assert len(result) > 10

    def test_returns_non_empty_string(self):
        result = _generate_director_response(
            "Hello", "ignatian", _analysis("hope"), _spiritual_state(), []
        )
        assert isinstance(result, str) and len(result) > 0


# ===========================================================================
# _generate_follow_up_questions
# ===========================================================================


class TestGenerateFollowUpQuestions:
    def test_returns_list(self):
        result = _generate_follow_up_questions("ignatian", "peace")
        assert isinstance(result, list)

    def test_length_at_most_3(self):
        for tradition in ("ignatian", "carmelite", "franciscan"):
            for emotion in ("sadness", "joy", "fear", "guilt", "longing", "unknown"):
                result = _generate_follow_up_questions(tradition, emotion)
                assert len(result) <= 3, f"Too many questions for {tradition}/{emotion}"

    def test_sadness_specific_question_present(self):
        result = _generate_follow_up_questions("ignatian", "sadness")
        combined = " ".join(result).lower()
        assert "smutek" in combined or "bol" in combined or "bliskos" in combined

    def test_joy_specific_question_present(self):
        result = _generate_follow_up_questions("ignatian", "joy")
        combined = " ".join(result).lower()
        assert "wdzieczn" in combined or "radosc" in combined

    def test_fear_specific_question_present(self):
        result = _generate_follow_up_questions("ignatian", "fear")
        combined = " ".join(result).lower()
        assert "obawia" in combined or "lek" in combined

    def test_guilt_specific_question_present(self):
        result = _generate_follow_up_questions("ignatian", "guilt")
        combined = " ".join(result).lower()
        assert "milosierdzie" in combined or "pojednania" in combined

    def test_longing_specific_question_present(self):
        result = _generate_follow_up_questions("ignatian", "longing")
        combined = " ".join(result).lower()
        assert "szuka" in combined or "pragnienie" in combined

    def test_unknown_emotion_returns_base_questions(self):
        result = _generate_follow_up_questions("ignatian", "unknown_emotion_xyz")
        assert len(result) >= 1
        combined = " ".join(result).lower()
        assert "powiedzie" in combined or "modlitw" in combined

    def test_all_elements_are_strings(self):
        result = _generate_follow_up_questions("carmelite", "peace")
        for q in result:
            assert isinstance(q, str)

    def test_all_questions_end_with_question_mark(self):
        result = _generate_follow_up_questions("benedictine", "joy")
        for q in result:
            assert q.strip().endswith("?"), f"Not a question: {q!r}"
