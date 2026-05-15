"""Unit tests for app/api/routes/sacraments.py.

Contracts verified:
- All endpoints present with correct HTTP methods
- No user_id in any request body (privacy-critical: examination of conscience)
- Reflection/examination data is not persisted (privacy note in responses)
- Streaming endpoints use StreamingResponse
- Request model field constraints (commandment ge=1, le=10 etc.)
- State-of-life validation (raises 400 on unknown value)
- Sacraments overview endpoint exists
- No require_authenticated on public catechetical endpoints
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

SACRAMENTS_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "sacraments.py"
SRC = SACRAMENTS_PATH.read_text()
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
            path = ast.literal_eval(path_arg) if path_arg and isinstance(path_arg, ast.Constant) else "?"
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


def _field_source(model_name: str) -> str:
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


ROUTES = _route_decorators()


# ── Endpoint presence ─────────────────────────────────────────────────────────


class TestConfessionEndpoints:
    def test_get_commandments_exists(self):
        assert "get_commandments" in ROUTES

    def test_get_state_questions_exists(self):
        assert "get_state_questions" in ROUTES

    def test_generate_examination_exists(self):
        assert "generate_examination" in ROUTES

    def test_stream_commandment_reflection_exists(self):
        assert "stream_commandment_reflection" in ROUTES

    def test_generate_act_of_contrition_exists(self):
        assert "generate_act_of_contrition" in ROUTES

    def test_generate_resolution_exists(self):
        assert "generate_resolution" in ROUTES


class TestRCIAEndpoints:
    def test_get_rcia_curriculum_exists(self):
        assert "get_rcia_curriculum" in ROUTES

    def test_get_rcia_session_exists(self):
        assert "get_rcia_session" in ROUTES

    def test_ask_rcia_question_exists(self):
        assert "ask_rcia_question" in ROUTES

    def test_get_rcia_reflection_exists(self):
        assert "get_rcia_reflection" in ROUTES


class TestMarriageEndpoints:
    def test_get_marriage_program_exists(self):
        assert "get_marriage_program" in ROUTES

    def test_get_marriage_session_exists(self):
        assert "get_marriage_session" in ROUTES

    def test_discuss_marriage_topic_exists(self):
        assert "discuss_marriage_topic" in ROUTES

    def test_get_marriage_reflection_exists(self):
        assert "get_marriage_reflection" in ROUTES


class TestConfirmationEndpoints:
    def test_get_confirmation_program_exists(self):
        assert "get_confirmation_program" in ROUTES

    def test_get_confirmation_session_exists(self):
        assert "get_confirmation_session" in ROUTES

    def test_get_gifts_of_spirit_exists(self):
        assert "get_gifts_of_spirit" in ROUTES

    def test_ask_confirmation_question_exists(self):
        assert "ask_confirmation_question" in ROUTES

    def test_suggest_patron_saint_exists(self):
        assert "suggest_patron_saint" in ROUTES


class TestOverviewEndpoint:
    def test_sacraments_overview_exists(self):
        assert "sacraments_overview" in ROUTES

    def test_sacraments_overview_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["sacraments_overview"])


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_get_commandments_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_commandments"])

    def test_get_state_questions_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_state_questions"])

    def test_generate_examination_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["generate_examination"])

    def test_stream_commandment_reflection_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["stream_commandment_reflection"])

    def test_generate_act_of_contrition_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["generate_act_of_contrition"])

    def test_generate_resolution_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["generate_resolution"])

    def test_ask_rcia_question_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["ask_rcia_question"])

    def test_discuss_marriage_topic_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["discuss_marriage_topic"])

    def test_ask_confirmation_question_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["ask_confirmation_question"])

    def test_suggest_patron_saint_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["suggest_patron_saint"])


# ── No user_id in request bodies (privacy-critical) ──────────────────────────


class TestNoUserIdInBodies:
    """Sacramental data is especially sensitive. No user_id may appear in any
    request body — identity must never be linked to confession/examination content."""

    def test_examination_request_no_user_id(self):
        fields = _model_fields("ExaminationRequest")
        assert "user_id" not in fields

    def test_contrition_request_no_user_id(self):
        fields = _model_fields("ContritionRequest")
        assert "user_id" not in fields

    def test_resolution_request_no_user_id(self):
        fields = _model_fields("ResolutionRequest")
        assert "user_id" not in fields

    def test_reflection_stream_request_no_user_id(self):
        fields = _model_fields("ReflectionStreamRequest")
        assert "user_id" not in fields

    def test_rcia_question_request_no_user_id(self):
        fields = _model_fields("RCIAQuestionRequest")
        assert "user_id" not in fields

    def test_marriage_question_request_no_user_id(self):
        fields = _model_fields("MarriageQuestionRequest")
        assert "user_id" not in fields

    def test_confirmation_question_request_no_user_id(self):
        fields = _model_fields("ConfirmationQuestionRequest")
        assert "user_id" not in fields

    def test_patron_request_no_user_id(self):
        fields = _model_fields("PatronRequest")
        assert "user_id" not in fields


# ── Request model field constraints ──────────────────────────────────────────


class TestRequestFieldConstraints:
    def test_reflection_stream_commandment_has_ge_1_le_10(self):
        """Commandment numbers must be 1-10 (Dekalog)."""
        src = _field_source("ReflectionStreamRequest")
        assert "ge=1" in src or "ge = 1" in src
        assert "le=10" in src or "le = 10" in src

    def test_reflection_stream_request_has_commandment_number(self):
        fields = _model_fields("ReflectionStreamRequest")
        assert "commandment_number" in fields

    def test_reflection_user_reflection_has_max_length(self):
        """User reflection is ephemeral — max_length prevents abuse."""
        src = _field_source("ReflectionStreamRequest")
        assert "max_length" in src

    def test_resolution_focus_area_has_max_length(self):
        src = _field_source("ResolutionRequest")
        assert "max_length" in src

    def test_contrition_personal_note_has_max_length(self):
        src = _field_source("ContritionRequest")
        assert "max_length" in src

    def test_examination_has_state_of_life(self):
        fields = _model_fields("ExaminationRequest")
        assert "state_of_life" in fields

    def test_examination_has_language_field(self):
        fields = _model_fields("ExaminationRequest")
        assert "language" in fields


# ── Privacy: data not persisted ───────────────────────────────────────────────


class TestPrivacyGuarantees:
    def test_generate_examination_notes_not_stored(self):
        """Examination response must include a note that data is not stored."""
        src = _function_source("generate_examination")
        assert "nie jest przechowywany" in src or "not stored" in src.lower() or "ephemeral" in src.lower()

    def test_privacy_comment_in_module_docstring(self):
        """Privacy guarantee must be documented at module level."""
        assert "persist" in SRC.lower() or "przechowywany" in SRC.lower() or "ephemeral" in SRC.lower()

    def test_confession_reflection_stream_no_db_dependency(self):
        """Streaming reflection should not use DbSession (no persistence)."""
        src = _function_source("stream_commandment_reflection")
        assert "DbSession" not in src
        assert "db:" not in src


# ── Streaming endpoints ───────────────────────────────────────────────────────


class TestStreamingEndpoints:
    def test_stream_commandment_reflection_returns_streaming_response(self):
        """Reflection streaming must use StreamingResponse."""
        src = _function_source("stream_commandment_reflection")
        assert "StreamingResponse" in src

    def test_streaming_response_imported(self):
        assert "StreamingResponse" in SRC


# ── State-of-life validation ──────────────────────────────────────────────────


class TestStateOfLifeValidation:
    def test_get_state_questions_validates_state(self):
        """Unknown state of life should raise HTTPException 400."""
        src = _function_source("get_state_questions")
        assert "HTTPException" in src or "HTTP_400_BAD_REQUEST" in src
        assert "400" in src or "HTTP_400_BAD_REQUEST" in src

    def test_generate_examination_validates_state(self):
        src = _function_source("generate_examination")
        assert "HTTPException" in src

    def test_valid_states_in_source(self):
        """The module must reference valid state-of-life options."""
        for state in ("single", "married", "parent", "religious"):
            assert state in SRC, f"State '{state}' not found in sacraments.py"


# ── Public access (no auth required for catechetical endpoints) ───────────────


class TestPublicAccess:
    """Sacramental prep is public catechetical content — no auth required.
    Users should be able to prepare for confession anonymously."""

    def test_get_commandments_is_public(self):
        src = _function_source("get_commandments")
        assert "require_authenticated" not in src
        assert "require_admin" not in src

    def test_get_state_questions_is_public(self):
        src = _function_source("get_state_questions")
        assert "require_authenticated" not in src

    def test_stream_commandment_reflection_is_public(self):
        src = _function_source("stream_commandment_reflection")
        assert "require_authenticated" not in src

    def test_get_rcia_curriculum_is_public(self):
        src = _function_source("get_rcia_curriculum")
        assert "require_authenticated" not in src

    def test_get_confirmation_program_is_public(self):
        src = _function_source("get_confirmation_program")
        assert "require_authenticated" not in src


# ── Path parameters ───────────────────────────────────────────────────────────


class TestPathParameters:
    def test_get_state_questions_has_state_path_param(self):
        paths = [p for _, p in ROUTES.get("get_state_questions", [])]
        assert any("{state_of_life}" in p for p in paths)

    def test_get_rcia_session_has_session_id_path_param(self):
        paths = [p for _, p in ROUTES.get("get_rcia_session", [])]
        assert any("{session_id}" in p for p in paths)

    def test_get_marriage_session_has_session_id_path_param(self):
        paths = [p for _, p in ROUTES.get("get_marriage_session", [])]
        assert any("{session_id}" in p for p in paths)

    def test_get_rcia_reflection_has_session_id_path_param(self):
        paths = [p for _, p in ROUTES.get("get_rcia_reflection", [])]
        assert any("{session_id}" in p for p in paths)


# ── Lazy service loading ──────────────────────────────────────────────────────


class TestLazyServiceLoading:
    """Services are loaded lazily to avoid import-time crashes."""

    def test_examination_service_loaded_lazily(self):
        assert "_get_examination" in SRC
        src = _function_source("_get_examination")
        assert "import" in src

    def test_rcia_service_loaded_lazily(self):
        assert "_get_rcia" in SRC

    def test_marriage_service_loaded_lazily(self):
        assert "_get_marriage" in SRC

    def test_confirmation_service_loaded_lazily(self):
        assert "_get_confirmation" in SRC
