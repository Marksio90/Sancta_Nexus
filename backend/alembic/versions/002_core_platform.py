"""Core Platform — role, prywatność, audit log, AI interactions.

Revision ID: 002
Revises: 001
Create Date: 2026-05-14

Dodaje:
- user_role enum + kolumna role w tabeli users
- is_active, deleted_at w tabeli users
- tabela user_privacy_settings
- tabela audit_logs (audit_event_type enum)
- tabela ai_interactions
- tabele społecznościowe z migracji 001 (przeniesione tutaj dla porządku):
  prayer_intentions, prayer_groups, prayer_group_memberships,
  community_rosaries, rosary_participations, novena_trackings
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Nowe enumy ────────────────────────────────────────────────────────────
    user_role_enum = sa.Enum(
        "user", "premium_user", "moderator", "editor",
        "spiritual_content_reviewer", "group_leader", "organization_admin", "admin",
        name="user_role",
    )
    audit_event_type_enum = sa.Enum(
        "user_registered", "user_role_changed", "user_deleted", "user_data_exported",
        "ai_response_generated", "ai_response_rewritten", "ai_crisis_detected",
        "content_created", "content_published", "content_archived",
        "intention_moderated", "module_toggled", "role_permission_denied",
        "journal_entry_deleted", "account_deletion_requested",
        name="audit_event_type",
    )
    intention_status_enum = sa.Enum(
        "active", "answered", "closed",
        name="intention_status",
    )

    user_role_enum.create(op.get_bind(), checkfirst=True)
    audit_event_type_enum.create(op.get_bind(), checkfirst=True)
    intention_status_enum.create(op.get_bind(), checkfirst=True)

    # ── Rozszerzenie tabeli users ─────────────────────────────────────────────
    op.add_column(
        "users",
        sa.Column("role", user_role_enum, nullable=False, server_default="user"),
    )
    op.add_column(
        "users",
        sa.Column("is_active", sa.Boolean, nullable=False, server_default="true"),
    )
    op.add_column(
        "users",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )

    # ── user_privacy_settings ─────────────────────────────────────────────────
    op.create_table(
        "user_privacy_settings",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
            index=True,
        ),
        sa.Column("journal_is_private", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ai_can_read_journal", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("ai_history_enabled", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("preferred_language", sa.String(5), nullable=False, server_default="pl"),
        sa.Column("spiritual_tradition", sa.String(64), nullable=False, server_default="ignatian"),
        sa.Column("deletion_requested_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── audit_logs ────────────────────────────────────────────────────────────
    op.create_table(
        "audit_logs",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("event_type", audit_event_type_enum, nullable=False, index=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("actor_id", UUID(as_uuid=False), nullable=True, index=True),
        sa.Column("description", sa.String(512), nullable=False),
        sa.Column("payload_json", sa.Text, nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    # ── ai_interactions ───────────────────────────────────────────────────────
    op.create_table(
        "ai_interactions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("session_id", sa.String(128), nullable=True, index=True),
        sa.Column("module", sa.String(64), nullable=False),
        sa.Column("risk_category", sa.String(64), nullable=False),
        sa.Column("was_modified", sa.Boolean, nullable=False, server_default="false"),
        sa.Column("violations", sa.String(256), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
    )

    # ── Tabele społecznościowe ────────────────────────────────────────────────
    op.create_table(
        "prayer_intentions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
        sa.Column("content", sa.String(500), nullable=False),
        sa.Column("author_display", sa.String(100), nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("prayer_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("status", intention_status_enum, nullable=False, server_default="active"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_table(
        "prayer_groups",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.Text, nullable=True),
        sa.Column("parish", sa.String(200), nullable=True),
        sa.Column(
            "leader_user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("category", sa.String(50), nullable=False, server_default="general"),
        sa.Column("schedule", sa.String(200), nullable=True),
        sa.Column("is_public", sa.Boolean, nullable=False, server_default="true"),
        sa.Column("member_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "prayer_group_memberships",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "group_id",
            UUID(as_uuid=False),
            sa.ForeignKey("prayer_groups.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("role", sa.String(20), nullable=False, server_default="member"),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("group_id", "user_id", name="uq_group_user"),
    )

    op.create_table(
        "community_rosaries",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "initiator_user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("mystery_type", sa.String(30), nullable=False),
        sa.Column("intention", sa.String(300), nullable=True),
        sa.Column(
            "scheduled_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="open"),
        sa.Column("participant_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    op.create_table(
        "rosary_participations",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "rosary_id",
            UUID(as_uuid=False),
            sa.ForeignKey("community_rosaries.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column(
            "joined_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("decades_mask", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("rosary_id", "user_id", name="uq_rosary_user"),
    )

    op.create_table(
        "novena_trackings",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("novena_id", sa.String(60), nullable=False),
        sa.Column("intention", sa.String(500), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("completed_days_mask", sa.Integer, nullable=False, server_default="0"),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_complete", sa.Boolean, nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_table("novena_trackings")
    op.drop_table("rosary_participations")
    op.drop_table("community_rosaries")
    op.drop_table("prayer_group_memberships")
    op.drop_table("prayer_groups")
    op.drop_table("prayer_intentions")
    op.drop_table("ai_interactions")
    op.drop_table("audit_logs")
    op.drop_table("user_privacy_settings")

    op.drop_column("users", "deleted_at")
    op.drop_column("users", "is_active")
    op.drop_column("users", "role")

    sa.Enum(name="intention_status").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="audit_event_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="user_role").drop(op.get_bind(), checkfirst=True)
