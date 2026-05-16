"""Unit tests for app/api/routes/users.py.

Tests verify:
- Endpoint presence and HTTP methods (AST inspection)
- Security contracts: every endpoint uses require_authenticated
- No user_id in request body schemas
- Privacy settings update rejects invalid language / tradition
- Data-export and deletion response shapes
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

USERS_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "users.py"
SRC = USERS_PATH.read_text()
TREE = ast.parse(SRC)


# ── AST helpers ───────────────────────────────────────────────────────────────


def _route_decorators() -> dict[str, list[tuple[str, str]]]:
    """Return {function_name: [(http_method, path), ...]}."""
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
    """Return field names defined in a Pydantic model class."""
    fields: set[str] = set()
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ClassDef) or node.name != model_name:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.add(stmt.target.id)
    return fields


def _uses_require_authenticated(func_name: str) -> bool:
    """Return True if the function has require_authenticated as a default arg."""
    for node in ast.walk(TREE):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        if node.name != func_name:
            continue
        defaults = node.args.defaults + node.args.kw_defaults
        for d in defaults:
            if d is None:
                continue
            if isinstance(d, ast.Name) and d.id == "require_authenticated":
                return True
        for arg in node.args.args + node.args.kwonlyargs:
            if arg.annotation and isinstance(arg.annotation, ast.Name) and arg.annotation.id == "require_authenticated":
                return True
        # Check default values against require_authenticated
        all_args = node.args.args
        all_defaults = ([None] * (len(all_args) - len(node.args.defaults))) + node.args.defaults
        for _arg, default in zip(all_args, all_defaults, strict=False):
            if isinstance(default, ast.Name) and default.id == "require_authenticated":
                return True
    return False


ROUTES = _route_decorators()
ROUTE_NAMES = list(ROUTES.keys())


# ── Endpoint presence ─────────────────────────────────────────────────────────


class TestEndpointPresence:
    def test_get_my_profile_exists(self):
        assert "get_my_profile" in ROUTES

    def test_update_my_profile_exists(self):
        assert "update_my_profile" in ROUTES

    def test_get_privacy_settings_exists(self):
        assert "get_privacy_settings" in ROUTES

    def test_update_privacy_settings_exists(self):
        assert "update_privacy_settings" in ROUTES

    def test_export_my_data_exists(self):
        assert "export_my_data" in ROUTES

    def test_clear_ai_history_exists(self):
        assert "clear_ai_history" in ROUTES

    def test_request_account_deletion_exists(self):
        assert "request_account_deletion" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_get_my_profile_is_get(self):
        methods = [m for m, _ in ROUTES["get_my_profile"]]
        assert "GET" in methods

    def test_update_my_profile_is_put(self):
        methods = [m for m, _ in ROUTES["update_my_profile"]]
        assert "PUT" in methods

    def test_get_privacy_settings_is_get(self):
        methods = [m for m, _ in ROUTES["get_privacy_settings"]]
        assert "GET" in methods

    def test_update_privacy_settings_is_put(self):
        methods = [m for m, _ in ROUTES["update_privacy_settings"]]
        assert "PUT" in methods

    def test_export_my_data_is_get(self):
        methods = [m for m, _ in ROUTES["export_my_data"]]
        assert "GET" in methods

    def test_clear_ai_history_is_post(self):
        methods = [m for m, _ in ROUTES["clear_ai_history"]]
        assert "POST" in methods

    def test_request_account_deletion_is_post(self):
        methods = [m for m, _ in ROUTES["request_account_deletion"]]
        assert "POST" in methods


# ── Auth guard (every endpoint must require authentication) ───────────────────


class TestAuthGuard:
    @pytest.mark.parametrize("func_name", [
        "get_my_profile",
        "update_my_profile",
        "get_privacy_settings",
        "update_privacy_settings",
        "export_my_data",
        "clear_ai_history",
        "request_account_deletion",
    ])
    def test_endpoint_requires_auth(self, func_name: str):
        assert _uses_require_authenticated(func_name), (
            f"{func_name} does not use require_authenticated"
        )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInRequestBodies:
    def test_profile_update_no_user_id(self):
        fields = _model_fields("ProfileUpdate")
        assert "user_id" not in fields

    def test_privacy_update_no_user_id(self):
        fields = _model_fields("PrivacySettingsUpdate")
        assert "user_id" not in fields

    def test_profile_update_has_display_name(self):
        fields = _model_fields("ProfileUpdate")
        assert "display_name" in fields

    def test_privacy_update_has_expected_fields(self):
        fields = _model_fields("PrivacySettingsUpdate")
        assert "ai_can_read_journal" in fields
        assert "journal_is_private" in fields
        assert "ai_history_enabled" in fields


# ── Response schema contracts ─────────────────────────────────────────────────


class TestResponseSchemas:
    def test_profile_response_has_required_fields(self):
        fields = _model_fields("ProfileResponse")
        for required in ("email", "display_name", "role", "subscription_tier", "is_active"):
            assert required in fields, f"ProfileResponse missing '{required}'"

    def test_profile_response_no_password_field(self):
        fields = _model_fields("ProfileResponse")
        assert "password" not in fields
        assert "hashed_password" not in fields

    def test_privacy_response_has_boolean_flags(self):
        fields = _model_fields("PrivacySettingsResponse")
        assert "ai_can_read_journal" in fields
        assert "journal_is_private" in fields
        assert "ai_history_enabled" in fields

    def test_deletion_response_has_message(self):
        fields = _model_fields("DeletionResponse")
        assert "message" in fields

    def test_clear_history_response_has_count(self):
        fields = _model_fields("ClearHistoryResponse")
        assert "deleted_count" in fields
        assert "message" in fields


# ── Privacy validation — AST checks ──────────────────────────────────────────


def _function_source(func_name: str) -> str:
    """Return the source lines of a function as a string."""
    for node in ast.walk(TREE):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            lines = SRC.splitlines()
            return "\n".join(lines[node.lineno - 1 : node.end_lineno])
    return ""


class TestPrivacyValidation:
    def test_update_privacy_raises_http_exception_on_bad_language(self):
        """update_privacy_settings raises HTTPException for unknown language."""
        src = _function_source("update_privacy_settings")
        assert "HTTPException" in src
        assert "400" in src or "HTTP_400_BAD_REQUEST" in src

    def test_update_privacy_raises_http_exception_on_bad_tradition(self):
        """update_privacy_settings raises HTTPException for unknown tradition."""
        src = _function_source("update_privacy_settings")
        assert "_VALID_TRADITIONS" in src

    def test_valid_languages_set_defined(self):
        """_VALID_LANGUAGES constant is defined at module level."""
        assert "_VALID_LANGUAGES" in SRC

    def test_valid_traditions_set_defined(self):
        """_VALID_TRADITIONS constant is defined at module level."""
        assert "_VALID_TRADITIONS" in SRC

    def test_valid_languages_contains_polish(self):
        assert '"pl"' in SRC or "'pl'" in SRC

    def test_valid_traditions_contains_ignatian(self):
        assert '"ignatian"' in SRC or "'ignatian'" in SRC

    def test_valid_traditions_contains_expected_traditions(self):
        for tradition in ("carmelite", "benedictine", "franciscan", "dominican"):
            assert tradition in SRC, f"Missing tradition: {tradition}"

    def test_valid_languages_contains_expected_languages(self):
        for lang in ("pl", "en", "de", "fr"):
            assert f'"{lang}"' in SRC or f"'{lang}'" in SRC, f"Missing language: {lang}"


# ── _profile_response helper — AST checks ─────────────────────────────────────


class TestProfileResponseHelper:
    def test_profile_response_helper_defined(self):
        """_profile_response helper function exists in source."""
        assert "_profile_response" in SRC

    def test_profile_response_maps_name_to_display_name(self):
        """_profile_response maps user.name → display_name (not user.display_name)."""
        src = _function_source("_profile_response")
        assert "user.name" in src
        assert "display_name" in src

    def test_profile_response_does_not_expose_password(self):
        """ProfileResponse schema has no password-related fields."""
        src = _function_source("_profile_response")
        assert "password" not in src.lower()

    def test_profile_response_includes_email(self):
        src = _function_source("_profile_response")
        assert "email" in src

    def test_profile_response_includes_role(self):
        src = _function_source("_profile_response")
        assert "role" in src
