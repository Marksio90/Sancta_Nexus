"""Unit tests for app/api/routes/auth.py.

Contracts verified:
- Registration, login, refresh, get_me endpoints exist
- Request schemas: no user_id in registration body; email + password required
- Response schemas: access_token, refresh_token, user.displayName (camelCase)
- get_me requires authentication
- No password field in any response schema
- Password field has min_length constraint in RegisterRequest
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

AUTH_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "auth.py"
SRC = AUTH_PATH.read_text()
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


def _field_annotations_source(model_name: str) -> str:
    """Return the source of a model class body."""
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ClassDef) or node.name != model_name:
            continue
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
    def test_register_exists(self):
        assert "register" in ROUTES

    def test_login_exists(self):
        assert "login" in ROUTES

    def test_refresh_exists(self):
        assert "refresh" in ROUTES

    def test_get_me_exists(self):
        assert "get_me" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_register_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["register"])

    def test_login_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["login"])

    def test_refresh_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["refresh"])

    def test_get_me_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_me"])


# ── Request schema contracts ──────────────────────────────────────────────────


class TestRequestSchemas:
    def test_register_request_has_email(self):
        fields = _model_fields("RegisterRequest")
        assert "email" in fields

    def test_register_request_has_password(self):
        fields = _model_fields("RegisterRequest")
        assert "password" in fields

    def test_register_request_has_display_name(self):
        fields = _model_fields("RegisterRequest")
        assert "display_name" in fields

    def test_register_request_no_user_id(self):
        """No user_id in registration — ID is generated server-side."""
        fields = _model_fields("RegisterRequest")
        assert "user_id" not in fields
        assert "id" not in fields

    def test_register_password_has_min_length(self):
        """Password must have min_length constraint for security."""
        src = _field_annotations_source("RegisterRequest")
        assert "min_length" in src

    def test_login_request_has_email_and_password(self):
        fields = _model_fields("LoginRequest")
        assert "email" in fields
        assert "password" in fields

    def test_login_request_no_user_id(self):
        fields = _model_fields("LoginRequest")
        assert "user_id" not in fields

    def test_refresh_request_has_refresh_token(self):
        fields = _model_fields("RefreshRequest")
        assert "refresh_token" in fields


# ── Response schema contracts ─────────────────────────────────────────────────


class TestResponseSchemas:
    def test_register_response_has_tokens(self):
        fields = _model_fields("RegisterResponse")
        assert "access_token" in fields
        assert "refresh_token" in fields

    def test_register_response_has_user(self):
        fields = _model_fields("RegisterResponse")
        assert "user" in fields

    def test_register_response_no_password(self):
        fields = _model_fields("RegisterResponse")
        assert "password" not in fields
        assert "hashed_password" not in fields

    def test_login_response_has_tokens(self):
        fields = _model_fields("LoginResponse")
        assert "access_token" in fields
        assert "refresh_token" in fields

    def test_user_info_has_display_name_camelcase(self):
        """Frontend expects displayName (camelCase) per AuthUser interface."""
        fields = _model_fields("UserInfo")
        assert "displayName" in fields, (
            "UserInfo.displayName must be camelCase to match AuthUser TypeScript interface"
        )

    def test_user_info_no_password(self):
        fields = _model_fields("UserInfo")
        assert "password" not in fields

    def test_token_type_is_bearer(self):
        """Standard OAuth2 token_type must be 'bearer'."""
        assert '"bearer"' in SRC or "'bearer'" in SRC


# ── Auth guard on get_me ──────────────────────────────────────────────────────


class TestAuthGuard:
    def test_get_me_requires_authenticated(self):
        assert _uses_require_authenticated("get_me"), (
            "get_me must use require_authenticated to return the current user's profile"
        )

    def test_register_does_not_require_auth(self):
        """Registration is a public endpoint — no auth needed."""
        assert not _uses_require_authenticated("register")

    def test_login_does_not_require_auth(self):
        """Login is a public endpoint — no auth needed."""
        assert not _uses_require_authenticated("login")


# ── Security: password hashing ────────────────────────────────────────────────


class TestPasswordSecurity:
    def test_hash_password_used_in_register(self):
        """Registration must hash the password before storing."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "register":
                lines = SRC.splitlines()
                func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                assert "hash_password" in func_src, (
                    "register() must call hash_password() — never store plaintext passwords"
                )
                return
        pytest.fail("register function not found")

    def test_verify_password_used_in_login(self):
        """Login must verify the password hash."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "login":
                lines = SRC.splitlines()
                func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                assert "verify_password" in func_src, (
                    "login() must call verify_password() — never compare plaintext"
                )
                return
        pytest.fail("login function not found")

    def test_hash_password_imported_from_security(self):
        assert "hash_password" in SRC

    def test_verify_password_imported_from_security(self):
        assert "verify_password" in SRC


# ── JWT token generation ──────────────────────────────────────────────────────


class TestJwtTokenGeneration:
    def test_create_access_token_used(self):
        assert "create_access_token" in SRC

    def test_create_refresh_token_used(self):
        assert "create_refresh_token" in SRC

    def test_verify_token_used_in_refresh(self):
        """Token refresh must verify the old refresh token."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "refresh":
                lines = SRC.splitlines()
                func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                assert "verify_token" in func_src
                return
        pytest.fail("refresh function not found")

    def test_register_response_has_expires_in(self):
        fields = _model_fields("RegisterResponse")
        assert "expires_in" in fields


# ── Inactive account handling ─────────────────────────────────────────────────


class TestInactiveAccountHandling:
    def test_login_checks_is_active(self):
        """Login must reject deactivated accounts."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "login":
                lines = SRC.splitlines()
                func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                assert "is_active" in func_src, (
                    "login() must check user.is_active to block soft-deleted accounts"
                )
                return
        pytest.fail("login function not found")

    def test_refresh_checks_is_active(self):
        """Token refresh must also reject deactivated accounts."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "refresh":
                lines = SRC.splitlines()
                func_src = "\n".join(lines[node.lineno - 1 : node.end_lineno])
                assert "is_active" in func_src, (
                    "refresh() must check user.is_active to block soft-deleted accounts"
                )
                return
        pytest.fail("refresh function not found")
