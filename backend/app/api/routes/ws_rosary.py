"""WebSocket — Różaniec Wspólnotowy w czasie rzeczywistym.

Protokół:

  Połączenie:  WS /ws/rosary/{session_id}?token=<jwt_access_token>

  Server → Client (JSON):
    {"type": "state",           "participants": N, "decades_completed": [1,2], "mystery_type": "..."}
    {"type": "joined",          "user_id": "...", "participants": N}
    {"type": "left",            "user_id": "...", "participants": N}
    {"type": "decade",          "decade": 3, "user_id": "...", "participants": N, "decades_completed": [...]}
    {"type": "error",           "message": "..."}

  Client → Server (JSON):
    {"type": "complete_decade", "decade": 3}
    {"type": "ping"}

Uwagi implementacyjne:
  - Autentykacja przez query param ?token= (przeglądarka nie obsługuje custom headers w WS)
  - Connection manager jest in-process (dict) — wystarczy dla jednej instancji serwera.
    W środowisku multi-instance należy zastąpić Redis pub/sub.
  - Decade completion jest zapisywana do bazy przez istniejący REST endpoint.
    WebSocket tylko rozgłasza zdarzenie — nie modyfikuje DB bezpośrednio.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.core.dependencies import _get_session_factory
from app.core.security import verify_token
from app.models.database import CommunityRosary

logger = logging.getLogger(__name__)
router = APIRouter()


# ── In-process connection registry ────────────────────────────────────────────

class _ConnectionManager:
    """Manages active WebSocket connections grouped by rosary session_id."""

    def __init__(self) -> None:
        # session_id → {user_id: WebSocket}
        self._sessions: dict[str, dict[str, WebSocket]] = defaultdict(dict)

    def connect(self, session_id: str, user_id: str, ws: WebSocket) -> None:
        self._sessions[session_id][user_id] = ws
        logger.info("WS connected: session=%s user=%s total=%d",
                    session_id, user_id, self.count(session_id))

    def disconnect(self, session_id: str, user_id: str) -> None:
        self._sessions[session_id].pop(user_id, None)
        if not self._sessions[session_id]:
            del self._sessions[session_id]
        logger.info("WS disconnected: session=%s user=%s", session_id, user_id)

    def count(self, session_id: str) -> int:
        return len(self._sessions.get(session_id, {}))

    async def broadcast(self, session_id: str, message: dict[str, Any]) -> None:
        text = json.dumps(message, ensure_ascii=False)
        dead: list[str] = []
        for uid, ws in list(self._sessions.get(session_id, {}).items()):
            try:
                await ws.send_text(text)
            except Exception:
                dead.append(uid)
        for uid in dead:
            self.disconnect(session_id, uid)

    async def send_to(self, session_id: str, user_id: str, message: dict[str, Any]) -> None:
        ws = self._sessions.get(session_id, {}).get(user_id)
        if ws:
            try:
                await ws.send_text(json.dumps(message, ensure_ascii=False))
            except Exception:
                self.disconnect(session_id, user_id)


_manager = _ConnectionManager()


# ── JWT auth helper (WebSocket can't use Bearer header) ───────────────────────

async def _authenticate(token: str | None) -> str | None:
    """Validate JWT and return user_id, or None on failure."""
    if not token:
        return None
    try:
        payload = verify_token(token, expected_type="access")
        return payload.get("sub")
    except Exception:
        return None


async def _get_session_mystery(session_id: str) -> str | None:
    """Return mystery_type for the rosary session from DB (best-effort)."""
    try:
        factory = _get_session_factory()
        async with factory() as db:
            result = await db.execute(
                select(CommunityRosary).where(CommunityRosary.id == session_id)
            )
            s = result.scalar_one_or_none()
            return s.mystery_type if s else None
    except Exception:
        return None


# ── WebSocket endpoint ────────────────────────────────────────────────────────

@router.websocket("/rosary/{session_id}")
async def rosary_ws(
    session_id: str,
    websocket: WebSocket,
    token: str | None = None,
) -> None:
    """Real-time sync dla Różańca Wspólnotowego.

    Użyj query param ?token=<access_token> przy łączeniu.
    Brak tokenu lub nieprawidłowy = rozłączenie 4001.
    """
    user_id = await _authenticate(token)
    if not user_id:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    _manager.connect(session_id, user_id, websocket)

    mystery_type = await _get_session_mystery(session_id)

    # Wyślij aktualny stan
    await _manager.send_to(session_id, user_id, {
        "type": "state",
        "participants": _manager.count(session_id),
        "decades_completed": [],
        "mystery_type": mystery_type or "radosne",
    })

    # Powiadom pozostałych uczestników
    await _manager.broadcast(session_id, {
        "type": "joined",
        "user_id": user_id,
        "participants": _manager.count(session_id),
    })

    try:
        while True:
            raw = await websocket.receive_text()
            try:
                msg = json.loads(raw)
            except json.JSONDecodeError:
                continue

            msg_type = msg.get("type")

            if msg_type == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))

            elif msg_type == "complete_decade":
                decade = msg.get("decade")
                if not isinstance(decade, int) or not (1 <= decade <= 5):
                    await websocket.send_text(json.dumps({
                        "type": "error",
                        "message": "Dziesiątka musi być liczbą 1–5.",
                    }))
                    continue

                # Rozgłoś do wszystkich uczestników sesji
                await _manager.broadcast(session_id, {
                    "type": "decade",
                    "decade": decade,
                    "user_id": user_id,
                    "participants": _manager.count(session_id),
                })
                logger.info("Decade %d broadcast: session=%s user=%s", decade, session_id, user_id)

    except WebSocketDisconnect:
        pass
    finally:
        _manager.disconnect(session_id, user_id)
        await _manager.broadcast(session_id, {
            "type": "left",
            "user_id": user_id,
            "participants": _manager.count(session_id),
        })
