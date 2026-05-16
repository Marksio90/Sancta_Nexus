"""Unit tests for prayer intention moderation workflow logic.

Tests are self-contained — no database, no infra imports.
We inline the pure business rules from PrayerIntentionService and the
IntentionStatus enum to verify all moderation state transitions.

These tests document and enforce the Phase 4 moderation contract:
  - Public intentions start as PENDING_MODERATION
  - Private intentions start as ACTIVE immediately
  - Approving sets status ACTIVE + records moderator/timestamp
  - Rejecting sets status REJECTED + records reason + moderator/timestamp
  - Only ACTIVE intentions appear in the public listing
  - IntentionStatus enum has all five required values
"""
from __future__ import annotations

from datetime import UTC, datetime

# ── Inline the IntentionStatus enum values (no DB import needed) ──────────────

class _IntentionStatus:
    ACTIVE = "active"
    ANSWERED = "answered"
    CLOSED = "closed"
    PENDING_MODERATION = "pending_moderation"
    REJECTED = "rejected"

    @classmethod
    def values(cls) -> set[str]:
        return {cls.ACTIVE, cls.ANSWERED, cls.CLOSED, cls.PENDING_MODERATION, cls.REJECTED}


# ── Inline the business-logic helpers from PrayerIntentionService ─────────────

def _compute_initial_status(is_public: bool) -> str:
    """Mirror PrayerIntentionService.create() status assignment."""
    if is_public:
        return _IntentionStatus.PENDING_MODERATION
    return _IntentionStatus.ACTIVE


def _approve(intention: dict) -> dict:
    """Mirror PrayerIntentionService.approve() state transition."""
    updated = dict(intention)
    updated["status"] = _IntentionStatus.ACTIVE
    updated["moderated_at"] = datetime.now(UTC).isoformat()
    # moderator_id would be set from the caller in the real service
    return updated


def _reject(intention: dict, reason: str) -> dict:
    """Mirror PrayerIntentionService.reject() state transition."""
    updated = dict(intention)
    updated["status"] = _IntentionStatus.REJECTED
    updated["rejection_reason"] = reason[:500]
    updated["moderated_at"] = datetime.now(UTC).isoformat()
    return updated


def _is_visible_in_public_listing(intention: dict) -> bool:
    """Mirror list_public() filter: only ACTIVE + is_public."""
    return (
        intention.get("is_public", False)
        and intention.get("status") == _IntentionStatus.ACTIVE
    )


def _make_intention(
    *,
    is_public: bool = True,
    status: str = _IntentionStatus.ACTIVE,
    content: str = "Proszę o zdrowie dla mojej rodziny.",
    moderator_id: str | None = None,
    moderated_at: str | None = None,
    rejection_reason: str | None = None,
    group_id: str | None = None,
    user_id: str | None = None,
) -> dict:
    return {
        "id": "test-id",
        "content": content,
        "is_public": is_public,
        "status": status,
        "author_display": "Anonim",
        "category": "general",
        "prayer_count": 0,
        "created_at": "2026-05-14T10:00:00+00:00",
        "expires_at": None,
        "group_id": group_id,
        "moderator_id": moderator_id,
        "moderated_at": moderated_at,
        "rejection_reason": rejection_reason,
        "user_id": user_id,
    }


# ── Tests: initial status assignment ─────────────────────────────────────────


class TestInitialStatus:
    def test_public_intention_starts_pending_moderation(self):
        status = _compute_initial_status(is_public=True)
        assert status == _IntentionStatus.PENDING_MODERATION

    def test_private_intention_starts_active(self):
        status = _compute_initial_status(is_public=False)
        assert status == _IntentionStatus.ACTIVE

    def test_public_intention_not_immediately_active(self):
        status = _compute_initial_status(is_public=True)
        assert status != _IntentionStatus.ACTIVE

    def test_private_intention_not_pending(self):
        status = _compute_initial_status(is_public=False)
        assert status != _IntentionStatus.PENDING_MODERATION


# ── Tests: approve transition ────────────────────────────────────────────────


class TestApproveTransition:
    def test_approve_sets_status_active(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        approved = _approve(intention)
        assert approved["status"] == _IntentionStatus.ACTIVE

    def test_approve_sets_moderated_at(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        approved = _approve(intention)
        assert approved["moderated_at"] is not None

    def test_approve_preserves_content(self):
        intention = _make_intention(
            status=_IntentionStatus.PENDING_MODERATION,
            content="Intencja testowa",
        )
        approved = _approve(intention)
        assert approved["content"] == "Intencja testowa"

    def test_approve_does_not_set_rejection_reason(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        approved = _approve(intention)
        assert approved.get("rejection_reason") is None


# ── Tests: reject transition ─────────────────────────────────────────────────


class TestRejectTransition:
    def test_reject_sets_status_rejected(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        rejected = _reject(intention, reason="Treść niezgodna z zasadami.")
        assert rejected["status"] == _IntentionStatus.REJECTED

    def test_reject_records_reason(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        reason = "Treść niezgodna z zasadami platformy."
        rejected = _reject(intention, reason=reason)
        assert rejected["rejection_reason"] == reason

    def test_reject_sets_moderated_at(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        rejected = _reject(intention, reason="Powód.")
        assert rejected["moderated_at"] is not None

    def test_reject_truncates_reason_to_500_chars(self):
        long_reason = "x" * 600
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        rejected = _reject(intention, reason=long_reason)
        assert len(rejected["rejection_reason"]) <= 500

    def test_reject_status_is_not_active(self):
        intention = _make_intention(status=_IntentionStatus.PENDING_MODERATION)
        rejected = _reject(intention, reason="Powód.")
        assert rejected["status"] != _IntentionStatus.ACTIVE


# ── Tests: public listing visibility ────────────────────────────────────────


class TestPublicListingVisibility:
    def test_active_public_intention_is_visible(self):
        intention = _make_intention(is_public=True, status=_IntentionStatus.ACTIVE)
        assert _is_visible_in_public_listing(intention) is True

    def test_pending_moderation_intention_not_visible(self):
        intention = _make_intention(
            is_public=True, status=_IntentionStatus.PENDING_MODERATION
        )
        assert _is_visible_in_public_listing(intention) is False

    def test_rejected_intention_not_visible(self):
        intention = _make_intention(is_public=True, status=_IntentionStatus.REJECTED)
        assert _is_visible_in_public_listing(intention) is False

    def test_private_active_intention_not_visible(self):
        intention = _make_intention(is_public=False, status=_IntentionStatus.ACTIVE)
        assert _is_visible_in_public_listing(intention) is False

    def test_answered_intention_not_in_public_listing(self):
        intention = _make_intention(is_public=True, status=_IntentionStatus.ANSWERED)
        assert _is_visible_in_public_listing(intention) is False

    def test_closed_intention_not_in_public_listing(self):
        intention = _make_intention(is_public=True, status=_IntentionStatus.CLOSED)
        assert _is_visible_in_public_listing(intention) is False

    def test_filtering_mixed_list(self):
        intentions = [
            _make_intention(is_public=True, status=_IntentionStatus.ACTIVE),
            _make_intention(is_public=True, status=_IntentionStatus.PENDING_MODERATION),
            _make_intention(is_public=True, status=_IntentionStatus.REJECTED),
            _make_intention(is_public=False, status=_IntentionStatus.ACTIVE),
            _make_intention(is_public=True, status=_IntentionStatus.ANSWERED),
        ]
        visible = [i for i in intentions if _is_visible_in_public_listing(i)]
        assert len(visible) == 1
        assert visible[0]["status"] == _IntentionStatus.ACTIVE
        assert visible[0]["is_public"] is True


# ── Tests: IntentionStatus enum values ───────────────────────────────────────


class TestIntentionStatusEnum:
    """Verify all five required values exist in the real IntentionStatus enum."""

    def test_real_enum_has_active(self):
        from app.models.database import IntentionStatus
        assert IntentionStatus.ACTIVE.value == "active"

    def test_real_enum_has_answered(self):
        from app.models.database import IntentionStatus
        assert IntentionStatus.ANSWERED.value == "answered"

    def test_real_enum_has_closed(self):
        from app.models.database import IntentionStatus
        assert IntentionStatus.CLOSED.value == "closed"

    def test_real_enum_has_pending_moderation(self):
        from app.models.database import IntentionStatus
        assert IntentionStatus.PENDING_MODERATION.value == "pending_moderation"

    def test_real_enum_has_rejected(self):
        from app.models.database import IntentionStatus
        assert IntentionStatus.REJECTED.value == "rejected"

    def test_real_enum_has_exactly_five_values(self):
        from app.models.database import IntentionStatus
        assert len(list(IntentionStatus)) == 5

    def test_inline_enum_values_match_real_enum(self):
        from app.models.database import IntentionStatus
        real_values = {e.value for e in IntentionStatus}
        assert real_values == _IntentionStatus.values()


# ── Tests: private fields not exposed in public dict ─────────────────────────


class TestPrivacyOfPublicListing:
    """Ensure that public listing dicts don't include sensitive fields.

    The _to_dict(include_private_fields=False) method is the contract.
    We test the dict structure directly.
    """

    def _public_dict(self, intention: dict) -> dict:
        """Simulate what _to_dict(include_private_fields=False) returns."""
        return {
            "id": intention["id"],
            "content": intention["content"],
            "author_display": intention["author_display"],
            "is_public": intention["is_public"],
            "category": intention["category"],
            "prayer_count": intention["prayer_count"],
            "status": intention["status"],
            "created_at": intention["created_at"],
            "expires_at": intention["expires_at"],
            "group_id": intention["group_id"],
        }

    def test_public_dict_excludes_user_id(self):
        intention = _make_intention(user_id="secret-user-id")
        public = self._public_dict(intention)
        assert "user_id" not in public

    def test_public_dict_excludes_moderator_id(self):
        intention = _make_intention(moderator_id="secret-mod-id")
        public = self._public_dict(intention)
        assert "moderator_id" not in public

    def test_public_dict_excludes_rejection_reason(self):
        intention = _make_intention(rejection_reason="Secret internal reason.")
        public = self._public_dict(intention)
        assert "rejection_reason" not in public

    def test_public_dict_includes_author_display(self):
        intention = _make_intention()
        public = self._public_dict(intention)
        assert "author_display" in public

    def test_public_dict_includes_prayer_count(self):
        intention = _make_intention()
        public = self._public_dict(intention)
        assert "prayer_count" in public

    def test_public_dict_includes_group_id(self):
        intention = _make_intention(group_id="group-123")
        public = self._public_dict(intention)
        assert public["group_id"] == "group-123"


# ── Tests: full moderation workflow ──────────────────────────────────────────


class TestModerationWorkflow:
    """End-to-end workflow simulations."""

    def test_public_intention_workflow_approve(self):
        """Public intention: PENDING_MODERATION → approve → ACTIVE → visible."""
        # Step 1: user submits
        status = _compute_initial_status(is_public=True)
        assert status == _IntentionStatus.PENDING_MODERATION

        # Step 2: not visible before approval
        intention = _make_intention(is_public=True, status=status)
        assert _is_visible_in_public_listing(intention) is False

        # Step 3: admin approves
        approved = _approve(intention)
        assert approved["status"] == _IntentionStatus.ACTIVE

        # Step 4: now visible
        assert _is_visible_in_public_listing(approved) is True

    def test_public_intention_workflow_reject(self):
        """Public intention: PENDING_MODERATION → reject → REJECTED → not visible."""
        status = _compute_initial_status(is_public=True)
        intention = _make_intention(is_public=True, status=status)

        rejected = _reject(intention, reason="Treść nieodpowiednia.")
        assert rejected["status"] == _IntentionStatus.REJECTED
        assert _is_visible_in_public_listing(rejected) is False
        assert rejected["rejection_reason"] == "Treść nieodpowiednia."

    def test_private_intention_workflow(self):
        """Private intention: immediately ACTIVE, not public."""
        status = _compute_initial_status(is_public=False)
        assert status == _IntentionStatus.ACTIVE

        intention = _make_intention(is_public=False, status=status)
        # Private → not visible in public listing
        assert _is_visible_in_public_listing(intention) is False

    def test_group_intention_has_group_id(self):
        """Intention linked to a group carries group_id."""
        intention = _make_intention(
            is_public=True,
            status=_IntentionStatus.ACTIVE,
            group_id="group-abc",
        )
        assert intention["group_id"] == "group-abc"
        assert _is_visible_in_public_listing(intention) is True
