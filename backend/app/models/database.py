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


class UserRole(str, enum.Enum):
    """Platform role assigned to a user.

    Hierarchy (ascending privilege):
        user < premium_user < moderator < editor
        < spiritual_content_reviewer < group_leader
        < organization_admin < admin
    """

    USER = "user"
    PREMIUM_USER = "premium_user"
    MODERATOR = "moderator"
    EDITOR = "editor"
    SPIRITUAL_CONTENT_REVIEWER = "spiritual_content_reviewer"
    GROUP_LEADER = "group_leader"
    ORGANIZATION_ADMIN = "organization_admin"
    ADMIN = "admin"


class AuditEventType(str, enum.Enum):
    """Types of operations recorded in the audit log."""

    USER_REGISTERED = "user_registered"
    USER_ROLE_CHANGED = "user_role_changed"
    USER_DELETED = "user_deleted"
    USER_DATA_EXPORTED = "user_data_exported"
    AI_RESPONSE_GENERATED = "ai_response_generated"
    AI_RESPONSE_REWRITTEN = "ai_response_rewritten"
    AI_CRISIS_DETECTED = "ai_crisis_detected"
    CONTENT_CREATED = "content_created"
    CONTENT_PUBLISHED = "content_published"
    CONTENT_ARCHIVED = "content_archived"
    INTENTION_MODERATED = "intention_moderated"
    MODULE_TOGGLED = "module_toggled"
    ROLE_PERMISSION_DENIED = "role_permission_denied"
    JOURNAL_ENTRY_DELETED = "journal_entry_deleted"
    ACCOUNT_DELETION_REQUESTED = "account_deletion_requested"


# ── Models ───────────────────────────────────────────────────────────────────


class User(Base):
    """Platform user with role, subscription, and soft-delete support."""

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
    role: Mapped[UserRole] = mapped_column(
        Enum(
            UserRole,
            name="user_role",
            values_callable=lambda e: [x.value for x in e],
        ),
        default=UserRole.USER,
        server_default=UserRole.USER.value,
        nullable=False,
    )
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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
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
    privacy_settings: Mapped[Optional["UserPrivacySettings"]] = relationship(
        back_populates="user", uselist=False, cascade="all, delete-orphan"
    )
    audit_logs: Mapped[list["AuditLog"]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    ai_interactions: Mapped[list["AiInteraction"]] = relationship(
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


# ── Privacy / GDPR ───────────────────────────────────────────────────────────


class UserPrivacySettings(Base):
    """Per-user privacy configuration. Created on first access (privacy-by-design)."""

    __tablename__ = "user_privacy_settings"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True, index=True
    )
    # Journal is private by default — user must explicitly share entries
    journal_is_private: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    # Allow AI to use journal text for reflection suggestions
    ai_can_read_journal: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    # Retain AI interaction history
    ai_history_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true", nullable=False)
    # Preferred language (overrides account default)
    preferred_language: Mapped[str] = mapped_column(String(5), default="pl", server_default="pl", nullable=False)
    # Preferred spiritual tradition
    spiritual_tradition: Mapped[str] = mapped_column(
        String(64), default="ignatian", server_default="ignatian", nullable=False
    )
    # Soft-delete requested timestamp (GDPR right to erasure)
    deletion_requested_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship(back_populates="privacy_settings")


# ── Audit Log ────────────────────────────────────────────────────────────────


class AuditLog(Base):
    """Immutable record of every important platform operation.

    Rules:
    - Never delete rows from this table.
    - user_id may be NULL for system/admin actions without a session.
    - actor_id is who performed the action (may differ from user_id for admin ops).
    - payload_json stores context without PII (use IDs, not content).
    """

    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    event_type: Mapped[AuditEventType] = mapped_column(
        Enum(AuditEventType, name="audit_event_type", values_callable=lambda e: [x.value for x in e]),
        nullable=False,
        index=True,
    )
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    actor_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), nullable=True, index=True
    )
    # Short human-readable summary — no PII, no sensitive content
    description: Mapped[str] = mapped_column(String(512), nullable=False)
    # JSON with non-sensitive context (module name, role, flag name, etc.)
    payload_json: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    ip_address: Mapped[Optional[str]] = mapped_column(String(45), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="audit_logs", foreign_keys=[user_id])


# ── AI Interactions ───────────────────────────────────────────────────────────


class AiInteraction(Base):
    """Record of every AI response, including safety assessment metadata.

    Stores only metadata — NOT the raw user message or AI response text.
    Full text lives in the session context (Redis) and expires automatically.
    """

    __tablename__ = "ai_interactions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    module: Mapped[str] = mapped_column(String(64), nullable=False)
    # Risk category from AISafetyLayer
    risk_category: Mapped[str] = mapped_column(String(64), nullable=False)
    was_modified: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    # Policy violations if any (comma-separated names)
    violations: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    user: Mapped[Optional["User"]] = relationship(back_populates="ai_interactions")


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


class JournalEntry(Base):
    """Wpis w dzienniku duchowym użytkownika.

    Prywatny domyślnie. Użytkownik może go eksportować i usunąć.
    Treść traktowana jako wrażliwa — nie jest przesyłana do AI
    bez jawnej zgody (privacy_settings.ai_can_read_journal).
    """

    __tablename__ = "journal_entries"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    # Comma-separated tags e.g. "modlitwa,Ewangelia,pokój"
    tags: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Mood / tone: spokój, niepokój, wdzięczność, smutek, radość, etc.
    mood: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    # Linked scripture reference e.g. "J 3,16"
    scripture_reference: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Linked Lectio Divina session ID (Redis key or DB session UUID)
    lectio_session_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Linked retreat program ID
    program_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    # Soft-delete
    deleted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")


class FavoritePassage(Base):
    """Ulubiony fragment Pisma Świętego zapisany przez użytkownika."""

    __tablename__ = "favorite_passages"
    __table_args__ = (UniqueConstraint("user_id", "book", "chapter", "verse_start", "verse_end",
                                       name="uq_favorite_passage"),)

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=lambda: str(uuid4()))
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    book: Mapped[str] = mapped_column(String(64), nullable=False)
    chapter: Mapped[int] = mapped_column(Integer, nullable=False)
    verse_start: Mapped[int] = mapped_column(Integer, nullable=False)
    verse_end: Mapped[int] = mapped_column(Integer, nullable=False)
    # Display reference e.g. "J 3,16-17"
    reference: Mapped[str] = mapped_column(String(128), nullable=False)
    # Short excerpt of the passage text
    excerpt: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    # Personal note added by user
    note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User")


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
