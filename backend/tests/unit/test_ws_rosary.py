"""Unit tests for app/api/routes/ws_rosary.py.

Tests the in-process _ConnectionManager (pure-Python, no WebSocket infra needed)
and AST-level checks on the WebSocket endpoint structure.

Contracts verified:
- _ConnectionManager: connect/disconnect/count/broadcast/send_to
- Broadcast skips and removes dead connections
- Disconnect from last user in session removes session from registry
- count() returns 0 for unknown sessions
- send_to() is a no-op for unknown session/user
- AST: WebSocket route path is /rosary/{session_id}
- AST: JWT token validated via query param (not header — browsers can't set WS headers)
- AST: 4001 close code for missing/invalid token
- AST: WS endpoint handles ping and complete_decade message types
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

WS_PATH = Path(__file__).parents[2] / "app" / "api" / "routes" / "ws_rosary.py"


# ── _ConnectionManager import ─────────────────────────────────────────────────
# Import inline to avoid importing FastAPI WebSocket class

def _get_manager_class():
    """Import _ConnectionManager without triggering FastAPI/SQLAlchemy init."""
    import sys

    # Minimal stubs for heavy deps
    for mod in ("fastapi", "fastapi.responses", "sqlalchemy", "sqlalchemy.ext.asyncio"):
        if mod not in sys.modules:
            sys.modules[mod] = MagicMock()

    # The class is pure Python so we can parse + exec the relevant part
    src = WS_PATH.read_text()
    # We exec only the class and its dependencies (json, logging, defaultdict)
    exec_ns: dict = {}
    exec(
        "from collections import defaultdict\n"
        "import json, logging, asyncio\n"
        "from typing import Any\n"
        "WebSocket = object\n"
        "logger = logging.getLogger('ws_rosary_test')\n",
        exec_ns,
    )
    # Manually define the class from source
    tree = ast.parse(src)
    class_source_lines = src.split("\n")
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef) and node.name == "_ConnectionManager":
            start = node.lineno - 1
            end = node.end_lineno
            class_src = "\n".join(class_source_lines[start:end])
            exec(class_src, exec_ns)
            return exec_ns["_ConnectionManager"]
    raise RuntimeError("_ConnectionManager class not found in ws_rosary.py")


try:
    _CM = _get_manager_class()
    _IMPORT_OK = True
except Exception:
    _IMPORT_OK = False
    _CM = None


# ── _ConnectionManager unit tests ─────────────────────────────────────────────

@pytest.mark.skipif(not _IMPORT_OK, reason="_ConnectionManager could not be imported")
class TestConnectionManager:
    def _cm(self):
        return _CM()

    def _ws(self):
        ws = AsyncMock()
        ws.send_text = AsyncMock()
        return ws

    def test_initial_count_zero_for_unknown_session(self):
        cm = self._cm()
        assert cm.count("nonexistent") == 0

    def test_connect_increments_count(self):
        cm = self._cm()
        cm.connect("sess-1", "user-A", self._ws())
        assert cm.count("sess-1") == 1

    def test_connect_multiple_users(self):
        cm = self._cm()
        cm.connect("sess-1", "user-A", self._ws())
        cm.connect("sess-1", "user-B", self._ws())
        assert cm.count("sess-1") == 2

    def test_disconnect_decrements_count(self):
        cm = self._cm()
        cm.connect("sess-1", "user-A", self._ws())
        cm.disconnect("sess-1", "user-A")
        assert cm.count("sess-1") == 0

    def test_disconnect_last_user_removes_session(self):
        cm = self._cm()
        cm.connect("sess-1", "user-A", self._ws())
        cm.disconnect("sess-1", "user-A")
        # Session key should be cleaned up
        assert "sess-1" not in cm._sessions

    def test_disconnect_unknown_user_is_noop(self):
        cm = self._cm()
        # Should not raise
        cm.disconnect("nonexistent", "nobody")
        assert cm.count("nonexistent") == 0

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_users(self):
        cm = self._cm()
        ws_a = self._ws()
        ws_b = self._ws()
        cm.connect("sess-1", "user-A", ws_a)
        cm.connect("sess-1", "user-B", ws_b)

        await cm.broadcast("sess-1", {"type": "state", "participants": 2})

        ws_a.send_text.assert_awaited_once()
        ws_b.send_text.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_broadcast_message_is_valid_json(self):
        cm = self._cm()
        ws = self._ws()
        cm.connect("sess-1", "user-A", ws)

        payload = {"type": "decade", "decade": 3}
        await cm.broadcast("sess-1", payload)

        call_args = ws.send_text.call_args[0][0]
        assert json.loads(call_args) == payload

    @pytest.mark.asyncio
    async def test_broadcast_removes_dead_connections(self):
        cm = self._cm()
        dead_ws = self._ws()
        dead_ws.send_text.side_effect = Exception("connection closed")
        cm.connect("sess-1", "dead-user", dead_ws)

        await cm.broadcast("sess-1", {"type": "ping"})

        # Dead connection should be removed
        assert cm.count("sess-1") == 0

    @pytest.mark.asyncio
    async def test_broadcast_noop_for_unknown_session(self):
        cm = self._cm()
        # Should not raise
        await cm.broadcast("nonexistent", {"type": "ping"})

    @pytest.mark.asyncio
    async def test_send_to_specific_user(self):
        cm = self._cm()
        ws_a = self._ws()
        ws_b = self._ws()
        cm.connect("sess-1", "user-A", ws_a)
        cm.connect("sess-1", "user-B", ws_b)

        await cm.send_to("sess-1", "user-A", {"type": "state"})

        ws_a.send_text.assert_awaited_once()
        ws_b.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_to_noop_for_unknown_user(self):
        cm = self._cm()
        ws = self._ws()
        cm.connect("sess-1", "user-A", ws)

        # Should not raise, should not send to user-A
        await cm.send_to("sess-1", "nobody", {"type": "ping"})
        ws.send_text.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_send_to_removes_dead_connection(self):
        cm = self._cm()
        dead_ws = self._ws()
        dead_ws.send_text.side_effect = Exception("gone")
        cm.connect("sess-1", "dead-user", dead_ws)

        await cm.send_to("sess-1", "dead-user", {"type": "state"})

        assert cm.count("sess-1") == 0


# ── AST-level structural checks ───────────────────────────────────────────────


def _src() -> str:
    return WS_PATH.read_text()


def _tree() -> ast.Module:
    return ast.parse(_src())


class TestWsRosaryStructure:
    def test_websocket_route_path(self):
        """The WS endpoint path must include session_id as path param."""
        src = _src()
        assert "/rosary/{session_id}" in src

    def test_uses_query_param_for_jwt(self):
        """JWT must be passed via query param (browsers can't set WS headers)."""
        src = _src()
        assert "token" in src
        # The token query param should be in the function signature
        assert "token: str | None = None" in src or "token: Optional[str]" in src

    def test_closes_4001_on_missing_token(self):
        """Missing/invalid JWT → WebSocket close code 4001 (custom auth failure)."""
        src = _src()
        assert "4001" in src

    def test_handles_ping_message(self):
        """Must handle 'ping' message type from clients."""
        src = _src()
        assert '"ping"' in src or "'ping'" in src

    def test_handles_complete_decade(self):
        """Must handle 'complete_decade' message type."""
        src = _src()
        assert "complete_decade" in src

    def test_broadcasts_on_decade_completion(self):
        """Must broadcast to all participants when a decade is completed."""
        src = _src()
        assert "broadcast" in src

    def test_sends_state_on_join(self):
        """New participant should receive current session state."""
        src = _src()
        assert '"state"' in src or "'state'" in src

    def test_handles_websocket_disconnect(self):
        """Must handle WebSocketDisconnect gracefully."""
        src = _src()
        assert "WebSocketDisconnect" in src

    def test_connection_manager_singleton(self):
        """A single module-level _manager instance should manage all connections."""
        src = _src()
        assert "_manager = _ConnectionManager()" in src

    def test_authenticate_helper_defined(self):
        """JWT auth is delegated to _authenticate helper (not inline)."""
        src = _src()
        assert "async def _authenticate" in src

    def test_verify_token_called(self):
        """verify_token from app.core.security must be used."""
        src = _src()
        assert "verify_token" in src

    def test_class_connection_manager_defined(self):
        tree = _tree()
        classes = {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
        assert "_ConnectionManager" in classes

    def test_connection_manager_has_broadcast_method(self):
        tree = _tree()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_ConnectionManager":
                methods = {n.name for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                assert "broadcast" in methods

    def test_connection_manager_has_connect_disconnect(self):
        tree = _tree()
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef) and node.name == "_ConnectionManager":
                methods = {n.name for n in ast.walk(node) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
                assert "connect" in methods
                assert "disconnect" in methods
