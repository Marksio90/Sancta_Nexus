"""SQLAlchemy ORM models for the Sancta Nexus relational store.

All models use ``mapped_column`` with explicit types for async-compatible
declarative mapping (SQLAlchemy 2.0+ style).
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import uuid4

from sqlalchemy import (
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
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
