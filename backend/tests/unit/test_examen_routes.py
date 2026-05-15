"""Unit tests for app/api/routes/examen.py.

Contracts verified (AST-based — no DB/Redis/LLM required):
- All 4 endpoints present with correct HTTP methods
- All endpoints require require_authenticated (Examen is personal/spiritual)
- No user_id in any request body (JWT-only identity)
- Disclaimer field present in every response schema (mission-critical)
- AI system prompt denies priest/confessor role (CZYM NIE JESTEŚ)
- Request field constraints (intention max_length, reflection min/max_length)
- Response schemas contain expected fields
- Soft-save pattern: save_to_journal is opt-in boolean (not forced)
- Phase progression: phases tracked in session
- 404 for missing/expired sessions
- 403 for wrong user
- Privacy: _EXAMEN_SYSTEM_PROMPT explicitly disclaims not evaluating sin
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

EXAMEN_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "examen.py"
SRC = EXAMEN_PATH.read_text()
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
    def test_start_examen_exists(self):
        assert "start_examen" in ROUTES

    def test_submit_examen_step_exists(self):
        assert "submit_examen_step" in ROUTES

    def test_complete_examen_exists(self):
        assert "complete_examen" in ROUTES

    def test_get_examen_session_exists(self):
        assert "get_examen_session" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_start_examen_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["start_examen"])

    def test_submit_examen_step_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["submit_examen_step"])

    def test_complete_examen_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["complete_examen"])

    def test_get_examen_session_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_examen_session"])


# ── Auth guard ────────────────────────────────────────────────────────────────


class TestAuthGuard:
    @pytest.mark.parametrize("func_name", [
        "start_examen",
        "submit_examen_step",
        "complete_examen",
        "get_examen_session",
    ])
    def test_endpoint_requires_auth(self, func_name: str):
        assert _uses_require_authenticated(func_name), (
            f"{func_name} must use require_authenticated — Rachunek Sumienia is deeply personal"
        )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInBodies:
    def test_start_request_no_user_id(self):
        assert "user_id" not in _model_fields("StartExamenRequest")

    def test_step_request_no_user_id(self):
        assert "user_id" not in _model_fields("StepRequest")

    def test_complete_request_no_user_id(self):
        assert "user_id" not in _model_fields("CompleteRequest")


# ── Disclaimer in every response (mission-critical) ──────────────────────────


class TestDisclaimerPresence:
    """Every response from the Examen must carry the disclaimer that the AI
    is not a confessor or spiritual director."""

    def test_start_response_has_disclaimer(self):
        assert "disclaimer" in _model_fields("StartExamenResponse"), (
            "StartExamenResponse must include disclaimer — AI is not a confessor"
        )

    def test_step_response_has_disclaimer(self):
        assert "disclaimer" in _model_fields("StepResponse"), (
            "StepResponse must include disclaimer after each AI reflection"
        )

    def test_complete_response_has_disclaimer(self):
        assert "disclaimer" in _model_fields("CompleteResponse"), (
            "CompleteResponse must include disclaimer on session completion"
        )

    def test_session_response_has_disclaimer(self):
        assert "disclaimer" in _model_fields("ExamenSessionResponse")


# ── AI system prompt safety ───────────────────────────────────────────────────


class TestSystemPromptSafety:
    """The AI system prompt must explicitly deny confessor/priest role."""

    def test_system_prompt_defined(self):
        assert "_EXAMEN_SYSTEM_PROMPT" in SRC

    def test_system_prompt_denies_confessor_role(self):
        """Prompt must state AI is not a confessor and cannot grant absolution."""
        prompt_variants = ("spowiednikiem", "rozgrzeszenia", "nie jesteś", "CZYM NIE JESTEŚ")
        assert any(v in SRC for v in prompt_variants), (
            "System prompt must explicitly deny confessor/absolution role"
        )

    def test_system_prompt_denies_sin_diagnosis(self):
        """Prompt must not evaluate sins — that is the confessor's role."""
        assert "nie oceniasz" in SRC or "nie wydajesz wyroków" in SRC or "stanu łaski" in SRC

    def test_system_prompt_references_real_support(self):
        """AI must refer users in crisis to real human support (kapłan, duszpasterz)."""
        assert "kapłana" in SRC or "duszpasterz" in SRC or "kapłan" in SRC


# ── Request field constraints ─────────────────────────────────────────────────


class TestRequestConstraints:
    def test_intention_has_max_length(self):
        src = _model_source("StartExamenRequest")
        assert "max_length=300" in src or "max_length = 300" in src

    def test_reflection_has_min_length(self):
        src = _model_source("StepRequest")
        assert "min_length=1" in src or "min_length = 1" in src

    def test_reflection_has_max_length(self):
        src = _model_source("StepRequest")
        assert "max_length=2000" in src or "max_length = 2000" in src

    def test_step_request_has_session_id(self):
        assert "session_id" in _model_fields("StepRequest")

    def test_step_request_has_reflection(self):
        assert "reflection" in _model_fields("StepRequest")

    def test_complete_request_has_save_to_journal(self):
        """Saving to journal must be opt-in, not automatic."""
        assert "save_to_journal" in _model_fields("CompleteRequest")

    def test_complete_request_has_session_id(self):
        assert "session_id" in _model_fields("CompleteRequest")


# ── Response schemas ──────────────────────────────────────────────────────────


class TestResponseSchemas:
    def test_start_response_has_session_id(self):
        assert "session_id" in _model_fields("StartExamenResponse")

    def test_start_response_has_current_phase(self):
        assert "current_phase" in _model_fields("StartExamenResponse")

    def test_step_response_has_ai_response(self):
        assert "ai_response" in _model_fields("StepResponse")

    def test_step_response_has_next_phase(self):
        assert "next_phase" in _model_fields("StepResponse")

    def test_step_response_has_is_final(self):
        assert "is_final" in _model_fields("StepResponse")

    def test_complete_response_has_summary(self):
        assert "summary" in _model_fields("CompleteResponse")

    def test_complete_response_has_journal_entry_id(self):
        """Optional journal entry ID — only set when save_to_journal=True."""
        assert "journal_entry_id" in _model_fields("CompleteResponse")

    def test_session_response_has_phases_completed(self):
        assert "phases_completed" in _model_fields("ExamenSessionResponse")

    def test_session_response_has_started_at(self):
        assert "started_at" in _model_fields("ExamenSessionResponse")


# ── Session ownership and error handling ──────────────────────────────────────


class TestSessionSecurity:
    def test_submit_step_raises_404_for_missing_session(self):
        src = _function_source("submit_examen_step")
        assert "404" in src or "HTTP_404_NOT_FOUND" in src

    def test_submit_step_raises_403_for_wrong_user(self):
        src = _function_source("submit_examen_step")
        assert "403" in src or "HTTP_403_FORBIDDEN" in src

    def test_complete_raises_404_for_missing_session(self):
        src = _function_source("complete_examen")
        assert "404" in src or "HTTP_404_NOT_FOUND" in src

    def test_get_session_raises_404_for_missing(self):
        src = _function_source("get_examen_session")
        assert "404" in src or "HTTP_404_NOT_FOUND" in src

    def test_get_session_checks_ownership(self):
        src = _function_source("get_examen_session")
        assert "user_id" in src or "current_user" in src


# ── Ignacjańskie fazy ─────────────────────────────────────────────────────────


class TestIgnatianPhases:
    """Ignatian Examen has 5 classic phases."""

    @pytest.mark.parametrize("phase", [
        "Wdzięczność",
        "consolatio",
        "desolatio",
    ])
    def test_ignatian_term_present(self, phase: str):
        assert phase in SRC, f"Ignatian term '{phase}' must appear in examen.py"

    def test_phases_tracked_in_session(self):
        """Session data must track which phases have been completed."""
        src = _function_source("submit_examen_step")
        assert "phase" in src

    def test_save_to_journal_is_optional(self):
        """Journal save must default to False — privacy."""
        src = _model_source("CompleteRequest")
        assert "False" in src or "false" in src
