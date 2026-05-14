"""Privacy service — GDPR-compliant data export and account deletion.

Implements the user's right to:
- Data portability (export all personal data as JSON)
- Erasure (soft-delete, then hard-delete by admin after retention period)

Journal entries and AI interaction text are treated as sensitive data:
- Journal text IS included in exports (it belongs to the user).
- AI interaction raw text is NOT stored (only metadata) — nothing to export.
- Confessional notes are stored in session memory only (Redis, TTL) — they
  expire automatically and are not in the database.

Usage::

    from app.services.privacy.privacy_service import privacy_svc

    export = await privacy_svc.export_user_data(db, user)
    await privacy_svc.request_deletion(db, user, actor_id=user.id)
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import (
    AuditEventType,
    AiInteraction,
    Prayer,
    ScriptureEncounter,
    Session,
    SpiritualInsight,
    User,
    UserPrivacySettings,
)
from app.services.audit.audit_service import audit


class PrivacyService:
    """Handles data export and account lifecycle for GDPR compliance."""

    async def get_or_create_privacy_settings(
        self, db: AsyncSession, user: User
    ) -> UserPrivacySettings:
        """Return existing privacy settings or create defaults (privacy-first)."""
        result = await db.execute(
            select(UserPrivacySettings).where(UserPrivacySettings.user_id == user.id)
        )
        settings = result.scalar_one_or_none()
        if settings is None:
            settings = UserPrivacySettings(user_id=user.id)
            db.add(settings)
            await db.flush()
            await db.refresh(settings)
        return settings

    async def export_user_data(self, db: AsyncSession, user: User) -> dict[str, Any]:
        """Collect all personal data and return as a structured dict.

        Exported data includes:
        - Account info (email, name, role, subscription, dates)
        - Privacy settings
        - Sessions metadata (no AI text)
        - Prayers (user's own texts)
        - Scripture encounters + reflections
        - Spiritual insights
        - AI interaction metadata (no message text)
        """
        # Sessions
        sessions_result = await db.execute(select(Session).where(Session.user_id == user.id))
        sessions = sessions_result.scalars().all()

        # Prayers
        prayers_result = await db.execute(select(Prayer).where(Prayer.user_id == user.id))
        prayers = prayers_result.scalars().all()

        # Scripture encounters
        encounters_result = await db.execute(
            select(ScriptureEncounter).where(ScriptureEncounter.user_id == user.id)
        )
        encounters = encounters_result.scalars().all()

        # Spiritual insights
        insights_result = await db.execute(
            select(SpiritualInsight).where(SpiritualInsight.user_id == user.id)
        )
        insights = insights_result.scalars().all()

        # AI interaction metadata
        ai_result = await db.execute(
            select(AiInteraction).where(AiInteraction.user_id == user.id)
        )
        ai_records = ai_result.scalars().all()

        # Privacy settings
        privacy = await self.get_or_create_privacy_settings(db, user)

        export: dict[str, Any] = {
            "export_generated_at": datetime.now(timezone.utc).isoformat(),
            "account": {
                "id": user.id,
                "email": user.email,
                "name": user.name,
                "role": user.role.value,
                "subscription_tier": user.subscription_tier.value,
                "is_active": user.is_active,
                "created_at": user.created_at.isoformat(),
                "updated_at": user.updated_at.isoformat(),
            },
            "privacy_settings": {
                "journal_is_private": privacy.journal_is_private,
                "ai_can_read_journal": privacy.ai_can_read_journal,
                "ai_history_enabled": privacy.ai_history_enabled,
                "preferred_language": privacy.preferred_language,
                "spiritual_tradition": privacy.spiritual_tradition,
            },
            "sessions": [
                {
                    "id": s.id,
                    "session_type": s.session_type.value,
                    "scripture_reference": s.scripture_reference,
                    "notes": s.notes,
                    "started_at": s.started_at.isoformat(),
                    "ended_at": s.ended_at.isoformat() if s.ended_at else None,
                }
                for s in sessions
            ],
            "prayers": [
                {
                    "id": p.id,
                    "content": p.content,
                    "prayer_type": p.prayer_type,
                    "tradition": p.tradition,
                    "created_at": p.created_at.isoformat(),
                }
                for p in prayers
            ],
            "scripture_encounters": [
                {
                    "id": e.id,
                    "book": e.book,
                    "chapter": e.chapter,
                    "verse_start": e.verse_start,
                    "verse_end": e.verse_end,
                    "user_reflection": e.user_reflection,
                    "created_at": e.created_at.isoformat(),
                }
                for e in encounters
            ],
            "spiritual_insights": [
                {
                    "id": i.id,
                    "insight_type": i.insight_type,
                    "content": i.content,
                    "created_at": i.created_at.isoformat(),
                }
                for i in insights
            ],
            "ai_interactions_metadata": [
                {
                    "id": ai.id,
                    "module": ai.module,
                    "risk_category": ai.risk_category,
                    "was_modified": ai.was_modified,
                    "created_at": ai.created_at.isoformat(),
                }
                for ai in ai_records
            ],
        }

        await audit.log(
            db,
            event_type=AuditEventType.USER_DATA_EXPORTED,
            user_id=user.id,
            actor_id=user.id,
            description=f"User data export generated for user {user.id}",
        )

        return export

    async def request_deletion(
        self,
        db: AsyncSession,
        user: User,
        *,
        actor_id: str,
    ) -> None:
        """Mark account for deletion (soft-delete).

        Sets deleted_at and is_active=False. Hard deletion is performed
        by admin after the configured retention period.
        """
        now = datetime.now(timezone.utc)
        user.is_active = False
        user.deleted_at = now

        privacy = await self.get_or_create_privacy_settings(db, user)
        privacy.deletion_requested_at = now

        await audit.log(
            db,
            event_type=AuditEventType.ACCOUNT_DELETION_REQUESTED,
            user_id=user.id,
            actor_id=actor_id,
            description=f"Account deletion requested for user {user.id}",
        )

    async def clear_ai_history(self, db: AsyncSession, user: User) -> int:
        """Delete AI interaction metadata records for the user.

        Returns the number of deleted records.
        """
        from sqlalchemy import delete

        result = await db.execute(
            delete(AiInteraction).where(AiInteraction.user_id == user.id)
        )
        deleted_count = result.rowcount

        await audit.log(
            db,
            event_type=AuditEventType.USER_DATA_EXPORTED,
            user_id=user.id,
            actor_id=user.id,
            description=f"AI interaction history cleared for user {user.id} ({deleted_count} records)",
            payload={"deleted_count": deleted_count},
        )

        return deleted_count


privacy_svc = PrivacyService()
