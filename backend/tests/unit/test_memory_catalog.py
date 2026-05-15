"""Unit tests for memory agent catalogs: JOURNEY_STAGES and PATTERN_TYPES.

No LLM, no network — pure data-layer testing.

Contracts verified:
JOURNEY_STAGES:
- Exactly 3 classical spiritual stages: purgation, illumination, union
- All have: name_pl, description, indicators, range
- name_pl is a non-empty Polish string
- indicators is a list with at least 3 items
- range is a tuple (min, max) with min < max
- Ranges cover 0–100 and do not overlap
- Purgation range starts at 0, union range ends at 100
- Specific Polish indicators present

PATTERN_TYPES:
- Exactly 6 pattern types
- All are non-empty strings
- Specific types present: recurring_theme, cyclical_crisis, grace_moment,
  growth_trajectory, scripture_affinity, emotional_pattern
- No duplicates
"""

from __future__ import annotations

from app.agents.memory.journey_tracker import JOURNEY_STAGES
from app.agents.memory.pattern_discovery import PATTERN_TYPES

_ALL_EXPECTED_STAGES = {"purgation", "illumination", "union"}
_ALL_EXPECTED_PATTERNS = {
    "recurring_theme", "cyclical_crisis", "grace_moment",
    "growth_trajectory", "scripture_affinity", "emotional_pattern",
}


# ===========================================================================
# JOURNEY_STAGES catalog
# ===========================================================================


class TestJourneyStagesCatalog:
    def test_exactly_3_stages(self):
        assert len(JOURNEY_STAGES) == 3

    def test_purgation_present(self):
        assert "purgation" in JOURNEY_STAGES

    def test_illumination_present(self):
        assert "illumination" in JOURNEY_STAGES

    def test_union_present(self):
        assert "union" in JOURNEY_STAGES

    def test_all_expected_stages_present(self):
        assert _ALL_EXPECTED_STAGES == set(JOURNEY_STAGES.keys())

    def test_all_have_name_pl(self):
        for stage, data in JOURNEY_STAGES.items():
            assert "name_pl" in data, f"{stage} missing name_pl"

    def test_all_have_description(self):
        for stage, data in JOURNEY_STAGES.items():
            assert "description" in data, f"{stage} missing description"

    def test_all_have_indicators(self):
        for stage, data in JOURNEY_STAGES.items():
            assert "indicators" in data, f"{stage} missing indicators"

    def test_all_have_range(self):
        for stage, data in JOURNEY_STAGES.items():
            assert "range" in data, f"{stage} missing range"

    def test_all_name_pl_non_empty(self):
        for stage, data in JOURNEY_STAGES.items():
            assert data["name_pl"].strip(), f"{stage} has empty name_pl"

    def test_purgation_polish_name(self):
        assert "Oczyszczenie" in JOURNEY_STAGES["purgation"]["name_pl"]

    def test_illumination_polish_name(self):
        assert "Oświecenie" in JOURNEY_STAGES["illumination"]["name_pl"]

    def test_union_polish_name(self):
        assert "Zjednoczenie" in JOURNEY_STAGES["union"]["name_pl"]

    def test_all_have_at_least_3_indicators(self):
        for stage, data in JOURNEY_STAGES.items():
            assert len(data["indicators"]) >= 3, f"{stage} has fewer than 3 indicators"

    def test_indicators_are_strings(self):
        for stage, data in JOURNEY_STAGES.items():
            for ind in data["indicators"]:
                assert isinstance(ind, str), f"{stage} indicator '{ind}' is not a string"

    def test_purgation_has_pokuta_indicator(self):
        indicators = JOURNEY_STAGES["purgation"]["indicators"]
        combined = " ".join(indicators).lower()
        assert "pokuta" in combined or "nawrócenie" in combined

    def test_union_has_kontemplacja_indicator(self):
        indicators = JOURNEY_STAGES["union"]["indicators"]
        combined = " ".join(indicators).lower()
        assert "kontemplacja" in combined or "zjednoczenie" in combined

    def test_illumination_has_modlitwa_indicator(self):
        indicators = JOURNEY_STAGES["illumination"]["indicators"]
        combined = " ".join(indicators).lower()
        assert "modlitwa" in combined

    def test_ranges_are_tuples(self):
        for stage, data in JOURNEY_STAGES.items():
            r = data["range"]
            assert isinstance(r, tuple), f"{stage} range is not a tuple"
            assert len(r) == 2, f"{stage} range should have 2 elements"

    def test_ranges_min_less_than_max(self):
        for stage, data in JOURNEY_STAGES.items():
            low, high = data["range"]
            assert low < high, f"{stage} range min >= max"

    def test_purgation_starts_at_0(self):
        assert JOURNEY_STAGES["purgation"]["range"][0] == 0

    def test_union_ends_at_100(self):
        assert JOURNEY_STAGES["union"]["range"][1] == 100

    def test_purgation_range(self):
        assert JOURNEY_STAGES["purgation"]["range"] == (0, 33)

    def test_illumination_range(self):
        assert JOURNEY_STAGES["illumination"]["range"] == (34, 66)

    def test_union_range(self):
        assert JOURNEY_STAGES["union"]["range"] == (67, 100)

    def test_ranges_cover_0_to_100(self):
        all_values: set[int] = set()
        for data in JOURNEY_STAGES.values():
            low, high = data["range"]
            all_values.update(range(low, high + 1))
        assert 0 in all_values
        assert 100 in all_values

    def test_ranges_do_not_overlap(self):
        ranges = [data["range"] for data in JOURNEY_STAGES.values()]
        all_values: list[int] = []
        for low, high in ranges:
            all_values.extend(range(low, high + 1))
        assert len(all_values) == len(set(all_values)), "Stage ranges overlap"


# ===========================================================================
# PATTERN_TYPES catalog
# ===========================================================================


class TestPatternTypesCatalog:
    def test_exactly_6_types(self):
        assert len(PATTERN_TYPES) == 6

    def test_all_expected_types_present(self):
        assert _ALL_EXPECTED_PATTERNS == set(PATTERN_TYPES)

    def test_recurring_theme_present(self):
        assert "recurring_theme" in PATTERN_TYPES

    def test_cyclical_crisis_present(self):
        assert "cyclical_crisis" in PATTERN_TYPES

    def test_grace_moment_present(self):
        assert "grace_moment" in PATTERN_TYPES

    def test_growth_trajectory_present(self):
        assert "growth_trajectory" in PATTERN_TYPES

    def test_scripture_affinity_present(self):
        assert "scripture_affinity" in PATTERN_TYPES

    def test_emotional_pattern_present(self):
        assert "emotional_pattern" in PATTERN_TYPES

    def test_all_are_strings(self):
        for pt in PATTERN_TYPES:
            assert isinstance(pt, str), f"Pattern type '{pt}' is not a string"

    def test_no_duplicates(self):
        assert len(PATTERN_TYPES) == len(set(PATTERN_TYPES))

    def test_all_non_empty(self):
        for pt in PATTERN_TYPES:
            assert pt.strip(), "Empty pattern type found"

    def test_all_use_underscore_convention(self):
        for pt in PATTERN_TYPES:
            assert "_" in pt, f"Pattern type '{pt}' doesn't use underscore convention"
