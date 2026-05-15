"""Unit tests for app/main.py — router registration catalog.

No HTTP, no FastAPI startup — pure inspection of the _ROUTERS data structure.

Contracts verified:
_ROUTERS list:
- Is a list of 3-tuples (module_path, prefix, tags)
- Has at least 15 routers registered
- All module paths are non-empty strings starting with "app."
- All prefixes are non-empty strings starting with "/"
- All tags are non-empty lists of strings
- No duplicate module paths
- No duplicate prefixes
- Critical routes present (lectio-divina, auth, users, journal, admin)
- API routes start with /api/v1/ or /ws
"""

from __future__ import annotations

import sys
from unittest.mock import MagicMock

# Stub heavy deps before main.py imports
for _mod in [
    "neo4j", "qdrant_client", "qdrant_client.models",
    "jose", "jose.jwt", "jose.exceptions",
]:
    if _mod not in sys.modules:
        sys.modules[_mod] = MagicMock()

from app.main import _ROUTERS


# ===========================================================================
# _ROUTERS structure
# ===========================================================================


class TestRoutersList:
    def test_is_list(self):
        assert isinstance(_ROUTERS, list)

    def test_has_at_least_15_routers(self):
        assert len(_ROUTERS) >= 15

    def test_each_entry_is_3_tuple(self):
        for entry in _ROUTERS:
            assert len(entry) == 3, f"Entry {entry!r} is not a 3-tuple"

    def test_all_module_paths_are_strings(self):
        for module_path, _, _ in _ROUTERS:
            assert isinstance(module_path, str), f"Module path is not a string: {module_path!r}"

    def test_all_module_paths_start_with_app(self):
        for module_path, _, _ in _ROUTERS:
            assert module_path.startswith("app."), f"Unexpected module path: {module_path!r}"

    def test_all_prefixes_are_strings(self):
        for _, prefix, _ in _ROUTERS:
            assert isinstance(prefix, str), f"Prefix is not a string: {prefix!r}"

    def test_all_prefixes_start_with_slash(self):
        for _, prefix, _ in _ROUTERS:
            assert prefix.startswith("/"), f"Prefix doesn't start with /: {prefix!r}"

    def test_all_tags_are_non_empty_lists(self):
        for module_path, _, tags in _ROUTERS:
            assert isinstance(tags, list), f"{module_path} tags is not a list"
            assert len(tags) >= 1, f"{module_path} has empty tags list"

    def test_all_tag_values_are_strings(self):
        for module_path, _, tags in _ROUTERS:
            for tag in tags:
                assert isinstance(tag, str), f"{module_path} has non-string tag: {tag!r}"

    def test_no_duplicate_module_paths(self):
        paths = [m for m, _, _ in _ROUTERS]
        assert len(paths) == len(set(paths)), "Duplicate module paths found"

    def test_no_duplicate_prefixes(self):
        prefixes = [p for _, p, _ in _ROUTERS]
        assert len(prefixes) == len(set(prefixes)), "Duplicate prefixes found"

    def test_no_empty_module_paths(self):
        for module_path, _, _ in _ROUTERS:
            assert module_path.strip(), "Empty module path found"

    def test_no_empty_prefixes(self):
        for _, prefix, _ in _ROUTERS:
            assert prefix.strip(), "Empty prefix found"


# ===========================================================================
# Critical route presence
# ===========================================================================


def _prefixes():
    return {prefix for _, prefix, _ in _ROUTERS}


def _modules():
    return {module_path for module_path, _, _ in _ROUTERS}


class TestCriticalRoutesPresent:
    def test_lectio_divina_route(self):
        assert "/api/v1/lectio-divina" in _prefixes()

    def test_auth_route(self):
        assert "/api/v1/auth" in _prefixes()

    def test_users_route(self):
        assert "/api/v1/users" in _prefixes()

    def test_journal_route(self):
        assert "/api/v1/journal" in _prefixes()

    def test_admin_route(self):
        assert "/api/v1/admin" in _prefixes()

    def test_examen_route(self):
        assert "/api/v1/examen" in _prefixes()

    def test_bible_route(self):
        assert "/api/v1/bible" in _prefixes()

    def test_breviary_route(self):
        assert "/api/v1/breviary" in _prefixes()

    def test_community_route(self):
        assert "/api/v1/community" in _prefixes()

    def test_knowledge_route(self):
        assert "/api/v1/knowledge" in _prefixes()

    def test_billing_route(self):
        assert "/api/v1/billing" in _prefixes()

    def test_voice_route(self):
        assert "/api/v1/voice" in _prefixes()

    def test_websocket_route(self):
        assert "/ws" in _prefixes()

    def test_reflection_assistant_route(self):
        assert "/api/v1/reflection-assistant" in _prefixes()


class TestRouteModulePaths:
    def test_lectio_divina_module(self):
        assert "app.api.routes.lectio_divina" in _modules()

    def test_auth_module(self):
        assert "app.api.routes.auth" in _modules()

    def test_billing_module(self):
        assert "app.api.routes.billing" in _modules()

    def test_ws_rosary_module(self):
        assert "app.api.routes.ws_rosary" in _modules()


class TestRoutePrefixFormat:
    def test_api_routes_use_v1(self):
        for _, prefix, _ in _ROUTERS:
            if prefix != "/ws":
                assert prefix.startswith("/api/v1/"), (
                    f"Non-WebSocket route doesn't use /api/v1/: {prefix!r}"
                )
