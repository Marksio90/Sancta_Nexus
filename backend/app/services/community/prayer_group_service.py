"""PrayerGroupService — management of parish and online prayer groups.

Supports creating groups, joining/leaving, listing members,
and seeding a set of default parish groups for onboarding.
"""
from __future__ import annotations

import logging
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.database import PrayerGroup, PrayerGroupMembership

logger = logging.getLogger(__name__)

GROUP_CATEGORIES = [
    "rodziny",
    "młodzież",
    "seniorzy",
    "chorzy",
    "różaniec",
    "adoracja",
    "ewangelizacja",
    "lectio_divina",
    "ogólna",
]

# Seed groups shown when no parish groups exist yet
SAMPLE_GROUPS: list[dict] = [
    {
        "name": "Żywy Różaniec — Parafia",
        "description": "Wspólna modlitwa różańcowa w grupach 20-osobowych. Każdy podejmuje się odmawiania jednej tajemnicy dziennie.",
        "category": "różaniec",
        "schedule": "Pierwszy piątek miesiąca 18:00",
        "parish": "Parafia Przykładowa",
    },
    {
        "name": "Wspólnota Rodzin",
        "description": "Spotkania dla małżeństw i rodzin: modlitwa, dzielenie się Słowem, wzajemne wsparcie.",
        "category": "rodziny",
        "schedule": "Niedziela po Mszy wieczornej",
        "parish": "Parafia Przykładowa",
    },
    {
        "name": "Młodzież w Drodze",
        "description": "Ewangelizacyjna wspólnota dla młodych 16–30 lat. Modlitwa uwielbienia, Lectio Divina, wolontariat.",
        "category": "młodzież",
        "schedule": "Piątek 19:30",
        "parish": "Parafia Przykładowa",
    },
    {
        "name": "Adoracja Wieczorna",
        "description": "Cicha adoracja Najświętszego Sakramentu — samotna i wspólnotowa. Dyżury godzinne.",
        "category": "adoracja",
        "schedule": "Codziennie 20:00–21:00",
        "parish": "Parafia Przykładowa",
    },
    {
        "name": "Lectio Divina — Dorośli",
        "description": "Słuchamy Słowa Bożego metodą starożytną Lectio Divina. Objaśnienia biblijne, modlitwa, sharing.",
        "category": "lectio_divina",
        "schedule": "Środa 18:30",
        "parish": "Parafia Przykładowa",
    },
    {
        "name": "Apostolstwo Chorych",
        "description": "Wsparcie duchowe i modlitewne dla chorych i ich rodzin. Komunia do domu, namaszczenie chorych.",
        "category": "chorzy",
        "schedule": "Kontakt z zakrystianem",
        "parish": "Parafia Przykładowa",
    },
]


class PrayerGroupService:

    async def ensure_sample_groups(self, db: AsyncSession) -> None:
        """Seed sample groups if the table is empty."""
        count = await db.scalar(select(func.count()).select_from(PrayerGroup))
        if count and count > 0:
            return
        for g in SAMPLE_GROUPS:
            group = PrayerGroup(
                id=str(uuid4()),
                name=g["name"],
                description=g["description"],
                category=g["category"],
                schedule=g.get("schedule"),
                parish=g.get("parish"),
                is_public=True,
                member_count=0,
            )
            db.add(group)
        await db.commit()

    async def list_groups(
        self,
        db: AsyncSession,
        category: str | None = None,
        limit: int = 30,
    ) -> list[dict[str, Any]]:
        await self.ensure_sample_groups(db)
        stmt = (
            select(PrayerGroup)
            .where(PrayerGroup.is_public.is_(True))
            .order_by(PrayerGroup.member_count.desc(), PrayerGroup.name)
            .limit(limit)
        )
        if category and category != "all":
            stmt = stmt.where(PrayerGroup.category == category)
        result = await db.execute(stmt)
        return [self._to_dict(g) for g in result.scalars().all()]

    async def get_group(self, db: AsyncSession, group_id: str) -> dict[str, Any] | None:
        result = await db.execute(
            select(PrayerGroup).where(PrayerGroup.id == group_id)
        )
        group = result.scalars().first()
        return self._to_dict(group) if group else None

    async def create_group(
        self,
        db: AsyncSession,
        name: str,
        description: str | None,
        category: str,
        schedule: str | None,
        parish: str | None,
        leader_user_id: str | None,
    ) -> dict[str, Any]:
        group = PrayerGroup(
            id=str(uuid4()),
            name=name,
            description=description,
            category=category if category in GROUP_CATEGORIES else "ogólna",
            schedule=schedule,
            parish=parish,
            leader_user_id=leader_user_id,
            is_public=True,
            member_count=0,
        )
        db.add(group)
        await db.commit()
        await db.refresh(group)
        return self._to_dict(group)

    async def join_group(
        self,
        db: AsyncSession,
        group_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        try:
            membership = PrayerGroupMembership(
                id=str(uuid4()),
                group_id=group_id,
                user_id=user_id,
                role="member",
            )
            db.add(membership)
            # increment member_count
            await db.execute(
                PrayerGroup.__table__.update()
                .where(PrayerGroup.id == group_id)
                .values(member_count=PrayerGroup.member_count + 1)
            )
            await db.commit()
            return {"joined": True, "group_id": group_id}
        except IntegrityError:
            await db.rollback()
            return {"joined": False, "reason": "already_member"}

    async def leave_group(
        self,
        db: AsyncSession,
        group_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        result = await db.execute(
            select(PrayerGroupMembership).where(
                PrayerGroupMembership.group_id == group_id,
                PrayerGroupMembership.user_id == user_id,
            )
        )
        membership = result.scalars().first()
        if not membership:
            return {"left": False, "reason": "not_member"}
        await db.delete(membership)
        await db.execute(
            PrayerGroup.__table__.update()
            .where(PrayerGroup.id == group_id)
            .values(member_count=PrayerGroup.member_count - 1)
        )
        await db.commit()
        return {"left": True}

    async def get_user_groups(
        self,
        db: AsyncSession,
        user_id: str,
    ) -> list[dict[str, Any]]:
        stmt = (
            select(PrayerGroup)
            .join(
                PrayerGroupMembership,
                PrayerGroupMembership.group_id == PrayerGroup.id,
            )
            .where(PrayerGroupMembership.user_id == user_id)
        )
        result = await db.execute(stmt)
        return [self._to_dict(g) for g in result.scalars().all()]

    def _to_dict(self, g: PrayerGroup) -> dict[str, Any]:
        return {
            "id": g.id,
            "name": g.name,
            "description": g.description,
            "parish": g.parish,
            "category": g.category,
            "schedule": g.schedule,
            "member_count": g.member_count,
            "is_public": g.is_public,
            "created_at": g.created_at.isoformat() if g.created_at else None,
        }
