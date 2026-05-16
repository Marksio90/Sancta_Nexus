"""Unit tests for app/api/routes/knowledge.py.

Contracts verified (AST-based — no DB/Qdrant required):
- All 8 endpoints present with correct HTTP methods
- All endpoints are public (catechetical knowledge base, no auth required)
- No user_id in any request body
- SearchRequest field constraints (query min/max_length, limit bounded, min_score bounded)
- SearchResponse has expected pagination fields
- KnowledgeResult has citation and theology_tags (patristic richness)
- CrossReferenceRequest has reference field
- Lazy RAG loading (_get_rag helper)
- Document endpoint has path parameter
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

KNOWLEDGE_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "knowledge.py"
SRC = KNOWLEDGE_PATH.read_text()
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
        for _arg, default in zip(all_args, all_defaults, strict=False):
            if isinstance(default, ast.Name) and default.id == "require_authenticated":
                return True
    return False


ROUTES = _route_decorators()


# ── Endpoint presence ─────────────────────────────────────────────────────────


class TestEndpointPresence:
    def test_search_knowledge_exists(self):
        assert "search_knowledge" in ROUTES

    def test_list_collections_exists(self):
        assert "list_collections" in ROUTES

    def test_get_collection_exists(self):
        assert "get_collection" in ROUTES

    def test_get_document_chunks_exists(self):
        assert "get_document_chunks" in ROUTES

    def test_knowledge_stats_exists(self):
        assert "knowledge_stats" in ROUTES

    def test_cross_reference_exists(self):
        assert "cross_reference" in ROUTES

    def test_search_scripture_exists(self):
        assert "search_scripture" in ROUTES

    def test_search_catechism_exists(self):
        assert "search_catechism" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_search_knowledge_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["search_knowledge"])

    def test_list_collections_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["list_collections"])

    def test_get_collection_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_collection"])

    def test_get_document_chunks_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_document_chunks"])

    def test_knowledge_stats_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["knowledge_stats"])

    def test_cross_reference_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["cross_reference"])

    def test_search_scripture_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["search_scripture"])

    def test_search_catechism_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["search_catechism"])


# ── Public access ─────────────────────────────────────────────────────────────


class TestPublicAccess:
    """Church knowledge base is public catechetical content — no auth required."""

    @pytest.mark.parametrize("func_name", [
        "search_knowledge",
        "list_collections",
        "get_collection",
        "get_document_chunks",
        "knowledge_stats",
        "cross_reference",
        "search_scripture",
        "search_catechism",
    ])
    def test_endpoint_is_public(self, func_name: str):
        assert not _uses_require_authenticated(func_name), (
            f"{func_name} must be public — Church knowledge base is catechetical"
        )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInBodies:
    def test_search_request_no_user_id(self):
        assert "user_id" not in _model_fields("SearchRequest")

    def test_cross_reference_request_no_user_id(self):
        assert "user_id" not in _model_fields("CrossReferenceRequest")


# ── SearchRequest constraints ─────────────────────────────────────────────────


class TestSearchRequestConstraints:
    def test_query_has_min_length(self):
        src = _model_source("SearchRequest")
        assert "min_length=3" in src or "min_length = 3" in src

    def test_query_has_max_length(self):
        src = _model_source("SearchRequest")
        assert "max_length=1000" in src or "max_length = 1000" in src

    def test_limit_is_bounded(self):
        src = _model_source("SearchRequest")
        assert "ge=1" in src or "ge = 1" in src
        assert "le=20" in src or "le = 20" in src

    def test_min_score_is_bounded(self):
        src = _model_source("SearchRequest")
        assert "ge=0" in src or "ge=0.0" in src
        assert "le=1" in src or "le=1.0" in src

    def test_search_request_has_collections(self):
        assert "collections" in _model_fields("SearchRequest")

    def test_search_request_has_tradition(self):
        assert "tradition" in _model_fields("SearchRequest")

    def test_search_request_has_filters(self):
        assert "filters" in _model_fields("SearchRequest")


# ── SearchResponse ────────────────────────────────────────────────────────────


class TestSearchResponse:
    def test_response_has_results(self):
        assert "results" in _model_fields("SearchResponse")

    def test_response_has_total_results(self):
        assert "total_results" in _model_fields("SearchResponse")

    def test_response_has_query(self):
        assert "query" in _model_fields("SearchResponse")

    def test_response_has_collections_searched(self):
        assert "collections_searched" in _model_fields("SearchResponse")

    def test_response_has_routed_automatically(self):
        assert "routed_automatically" in _model_fields("SearchResponse")


# ── KnowledgeResult ───────────────────────────────────────────────────────────


class TestKnowledgeResult:
    def test_result_has_content(self):
        assert "content" in _model_fields("KnowledgeResult")

    def test_result_has_score(self):
        assert "score" in _model_fields("KnowledgeResult")

    def test_result_has_collection(self):
        assert "collection" in _model_fields("KnowledgeResult")

    def test_result_has_citation(self):
        """Citation field enables quoting sources (CCC, scripture, encyclicals)."""
        assert "citation" in _model_fields("KnowledgeResult")

    def test_result_has_theology_tags(self):
        """Theology tags allow filtering by doctrinal category."""
        assert "theology_tags" in _model_fields("KnowledgeResult")

    def test_result_has_tradition_tags(self):
        assert "tradition_tags" in _model_fields("KnowledgeResult")

    def test_result_has_doc_type(self):
        assert "doc_type" in _model_fields("KnowledgeResult")


# ── CrossReferenceRequest ─────────────────────────────────────────────────────


class TestCrossReferenceRequest:
    def test_has_reference_field(self):
        assert "reference" in _model_fields("CrossReferenceRequest")

    def test_has_content_field(self):
        assert "content" in _model_fields("CrossReferenceRequest")

    def test_has_include_collections(self):
        assert "include_collections" in _model_fields("CrossReferenceRequest")


# ── Path parameters ───────────────────────────────────────────────────────────


class TestPathParameters:
    def test_get_collection_has_path_param(self):
        paths = [p for _, p in ROUTES.get("get_collection", [])]
        assert any("{" in p for p in paths)

    def test_get_document_chunks_has_path_param(self):
        paths = [p for _, p in ROUTES.get("get_document_chunks", [])]
        assert any("{" in p for p in paths)


# ── Lazy RAG loading ──────────────────────────────────────────────────────────


class TestLazyRagLoading:
    def test_get_rag_helper_exists(self):
        assert "_get_rag" in SRC

    def test_search_knowledge_uses_rag(self):
        src = _function_source("search_knowledge")
        assert "_get_rag" in src or "rag" in src.lower()
