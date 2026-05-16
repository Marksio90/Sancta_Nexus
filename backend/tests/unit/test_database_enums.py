"""Unit tests for database model enum catalogs.

Pure-Python — no DB, no stubs required (all enums are plain str+Enum).

Contracts verified:
SubscriptionTier:
- Exactly 4 tiers: free, pilgrim, disciple, mystic
- Is str subclass, all unique values

SessionType:
- Exactly 5 types: lectio_divina, spiritual_direction, bible_study,
  prayer, meditation
- Is str subclass, all unique values

AuditEventType:
- Exactly 15 event types
- Key user events present: USER_REGISTERED, USER_ROLE_CHANGED,
  USER_DELETED, USER_DATA_EXPORTED
- Key AI events present: AI_RESPONSE_GENERATED, AI_RESPONSE_REWRITTEN,
  AI_CRISIS_DETECTED
- Key content events present: CONTENT_CREATED, CONTENT_PUBLISHED,
  CONTENT_ARCHIVED
- Key admin/moderation events present: INTENTION_MODERATED,
  MODULE_TOGGLED, ROLE_PERMISSION_DENIED
- Privacy events present: JOURNAL_ENTRY_DELETED,
  ACCOUNT_DELETION_REQUESTED
- All values use snake_case (no uppercase, no hyphens)
- Is str subclass, all unique values

IntentionStatus:
- Exactly 5 statuses: active, answered, closed, pending_moderation,
  rejected
- Is str subclass, all unique values
"""

from __future__ import annotations

from app.models.database import (
    AuditEventType,
    IntentionStatus,
    SessionType,
    SubscriptionTier,
)

# ===========================================================================
# SubscriptionTier
# ===========================================================================


class TestSubscriptionTier:
    def test_exactly_4_tiers(self):
        assert len(SubscriptionTier) == 4

    def test_free(self):
        assert SubscriptionTier.FREE == "free"

    def test_pilgrim(self):
        assert SubscriptionTier.PILGRIM == "pilgrim"

    def test_disciple(self):
        assert SubscriptionTier.DISCIPLE == "disciple"

    def test_mystic(self):
        assert SubscriptionTier.MYSTIC == "mystic"

    def test_is_str_subclass(self):
        assert isinstance(SubscriptionTier.FREE, str)

    def test_all_values_unique(self):
        vals = [t.value for t in SubscriptionTier]
        assert len(vals) == len(set(vals))

    def test_all_values_lowercase(self):
        for tier in SubscriptionTier:
            assert tier.value == tier.value.lower(), f"{tier} value not lowercase"

    def test_free_is_base_tier(self):
        # FREE must exist as the default — checked by ordering value exists
        assert "free" in {t.value for t in SubscriptionTier}


# ===========================================================================
# SessionType
# ===========================================================================


class TestSessionType:
    def test_exactly_5_types(self):
        assert len(SessionType) == 5

    def test_lectio_divina(self):
        assert SessionType.LECTIO_DIVINA == "lectio_divina"

    def test_spiritual_direction(self):
        assert SessionType.SPIRITUAL_DIRECTION == "spiritual_direction"

    def test_bible_study(self):
        assert SessionType.BIBLE_STUDY == "bible_study"

    def test_prayer(self):
        assert SessionType.PRAYER == "prayer"

    def test_meditation(self):
        assert SessionType.MEDITATION == "meditation"

    def test_is_str_subclass(self):
        assert isinstance(SessionType.PRAYER, str)

    def test_all_values_unique(self):
        vals = [t.value for t in SessionType]
        assert len(vals) == len(set(vals))

    def test_all_expected_present(self):
        expected = {
            "lectio_divina", "spiritual_direction", "bible_study",
            "prayer", "meditation",
        }
        assert expected == {t.value for t in SessionType}


# ===========================================================================
# AuditEventType
# ===========================================================================


class TestAuditEventType:
    def test_exactly_16_types(self):
        assert len(AuditEventType) == 16

    # User lifecycle events
    def test_user_registered(self):
        assert AuditEventType.USER_REGISTERED == "user_registered"

    def test_user_role_changed(self):
        assert AuditEventType.USER_ROLE_CHANGED == "user_role_changed"

    def test_user_deleted(self):
        assert AuditEventType.USER_DELETED == "user_deleted"

    def test_user_data_exported(self):
        assert AuditEventType.USER_DATA_EXPORTED == "user_data_exported"

    # AI safety events
    def test_ai_response_generated(self):
        assert AuditEventType.AI_RESPONSE_GENERATED == "ai_response_generated"

    def test_ai_response_rewritten(self):
        assert AuditEventType.AI_RESPONSE_REWRITTEN == "ai_response_rewritten"

    def test_ai_crisis_detected(self):
        assert AuditEventType.AI_CRISIS_DETECTED == "ai_crisis_detected"

    # Content management events
    def test_content_created(self):
        assert AuditEventType.CONTENT_CREATED == "content_created"

    def test_content_published(self):
        assert AuditEventType.CONTENT_PUBLISHED == "content_published"

    def test_content_archived(self):
        assert AuditEventType.CONTENT_ARCHIVED == "content_archived"

    # Moderation and admin events
    def test_intention_moderated(self):
        assert AuditEventType.INTENTION_MODERATED == "intention_moderated"

    def test_module_toggled(self):
        assert AuditEventType.MODULE_TOGGLED == "module_toggled"

    def test_role_permission_denied(self):
        assert AuditEventType.ROLE_PERMISSION_DENIED == "role_permission_denied"

    # Privacy / GDPR events
    def test_journal_entry_deleted(self):
        assert AuditEventType.JOURNAL_ENTRY_DELETED == "journal_entry_deleted"

    def test_account_deletion_requested(self):
        assert AuditEventType.ACCOUNT_DELETION_REQUESTED == "account_deletion_requested"

    def test_is_str_subclass(self):
        assert isinstance(AuditEventType.USER_REGISTERED, str)

    def test_all_values_unique(self):
        vals = [e.value for e in AuditEventType]
        assert len(vals) == len(set(vals))

    def test_all_values_snake_case(self):
        for event in AuditEventType:
            v = event.value
            assert v == v.lower(), f"{event} value not lowercase"
            assert "-" not in v, f"{event} value contains hyphen"
            assert " " not in v, f"{event} value contains space"

    def test_all_expected_present(self):
        expected = {
            "user_registered", "user_role_changed", "user_deleted",
            "user_data_exported", "login_failed",
            "ai_response_generated", "ai_response_rewritten", "ai_crisis_detected",
            "content_created", "content_published", "content_archived",
            "intention_moderated", "module_toggled",
            "role_permission_denied", "journal_entry_deleted",
            "account_deletion_requested",
        }
        assert expected == {e.value for e in AuditEventType}


# ===========================================================================
# IntentionStatus
# ===========================================================================


class TestIntentionStatus:
    def test_exactly_5_statuses(self):
        assert len(IntentionStatus) == 5

    def test_active(self):
        assert IntentionStatus.ACTIVE == "active"

    def test_answered(self):
        assert IntentionStatus.ANSWERED == "answered"

    def test_closed(self):
        assert IntentionStatus.CLOSED == "closed"

    def test_pending_moderation(self):
        assert IntentionStatus.PENDING_MODERATION == "pending_moderation"

    def test_rejected(self):
        assert IntentionStatus.REJECTED == "rejected"

    def test_is_str_subclass(self):
        assert isinstance(IntentionStatus.ACTIVE, str)

    def test_all_values_unique(self):
        vals = [s.value for s in IntentionStatus]
        assert len(vals) == len(set(vals))

    def test_all_expected_present(self):
        expected = {
            "active", "answered", "closed", "pending_moderation", "rejected",
        }
        assert expected == {s.value for s in IntentionStatus}

    def test_moderation_states_present(self):
        # Both pre- and post-moderation states must exist
        assert IntentionStatus.PENDING_MODERATION in IntentionStatus
        assert IntentionStatus.REJECTED in IntentionStatus
        assert IntentionStatus.ACTIVE in IntentionStatus
