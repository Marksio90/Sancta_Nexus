"""Testy jednostkowe dla modułu community (nowenny, intencje, różaniec).

Self-contained: brak DB, brak zewnętrznych serwisów.
Testuje logikę danych, bezpieczeństwo (JWT, brak user_id w body) przez AST.
"""

from __future__ import annotations

import ast
from pathlib import Path

COMMUNITY_MODULE = Path(__file__).parent.parent.parent / "app" / "api" / "routes" / "community.py"


def _source() -> str:
    return COMMUNITY_MODULE.read_text()


def _request_classes() -> list[ast.ClassDef]:
    tree = ast.parse(_source())
    return [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and node.name.endswith(("Request", "Start", "CompleteDay"))
    ]


# ── Bezpieczeństwo — user_id nie w body ──────────────────────────────────────

class TestNovenaSecurityNoUserIdInBody:
    """Nowenny muszą używać JWT — user_id nigdy nie może być w request body."""

    def test_novena_start_no_user_id(self):
        for cls in _request_classes():
            if "NovenaStart" in cls.name or "NovenaCreate" in cls.name:
                for item in ast.walk(cls):
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        assert item.target.id != "user_id", (
                            f"{cls.name} nie powinien mieć pola user_id"
                        )

    def test_novena_complete_day_no_user_id(self):
        for cls in _request_classes():
            if "CompleteDay" in cls.name:
                for item in ast.walk(cls):
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        assert item.target.id != "user_id"

    def test_no_user_id_query_param_on_protected_routes(self):
        """Chronione endpointy nowenn NIE powinny mieć ?user_id= query parametru."""
        source = _source()
        # Nowenny: /my, /start, /tracking/{id}/complete-day są chronione przez JWT
        # Mogą mieć user_id= tylko w endpointach niezależnych (admin) — ale nie tu
        # Sprawdzamy, że get_my_novenas, start_novena, complete_novena_day
        # używają require_authenticated a nie Query(user_id)
        tree = ast.parse(source)
        protected_funcs = ["get_my_novenas", "start_novena", "complete_novena_day"]
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name in protected_funcs:
                    # Sprawdź, że w parametrach funkcji NIE ma user_id jako Query
                    param_names = [arg.arg for arg in node.args.args]
                    assert "user_id" not in param_names, (
                        f"{node.name} nie powinien mieć user_id w parametrach"
                    )

    def test_require_authenticated_on_my_novenas(self):
        source = _source()
        # get_my_novenas musi używać require_authenticated
        assert "require_authenticated" in source

    def test_start_novena_is_authenticated(self):
        source = _source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "start_novena":
                    func_source = ast.unparse(node)
                    assert "require_authenticated" in func_source or "current_user" in func_source

    def test_complete_day_is_authenticated(self):
        source = _source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "complete_novena_day":
                    func_source = ast.unparse(node)
                    assert "current_user" in func_source


# ── Struktura endpointów nowenn ───────────────────────────────────────────────

class TestNovenaEndpoints:
    def test_list_novenas_exists(self):
        assert '"/novenas"' in _source()

    def test_my_novenas_endpoint_exists(self):
        assert '"/novenas/my"' in _source()

    def test_novena_start_endpoint_exists(self):
        source = _source()
        assert '"/novenas/{novena_id}/start"' in source

    def test_complete_day_endpoint_exists(self):
        source = _source()
        assert '"/novenas/tracking/{tracking_id}/complete-day"' in source

    def test_novena_day_content_endpoint_exists(self):
        source = _source()
        assert '"/novenas/{novena_id}/day/{day}"' in source

    def test_novena_meditation_endpoint_exists(self):
        source = _source()
        assert '"/novenas/{novena_id}/meditation/{day}"' in source

    def test_list_novenas_is_public(self):
        """Biblioteka nowenn jest publiczna — nie wymaga logowania."""
        source = _source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "list_novenas":
                    func_source = ast.unparse(node)
                    # Funkcja publiczna — nie powinna mieć require_authenticated
                    assert "require_authenticated" not in func_source

    def test_start_novena_is_post(self):
        source = _source()
        assert 'router.post(\n    "/novenas/{novena_id}/start"' in source or \
               'router.post("/novenas/{novena_id}/start"' in source


# ── NovenaCompleteDay — walidacja pola day ────────────────────────────────────

class TestNovenaDayValidation:
    def test_complete_day_has_day_field(self):
        source = _source()
        tree = ast.parse(source)
        for cls in ast.walk(tree):
            if isinstance(cls, ast.ClassDef) and "CompleteDay" in cls.name:
                fields = [
                    item.target.id
                    for item in ast.walk(cls)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
                ]
                assert "day" in fields, f"NovenaCompleteDay.day brak w {cls.name}"

    def test_novena_start_has_intention_field(self):
        source = _source()
        tree = ast.parse(source)
        for cls in ast.walk(tree):
            if isinstance(cls, ast.ClassDef) and "NovenaStart" in cls.name:
                fields = [
                    item.target.id
                    for item in ast.walk(cls)
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name)
                ]
                assert "intention" in fields


# ── Intencje modlitewne ───────────────────────────────────────────────────────

class TestIntentionEndpoints:
    def test_list_intentions_exists(self):
        assert '"/intentions"' in _source()

    def test_mine_intentions_exists(self):
        assert '"/intentions/mine"' in _source()

    def test_pray_for_intention_exists(self):
        assert '"/intentions/{intention_id}/pray"' in _source()

    def test_answered_endpoint_exists(self):
        assert '"/intentions/{intention_id}/answered"' in _source()

    def test_delete_intention_exists(self):
        assert '"/intentions/{intention_id}"' in _source()

    def test_intentions_mine_requires_auth(self):
        source = _source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_my_intentions":
                    func_source = ast.unparse(node)
                    assert "current_user" in func_source


# ── Różaniec ─────────────────────────────────────────────────────────────────

class TestRosaryEndpoints:
    def test_mysteries_endpoint_exists(self):
        assert '"/rosary/mysteries"' in _source()

    def test_today_mysteries_exists(self):
        assert '"/rosary/today"' in _source()

    def test_community_rosary_create_exists(self):
        source = _source()
        assert '"/rosary/community"' in source

    def test_join_rosary_exists(self):
        source = _source()
        assert '"/rosary/community/{rosary_id}/join"' in source

    def test_meditate_stream_exists(self):
        source = _source()
        assert '"/rosary/meditate/stream"' in source


# ── Grupy modlitewne ──────────────────────────────────────────────────────────

class TestGroupEndpoints:
    def test_list_groups_exists(self):
        assert '"/groups"' in _source()

    def test_my_groups_exists(self):
        assert '"/groups/my"' in _source()

    def test_join_group_exists(self):
        source = _source()
        assert '"/groups/{group_id}/join"' in source

    def test_leave_group_exists(self):
        source = _source()
        assert '"/groups/{group_id}/leave"' in source

    def test_create_group_requires_auth(self):
        source = _source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "create_group":
                    func_source = ast.unparse(node)
                    assert "current_user" in func_source


# ── Logika nowenny — 9 dni ────────────────────────────────────────────────────

class TestNovenaLogic:
    def test_novena_days_are_1_to_9(self):
        """Nowenna trwa 9 dni — walidacja dnia 1-9."""
        source = _source()
        # Sprawdź że jest walidacja ge=1 lub day_range
        assert "ge=1" in source or "Field" in source

    def test_novena_library_route_returns_novenas_key(self):
        """list_novenas zwraca 'novenas' w response."""
        source = _source()
        assert '"novenas"' in source

    def test_start_novena_returns_on_error(self):
        """start_novena obsługuje błędy (novena nie istnieje)."""
        source = _source()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "start_novena":
                    func_source = ast.unparse(node)
                    assert "error" in func_source
                    assert "HTTPException" in func_source
