"""Unit tests for PushNotificationService and AuditService.

No network calls, no DB — pure data-layer testing.

Contracts verified:
PushNotificationService:
- PushSubscription / PushPayload dataclasses: fields, defaults
- morning_prayer_payload: correct title, url, tag; feast appended when present
- vespers_payload: breviary URL, vespers tag
- compline_payload: breviary URL, compline tag
- broadcast with no subscriptions returns {sent:0, failed:0}
- send returns False when VAPID keys not configured

AuditService.log (AsyncMock DB):
- Creates AuditLog entry with correct fields
- description truncated at 512 chars
- payload serialised to JSON string
- payload=None → payload_json=None
- non-serialisable payload falls back to "{}"
- returns AuditLog instance

AuditService.log_ai_interaction:
- was_modified=False → no AI_RESPONSE_REWRITTEN entry
- was_modified=True → extra audit entry added
- crisis risk_category → extra audit entry
- violations joined with comma
"""

from __future__ import annotations

import json

# Stub pywebpush before import (not installed)
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

if "pywebpush" not in sys.modules:
    sys.modules["pywebpush"] = MagicMock()

# Import AuditEventType via the ORM module (sqlalchemy is installed)
from app.models.database import AuditEventType
from app.services.audit.audit_service import AuditService
from app.services.notifications.push_service import (
    PushNotificationService,
    PushPayload,
    PushSubscription,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _push_svc(enabled: bool = False) -> PushNotificationService:
    svc = PushNotificationService.__new__(PushNotificationService)
    svc._enabled = enabled
    return svc


def _audit_svc() -> AuditService:
    return AuditService()


def _mock_db() -> AsyncMock:
    db = AsyncMock()
    db.add = MagicMock()
    return db


# ===========================================================================
# PushSubscription dataclass
# ===========================================================================


class TestPushSubscription:
    def test_all_fields(self):
        sub = PushSubscription(
            endpoint="https://push.example.com/sub/abc",
            p256dh="publickey_b64",
            auth="auth_secret_b64",
        )
        assert sub.endpoint.startswith("https://")
        assert sub.p256dh == "publickey_b64"
        assert sub.auth == "auth_secret_b64"


# ===========================================================================
# PushPayload dataclass
# ===========================================================================


class TestPushPayload:
    def test_required_fields(self):
        p = PushPayload(title="Test", body="Hello")
        assert p.title == "Test"
        assert p.body == "Hello"

    def test_url_defaults_to_lectio(self):
        p = PushPayload(title="T", body="B")
        assert p.url == "/lectio-divina"

    def test_tag_default(self):
        p = PushPayload(title="T", body="B")
        assert p.tag == "sancta-prayer"

    def test_icon_default(self):
        p = PushPayload(title="T", body="B")
        assert p.icon == "/icons/icon-192.svg"

    def test_data_default_empty(self):
        p = PushPayload(title="T", body="B")
        assert p.data == {}

    def test_custom_fields(self):
        p = PushPayload(
            title="Custom",
            body="Custom body",
            url="/my-route",
            tag="custom-tag",
            data={"key": "value"},
        )
        assert p.url == "/my-route"
        assert p.tag == "custom-tag"
        assert p.data["key"] == "value"


# ===========================================================================
# Canned payloads
# ===========================================================================


class TestMorningPrayerPayload:
    def test_no_feast(self):
        p = PushNotificationService.morning_prayer_payload()
        assert "Lectio Divina" in p.body
        assert p.url == "/lectio-divina"
        assert p.tag == "morning-prayer"

    def test_with_feast(self):
        p = PushNotificationService.morning_prayer_payload("Święty Józef")
        assert "Święty Józef" in p.body

    def test_title_contains_jutrznia(self):
        p = PushNotificationService.morning_prayer_payload()
        assert "Jutrznia" in p.title or "jutrznia" in p.title.lower()

    def test_returns_push_payload_instance(self):
        assert isinstance(PushNotificationService.morning_prayer_payload(), PushPayload)


class TestVespersPayload:
    def test_url_breviary(self):
        p = PushNotificationService.vespers_payload()
        assert p.url == "/breviary"

    def test_tag_vespers(self):
        p = PushNotificationService.vespers_payload()
        assert "vespers" in p.tag

    def test_body_non_empty(self):
        p = PushNotificationService.vespers_payload()
        assert p.body.strip()


class TestComplinePayload:
    def test_url_breviary(self):
        p = PushNotificationService.compline_payload()
        assert p.url == "/breviary"

    def test_tag_compline(self):
        p = PushNotificationService.compline_payload()
        assert "compline" in p.tag

    def test_body_mentions_rachuneksumiena_or_noc(self):
        p = PushNotificationService.compline_payload()
        body = p.body.lower()
        assert "rachunek" in body or "noc" in body or "kompleta" in body or "sen" in body


# ===========================================================================
# send / broadcast
# ===========================================================================


class TestPushSend:
    @pytest.mark.asyncio
    async def test_send_returns_false_when_disabled(self):
        svc = _push_svc(enabled=False)
        sub = PushSubscription(endpoint="https://x.com/sub", p256dh="k", auth="a")
        payload = PushPayload(title="T", body="B")
        result = await svc.send(sub, payload)
        assert result is False

    @pytest.mark.asyncio
    async def test_broadcast_empty_list_returns_zero_counts(self):
        svc = _push_svc(enabled=False)
        result = await svc.broadcast([], PushPayload(title="T", body="B"))
        assert result == {"sent": 0, "failed": 0}

    @pytest.mark.asyncio
    async def test_broadcast_all_disabled_returns_failed_count(self):
        svc = _push_svc(enabled=False)
        subs = [
            PushSubscription(endpoint=f"https://x.com/{i}", p256dh="k", auth="a")
            for i in range(3)
        ]
        result = await svc.broadcast(subs, PushPayload(title="T", body="B"))
        assert result == {"sent": 0, "failed": 3}


# ===========================================================================
# AuditService.log
# ===========================================================================


class TestAuditServiceLog:
    @pytest.mark.asyncio
    async def test_creates_entry_with_correct_fields(self):
        svc = _audit_svc()
        db = _mock_db()
        entry = await svc.log(
            db,
            AuditEventType.USER_ROLE_CHANGED,
            "Role changed to admin",
            user_id="user-001",
            actor_id="admin-001",
            payload={"old_role": "user", "new_role": "admin"},
            ip_address="127.0.0.1",
        )
        assert entry.event_type == AuditEventType.USER_ROLE_CHANGED
        assert entry.user_id == "user-001"
        assert entry.actor_id == "admin-001"
        assert entry.description == "Role changed to admin"
        assert entry.ip_address == "127.0.0.1"

    @pytest.mark.asyncio
    async def test_payload_serialised_to_json(self):
        svc = _audit_svc()
        db = _mock_db()
        entry = await svc.log(
            db,
            AuditEventType.USER_ROLE_CHANGED,
            "desc",
            payload={"key": "value"},
        )
        payload_data = json.loads(entry.payload_json)
        assert payload_data["key"] == "value"

    @pytest.mark.asyncio
    async def test_none_payload_gives_none_json(self):
        svc = _audit_svc()
        db = _mock_db()
        entry = await svc.log(db, AuditEventType.USER_ROLE_CHANGED, "desc")
        assert entry.payload_json is None

    @pytest.mark.asyncio
    async def test_description_truncated_at_512(self):
        svc = _audit_svc()
        db = _mock_db()
        long_desc = "x" * 600
        entry = await svc.log(db, AuditEventType.USER_ROLE_CHANGED, long_desc)
        assert len(entry.description) == 512

    @pytest.mark.asyncio
    async def test_db_add_called(self):
        svc = _audit_svc()
        db = _mock_db()
        await svc.log(db, AuditEventType.USER_ROLE_CHANGED, "desc")
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_returns_audit_log_instance(self):
        from app.models.database import AuditLog
        svc = _audit_svc()
        db = _mock_db()
        entry = await svc.log(db, AuditEventType.USER_ROLE_CHANGED, "desc")
        assert isinstance(entry, AuditLog)

    @pytest.mark.asyncio
    async def test_non_serialisable_payload_falls_back(self):
        svc = _audit_svc()
        db = _mock_db()
        # date objects aren't JSON-serialisable by default; json.dumps default=str handles it
        from datetime import datetime
        entry = await svc.log(
            db,
            AuditEventType.USER_ROLE_CHANGED,
            "desc",
            payload={"ts": datetime(2026, 1, 1)},
        )
        assert entry.payload_json is not None
        # Should succeed via default=str
        parsed = json.loads(entry.payload_json)
        assert "ts" in parsed


# ===========================================================================
# AuditService.log_ai_interaction
# ===========================================================================


class TestAuditLogAiInteraction:
    @pytest.mark.asyncio
    async def test_was_modified_false_no_extra_log(self):
        svc = _audit_svc()
        db = _mock_db()
        await svc.log_ai_interaction(
            db,
            user_id="user-001",
            module="lectio_divina",
            risk_category="low",
            was_modified=False,
        )
        # Only AiInteraction added — no extra audit log for rewritten
        db.add.assert_called_once()

    @pytest.mark.asyncio
    async def test_was_modified_true_adds_audit_entry(self):
        svc = _audit_svc()
        db = _mock_db()
        await svc.log_ai_interaction(
            db,
            user_id="user-001",
            module="reflection",
            risk_category="low",
            was_modified=True,
        )
        # AiInteraction + AuditLog = 2 adds
        assert db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_crisis_category_adds_audit_entry(self):
        svc = _audit_svc()
        db = _mock_db()
        await svc.log_ai_interaction(
            db,
            user_id="user-001",
            module="emotion",
            risk_category="crisis",
            was_modified=False,
        )
        # AiInteraction + crisis AuditLog = 2 adds
        assert db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_self_harm_risk_adds_audit_entry(self):
        svc = _audit_svc()
        db = _mock_db()
        await svc.log_ai_interaction(
            db,
            user_id="u",
            module="m",
            risk_category="self_harm_risk",
            was_modified=False,
        )
        assert db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_abuse_risk_adds_audit_entry(self):
        svc = _audit_svc()
        db = _mock_db()
        await svc.log_ai_interaction(
            db,
            user_id="u",
            module="m",
            risk_category="abuse_risk",
            was_modified=False,
        )
        assert db.add.call_count == 2

    @pytest.mark.asyncio
    async def test_violations_joined_with_comma(self):
        svc = _audit_svc()
        db = _mock_db()
        from app.models.database import AiInteraction

        captured_interaction = None
        original_add = db.add

        def capture_add(obj):
            nonlocal captured_interaction
            if isinstance(obj, AiInteraction):
                captured_interaction = obj
            original_add(obj)

        db.add = capture_add

        await svc.log_ai_interaction(
            db,
            user_id="u",
            module="m",
            risk_category="low",
            was_modified=False,
            violations=["T-02", "E-01"],
        )
        assert captured_interaction is not None
        assert captured_interaction.violations == "T-02,E-01"

    @pytest.mark.asyncio
    async def test_no_violations_leaves_violations_none(self):
        svc = _audit_svc()
        db = _mock_db()
        from app.models.database import AiInteraction

        captured_interaction = None

        def capture_add(obj):
            nonlocal captured_interaction
            if isinstance(obj, AiInteraction):
                captured_interaction = obj

        db.add = capture_add

        await svc.log_ai_interaction(
            db,
            user_id="u",
            module="m",
            risk_category="low",
            was_modified=False,
        )
        assert captured_interaction is not None
        assert captured_interaction.violations is None
