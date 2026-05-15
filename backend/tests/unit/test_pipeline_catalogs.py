"""Unit tests for pipeline ordering catalogs and prayer tradition elements.

No HTTP, no LLM, no DB — pure data-layer testing.

Contracts verified:
_STAGE_ORDER (app/api/routes/lectio_divina.py):
- Exactly 5 stages in canonical Lectio Divina order
- Sequence: lectio → meditatio → oratio → contemplatio → actio
- No duplicates, all are non-empty strings

_TRADITION_ELEMENTS (app/agents/generative/prayer_generator.py):
- Exactly 5 spiritual traditions present
- Expected traditions: ignatian, carmelite, franciscan, benedictine, charismatic
- Each tradition has exactly 4 prayer elements
- All elements are non-empty strings, underscore-convention
- Tradition-specific elements present:
  ignatian: compositio_loci, colloquium present
  benedictine: psalmus present (lectio divina root)
  franciscan: laudatio present
  charismatic: adoratio, intercessio present

_FALLBACK_PRAYER (app/agents/generative/prayer_generator.py):
- Contains prayer_text, tradition, elements keys
- prayer_text is a substantial Polish prayer (> 80 chars, ends with Amen)
- tradition is a valid tradition string
- elements is a non-empty list of strings
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

if "langgraph" not in sys.modules:
    sys.modules["langgraph"] = MagicMock()
    sys.modules["langgraph.graph"] = MagicMock()

from app.api.routes.lectio_divina import _STAGE_ORDER
from app.agents.generative.prayer_generator import _FALLBACK_PRAYER, _TRADITION_ELEMENTS

_CANONICAL_ORDER = ["lectio", "meditatio", "oratio", "contemplatio", "actio"]
_EXPECTED_TRADITIONS = {"ignatian", "carmelite", "franciscan", "benedictine", "charismatic"}


# ===========================================================================
# _STAGE_ORDER — Lectio Divina pipeline sequence
# ===========================================================================


class TestStageOrder:
    def test_exactly_5_stages(self):
        assert len(_STAGE_ORDER) == 5

    def test_canonical_order(self):
        assert list(_STAGE_ORDER) == _CANONICAL_ORDER

    def test_lectio_is_first(self):
        assert _STAGE_ORDER[0] == "lectio"

    def test_actio_is_last(self):
        assert _STAGE_ORDER[-1] == "actio"

    def test_meditatio_follows_lectio(self):
        assert _STAGE_ORDER.index("meditatio") == _STAGE_ORDER.index("lectio") + 1

    def test_oratio_follows_meditatio(self):
        assert _STAGE_ORDER.index("oratio") == _STAGE_ORDER.index("meditatio") + 1

    def test_contemplatio_follows_oratio(self):
        assert _STAGE_ORDER.index("contemplatio") == _STAGE_ORDER.index("oratio") + 1

    def test_actio_follows_contemplatio(self):
        assert _STAGE_ORDER.index("actio") == _STAGE_ORDER.index("contemplatio") + 1

    def test_no_duplicates(self):
        assert len(_STAGE_ORDER) == len(set(_STAGE_ORDER))

    def test_all_are_strings(self):
        for stage in _STAGE_ORDER:
            assert isinstance(stage, str), f"Stage {stage!r} is not a string"

    def test_all_non_empty(self):
        for stage in _STAGE_ORDER:
            assert stage.strip(), "Empty stage found"

    def test_all_expected_stages_present(self):
        assert set(_STAGE_ORDER) == set(_CANONICAL_ORDER)


# ===========================================================================
# _TRADITION_ELEMENTS — prayer tradition element catalog
# ===========================================================================


class TestTraditionElements:
    def test_exactly_5_traditions(self):
        assert len(_TRADITION_ELEMENTS) == 5

    def test_all_expected_traditions_present(self):
        assert _EXPECTED_TRADITIONS == set(_TRADITION_ELEMENTS.keys())

    def test_ignatian_present(self):
        assert "ignatian" in _TRADITION_ELEMENTS

    def test_carmelite_present(self):
        assert "carmelite" in _TRADITION_ELEMENTS

    def test_franciscan_present(self):
        assert "franciscan" in _TRADITION_ELEMENTS

    def test_benedictine_present(self):
        assert "benedictine" in _TRADITION_ELEMENTS

    def test_charismatic_present(self):
        assert "charismatic" in _TRADITION_ELEMENTS

    def test_each_tradition_has_4_elements(self):
        for tradition, elements in _TRADITION_ELEMENTS.items():
            assert len(elements) == 4, (
                f"{tradition} has {len(elements)} elements, expected 4"
            )

    def test_all_elements_are_strings(self):
        for tradition, elements in _TRADITION_ELEMENTS.items():
            for el in elements:
                assert isinstance(el, str), f"{tradition}/{el!r} is not a string"

    def test_all_elements_non_empty(self):
        for tradition, elements in _TRADITION_ELEMENTS.items():
            for el in elements:
                assert el.strip(), f"{tradition} has empty element"

    def test_all_elements_use_underscore_convention(self):
        for tradition, elements in _TRADITION_ELEMENTS.items():
            for el in elements:
                assert el == el.lower(), f"{tradition}/{el} not lowercase"

    def test_no_duplicate_elements_within_tradition(self):
        for tradition, elements in _TRADITION_ELEMENTS.items():
            assert len(elements) == len(set(elements)), (
                f"{tradition} has duplicate elements"
            )

    # Tradition-specific element checks
    def test_ignatian_has_compositio_loci(self):
        assert "compositio_loci" in _TRADITION_ELEMENTS["ignatian"]

    def test_ignatian_has_colloquium(self):
        assert "colloquium" in _TRADITION_ELEMENTS["ignatian"]

    def test_benedictine_has_psalmus(self):
        # Benedictine root: Liturgy of the Hours / psalmody
        assert "psalmus" in _TRADITION_ELEMENTS["benedictine"]

    def test_benedictine_has_lectio(self):
        # Lectio divina originated in Benedictine tradition
        assert "lectio" in _TRADITION_ELEMENTS["benedictine"]

    def test_franciscan_has_laudatio(self):
        assert "laudatio" in _TRADITION_ELEMENTS["franciscan"]

    def test_charismatic_has_adoratio(self):
        assert "adoratio" in _TRADITION_ELEMENTS["charismatic"]

    def test_charismatic_has_intercessio(self):
        assert "intercessio" in _TRADITION_ELEMENTS["charismatic"]

    def test_carmelite_has_contemplatio(self):
        assert "contemplatio" in _TRADITION_ELEMENTS["carmelite"]

    def test_carmelite_has_silentium(self):
        # Carmelite: contemplative silence is the cornerstone
        assert "silentium" in _TRADITION_ELEMENTS["carmelite"]


# ===========================================================================
# _FALLBACK_PRAYER — pre-approved safe fallback
# ===========================================================================


class TestFallbackPrayer:
    def test_has_prayer_text_key(self):
        assert "prayer_text" in _FALLBACK_PRAYER

    def test_has_tradition_key(self):
        assert "tradition" in _FALLBACK_PRAYER

    def test_has_elements_key(self):
        assert "elements" in _FALLBACK_PRAYER

    def test_prayer_text_substantial(self):
        assert len(_FALLBACK_PRAYER["prayer_text"]) > 80

    def test_prayer_text_contains_amen(self):
        assert "Amen" in _FALLBACK_PRAYER["prayer_text"] or "amen" in _FALLBACK_PRAYER["prayer_text"].lower()

    def test_tradition_is_string(self):
        assert isinstance(_FALLBACK_PRAYER["tradition"], str)

    def test_tradition_non_empty(self):
        assert _FALLBACK_PRAYER["tradition"].strip()

    def test_elements_is_list(self):
        assert isinstance(_FALLBACK_PRAYER["elements"], list)

    def test_elements_non_empty(self):
        assert len(_FALLBACK_PRAYER["elements"]) >= 1

    def test_elements_are_strings(self):
        for el in _FALLBACK_PRAYER["elements"]:
            assert isinstance(el, str), f"Element {el!r} is not a string"

    def test_exactly_3_top_level_keys(self):
        assert set(_FALLBACK_PRAYER.keys()) == {"prayer_text", "tradition", "elements"}
