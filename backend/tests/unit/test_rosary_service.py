"""Unit tests for app/services/community/rosary_service.py.

Self-contained — no DB, no LLM. Only pure-Python logic is tested:
the MYSTERIES catalog, DAILY_MYSTERY schedule, and the three synchronous
query methods.

Contracts verified:
- MYSTERIES: 4 types, each has exactly 5 mysteries, all required fields
- DAILY_MYSTERY: all 7 weekdays mapped, correct tradition per day
- get_mysteries: returns list for valid type, empty for unknown
- get_today_mystery: returns a valid mystery type (weekday-dependent)
- get_all_mystery_types: returns 4 types with required keys
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub openai (may not be installed)
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()

from app.services.community.rosary_service import (
    DAILY_MYSTERY,
    MYSTERIES,
    RosaryService,
)


def _service() -> RosaryService:
    svc = RosaryService.__new__(RosaryService)
    return svc


# ---------------------------------------------------------------------------
# MYSTERIES catalog
# ---------------------------------------------------------------------------


class TestMysteriesCatalog:
    def test_four_mystery_types(self):
        assert set(MYSTERIES.keys()) == {"radosne", "bolesne", "chwalebne", "swietlne"}

    def test_each_type_has_five_mysteries(self):
        for mtype, mysteries in MYSTERIES.items():
            assert len(mysteries) == 5, f"{mtype} has {len(mysteries)} mysteries"

    def test_each_mystery_has_required_fields(self):
        required = {"number", "title", "scripture", "fruit", "meditation"}
        for mtype, mysteries in MYSTERIES.items():
            for m in mysteries:
                assert required <= set(m.keys()), f"Missing fields in {mtype} mystery {m['number']}"

    def test_mysteries_numbered_1_to_5(self):
        for mtype, mysteries in MYSTERIES.items():
            numbers = [m["number"] for m in mysteries]
            assert numbers == list(range(1, 6)), f"{mtype} numbers wrong: {numbers}"

    def test_all_have_scripture_reference(self):
        for mtype, mysteries in MYSTERIES.items():
            for m in mysteries:
                assert m["scripture"].strip(), f"{mtype} mystery {m['number']} has empty scripture"

    def test_all_have_fruit(self):
        for mtype, mysteries in MYSTERIES.items():
            for m in mysteries:
                assert m["fruit"].strip()

    def test_radosne_first_mystery_is_zwiastowanie(self):
        first = MYSTERIES["radosne"][0]
        assert "Zwiastowanie" in first["title"]

    def test_bolesne_last_mystery_is_ukrzyzowanie(self):
        last = MYSTERIES["bolesne"][4]
        assert "Ukrzyżowanie" in last["title"] or "śmierć" in last["title"].lower()

    def test_chwalebne_has_zmartwychwstanie(self):
        titles = [m["title"] for m in MYSTERIES["chwalebne"]]
        assert any("Zmartwychwstanie" in t for t in titles)

    def test_swietlne_has_eucharystia(self):
        titles = [m["title"] for m in MYSTERIES["swietlne"]]
        assert any("Eucharystii" in t or "Eucharystia" in t for t in titles)


# ---------------------------------------------------------------------------
# DAILY_MYSTERY schedule
# ---------------------------------------------------------------------------


class TestDailyMystery:
    def test_all_seven_weekdays_mapped(self):
        assert set(DAILY_MYSTERY.keys()) == {0, 1, 2, 3, 4, 5, 6}

    def test_monday_is_radosne(self):
        assert DAILY_MYSTERY[0] == "radosne"

    def test_tuesday_is_bolesne(self):
        assert DAILY_MYSTERY[1] == "bolesne"

    def test_wednesday_is_chwalebne(self):
        assert DAILY_MYSTERY[2] == "chwalebne"

    def test_thursday_is_swietlne(self):
        assert DAILY_MYSTERY[3] == "swietlne"

    def test_friday_is_bolesne(self):
        assert DAILY_MYSTERY[4] == "bolesne"

    def test_saturday_is_radosne(self):
        assert DAILY_MYSTERY[5] == "radosne"

    def test_sunday_is_chwalebne(self):
        assert DAILY_MYSTERY[6] == "chwalebne"

    def test_all_values_are_valid_mystery_types(self):
        valid = set(MYSTERIES.keys())
        for weekday, mystery in DAILY_MYSTERY.items():
            assert mystery in valid, f"Weekday {weekday} maps to unknown mystery '{mystery}'"


# ---------------------------------------------------------------------------
# RosaryService query methods
# ---------------------------------------------------------------------------


class TestGetMysteries:
    def test_radosne_returns_5_mysteries(self):
        svc = _service()
        result = svc.get_mysteries("radosne")
        assert len(result) == 5

    def test_unknown_type_returns_empty(self):
        svc = _service()
        assert svc.get_mysteries("unknown") == []

    def test_returns_list_of_dicts(self):
        svc = _service()
        result = svc.get_mysteries("bolesne")
        assert isinstance(result, list)
        assert all(isinstance(m, dict) for m in result)


class TestGetTodayMystery:
    def test_returns_valid_mystery_type(self):
        svc = _service()
        result = svc.get_today_mystery()
        assert result in MYSTERIES

    def test_returns_string(self):
        svc = _service()
        assert isinstance(svc.get_today_mystery(), str)


class TestGetAllMysteryTypes:
    def test_returns_four_types(self):
        svc = _service()
        result = svc.get_all_mystery_types()
        assert len(result) == 4

    def test_each_has_id_and_label(self):
        svc = _service()
        for item in svc.get_all_mystery_types():
            assert "id" in item
            assert "label" in item

    def test_ids_match_mysteries_keys(self):
        svc = _service()
        ids = {item["id"] for item in svc.get_all_mystery_types()}
        assert ids == set(MYSTERIES.keys())
