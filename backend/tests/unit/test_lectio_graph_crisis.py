"""Unit tests for LectioDivinaGraph crisis detection and routing.

All tests bypass __init__ (avoids LangGraph + LLM imports).

Contracts verified:
CRISIS_KEYWORDS:
- frozenset, non-empty, Polish + English crisis phrases present

CRISIS_EMOTION_THRESHOLD:
- float value 0.85

_detect_crisis:
- despair above threshold → True
- despair at or below threshold → False
- suicidal_ideation > 0 → True (even tiny value)
- suicidal_ideation = 0 → not triggered by this path
- crisis keyword in raw_input → True (Polish and English)
- case-insensitive keyword detection
- no crisis signals → False
- empty state → False

LectioDivinaSupervisor._check_crisis (static):
- crisis state → "crisis_handler"
- clean state → "scripture_selection"

LectioDivinaSupervisor._check_crisis_after_scripture (static):
- crisis state → "crisis_handler"
- clean state → "lectio"

CollectionManager constants:
- VECTOR_DIM = 1536
- _PAYLOAD_INDICES covers all 8 QdrantCollection values
- _COMMON_INDICES has source_type, language, theology_tags, tradition_tags
- Each collection has at least 1 indexed field beyond common
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub langgraph and qdrant before the graph module loads
if "langgraph" not in sys.modules:
    _sg = MagicMock()
    _sg.return_value = MagicMock()
    sys.modules["langgraph"] = MagicMock()
    sys.modules["langgraph.graph"] = MagicMock()
    sys.modules["langgraph.graph"].StateGraph = _sg
    sys.modules["langgraph.graph"].START = "__start__"
    sys.modules["langgraph.graph"].END = "__end__"

if "qdrant_client" not in sys.modules:
    sys.modules["qdrant_client"] = MagicMock()
    sys.modules["qdrant_client.models"] = MagicMock()

from app.agents.lectio_divina.lectio_divina_graph import (
    CRISIS_EMOTION_THRESHOLD,
    CRISIS_KEYWORDS,
    LectioDivinaSupervisor,
    LectioDivinaState,
    _detect_crisis,
)
from app.services.knowledge.collection_manager import (
    VECTOR_DIM,
    _COMMON_INDICES,
    _PAYLOAD_INDICES,
)
from app.services.knowledge.corpus_registry import QdrantCollection


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _state(**kwargs) -> LectioDivinaState:
    base: LectioDivinaState = {
        "user_id": "test-user",
        "raw_input": "Pragnę modlitwy i pokoju.",
        "emotion_vector": {},
    }
    base.update(kwargs)
    return base


# ===========================================================================
# CRISIS_KEYWORDS
# ===========================================================================


class TestCrisisKeywords:
    def test_is_frozenset(self):
        assert isinstance(CRISIS_KEYWORDS, frozenset)

    def test_non_empty(self):
        assert len(CRISIS_KEYWORDS) >= 5

    def test_polish_suicide_keyword_present(self):
        assert "samobojstwo" in CRISIS_KEYWORDS

    def test_english_suicide_keyword_present(self):
        assert "suicide" in CRISIS_KEYWORDS

    def test_self_harm_keyword_present(self):
        assert "self-harm" in CRISIS_KEYWORDS

    def test_chce_umrzec_present(self):
        assert "chce umrzec" in CRISIS_KEYWORDS

    def test_all_keywords_are_strings(self):
        for kw in CRISIS_KEYWORDS:
            assert isinstance(kw, str)


class TestCrisisEmotionThreshold:
    def test_value_is_085(self):
        assert CRISIS_EMOTION_THRESHOLD == 0.85

    def test_is_float(self):
        assert isinstance(CRISIS_EMOTION_THRESHOLD, float)


# ===========================================================================
# _detect_crisis
# ===========================================================================


class TestDetectCrisis:
    def test_empty_state_returns_false(self):
        assert _detect_crisis({}) is False

    def test_no_crisis_signals_returns_false(self):
        state = _state(
            raw_input="Czuję pokój w sercu i wdzięczność za dar modlitwy.",
            emotion_vector={"peace": 0.9, "joy": 0.8},
        )
        assert _detect_crisis(state) is False

    def test_despair_above_threshold_returns_true(self):
        state = _state(emotion_vector={"despair": 0.90})
        assert _detect_crisis(state) is True

    def test_despair_exactly_at_threshold_returns_false(self):
        state = _state(emotion_vector={"despair": 0.85})
        assert _detect_crisis(state) is False

    def test_despair_below_threshold_returns_false(self):
        state = _state(emotion_vector={"despair": 0.80})
        assert _detect_crisis(state) is False

    def test_suicidal_ideation_tiny_value_returns_true(self):
        state = _state(emotion_vector={"suicidal_ideation": 0.001})
        assert _detect_crisis(state) is True

    def test_suicidal_ideation_zero_not_triggered(self):
        state = _state(emotion_vector={"suicidal_ideation": 0.0})
        assert _detect_crisis(state) is False

    def test_polish_keyword_samobojstwo(self):
        state = _state(raw_input="Myślę o samobojstwo")
        assert _detect_crisis(state) is True

    def test_english_keyword_suicide(self):
        state = _state(raw_input="I am thinking about suicide")
        assert _detect_crisis(state) is True

    def test_chce_umrzec_keyword(self):
        state = _state(raw_input="Nie chce zyc na tym świecie")
        assert _detect_crisis(state) is True

    def test_case_insensitive_keyword(self):
        state = _state(raw_input="SAMOBOJSTWO")
        assert _detect_crisis(state) is True

    def test_keyword_embedded_in_sentence(self):
        state = _state(raw_input="Mam myśli o suicide cały czas")
        assert _detect_crisis(state) is True

    def test_multiple_signals_still_true(self):
        state = _state(
            raw_input="Nie mam po co zyc",
            emotion_vector={"despair": 0.99, "suicidal_ideation": 0.5},
        )
        assert _detect_crisis(state) is True

    def test_self_harm_keyword(self):
        state = _state(raw_input="I want to do self-harm")
        assert _detect_crisis(state) is True

    def test_chce_sie_zabic_keyword(self):
        state = _state(raw_input="chce sie zabic")
        assert _detect_crisis(state) is True


# ===========================================================================
# _check_crisis routing
# ===========================================================================


class TestCheckCrisis:
    def test_crisis_state_routes_to_crisis_handler(self):
        state = _state(raw_input="samobojstwo")
        result = LectioDivinaSupervisor._check_crisis(state)
        assert result == "crisis_handler"

    def test_clean_state_routes_to_scripture_selection(self):
        state = _state(raw_input="Kocham modlitwę")
        result = LectioDivinaSupervisor._check_crisis(state)
        assert result == "scripture_selection"

    def test_despair_emotion_routes_to_crisis_handler(self):
        state = _state(emotion_vector={"despair": 0.95})
        result = LectioDivinaSupervisor._check_crisis(state)
        assert result == "crisis_handler"

    def test_low_despair_routes_normally(self):
        state = _state(emotion_vector={"despair": 0.5})
        result = LectioDivinaSupervisor._check_crisis(state)
        assert result == "scripture_selection"


class TestCheckCrisisAfterScripture:
    def test_crisis_state_routes_to_crisis_handler(self):
        state = _state(raw_input="nie mam po co zyc")
        result = LectioDivinaSupervisor._check_crisis_after_scripture(state)
        assert result == "crisis_handler"

    def test_clean_state_routes_to_lectio(self):
        state = _state(raw_input="Chcę rozważać Ewangelię Jana")
        result = LectioDivinaSupervisor._check_crisis_after_scripture(state)
        assert result == "lectio"

    def test_suicidal_ideation_routes_to_crisis(self):
        state = _state(emotion_vector={"suicidal_ideation": 0.1})
        result = LectioDivinaSupervisor._check_crisis_after_scripture(state)
        assert result == "crisis_handler"


# ===========================================================================
# CollectionManager constants
# ===========================================================================


class TestVectorDim:
    def test_vector_dim_is_1536(self):
        assert VECTOR_DIM == 1536


class TestPayloadIndices:
    def test_all_8_collections_have_indices(self):
        assert len(_PAYLOAD_INDICES) == 8

    def test_biblia_pl_has_book_index(self):
        fields = [f for f, _ in _PAYLOAD_INDICES[QdrantCollection.BIBLIA_PL]]
        assert "book" in fields

    def test_biblia_pl_has_chapter_index(self):
        fields = [f for f, _ in _PAYLOAD_INDICES[QdrantCollection.BIBLIA_PL]]
        assert "chapter" in fields

    def test_katechizm_has_section_ref(self):
        fields = [f for f, _ in _PAYLOAD_INDICES[QdrantCollection.KATECHIZM]]
        assert "section_ref" in fields

    def test_magisterium_has_doc_id(self):
        fields = [f for f, _ in _PAYLOAD_INDICES[QdrantCollection.MAGISTERIUM]]
        assert "doc_id" in fields

    def test_patrystyka_has_author(self):
        fields = [f for f, _ in _PAYLOAD_INDICES[QdrantCollection.PATRYSTYKA]]
        assert "author" in fields

    def test_liturgia_has_liturgical_season(self):
        fields = [f for f, _ in _PAYLOAD_INDICES[QdrantCollection.LITURGIA]]
        assert "liturgical_season" in fields

    def test_each_collection_has_at_least_one_index(self):
        for coll, indices in _PAYLOAD_INDICES.items():
            assert len(indices) >= 1, f"{coll} has no payload indices"


class TestCommonIndices:
    def test_has_4_common_fields(self):
        assert len(_COMMON_INDICES) == 4

    def test_source_type_indexed(self):
        fields = [f for f, _ in _COMMON_INDICES]
        assert "source_type" in fields

    def test_language_indexed(self):
        fields = [f for f, _ in _COMMON_INDICES]
        assert "language" in fields

    def test_theology_tags_indexed(self):
        fields = [f for f, _ in _COMMON_INDICES]
        assert "theology_tags" in fields

    def test_tradition_tags_indexed(self):
        fields = [f for f, _ in _COMMON_INDICES]
        assert "tradition_tags" in fields
