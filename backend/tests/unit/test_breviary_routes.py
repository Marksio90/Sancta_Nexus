"""Testy jednostkowe dla breviary.py — saint-today, daily-engagement.

Sprawdzamy:
  - Endpointy istnieją i mają właściwą metodę HTTP
  - /saint-today zwraca wszystkie wymagane pola
  - /daily-engagement zwraca pełną strukturę (liturgical, saint, morning_prayer, suggested_practices)
  - Sugerowane praktyki prowadzą do właściwych tras
  - Endpoint nie wymaga JWT (jest publiczny)
  - Modlitwy poranne istnieją dla wszystkich 5 sezonów
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

BREVIARY_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "breviary.py"
sys.path.insert(0, str(Path(__file__).parents[2]))


# ── AST helpers ───────────────────────────────────────────────────────────────


def _parse_tree() -> ast.Module:
    return ast.parse(BREVIARY_PATH.read_text())


def _get_route_decorators(tree: ast.Module) -> list[tuple[str, str]]:
    """Zwraca listę (method, path) ze wszystkich dekoratorów @router.*"""
    routes = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    method = dec.func.attr  # get/post/delete…
                    args = dec.args
                    if args and isinstance(args[0], ast.Constant):
                        routes.append((method, args[0].value))
    return routes


# ── Endpointy ─────────────────────────────────────────────────────────────────


class TestBreviaryEndpoints:
    def test_saint_today_endpoint_exists(self):
        routes = _get_route_decorators(_parse_tree())
        assert any(path == "/saint-today" for _, path in routes)

    def test_daily_engagement_endpoint_exists(self):
        routes = _get_route_decorators(_parse_tree())
        assert any(path == "/daily-engagement" for _, path in routes)

    def test_saint_today_is_get(self):
        routes = _get_route_decorators(_parse_tree())
        assert ("get", "/saint-today") in routes

    def test_daily_engagement_is_get(self):
        routes = _get_route_decorators(_parse_tree())
        assert ("get", "/daily-engagement") in routes

    def test_hours_endpoint_exists(self):
        routes = _get_route_decorators(_parse_tree())
        assert any("/hours/" in path or "hour_id" in path for _, path in routes)

    def test_today_endpoint_exists(self):
        routes = _get_route_decorators(_parse_tree())
        assert any(path == "/today" for _, path in routes)

    def test_no_require_authenticated_on_saint_today(self):
        source = BREVIARY_PATH.read_text()
        # saint-today jest publiczne — sprawdź że JWT nie jest wymagane
        lines = source.split("\n")
        saint_today_line = None
        for i, line in enumerate(lines):
            if '"/saint-today"' in line:
                saint_today_line = i
                break
        assert saint_today_line is not None
        # Funkcja powinna być prosta — bez require_authenticated w jej sygnaturze
        func_lines = lines[saint_today_line: saint_today_line + 10]
        func_text = " ".join(func_lines)
        assert "require_authenticated" not in func_text


# ── Struktura odpowiedzi saint-today ─────────────────────────────────────────


class TestSaintTodayResponse:
    def test_returns_date_field(self):
        import asyncio
        from app.api.routes.breviary import get_saint_of_day
        result = asyncio.run(get_saint_of_day())
        assert "date" in result

    def test_returns_name_field(self):
        import asyncio
        from app.api.routes.breviary import get_saint_of_day
        result = asyncio.run(get_saint_of_day())
        assert "name" in result and result["name"]

    def test_returns_description_field(self):
        import asyncio
        from app.api.routes.breviary import get_saint_of_day
        result = asyncio.run(get_saint_of_day())
        assert "description" in result and result["description"]

    def test_returns_icon_field(self):
        import asyncio
        from app.api.routes.breviary import get_saint_of_day
        result = asyncio.run(get_saint_of_day())
        assert "icon" in result and result["icon"]

    def test_returns_patronage_field(self):
        import asyncio
        from app.api.routes.breviary import get_saint_of_day
        result = asyncio.run(get_saint_of_day())
        assert "patronage" in result

    def test_returns_died_field(self):
        import asyncio
        from app.api.routes.breviary import get_saint_of_day
        result = asyncio.run(get_saint_of_day())
        assert "died" in result


# ── Struktura daily-engagement ────────────────────────────────────────────────


class TestDailyEngagementResponse:
    @pytest.fixture(scope="class")
    def engagement(self):
        import asyncio
        from app.api.routes.breviary import get_daily_engagement
        return asyncio.run(get_daily_engagement())

    def test_has_date(self, engagement):
        assert "date" in engagement

    def test_has_liturgical(self, engagement):
        assert "liturgical" in engagement
        lit = engagement["liturgical"]
        assert "season" in lit
        assert "color" in lit

    def test_liturgical_season_is_valid(self, engagement):
        valid_seasons = {"advent", "christmas", "lent", "easter", "ordinary"}
        assert engagement["liturgical"]["season"] in valid_seasons

    def test_has_saint(self, engagement):
        assert "saint" in engagement
        saint = engagement["saint"]
        assert "name" in saint
        assert "icon" in saint

    def test_has_morning_prayer(self, engagement):
        assert "morning_prayer" in engagement
        assert engagement["morning_prayer"]

    def test_has_suggested_practices(self, engagement):
        assert "suggested_practices" in engagement
        assert len(engagement["suggested_practices"]) == 4

    def test_suggested_practices_have_required_fields(self, engagement):
        for practice in engagement["suggested_practices"]:
            assert "label" in practice
            assert "href" in practice
            assert "icon" in practice

    def test_practices_link_to_core_modules(self, engagement):
        hrefs = {p["href"] for p in engagement["suggested_practices"]}
        assert "/lectio-divina" in hrefs
        assert "/rozaniec" in hrefs or "/rachunek-sumienia" in hrefs


# ── Modlitwy poranne ──────────────────────────────────────────────────────────


class TestMorningPrayers:
    def test_source_has_all_five_seasons(self):
        source = BREVIARY_PATH.read_text()
        for season in ("advent", "christmas", "lent", "easter", "ordinary"):
            assert f'"{season}"' in source, f"Brak modlitwy dla sezonu: {season}"

    def test_morning_prayer_maranatha_in_advent(self):
        source = BREVIARY_PATH.read_text()
        assert "Maranatha" in source or "Przyjdź Panie" in source

    def test_morning_prayer_alleluja_in_easter(self):
        source = BREVIARY_PATH.read_text()
        assert "Alleluja" in source


# ── Import saints_calendar ────────────────────────────────────────────────────


class TestBreviaryUsesCalendar:
    def test_imports_get_saint_today(self):
        tree = _parse_tree()
        imports = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                for alias in node.names:
                    imports.append(alias.name)
        assert "get_saint_today" in imports

    def test_imports_from_saints_calendar_module(self):
        source = BREVIARY_PATH.read_text()
        assert "saints_calendar" in source
