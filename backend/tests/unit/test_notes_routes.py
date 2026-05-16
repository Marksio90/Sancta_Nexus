"""Unit tests for the /api/v1/notes endpoints."""

from __future__ import annotations

import json
import sys
from unittest.mock import MagicMock

for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
    "redis", "redis.asyncio",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()


from app.api.routes.notes import _get_notes, _set_notes, _load_profile, _save_profile
from app.models.database import User


def _make_user(profile_json: str | None = None) -> MagicMock:
    user = MagicMock(spec=User)
    user.spiritual_profile_json = profile_json
    return user


class TestLoadSaveProfile:
    def test_load_empty_returns_dict(self):
        user = _make_user(None)
        assert _load_profile(user) == {}

    def test_load_invalid_json_returns_dict(self):
        user = _make_user("not-json")
        assert _load_profile(user) == {}

    def test_load_valid_json(self):
        user = _make_user('{"key": "val"}')
        assert _load_profile(user) == {"key": "val"}

    def test_save_profile_writes_json(self):
        user = _make_user(None)
        _save_profile(user, {"a": 1})
        assert json.loads(user.spiritual_profile_json) == {"a": 1}

    def test_save_profile_preserves_unicode(self):
        user = _make_user(None)
        _save_profile(user, {"note": "Pójdź w pokoju"})
        assert "Pójdź" in user.spiritual_profile_json


class TestGetSetNotes:
    def test_get_notes_empty(self):
        user = _make_user(None)
        assert _get_notes(user) == {}

    def test_get_notes_from_profile(self):
        user = _make_user(json.dumps({"notes": {"j 3,16": "To jest ten werset"}}))
        notes = _get_notes(user)
        assert notes["j 3,16"] == "To jest ten werset"

    def test_set_notes_creates_notes_key(self):
        user = _make_user(None)
        _set_notes(user, {"rz 8,28": "Wszystko współdziała"})
        profile = json.loads(user.spiritual_profile_json)
        assert "notes" in profile
        assert profile["notes"]["rz 8,28"] == "Wszystko współdziała"

    def test_set_notes_preserves_other_profile_keys(self):
        user = _make_user(json.dumps({"progress_themes": [{"name": "peace", "count": 3}]}))
        _set_notes(user, {"ps 23,1": "Pan jest moim pasterzem"})
        profile = json.loads(user.spiritual_profile_json)
        assert "progress_themes" in profile
        assert profile["notes"]["ps 23,1"] == "Pan jest moim pasterzem"


class TestNotesRouteRegistration:
    def test_notes_router_has_expected_routes(self):
        from app.api.routes.notes import router

        paths = {r.path for r in router.routes}
        assert "" in paths or "/" in paths
        # At minimum the root and parameterised path must exist
        assert any("{ref" in p for p in paths)

    def test_notes_router_has_get_put_delete(self):
        from app.api.routes.notes import router

        methods = set()
        for route in router.routes:
            if hasattr(route, "methods"):
                methods.update(route.methods)
        assert "GET" in methods
        assert "PUT" in methods
        assert "DELETE" in methods
