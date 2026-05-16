"""PrayerIntentionService — CRUD and intercession logic for prayer intentions.

Handles public/private intentions, category filtering, intercession counting
(«I prayed for this»), auto-expiry after 30 days, and moderation workflow.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import IntentionStatus, PrayerIntention

logger = logging.getLogger(__name__)

INTENTION_CATEGORIES = [
    "general",
    "zdrowie",
    "rodzina",
    "praca",
    "pokój",
    "nawrócenie",
    "żałoba",
    "wdzięczność",
    "egzaminy",
    "powołanie",
]

DEFAULT_EXPIRY_DAYS = 30


class PrayerIntentionService:

    async def create(
        self,
        db: AsyncSession,
        content: str,
        is_public: bool = True,
        category: str = "general",
        author_display: str | None = None,
        user_id: str | None = None,
        group_id: str | None = None,
    ) -> dict[str, Any]:
        # Public intentions require moderation; private are immediately active
        initial_status = IntentionStatus.PENDING_MODERATION if is_public else IntentionStatus.ACTIVE

        intention = PrayerIntention(
            id=str(uuid4()),
            user_id=user_id,
            content=content,
            is_public=is_public,
            category=category if category in INTENTION_CATEGORIES else "general",
            author_display=author_display or ("Anonim" if not user_id else None),
            prayer_count=0,
            status=initial_status,
            expires_at=datetime.now(UTC) + timedelta(days=DEFAULT_EXPIRY_DAYS),
            group_id=group_id,
        )
        db.add(intention)
        await db.commit()
        await db.refresh(intention)
        return self._to_dict(intention, include_private_fields=True)

    async def list_public(
        self,
        db: AsyncSession,
        category: str | None = None,
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(PrayerIntention)
            .where(
                PrayerIntention.is_public.is_(True),
                PrayerIntention.status == IntentionStatus.ACTIVE,
            )
            .order_by(PrayerIntention.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        if category and category != "all":
            stmt = stmt.where(PrayerIntention.category == category)

        result = await db.execute(stmt)
        return [self._to_dict(r) for r in result.scalars().all()]

    async def list_by_user(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(PrayerIntention)
            .where(PrayerIntention.user_id == user_id)
            .order_by(PrayerIntention.created_at.desc())
        )
        result = await db.execute(stmt)
        return [self._to_dict(r, include_private_fields=True) for r in result.scalars().all()]

    async def list_pending_moderation(
        self,
        db: AsyncSession,
    ) -> list[dict[str, Any]]:
        """Return all intentions awaiting moderation. For admin/moderator use only."""
        stmt = (
            select(PrayerIntention)
            .where(PrayerIntention.status == IntentionStatus.PENDING_MODERATION)
            .order_by(PrayerIntention.created_at.asc())
        )
        result = await db.execute(stmt)
        return [self._to_dict(r, include_private_fields=True) for r in result.scalars().all()]

    async def approve(
        self,
        db: AsyncSession,
        intention_id: str,
        moderator_id: str,
    ) -> dict[str, Any] | None:
        """Approve a pending intention — sets status to ACTIVE."""
        stmt = (
            update(PrayerIntention)
            .where(PrayerIntention.id == intention_id)
            .values(
                status=IntentionStatus.ACTIVE,
                moderator_id=moderator_id,
                moderated_at=datetime.now(UTC),
            )
            .returning(PrayerIntention)
        )
        result = await db.execute(stmt)
        await db.commit()
        row = result.scalars().first()
        if not row:
            return None
        return self._to_dict(row, include_private_fields=True)

    async def reject(
        self,
        db: AsyncSession,
        intention_id: str,
        moderator_id: str,
        reason: str,
    ) -> dict[str, Any] | None:
        """Reject a pending intention with a reason."""
        stmt = (
            update(PrayerIntention)
            .where(PrayerIntention.id == intention_id)
            .values(
                status=IntentionStatus.REJECTED,
                moderator_id=moderator_id,
                moderated_at=datetime.now(UTC),
                rejection_reason=reason[:500],
            )
            .returning(PrayerIntention)
        )
        result = await db.execute(stmt)
        await db.commit()
        row = result.scalars().first()
        if not row:
            return None
        return self._to_dict(row, include_private_fields=True)

    async def list_by_group(
        self,
        db: AsyncSession,
        group_id: str,
        limit: int = 30,
        offset: int = 0,
    ) -> list[dict[str, Any]]:
        """Return active public intentions for a specific prayer group."""
        stmt = (
            select(PrayerIntention)
            .where(
                PrayerIntention.group_id == group_id,
                PrayerIntention.status == IntentionStatus.ACTIVE,
                PrayerIntention.is_public.is_(True),
            )
            .order_by(PrayerIntention.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        result = await db.execute(stmt)
        return [self._to_dict(r) for r in result.scalars().all()]

    async def intercede(
        self,
        db: AsyncSession,
        intention_id: str,
    ) -> dict[str, Any]:
        """Increment the prayer count — «I prayed for this intention»."""
        stmt = (
            update(PrayerIntention)
            .where(PrayerIntention.id == intention_id)
            .values(prayer_count=PrayerIntention.prayer_count + 1)
            .returning(PrayerIntention)
        )
        result = await db.execute(stmt)
        await db.commit()
        row = result.scalars().first()
        if not row:
            return {}
        return self._to_dict(row)

    async def mark_answered(
        self,
        db: AsyncSession,
        intention_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        stmt = (
            update(PrayerIntention)
            .where(
                PrayerIntention.id == intention_id,
                PrayerIntention.user_id == user_id,
            )
            .values(status=IntentionStatus.ANSWERED)
            .returning(PrayerIntention)
        )
        result = await db.execute(stmt)
        await db.commit()
        row = result.scalars().first()
        return self._to_dict(row, include_private_fields=True) if row else {}

    def _to_dict(
        self,
        obj: PrayerIntention,
        include_private_fields: bool = False,
    ) -> dict[str, Any]:
        data: dict[str, Any] = {
            "id": obj.id,
            "content": obj.content,
            "author_display": obj.author_display,
            "is_public": obj.is_public,
            "category": obj.category,
            "prayer_count": obj.prayer_count,
            "status": obj.status.value if obj.status else "active",
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "expires_at": obj.expires_at.isoformat() if obj.expires_at else None,
            "group_id": obj.group_id,
        }
        if include_private_fields:
            data["user_id"] = obj.user_id
            data["moderator_id"] = obj.moderator_id
            data["moderated_at"] = obj.moderated_at.isoformat() if obj.moderated_at else None
            data["rejection_reason"] = obj.rejection_reason
        return data
