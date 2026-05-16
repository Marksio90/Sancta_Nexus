"""Unit tests for app/api/routes/orchestrate.py.

Contracts verified (AST-based):
- Single POST endpoint exists
- Endpoint requires require_authenticated (identity from JWT, not request body)
- No user_id in OrchestrateRequest (security critical — was a violation)
- OrchestrateResponse has no user_id (user identity is not exposed back)
- Response contains AI pipeline output fields
- Lazy import of OrchestratorSupremus
- 500 raised on pipeline failure
"""

from __future__ import annotations

import ast
from pathlib import Path

ORCHESTRATE_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "orchestrate.py"
SRC = ORCHESTRATE_PATH.read_text()
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


# ── Endpoint presence and method ──────────────────────────────────────────────


class TestEndpoint:
    def test_orchestrate_exists(self):
        assert "orchestrate" in ROUTES

    def test_orchestrate_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["orchestrate"])


# ── Auth guard ────────────────────────────────────────────────────────────────


class TestAuthGuard:
    def test_orchestrate_requires_auth(self):
        """Orchestration is personal spiritual guidance — must be authenticated."""
        assert _uses_require_authenticated("orchestrate"), (
            "orchestrate must use require_authenticated — AI spiritual guidance is personal"
        )


# ── No user_id in request body ────────────────────────────────────────────────


class TestNoUserIdInBody:
    def test_request_no_user_id(self):
        """user_id must never appear in request body — JWT identity only."""
        assert "user_id" not in _model_fields("OrchestrateRequest"), (
            "OrchestrateRequest must not have user_id — identity comes from JWT"
        )

    def test_request_has_emotion_vector(self):
        assert "emotion_vector" in _model_fields("OrchestrateRequest")

    def test_request_has_tradition(self):
        assert "tradition" in _model_fields("OrchestrateRequest")

    def test_request_has_session_history(self):
        assert "session_history" in _model_fields("OrchestrateRequest")

    def test_request_has_intent(self):
        assert "intent" in _model_fields("OrchestrateRequest")


# ── Response schema ───────────────────────────────────────────────────────────


class TestResponseSchema:
    def test_response_no_user_id(self):
        """Response must not echo back user_id — not needed by client."""
        assert "user_id" not in _model_fields("OrchestrateResponse")

    def test_response_has_intent(self):
        assert "intent" in _model_fields("OrchestrateResponse")

    def test_response_has_scripture(self):
        assert "scripture" in _model_fields("OrchestrateResponse")

    def test_response_has_meditation(self):
        assert "meditation" in _model_fields("OrchestrateResponse")

    def test_response_has_prayer(self):
        assert "prayer" in _model_fields("OrchestrateResponse")

    def test_response_has_error(self):
        """Pipeline errors must surface to the client."""
        assert "error" in _model_fields("OrchestrateResponse")

    def test_response_has_theological_validation(self):
        assert "theological_validation" in _model_fields("OrchestrateResponse")


# ── Implementation contracts ──────────────────────────────────────────────────


class TestImplementation:
    def test_orchestrator_lazy_imported(self):
        src = _function_source("orchestrate")
        assert "import" in src
        assert "OrchestratorSupremus" in src

    def test_user_id_comes_from_current_user(self):
        """user_id passed to pipeline must come from JWT, not request body."""
        src = _function_source("orchestrate")
        assert "current_user.id" in src

    def test_pipeline_failure_raises_500(self):
        src = _function_source("orchestrate")
        assert "500" in src or "HTTP_500_INTERNAL_SERVER_ERROR" in src
