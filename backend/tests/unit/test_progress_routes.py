"""Unit tests for the /api/v1/progress endpoints."""

from __future__ import annotations

import sys
from datetime import date, timedelta
from unittest.mock import MagicMock

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.api.routes.progress import (
    _compute_streak,
    _compute_journey,
    _load_themes,
    _save_themes,
    JourneyProgress,
)
from app.models.database import User


def _make_user(profile_json: str | None = None) -> MagicMock:
    user = MagicMock(spec=User)
    user.spiritual_profile_json = profile_json
    return user


class TestComputeStreak:
    def test_empty_sessions_returns_0(self):
        assert _compute_streak([]) == 0

    def test_single_today_returns_1(self):
        assert _compute_streak([date.today()]) == 1

    def test_consecutive_3_days(self):
        today = date.today()
        dates = [today, today - timedelta(days=1), today - timedelta(days=2)]
        assert _compute_streak(dates) == 3

    def test_gap_breaks_streak(self):
        today = date.today()
        dates = [today, today - timedelta(days=2)]  # gap of 1 day
        assert _compute_streak(dates) == 1

    def test_duplicate_dates_counted_once(self):
        today = date.today()
        # Two sessions on the same day count as one streak day
        dates = [today, today, today - timedelta(days=1)]
        assert _compute_streak(dates) == 2

    def test_yesterday_only_returns_0(self):
        # No session today → streak is broken
        yesterday = date.today() - timedelta(days=1)
        assert _compute_streak([yesterday]) == 0


class TestComputeJourney:
    def test_zero_sessions(self):
        j = _compute_journey(0)
        assert j == JourneyProgress(purgativa=0, illuminativa=0, unitiva=0)

    def test_10_sessions(self):
        j = _compute_journey(10)
        assert j.purgativa == 50.0
        assert j.illuminativa == 0.0

    def test_20_sessions_starts_illuminativa(self):
        j = _compute_journey(20)
        assert j.purgativa == 100.0
        assert j.illuminativa == 0.0

    def test_40_sessions_starts_unitiva(self):
        j = _compute_journey(40)
        assert j.purgativa == 100.0
        assert j.illuminativa == 100.0
        assert j.unitiva == 0.0

    def test_caps_at_100(self):
        j = _compute_journey(1000)
        assert j.purgativa == 100.0
        assert j.illuminativa == 100.0
        assert j.unitiva == 100.0


class TestThemes:
    def test_load_empty_returns_list(self):
        user = _make_user(None)
        assert _load_themes(user) == []

    def test_load_themes_from_profile(self):
        import json
        user = _make_user(json.dumps({"progress_themes": [{"name": "peace", "count": 5}]}))
        themes = _load_themes(user)
        assert themes[0]["name"] == "peace"
        assert themes[0]["count"] == 5

    def test_save_themes_writes_to_profile(self):
        import json
        user = _make_user(None)
        _save_themes(user, [{"name": "gratitude", "count": 3}])
        profile = json.loads(user.spiritual_profile_json)
        assert profile["progress_themes"][0]["name"] == "gratitude"

    def test_save_themes_preserves_other_keys(self):
        import json
        user = _make_user(json.dumps({"notes": {"j 3,16": "text"}}))
        _save_themes(user, [{"name": "joy", "count": 1}])
        profile = json.loads(user.spiritual_profile_json)
        assert "notes" in profile
        assert profile["progress_themes"][0]["name"] == "joy"


class TestProgressRouteRegistration:
    def test_progress_router_exists(self):
        from app.api.routes.progress import router
        assert router is not None

    def test_has_get_and_post(self):
        from app.api.routes.progress import router
        methods = set()
        for route in router.routes:
            if hasattr(route, "methods"):
                methods.update(route.methods)
        assert "GET" in methods
        assert "POST" in methods
