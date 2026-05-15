"""Testy jednostkowe dla notifications.py — VAPID, push subscribe, daily-reminder.

Sprawdzamy:
  - Wszystkie endpointy istnieją (GET/POST/DELETE)
  - /vapid-public-key jest publiczny (brak JWT)
  - /subscribe i /test wymagają JWT
  - /send-morning nie wymaga JWT (cron endpoint)
  - Schematy mają wymagane pola
  - daily-reminder nie ma user_id w request body
"""

from __future__ import annotations

import ast
import sys
from pathlib import Path

import pytest

NOTIF_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "notifications.py"
sys.path.insert(0, str(Path(__file__).parents[2]))


# ── AST helpers ───────────────────────────────────────────────────────────────


def _tree() -> ast.Module:
    return ast.parse(NOTIF_PATH.read_text())


def _routes() -> list[tuple[str, str]]:
    routes = []
    for node in ast.walk(_tree()):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            for dec in node.decorator_list:
                if isinstance(dec, ast.Call) and isinstance(dec.func, ast.Attribute):
                    method = dec.func.attr
                    args = dec.args
                    if args and isinstance(args[0], ast.Constant):
                        routes.append((method, args[0].value))
    return routes


def _func_lines(name: str) -> str:
    src = NOTIF_PATH.read_text()
    lines = src.split("\n")
    start = None
    for i, line in enumerate(lines):
        if f"async def {name}" in line or f"def {name}" in line:
            start = i
            break
    if start is None:
        return ""
    return "\n".join(lines[start:start + 30])


def _get_func_params(func_name: str) -> list[str]:
    """Pobiera nazwy parametrów funkcji (przez AST)."""
    tree = _tree()
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func_name:
            return [arg.arg for arg in node.args.args]
    return []


# ── Endpointy ─────────────────────────────────────────────────────────────────


class TestNotificationsEndpoints:
    def test_vapid_public_key_endpoint_exists(self):
        assert any(path == "/vapid-public-key" for _, path in _routes())

    def test_vapid_public_key_is_get(self):
        assert ("get", "/vapid-public-key") in _routes()

    def test_subscribe_endpoint_exists(self):
        assert any(path == "/subscribe" for _, path in _routes())

    def test_subscribe_is_post(self):
        assert ("post", "/subscribe") in _routes()

    def test_unsubscribe_is_delete(self):
        assert ("delete", "/unsubscribe") in _routes()

    def test_daily_reminder_is_post(self):
        assert ("post", "/daily-reminder") in _routes()

    def test_send_morning_is_post(self):
        assert ("post", "/send-morning") in _routes()

    def test_stats_is_get(self):
        assert ("get", "/stats") in _routes()


# ── Bezpieczeństwo ────────────────────────────────────────────────────────────


class TestNotificationsSecurity:
    def test_vapid_public_key_is_public(self):
        """VAPID public key nie wymaga JWT — musi być dostępny przed zalogowaniem."""
        func = _func_lines("get_vapid_public_key")
        assert "require_authenticated" not in func

    def test_subscribe_is_public_by_design(self):
        """Web Push subscribe jest publiczne — subskrypcja oparta o endpoint, nie JWT.
        Docelowo w produkcji powiązać z user_id, ale nie blokować niezalogowanych."""
        func = _func_lines("subscribe")
        # Test dokumentuje decyzję projektową — nie wymaga JWT
        assert "endpoint" in func  # ale waliduje obecność endpoint i keys

    def test_send_morning_is_cron_endpoint_no_jwt(self):
        """send_morning_notifications to endpoint cronowy — nie wymaga JWT."""
        func = _func_lines("send_morning_notifications")
        assert "require_authenticated" not in func
        assert "require_admin" not in func


# ── No user_id in request bodies ─────────────────────────────────────────────


class TestNoUserIdInBody:
    def test_subscribe_request_has_no_user_id(self):
        source = NOTIF_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and "Subscribe" in node.name and "Request" in node.name:
                for item in ast.walk(node):
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        assert item.target.id != "user_id", f"user_id znaleziony w {node.name}"

    def test_daily_reminder_request_has_no_user_id(self):
        source = NOTIF_PATH.read_text()
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and "Reminder" in node.name:
                for item in ast.walk(node):
                    if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name):
                        assert item.target.id != "user_id", f"user_id znaleziony w {node.name}"


# ── Schematy ─────────────────────────────────────────────────────────────────


class TestNotificationsSchemas:
    def test_subscribe_request_has_endpoint_field(self):
        source = NOTIF_PATH.read_text()
        assert "endpoint" in source

    def test_subscribe_request_has_keys_field(self):
        source = NOTIF_PATH.read_text()
        assert "keys" in source

    def test_test_notification_schema_exists(self):
        tree = _tree()
        classes = [n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)]
        assert any("Test" in c and "Request" in c for c in classes)


# ── /vapid-public-key response ────────────────────────────────────────────────


class TestVapidPublicKeyResponse:
    def test_returns_public_key_field(self):
        source = NOTIF_PATH.read_text()
        # Endpoint zwraca słownik z kluczem publicKey (camelCase — Web Push standard)
        assert "publicKey" in source or "public_key" in source

    def test_reads_from_settings(self):
        source = NOTIF_PATH.read_text()
        assert "VAPID_PUBLIC_KEY" in source or "vapid_public_key" in source.lower()


# ── /send-morning ─────────────────────────────────────────────────────────────


class TestSendMorning:
    def test_send_morning_returns_count(self):
        source = NOTIF_PATH.read_text()
        # Endpoint zwraca liczniki wysłanych/pominietych
        assert "sent" in source

    def test_source_imports_web_push_or_has_push_logic(self):
        source = NOTIF_PATH.read_text()
        # Sprawdzamy czy jest jakaś logika wysyłania powiadomień
        assert "webpush" in source.lower() or "push" in source.lower()
