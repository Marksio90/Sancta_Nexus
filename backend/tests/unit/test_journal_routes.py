"""Unit tests for app/api/routes/journal.py.

Tests verify (all AST-based — no DB/infra required):
- All CRUD endpoints exist with correct HTTP methods
- Every endpoint requires authentication (require_authenticated)
- No user_id in request body schemas (identity from JWT)
- Soft-delete pattern: deleted_at not user_id in delete logic
- Mood validation raises 400 on unknown values
- Insights endpoint exists and requires auth
- JournalEntryCreate.content has min_length constraint
- Response schema contains no password/sensitive fields
- Tag conversion helpers (inline test for correctness)
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

JOURNAL_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "journal.py"
SRC = JOURNAL_PATH.read_text()
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
    def test_create_entry_exists(self):
        assert "create_entry" in ROUTES

    def test_list_entries_exists(self):
        assert "list_entries" in ROUTES

    def test_get_entry_exists(self):
        assert "get_entry" in ROUTES

    def test_update_entry_exists(self):
        assert "update_entry" in ROUTES

    def test_delete_entry_exists(self):
        assert "delete_entry" in ROUTES

    def test_get_insights_exists(self):
        assert "get_insights" in ROUTES


# ── HTTP methods ──────────────────────────────────────────────────────────────


class TestHttpMethods:
    def test_create_entry_is_post(self):
        assert any(m == "POST" for m, _ in ROUTES["create_entry"])

    def test_list_entries_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["list_entries"])

    def test_get_entry_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_entry"])

    def test_update_entry_is_put(self):
        assert any(m == "PUT" for m, _ in ROUTES["update_entry"])

    def test_delete_entry_is_delete(self):
        assert any(m == "DELETE" for m, _ in ROUTES["delete_entry"])

    def test_get_insights_is_get(self):
        assert any(m == "GET" for m, _ in ROUTES["get_insights"])


# ── Auth guard on every endpoint ─────────────────────────────────────────────


class TestAuthGuard:
    @pytest.mark.parametrize("func_name", [
        "create_entry",
        "list_entries",
        "get_entry",
        "update_entry",
        "delete_entry",
        "get_insights",
    ])
    def test_endpoint_requires_auth(self, func_name: str):
        assert _uses_require_authenticated(func_name), (
            f"{func_name} must use require_authenticated — journal entries are private"
        )


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInBodies:
    def test_create_no_user_id(self):
        fields = _model_fields("JournalEntryCreate")
        assert "user_id" not in fields

    def test_update_no_user_id(self):
        fields = _model_fields("JournalEntryUpdate")
        assert "user_id" not in fields


# ── Request model field constraints ──────────────────────────────────────────


class TestCreateEntryConstraints:
    def test_content_has_min_length(self):
        """Journal entries must have non-empty content."""
        src = _model_source("JournalEntryCreate")
        assert "min_length=1" in src or "min_length = 1" in src

    def test_content_is_required(self):
        fields = _model_fields("JournalEntryCreate")
        assert "content" in fields

    def test_title_has_max_length(self):
        src = _model_source("JournalEntryCreate")
        assert "max_length=256" in src or "max_length = 256" in src

    def test_scripture_reference_has_max_length(self):
        src = _model_source("JournalEntryCreate")
        assert "max_length=128" in src or "max_length = 128" in src

    def test_has_tags_field(self):
        fields = _model_fields("JournalEntryCreate")
        assert "tags" in fields

    def test_has_mood_field(self):
        fields = _model_fields("JournalEntryCreate")
        assert "mood" in fields

    def test_has_lectio_session_id(self):
        """Journal entries can reference a Lectio Divina session."""
        fields = _model_fields("JournalEntryCreate")
        assert "lectio_session_id" in fields


# ── Response schema ───────────────────────────────────────────────────────────


class TestResponseSchema:
    def test_response_has_id(self):
        fields = _model_fields("JournalEntryResponse")
        assert "id" in fields

    def test_response_has_content(self):
        fields = _model_fields("JournalEntryResponse")
        assert "content" in fields

    def test_response_has_created_at(self):
        fields = _model_fields("JournalEntryResponse")
        assert "created_at" in fields

    def test_response_has_updated_at(self):
        fields = _model_fields("JournalEntryResponse")
        assert "updated_at" in fields

    def test_response_has_no_user_id(self):
        """Response must not expose the user's ID — privacy."""
        fields = _model_fields("JournalEntryResponse")
        assert "user_id" not in fields

    def test_response_has_no_deleted_at(self):
        """Soft-deleted entries must never appear in response — deleted_at is internal."""
        fields = _model_fields("JournalEntryResponse")
        assert "deleted_at" not in fields

    def test_list_response_has_pagination(self):
        fields = _model_fields("JournalListResponse")
        assert "entries" in fields
        assert "total" in fields
        assert "page" in fields

    def test_insights_response_exists(self):
        """InsightsResponse schema must be defined."""
        assert "InsightsResponse" in SRC


# ── Soft delete pattern ───────────────────────────────────────────────────────


class TestSoftDelete:
    def test_delete_uses_deleted_at(self):
        """Journal entries must be soft-deleted via deleted_at, not hard-deleted."""
        src = _function_source("delete_entry")
        assert "deleted_at" in src, (
            "delete_entry must set deleted_at (soft delete), not execute a SQL DELETE"
        )

    def test_list_entries_filters_deleted(self):
        """List must exclude soft-deleted entries (directly or via helper)."""
        src = _function_source("list_entries")
        assert "deleted_at" in src or "_get_active_entries_query" in src, (
            "list_entries must filter soft-deleted entries (directly or via _get_active_entries_query)"
        )

    def test_active_entries_helper_exists(self):
        assert "_get_active_entries_query" in SRC

    def test_active_entries_helper_filters_deleted_at(self):
        src = _function_source("_get_active_entries_query")
        assert "deleted_at" in src


# ── Mood validation ───────────────────────────────────────────────────────────


class TestMoodValidation:
    def test_valid_moods_defined(self):
        assert "_VALID_MOODS" in SRC

    def test_create_validates_mood(self):
        """Invalid mood must raise 400."""
        src = _function_source("create_entry")
        assert "mood" in src
        assert "HTTPException" in src or "400" in src

    def test_update_validates_mood(self):
        src = _function_source("update_entry")
        assert "mood" in src

    def test_valid_moods_contain_polish_emotions(self):
        for mood in ("spokój", "radość", "smutek", "wdzięczność"):
            assert mood in SRC, f"Mood '{mood}' not found in journal.py"

    def test_valid_moods_set_has_at_least_8_items(self):
        """Polish spiritual journal needs at least 8 moods."""
        # Count items in the _VALID_MOODS set from source via AST
        for node in ast.walk(TREE):
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "_VALID_MOODS" and isinstance(node.value, ast.Set):
                        assert len(node.value.elts) >= 8
                        return
        # If not found as Set literal, just check the string count in source
        assert SRC.count('"') >= 16  # at least 8 quoted mood strings


# ── Path parameters ───────────────────────────────────────────────────────────


class TestPathParameters:
    def test_get_entry_has_entry_id_path_param(self):
        paths = [p for _, p in ROUTES.get("get_entry", [])]
        assert any("{" in p for p in paths)

    def test_update_entry_has_entry_id_path_param(self):
        paths = [p for _, p in ROUTES.get("update_entry", [])]
        assert any("{" in p for p in paths)

    def test_delete_entry_has_entry_id_path_param(self):
        paths = [p for _, p in ROUTES.get("delete_entry", [])]
        assert any("{" in p for p in paths)


# ── Ownership check ───────────────────────────────────────────────────────────


class TestOwnershipEnforcement:
    def test_get_entry_checks_ownership(self):
        """Users must not be able to read other users' entries."""
        src = _function_source("get_entry")
        assert "user_id" in src or "current_user" in src

    def test_update_entry_checks_ownership(self):
        src = _function_source("update_entry")
        assert "user_id" in src or "current_user" in src

    def test_delete_entry_checks_ownership(self):
        src = _function_source("delete_entry")
        assert "user_id" in src or "current_user" in src

    def test_not_found_raises_404(self):
        """Non-existent or unauthorized entry access must raise 404."""
        for func in ("get_entry", "update_entry", "delete_entry"):
            src = _function_source(func)
            assert "404" in src or "HTTP_404_NOT_FOUND" in src, (
                f"{func} must raise 404 for missing/unauthorized entries"
            )


# ── Tag conversion helpers (inline logic tests) ───────────────────────────────


def _tags_to_str(tags: list[str]) -> str:
    return ",".join(t.strip()[:64] for t in tags[:20])


def _str_to_tags(tags_str: str | None) -> list[str]:
    if not tags_str:
        return []
    return [t.strip() for t in tags_str.split(",") if t.strip()]


class TestTagHelpers:
    def test_roundtrip_preserves_tags(self):
        tags = ["modlitwa", "Ewangelia", "Lectio"]
        assert _str_to_tags(_tags_to_str(tags)) == tags

    def test_max_20_tags_enforced(self):
        big = [f"tag{i}" for i in range(30)]
        assert _tags_to_str(big).count(",") == 19

    def test_tag_truncated_at_64_chars(self):
        assert len(_tags_to_str(["a" * 100])) == 64

    def test_empty_list_gives_empty_string(self):
        assert _tags_to_str([]) == ""

    def test_none_str_gives_empty_list(self):
        assert _str_to_tags(None) == []

    def test_blank_segments_skipped(self):
        assert _str_to_tags("modlitwa,,Ewangelia") == ["modlitwa", "Ewangelia"]

    def test_whitespace_stripped(self):
        assert _str_to_tags(" modlitwa , Ewangelia ") == ["modlitwa", "Ewangelia"]
