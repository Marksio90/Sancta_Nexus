"""Unit tests for app/api/routes/admin.py.

Contracts verified:
- All endpoints require require_admin (not just require_authenticated)
- RoleChangeRequest body has no user_id (user identity from path param only)
- Response schemas have expected fields
- Audit log endpoint exists and is GET
- Intention moderation endpoints (approve/reject) are POST
- AI interactions endpoint exists for safety monitoring
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ADMIN_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "admin.py"
SRC = ADMIN_PATH.read_text()
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


def _uses_guard(func_name: str, guard_name: str) -> bool:
    """Return True if the function has guard_name as a default arg value."""
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
            if isinstance(default, ast.Name) and default.id == guard_name:
                return True
    return False


def _model_fields(model_name: str) -> set[str]:
    fields: set[str] = set()
    for node in ast.walk(TREE):
        if not isinstance(node, ast.ClassDef) or node.name != model_name:
            continue
        for stmt in node.body:
            if isinstance(stmt, ast.AnnAssign) and isinstance(stmt.target, ast.Name):
                fields.add(stmt.target.id)
    return fields


ROUTES = _route_decorators()


# ── Endpoint presence ─────────────────────────────────────────────────────────


class TestEndpointPresence:
    def test_list_users_exists(self):
        assert "list_users" in ROUTES

    def test_get_user_admin_exists(self):
        assert "get_user_admin" in ROUTES

    def test_change_user_role_exists(self):
        assert "change_user_role" in ROUTES

    def test_deactivate_user_exists(self):
        assert "deactivate_user" in ROUTES

    def test_list_audit_logs_exists(self):
        assert "list_audit_logs" in ROUTES

    def test_get_feature_flags_exists(self):
        assert "get_feature_flags" in ROUTES

    def test_list_ai_interactions_exists(self):
        assert "list_ai_interactions" in ROUTES

    def test_list_pending_intentions_exists(self):
        assert "list_pending_intentions" in ROUTES

    def test_approve_intention_exists(self):
        assert "approve_intention" in ROUTES

    def test_reject_intention_exists(self):
        assert "reject_intention" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_list_users_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["list_users"])

    def test_get_user_admin_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_user_admin"])

    def test_change_user_role_is_put(self):
        assert any(m == "PUT" for m, _ in ROUTES["change_user_role"])

    def test_deactivate_user_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["deactivate_user"])

    def test_list_audit_logs_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["list_audit_logs"])

    def test_get_feature_flags_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_feature_flags"])

    def test_list_ai_interactions_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["list_ai_interactions"])

    def test_approve_intention_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["approve_intention"])

    def test_reject_intention_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["reject_intention"])


# ── Admin-only guard ──────────────────────────────────────────────────────────


class TestAdminOnlyGuard:
    """Every endpoint must use require_admin, not just require_authenticated."""

    @pytest.mark.parametrize("func_name", [
        "list_users",
        "get_user_admin",
        "change_user_role",
        "deactivate_user",
        "list_audit_logs",
        "get_feature_flags",
        "list_ai_interactions",
        "list_pending_intentions",
        "approve_intention",
        "reject_intention",
    ])
    def test_endpoint_requires_admin(self, func_name: str):
        assert _uses_guard(func_name, "require_admin"), (
            f"{func_name} must use require_admin, not just require_authenticated"
        )

    def test_require_admin_imported(self):
        assert "require_admin" in SRC

    def test_require_authenticated_not_used_as_guard(self):
        """Admin routes should never downgrade to require_authenticated."""
        # It may be imported transitively but should not be used as a decorator default
        for func_name in [
            "list_users", "change_user_role", "deactivate_user",
            "list_audit_logs", "approve_intention", "reject_intention",
        ]:
            assert not _uses_guard(func_name, "require_authenticated"), (
                f"{func_name} incorrectly uses require_authenticated instead of require_admin"
            )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInRequestBodies:
    def test_role_change_request_no_user_id(self):
        """user_id must come from path parameter, not request body."""
        fields = _model_fields("RoleChangeRequest")
        assert "user_id" not in fields

    def test_role_change_request_has_new_role(self):
        fields = _model_fields("RoleChangeRequest")
        assert "new_role" in fields


# ── Response schema contracts ─────────────────────────────────────────────────


class TestResponseSchemas:
    def test_admin_user_list_item_has_required_fields(self):
        fields = _model_fields("AdminUserListItem")
        for f in ("id", "email", "name", "role", "subscription_tier", "is_active"):
            assert f in fields, f"AdminUserListItem missing '{f}'"

    def test_admin_user_list_response_has_pagination(self):
        fields = _model_fields("AdminUserListResponse")
        assert "users" in fields
        assert "total" in fields
        assert "page" in fields

    def test_role_change_response_has_old_and_new_role(self):
        fields = _model_fields("RoleChangeResponse")
        assert "old_role" in fields
        assert "new_role" in fields
        assert "message" in fields

    def test_audit_log_item_has_actor(self):
        """Audit logs track who performed the action."""
        fields = _model_fields("AuditLogItem")
        assert "actor_id" in fields
        assert "event_type" in fields
        assert "description" in fields

    def test_ai_interaction_item_has_safety_fields(self):
        """AI safety monitoring fields are present."""
        fields = _model_fields("AiInteractionItem")
        assert "risk_category" in fields
        assert "was_modified" in fields
        assert "violations" in fields

    def test_feature_flags_response_has_flags_dict(self):
        fields = _model_fields("FeatureFlagsResponse")
        assert "flags" in fields


# ── Audit logging on sensitive actions ───────────────────────────────────────


class TestAuditLogging:
    def test_change_role_calls_audit(self):
        """Role changes are security-sensitive and must be audited."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "change_user_role":
                src_lines = SRC.splitlines()
                func_src = "\n".join(src_lines[node.lineno - 1 : node.end_lineno])
                assert "audit" in func_src, "change_user_role must call audit()"
                return
        pytest.fail("change_user_role not found")

    def test_deactivate_user_calls_audit(self):
        """Account deactivations are security-sensitive and must be audited."""
        for node in ast.walk(TREE):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == "deactivate_user":
                src_lines = SRC.splitlines()
                func_src = "\n".join(src_lines[node.lineno - 1 : node.end_lineno])
                assert "audit" in func_src, "deactivate_user must call audit()"
                return
        pytest.fail("deactivate_user not found")

    def test_audit_service_imported(self):
        assert "audit" in SRC
        assert "AuditLog" in SRC or "audit_service" in SRC


# ── Path parameter safety ─────────────────────────────────────────────────────


class TestPathParameterSafety:
    def test_user_endpoints_use_path_param(self):
        """Admin user endpoints must use {user_id} or {id} path param."""
        for func_name in ("get_user_admin", "change_user_role", "deactivate_user"):
            paths = [p for _, p in ROUTES.get(func_name, [])]
            assert any("{" in p for p in paths), (
                f"{func_name} should use path parameter for user identification"
            )

    def test_intention_moderation_uses_path_param(self):
        for func_name in ("approve_intention", "reject_intention"):
            paths = [p for _, p in ROUTES.get(func_name, [])]
            assert any("{" in p for p in paths), (
                f"{func_name} should use path parameter for intention_id"
            )
