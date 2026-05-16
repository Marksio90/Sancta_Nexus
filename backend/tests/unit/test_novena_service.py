"""Unit tests for app/services/community/novena_service.py.

Self-contained — no DB, no LLM, no real OpenAI API.
NovenaService.__init__ is bypassed; _tracking_to_dict is tested with a mock
NovenaTracking object to validate the bitmask logic.

Contracts verified:
- NOVENAS: exactly 8 novenas, all required fields, unique IDs
- milosierdzie novena present (key Polish devotion)
- get_all_novenas: lightweight catalogue (no daily_prayers), 8 items
- get_novena: found / not found
- get_day: valid day, out-of-range, unknown novena
- _tracking_to_dict: bitmask→completed_days, progress_percent, is_complete
- Bitmask: day 1 = bit 0, day 9 = bit 8; all_mask for 9 days = 511
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub openai (may not be installed) and ensure app.core.config is available
if "openai" not in sys.modules:
    sys.modules["openai"] = MagicMock()

from app.services.community.novena_service import NOVENAS, NovenaService

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _service() -> NovenaService:
    """Create NovenaService bypassing __init__ to avoid OpenAI/config init."""
    svc = NovenaService.__new__(NovenaService)
    svc._model = "gpt-4o-mini"
    return svc


def _mock_tracking(
    tracking_id: str = "t-001",
    novena_id: str = "milosierdzie",
    intention: str | None = "moja intencja",
    mask: int = 0,
    is_complete: bool = False,
):
    t = MagicMock()
    t.id = tracking_id
    t.novena_id = novena_id
    t.intention = intention
    t.completed_days_mask = mask
    t.is_complete = is_complete
    t.started_at = None
    t.completed_at = None
    return t


# ---------------------------------------------------------------------------
# NOVENAS catalog
# ---------------------------------------------------------------------------


class TestNovenasCatalog:
    def test_eight_novenas(self):
        assert len(NOVENAS) == 8

    def test_all_have_required_fields(self):
        required = {"id", "title", "subtitle", "patron", "patron_icon", "days",
                    "scripture", "ccc", "daily_intentions", "daily_prayer"}
        for n in NOVENAS:
            assert required <= set(n.keys()), f"Missing fields in novena: {n['id']}"

    def test_unique_ids(self):
        ids = [n["id"] for n in NOVENAS]
        assert len(ids) == len(set(ids)), "Duplicate novena IDs"

    def test_all_have_9_days(self):
        for n in NOVENAS:
            assert n["days"] == 9, f"Novena {n['id']} has {n['days']} days"

    def test_all_have_9_intentions(self):
        for n in NOVENAS:
            assert len(n["daily_intentions"]) == 9, (
                f"Novena {n['id']} has {len(n['daily_intentions'])} intentions"
            )

    def test_milosierdzie_present(self):
        ids = {n["id"] for n in NOVENAS}
        assert "milosierdzie" in ids

    def test_all_titles_non_empty(self):
        for n in NOVENAS:
            assert n["title"].strip()

    def test_all_have_scripture_reference(self):
        for n in NOVENAS:
            assert n["scripture"].strip()

    def test_all_have_ccc_reference(self):
        for n in NOVENAS:
            assert n["ccc"].strip()


# ---------------------------------------------------------------------------
# get_all_novenas
# ---------------------------------------------------------------------------


class TestGetAllNovenas:
    def test_returns_8_items(self):
        svc = _service()
        result = svc.get_all_novenas()
        assert len(result) == 8

    def test_items_have_id_and_title(self):
        svc = _service()
        for item in svc.get_all_novenas():
            assert "id" in item
            assert "title" in item

    def test_items_do_not_have_daily_prayer(self):
        """Catalogue endpoint must be lightweight — no full prayer text."""
        svc = _service()
        for item in svc.get_all_novenas():
            assert "daily_prayer" not in item
            assert "daily_intentions" not in item

    def test_returns_list_of_dicts(self):
        svc = _service()
        result = svc.get_all_novenas()
        assert isinstance(result, list)
        assert all(isinstance(i, dict) for i in result)


# ---------------------------------------------------------------------------
# get_novena
# ---------------------------------------------------------------------------


class TestGetNovena:
    def test_returns_novena_by_id(self):
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        assert novena is not None
        assert novena["id"] == "milosierdzie"

    def test_returns_none_for_unknown_id(self):
        svc = _service()
        assert svc.get_novena("nonexistent_novena") is None

    def test_returns_full_data_including_daily_prayer(self):
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        assert "daily_prayer" in novena
        assert "daily_intentions" in novena


# ---------------------------------------------------------------------------
# get_day
# ---------------------------------------------------------------------------


class TestGetDay:
    def test_day_1_returns_first_intention(self):
        svc = _service()
        day = svc.get_day("milosierdzie", 1)
        assert day is not None
        assert day["day"] == 1
        assert "Dzień 1" in day["title"] or "1" in day["title"]

    def test_day_9_returns_last_intention(self):
        svc = _service()
        day = svc.get_day("milosierdzie", 9)
        assert day is not None
        assert day["day"] == 9

    def test_day_out_of_range_low(self):
        svc = _service()
        assert svc.get_day("milosierdzie", 0) is None

    def test_day_out_of_range_high(self):
        svc = _service()
        assert svc.get_day("milosierdzie", 10) is None

    def test_unknown_novena_returns_none(self):
        svc = _service()
        assert svc.get_day("ghost_novena", 1) is None

    def test_has_required_keys(self):
        svc = _service()
        day = svc.get_day("milosierdzie", 3)
        assert {"day", "title", "prayer", "patron", "novena_title"} <= set(day.keys())


# ---------------------------------------------------------------------------
# Bitmask logic via _tracking_to_dict
# ---------------------------------------------------------------------------


class TestBitmaskLogic:
    def test_empty_mask_no_completed_days(self):
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        t = _mock_tracking(mask=0)
        result = svc._tracking_to_dict(t, novena)
        assert result["completed_days"] == []
        assert result["progress_percent"] == 0

    def test_day_1_mask_is_bit_0(self):
        """Day 1 corresponds to bit 0 (value 1)."""
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        t = _mock_tracking(mask=1)  # bit 0 set
        result = svc._tracking_to_dict(t, novena)
        assert 1 in result["completed_days"]

    def test_day_9_mask_is_bit_8(self):
        """Day 9 corresponds to bit 8 (value 256)."""
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        t = _mock_tracking(mask=256)  # bit 8 set
        result = svc._tracking_to_dict(t, novena)
        assert 9 in result["completed_days"]

    def test_all_9_days_mask_is_511(self):
        """All 9 days completed: mask = 2^9 - 1 = 511."""
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        t = _mock_tracking(mask=511, is_complete=True)
        result = svc._tracking_to_dict(t, novena)
        assert result["completed_days"] == list(range(1, 10))
        assert result["progress_percent"] == 100

    def test_days_3_and_7_set(self):
        """Days 3 and 7 → mask = (1<<2) | (1<<6) = 4 + 64 = 68."""
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        mask = (1 << 2) | (1 << 6)  # days 3 and 7
        t = _mock_tracking(mask=mask)
        result = svc._tracking_to_dict(t, novena)
        assert set(result["completed_days"]) == {3, 7}

    def test_progress_percent_for_3_of_9(self):
        """3 of 9 days completed = 33%."""
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        # Days 1, 2, 3 = bits 0, 1, 2 = mask 7
        t = _mock_tracking(mask=7)
        result = svc._tracking_to_dict(t, novena)
        assert result["progress_percent"] == 33

    def test_total_days_is_9(self):
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        result = svc._tracking_to_dict(_mock_tracking(), novena)
        assert result["total_days"] == 9

    def test_is_complete_reflects_tracking(self):
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        t_done = _mock_tracking(mask=511, is_complete=True)
        result = svc._tracking_to_dict(t_done, novena)
        assert result["is_complete"] is True

    def test_intention_preserved(self):
        svc = _service()
        novena = svc.get_novena("milosierdzie")
        t = _mock_tracking(intention="Za moją rodzinę")
        result = svc._tracking_to_dict(t, novena)
        assert result["intention"] == "Za moją rodzinę"

    def test_none_novena_fallback(self):
        svc = _service()
        t = _mock_tracking(novena_id="ghost_id", mask=3)
        result = svc._tracking_to_dict(t, None)
        assert result["total_days"] == 9  # fallback
        assert result["novena_title"] == "ghost_id"  # uses novena_id
