"""SQLAlchemy ORM models for the Sancta Nexus relational store.

All models use ``mapped_column`` with explicit types for async-compatible
declarative mapping (SQLAlchemy 2.0+ style).
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship,
)


# ── Base ─────────────────────────────────────────────────────────────────────


class Base(DeclarativeBase):
    """Shared declarative base for every ORM model."""


# ── Enums ────────────────────────────────────────────────────────────────────


class SubscriptionTier(str, enum.Enum):
    """User subscription levels."""

    FREE = "free"
    PILGRIM = "pilgrim"
    DISCIPLE = "disciple"
    MYSTIC = "mystic"


class SessionType(str, enum.Enum):
    """Supported spiritual-session types."""

    LECTIO_DIVINA = "lectio_divina"
    SPIRITUAL_DIRECTION = "spiritual_direction"
    BIBLE_STUDY = "bible_study"
    PRAYER = "prayer"
    MEDITATION = "meditation"


# ── Models ───────────────────────────────────────────────────────────────────


class User(Base):
    """Platform user with spiritual profile and subscription metadata."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1024), nullable=False)
    spiritual_profile_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    subscription_tier: Mapped[SubscriptionTier] = mapped_column(
        Enum(
            SubscriptionTier,
            name="subscription_tier",
            values_callable=lambda e: [x.value for x in e],
        ),
        default=SubscriptionTier.FREE,
        server_default=SubscriptionTier.FREE.value,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    sessions: Mapped[list["Session"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    prayers: Mapped[list["Prayer"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    scripture_encounters: Mapped[list["ScriptureEncounter"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    spiritual_insights: Mapped[list["SpiritualInsight"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Session(Base):
    """A single spiritual-practice session (Lectio Divina, direction, etc.)."""

    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_type: Mapped[SessionType] = mapped_column(
        Enum(
            SessionType,
            name="session_type",
            values_callable=lambda e: [x.value for x in e],
        ),
        nullable=False,
    )
    emotion_vector_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scripture_reference: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    user: Mapped["User"] = relationship(back_populates="sessions")
    prayers: Mapped[list["Prayer"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    scripture_encounters: Mapped[list["ScriptureEncounter"]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )


class Prayer(Base):
    """A prayer composed during or outside a session."""

    __tablename__ = "prayers"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    prayer_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    tradition: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="prayers")
    session: Mapped[Optional["Session"]] = relationship(back_populates="prayers")


class ScriptureEncounter(Base):
    """Record of a user's engagement with a specific Bible passage."""

    __tablename__ = "scripture_encounters"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
    )
    book: Mapped[str] = mapped_column(String(64), nullable=False)
    chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    verse_start: Mapped[int] = mapped_column(Integer, nullable=False)
    verse_end: Mapped[int] = mapped_column(Integer, nullable=False)
    user_reflection: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    emotion_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="scripture_encounters")
    session: Mapped[Optional["Session"]] = relationship(back_populates="scripture_encounters")


class SpiritualInsight(Base):
    """AI-generated insight derived from aggregating a user's spiritual data."""

    __tablename__ = "spiritual_insights"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    insight_type: Mapped[str] = mapped_column(String(128), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    period_start: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    period_end: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(back_populates="spiritual_insights")


# ── Community models ──────────────────────────────────────────────────────────


class IntentionStatus(str, enum.Enum):
    ACTIVE = "active"
    ANSWERED = "answered"
    CLOSED = "closed"


class PrayerIntention(Base):
    """A prayer request shared publicly or kept private within the community."""

    __tablename__ = "prayer_intentions"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    # nullable → allows anonymous / guest intentions
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    content: Mapped[str] = mapped_column(String(500), nullable=False)
    author_display: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    prayer_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    status: Mapped[IntentionStatus] = mapped_column(
        Enum(IntentionStatus, name="intention_status",
             values_callable=lambda e: [x.value for x in e]),
        default=IntentionStatus.ACTIVE,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )


class PrayerGroup(Base):
    """A parish or online prayer group."""

    __tablename__ = "prayer_groups"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parish: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    leader_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    category: Mapped[str] = mapped_column(String(50), default="general", nullable=False)
    schedule: Mapped[Optional[str]] = mapped_column(String(200), nullable=True)
    is_public: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    member_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    memberships: Mapped[list["PrayerGroupMembership"]] = relationship(
        back_populates="group", cascade="all, delete-orphan"
    )


class PrayerGroupMembership(Base):
    """Membership of a user in a prayer group."""

    __tablename__ = "prayer_group_memberships"
    __table_args__ = (UniqueConstraint("group_id", "user_id", name="uq_group_user"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    group_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("prayer_groups.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    role: Mapped[str] = mapped_column(String(20), default="member", nullable=False)
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    group: Mapped["PrayerGroup"] = relationship(back_populates="memberships")


class CommunityRosary(Base):
    """A community Rosary session (synchronous or asynchronous)."""

    __tablename__ = "community_rosaries"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    initiator_user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    mystery_type: Mapped[str] = mapped_column(String(30), nullable=False)
    intention: Mapped[Optional[str]] = mapped_column(String(300), nullable=True)
    scheduled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    status: Mapped[str] = mapped_column(String(20), default="open", nullable=False)
    participant_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    participations: Mapped[list["RosaryParticipation"]] = relationship(
        back_populates="rosary", cascade="all, delete-orphan"
    )


class RosaryParticipation(Base):
    """Record of a user joining and completing a community Rosary."""

    __tablename__ = "rosary_participations"
    __table_args__ = (UniqueConstraint("rosary_id", "user_id", name="uq_rosary_user"),)

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    rosary_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("community_rosaries.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # bitmask: bit N set → decade N+1 completed (5 bits → 5 decades)
    decades_mask: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    rosary: Mapped["CommunityRosary"] = relationship(back_populates="participations")


class NovenaTracking(Base):
    """User's progress through a specific novena."""

    __tablename__ = "novena_trackings"

    id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    novena_id: Mapped[str] = mapped_column(String(60), nullable=False)
    intention: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    # bitmask: bit N set → day N+1 prayed (9 bits)
    completed_days_mask: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    is_complete: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
