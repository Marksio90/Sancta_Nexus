"""Unit tests for app/api/routes/lectio_divina.py.

Contracts verified (all AST-based — no DB/Redis/LLM required):
- All endpoints present with correct HTTP methods
- Protected endpoints require require_authenticated
- get_scripture_for_date is public (liturgical data, no personal info)
- No user_id in any request body (JWT-only identity)
- Request model field constraints
- Response schemas contain expected fields, no sensitive data
- Session ownership enforced (403 forbidden for wrong user)
- 404 for missing/expired sessions
- 409 for duplicate favorites
- Five stages of Lectio Divina referenced in source
- Favorites CRUD complete
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

LECTIO_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "lectio_divina.py"
SRC = LECTIO_PATH.read_text()
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
    def test_start_session_exists(self):
        assert "start_session" in ROUTES

    def test_complete_session_exists(self):
        assert "complete_session" in ROUTES

    def test_analyze_emotion_exists(self):
        assert "analyze_emotion" in ROUTES

    def test_get_scripture_for_date_exists(self):
        assert "get_scripture_for_date" in ROUTES

    def test_submit_reflection_exists(self):
        assert "submit_reflection" in ROUTES

    def test_get_spiritual_journey_exists(self):
        assert "get_spiritual_journey" in ROUTES

    def test_get_spiritual_patterns_exists(self):
        assert "get_spiritual_patterns" in ROUTES

    def test_get_session_history_exists(self):
        assert "get_session_history" in ROUTES

    def test_run_lectio_pipeline_exists(self):
        assert "run_lectio_pipeline" in ROUTES

    def test_add_favorite_exists(self):
        assert "add_favorite" in ROUTES

    def test_list_favorites_exists(self):
        assert "list_favorites" in ROUTES

    def test_remove_favorite_exists(self):
        assert "remove_favorite" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_start_session_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["start_session"])

    def test_complete_session_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["complete_session"])

    def test_analyze_emotion_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["analyze_emotion"])

    def test_get_scripture_for_date_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_scripture_for_date"])

    def test_submit_reflection_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["submit_reflection"])

    def test_get_spiritual_journey_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_spiritual_journey"])

    def test_get_spiritual_patterns_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_spiritual_patterns"])

    def test_get_session_history_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_session_history"])

    def test_run_lectio_pipeline_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["run_lectio_pipeline"])

    def test_add_favorite_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["add_favorite"])

    def test_list_favorites_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["list_favorites"])

    def test_remove_favorite_is_delete(self):
        assert any(m == "DELETE" for m, _ in ROUTES["remove_favorite"])


# ── Auth guard ────────────────────────────────────────────────────────────────


class TestAuthGuard:
    @pytest.mark.parametrize("func_name", [
        "start_session",
        "complete_session",
        "analyze_emotion",
        "submit_reflection",
        "get_spiritual_journey",
        "get_spiritual_patterns",
        "get_session_history",
        "run_lectio_pipeline",
        "add_favorite",
        "list_favorites",
        "remove_favorite",
    ])
    def test_endpoint_requires_auth(self, func_name: str):
        assert _uses_require_authenticated(func_name), (
            f"{func_name} must use require_authenticated — Lectio Divina sessions are personal"
        )

    def test_get_scripture_for_date_is_public(self):
        """Liturgical calendar data is public — no login needed to see today's readings."""
        assert not _uses_require_authenticated("get_scripture_for_date"), (
            "get_scripture_for_date must be public (liturgical data)"
        )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInBodies:
    def test_start_session_no_user_id(self):
        assert "user_id" not in _model_fields("StartSessionRequest")

    def test_complete_session_no_user_id(self):
        assert "user_id" not in _model_fields("CompleteSessionRequest")

    def test_emotion_input_no_user_id(self):
        assert "user_id" not in _model_fields("EmotionInputRequest")

    def test_reflection_request_no_user_id(self):
        assert "user_id" not in _model_fields("ReflectionRequest")

    def test_favorite_request_no_user_id(self):
        assert "user_id" not in _model_fields("FavoritePassageRequest")

    def test_run_pipeline_request_no_user_id(self):
        assert "user_id" not in _model_fields("RunPipelineRequest")


# ── Request model field constraints ──────────────────────────────────────────


class TestRequestConstraints:
    def test_favorite_book_has_min_max_length(self):
        src = _model_source("FavoritePassageRequest")
        assert "min_length=1" in src or "min_length = 1" in src
        assert "max_length=64" in src or "max_length = 64" in src

    def test_favorite_reference_has_max_length(self):
        src = _model_source("FavoritePassageRequest")
        assert "max_length=128" in src or "max_length = 128" in src

    def test_favorite_excerpt_has_max_length(self):
        src = _model_source("FavoritePassageRequest")
        assert "max_length=512" in src or "max_length = 512" in src

    def test_favorite_chapter_is_positive(self):
        src = _model_source("FavoritePassageRequest")
        assert "ge=1" in src or "ge = 1" in src

    def test_reflection_request_has_stage(self):
        assert "stage" in _model_fields("ReflectionRequest")

    def test_reflection_request_has_reflection_text(self):
        assert "reflection_text" in _model_fields("ReflectionRequest")


# ── Response schema ───────────────────────────────────────────────────────────


class TestResponseSchema:
    def test_session_response_has_session_id(self):
        assert "session_id" in _model_fields("SessionResponse")

    def test_session_response_has_status(self):
        assert "status" in _model_fields("SessionResponse")

    def test_session_response_has_stage(self):
        assert "stage" in _model_fields("SessionResponse")

    def test_session_response_has_user_id(self):
        """SessionResponse exposes user_id (it's the authenticated user's own id — not a privacy leak)."""
        assert "user_id" in _model_fields("SessionResponse")

    def test_favorite_response_has_id(self):
        assert "id" in _model_fields("FavoritePassageResponse")

    def test_favorite_response_has_reference(self):
        assert "reference" in _model_fields("FavoritePassageResponse")

    def test_favorite_response_has_created_at(self):
        assert "created_at" in _model_fields("FavoritePassageResponse")

    def test_run_pipeline_response_has_scripture(self):
        assert "scripture" in _model_fields("RunPipelineResponse")

    def test_run_pipeline_response_has_journey(self):
        """Journey tracking (A-036) must be included in the pipeline response."""
        assert "journey" in _model_fields("RunPipelineResponse")

    def test_run_pipeline_response_has_error(self):
        """Errors in the AI pipeline must surface to the client."""
        assert "error" in _model_fields("RunPipelineResponse")

    def test_emotion_response_has_primary_emotion(self):
        assert "primary_emotion" in _model_fields("EmotionResponse")

    def test_emotion_response_has_spiritual_state(self):
        assert "spiritual_state" in _model_fields("EmotionResponse")

    def test_emotion_response_has_suggested_scripture(self):
        assert "suggested_scripture" in _model_fields("EmotionResponse")

    def test_complete_response_has_db_session_id(self):
        assert "db_session_id" in _model_fields("CompleteSessionResponse")


# ── Five stages of Lectio Divina ──────────────────────────────────────────────


class TestLectioDivinaStages:
    @pytest.mark.parametrize("stage", ["lectio", "meditatio", "oratio", "contemplatio", "actio"])
    def test_stage_referenced_in_source(self, stage: str):
        assert stage in SRC, f"Stage '{stage}' must be referenced in lectio_divina.py"

    def test_stage_order_defined(self):
        assert "_STAGE_ORDER" in SRC

    def test_stage_validation_raises_400(self):
        src = _function_source("submit_reflection")
        assert "400" in src or "HTTP_400_BAD_REQUEST" in src

    def test_reflection_advances_stage(self):
        src = _function_source("submit_reflection")
        assert "next_stage" in src

    def test_reflection_response_has_guidance(self):
        assert "guidance" in _model_fields("ReflectionResponse")


# ── Session ownership ─────────────────────────────────────────────────────────


class TestSessionOwnership:
    def test_complete_session_checks_ownership(self):
        src = _function_source("complete_session")
        assert "user_id" in src or "current_user" in src

    def test_complete_session_raises_403_for_wrong_user(self):
        src = _function_source("complete_session")
        assert "403" in src or "HTTP_403_FORBIDDEN" in src

    def test_submit_reflection_checks_ownership(self):
        src = _function_source("submit_reflection")
        assert "user_id" in src or "current_user" in src

    def test_submit_reflection_raises_403_for_wrong_user(self):
        src = _function_source("submit_reflection")
        assert "403" in src or "HTTP_403_FORBIDDEN" in src

    def test_complete_session_raises_404_for_missing(self):
        src = _function_source("complete_session")
        assert "404" in src or "HTTP_404_NOT_FOUND" in src

    def test_submit_reflection_raises_404_for_missing(self):
        src = _function_source("submit_reflection")
        assert "404" in src or "HTTP_404_NOT_FOUND" in src


# ── Favorites ─────────────────────────────────────────────────────────────────


class TestFavorites:
    def test_remove_favorite_has_path_param(self):
        paths = [p for _, p in ROUTES.get("remove_favorite", [])]
        assert any("{" in p for p in paths)

    def test_add_favorite_raises_409_on_duplicate(self):
        src = _function_source("add_favorite")
        assert "409" in src or "HTTP_409_CONFLICT" in src

    def test_remove_favorite_raises_404_when_not_found(self):
        src = _function_source("remove_favorite")
        assert "404" in src or "HTTP_404_NOT_FOUND" in src

    def test_list_favorites_filters_by_current_user(self):
        src = _function_source("list_favorites")
        assert "user_id" in src or "current_user" in src

    def test_remove_favorite_checks_ownership(self):
        src = _function_source("remove_favorite")
        assert "user_id" in src or "current_user" in src


# ── Lazy service loading ──────────────────────────────────────────────────────


class TestLazyLoading:
    def test_start_session_lazy_imports_calendar(self):
        src = _function_source("start_session")
        assert "import" in src

    def test_run_pipeline_lazy_imports_graph(self):
        src = _function_source("run_lectio_pipeline")
        assert "import" in src

    def test_analyze_emotion_lazy_imports_service(self):
        src = _function_source("analyze_emotion")
        assert "import" in src

    def test_journey_agent_lazy_imported(self):
        src = _function_source("run_lectio_pipeline")
        assert "JourneyTrackerAgent" in src

    def test_pattern_agent_lazy_imported(self):
        src = _function_source("get_spiritual_patterns")
        assert "PatternDiscoveryAgent" in src


# ── SessionStore usage ────────────────────────────────────────────────────────


class TestSessionStore:
    def test_session_store_used_in_start(self):
        src = _function_source("start_session")
        assert "SessionStore" in src

    def test_session_store_namespace_is_lectio(self):
        assert 'namespace="lectio"' in SRC or "namespace='lectio'" in SRC

    def test_start_session_creates_session(self):
        src = _function_source("start_session")
        assert "store.create" in src

    def test_complete_session_updates_session(self):
        src = _function_source("complete_session")
        assert "store.update" in src


# ── Scripture for date ────────────────────────────────────────────────────────


class TestScriptureForDate:
    def test_get_scripture_has_date_path_param(self):
        paths = [p for _, p in ROUTES.get("get_scripture_for_date", [])]
        assert any("{" in p for p in paths)

    def test_invalid_date_raises_400(self):
        src = _function_source("get_scripture_for_date")
        assert "400" in src or "HTTP_400_BAD_REQUEST" in src

    def test_scripture_response_has_season(self):
        assert "season" in _model_fields("ScriptureForDateResponse")

    def test_scripture_response_has_readings(self):
        assert "readings" in _model_fields("ScriptureForDateResponse")
