"""Unit tests for app/api/routes/bible.py.

Contracts verified (all AST-based — no DB/infra required):
- All 4 endpoints present with correct HTTP methods
- All endpoints are public (no authentication required — catechetical resource)
- No user_id in AskRequest
- AskRequest field constraints (max_passages bounded)
- FourDimensionalResponse has all 4 senses (patristic exegesis)
- Search response has results + total_results
- PassageResponse has expected fields
- Random verse endpoint exists and is GET
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

BIBLE_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "bible.py"
SRC = BIBLE_PATH.read_text()
TREE = ast.parse(SRC)


# ── AST helpers ───────────────────────────────────────────────────────────────


def _route_decorators() -> dict[str, list[tuple[str, str]]]:
    result: dict[str, list[tuple[str, str]]] = {}
    for node in ast.walk(TREE):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        routes: list[tuple[str, str]] = []
        for dec in node.decorator_list:
            if not isinstance(dec, ast.Call):
                continue
            func = dec.func
            if not isinstance(func, ast.Attribute):
                continue
            if not (isinstance(func.value, ast.Name) and func.value.id == "router"):
                continue
            method = func.attr.upper()
            path_arg = dec.args[0] if dec.args else None
            path = (
                ast.literal_eval(path_arg)
                if path_arg and isinstance(path_arg, ast.Constant)
                else "?"
            )
            routes.append((method, path))
        if routes:
            result[node.name] = routes
    return result


def _model_fields(model_name: str) -> set[str]:
    fields: set[str] = set()
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ClassDef) or node.name != model_name:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.add(stmt.target.id)
    return fields


def _model_source(model_name: str) -> str:
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ClassDef) or node.name != model_name:
            continue
        lines = SRC.splitlines()
        return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def _function_source(func_name: str) -> str:
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            lines = SRC.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


def _uses_require_authenticated(func_name: str) -> bool:
    for node in ast.walk(TREE):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func_name:
            continue
        all_args = node.args.args
        all_defaults = (
            [None] * (len(all_args) - len(node.args.defaults))
        ) + node.args.defaults
        for _arg, default in zip(all_args, all_defaults):
            if isinstance(default, ast.Name) and default.id == "require_authenticated":
                return True
    return False


ROUTES = _route_decorators()


# ── Endpoint presence ─────────────────────────────────────────────────────────


class TestEndpointPresence:
    def test_ask_scripture_exists(self):
        assert "ask_scripture" in ROUTES

    def test_get_passage_exists(self):
        assert "get_passage" in ROUTES

    def test_search_scripture_exists(self):
        assert "search_scripture" in ROUTES

    def test_get_random_verse_exists(self):
        assert "get_random_verse" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_ask_scripture_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["ask_scripture"])

    def test_get_passage_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_passage"])

    def test_search_scripture_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["search_scripture"])

    def test_get_random_verse_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_random_verse"])


# ── Public access ─────────────────────────────────────────────────────────────


class TestPublicAccess:
    """Bible resources are public catechetical content — no authentication required."""

    @pytest.mark.parametrize("func_name", [
        "ask_scripture",
        "get_passage",
        "search_scripture",
        "get_random_verse",
    ])
    def test_endpoint_is_public(self, func_name: str):
        assert not _uses_require_authenticated(func_name), (
            f"{func_name} must be public — Bible is a catechetical resource"
        )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInBodies:
    def test_ask_request_no_user_id(self):
        fields = _model_fields("AskRequest")
        assert "user_id" not in fields

    def test_ask_request_has_question(self):
        assert "question" in _model_fields("AskRequest")

    def test_ask_request_has_translation(self):
        assert "translation" in _model_fields("AskRequest")


# ── Request field constraints ─────────────────────────────────────────────────


class TestRequestConstraints:
    def test_max_passages_bounded(self):
        """max_passages must have ge=1 and le=20 to prevent abuse."""
        src = _model_source("AskRequest")
        assert "ge=1" in src or "ge = 1" in src
        assert "le=20" in src or "le = 20" in src

    def test_ask_request_has_include_magisterium(self):
        """Magisterium references toggle — enables richer theological responses."""
        assert "include_magisterium" in _model_fields("AskRequest")

    def test_ask_request_has_include_patristic(self):
        """Patristic references toggle — Fathers of the Church citations."""
        assert "include_patristic" in _model_fields("AskRequest")


# ── Four-dimensional response ─────────────────────────────────────────────────


class TestFourDimensionalResponse:
    """The four senses of scripture (patristic exegesis tradition)."""

    def test_response_has_literal_sense(self):
        assert "literal_sense" in _model_fields("FourDimensionalResponse")

    def test_response_has_allegorical_sense(self):
        assert "allegorical_sense" in _model_fields("FourDimensionalResponse")

    def test_response_has_moral_sense(self):
        assert "moral_sense" in _model_fields("FourDimensionalResponse")

    def test_response_has_anagogical_sense(self):
        assert "anagogical_sense" in _model_fields("FourDimensionalResponse")

    def test_response_has_passages(self):
        assert "passages" in _model_fields("FourDimensionalResponse")

    def test_response_has_magisterium_references(self):
        assert "magisterium_references" in _model_fields("FourDimensionalResponse")

    def test_response_has_patristic_references(self):
        assert "patristic_references" in _model_fields("FourDimensionalResponse")

    def test_response_has_question(self):
        assert "question" in _model_fields("FourDimensionalResponse")


# ── Passage response ──────────────────────────────────────────────────────────


class TestPassageResponse:
    def test_passage_response_has_book(self):
        assert "book" in _model_fields("PassageResponse")

    def test_passage_response_has_chapter(self):
        assert "chapter" in _model_fields("PassageResponse")

    def test_passage_response_has_verses(self):
        assert "verses" in _model_fields("PassageResponse")

    def test_passage_response_has_translation(self):
        assert "translation" in _model_fields("PassageResponse")

    def test_get_passage_has_path_params(self):
        paths = [p for _, p in ROUTES.get("get_passage", [])]
        assert any("{" in p for p in paths)


# ── Search response ───────────────────────────────────────────────────────────


class TestSearchResponse:
    def test_search_response_has_results(self):
        assert "results" in _model_fields("SearchResponse")

    def test_search_response_has_total_results(self):
        assert "total_results" in _model_fields("SearchResponse")

    def test_search_response_has_query(self):
        assert "query" in _model_fields("SearchResponse")

    def test_search_result_item_has_reference(self):
        assert "reference" in _model_fields("SearchResultItem")

    def test_search_result_item_has_score(self):
        assert "score" in _model_fields("SearchResultItem")

    def test_search_result_item_has_content(self):
        assert "content" in _model_fields("SearchResultItem")
