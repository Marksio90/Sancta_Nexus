"""PrayerIntentionService — CRUD and intercession logic for prayer intentions.

Handles public/private intentions, category filtering, intercession counting
(«I prayed for this»), and auto-expiry after 30 days.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
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
    ) -> dict[str, Any]:
        intention = PrayerIntention(
            id=str(uuid4()),
            user_id=user_id,
            content=content,
            is_public=is_public,
            category=category if category in INTENTION_CATEGORIES else "general",
            author_display=author_display or ("Anonim" if not user_id else None),
            prayer_count=0,
            status=IntentionStatus.ACTIVE,
            expires_at=datetime.now(timezone.utc) + timedelta(days=DEFAULT_EXPIRY_DAYS),
        )
        db.add(intention)
        await db.commit()
        await db.refresh(intention)
        return self._to_dict(intention)

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
        return self._to_dict(row) if row else {}

    def _to_dict(self, obj: PrayerIntention) -> dict[str, Any]:
        return {
            "id": obj.id,
            "content": obj.content,
            "author_display": obj.author_display,
            "is_public": obj.is_public,
            "category": obj.category,
            "prayer_count": obj.prayer_count,
            "status": obj.status.value if obj.status else "active",
            "created_at": obj.created_at.isoformat() if obj.created_at else None,
            "expires_at": obj.expires_at.isoformat() if obj.expires_at else None,
        }
