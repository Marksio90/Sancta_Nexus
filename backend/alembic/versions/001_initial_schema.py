"""Initial schema — create all Sancta Nexus tables.

Revision ID: 001
Revises: None
Create Date: 2026-03-16

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

# revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Enum types ────────────────────────────────────────────────────────
    subscription_tier_enum = sa.Enum(
        "free", "pilgrim", "disciple", "mystic",
        name="subscription_tier",
    )
    session_type_enum = sa.Enum(
        "lectio_divina", "spiritual_direction", "bible_study", "prayer", "meditation",
        name="session_type",
    )
    subscription_tier_enum.create(op.get_bind(), checkfirst=True)
    session_type_enum.create(op.get_bind(), checkfirst=True)

    # ── users ─────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True, index=True),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("hashed_password", sa.String(1024), nullable=False),
        sa.Column("spiritual_profile_json", sa.Text, nullable=True),
        sa.Column(
            "subscription_tier",
            subscription_tier_enum,
            nullable=False,
            server_default="free",
        ),
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

    # ── sessions ──────────────────────────────────────────────────────────
    op.create_table(
        "sessions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("session_type", session_type_enum, nullable=False),
        sa.Column("emotion_vector_json", sa.Text, nullable=True),
        sa.Column("scripture_reference", sa.String(256), nullable=True),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("ended_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text, nullable=True),
    )

    # ── prayers ───────────────────────────────────────────────────────────
    op.create_table(
        "prayers",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("prayer_type", sa.String(128), nullable=True),
        sa.Column("tradition", sa.String(128), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── scripture_encounters ──────────────────────────────────────────────
    op.create_table(
        "scripture_encounters",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "session_id",
            UUID(as_uuid=False),
            sa.ForeignKey("sessions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("book", sa.String(64), nullable=False),
        sa.Column("chapter", sa.Integer, nullable=False),
        sa.Column("verse_start", sa.Integer, nullable=False),
        sa.Column("verse_end", sa.Integer, nullable=False),
        sa.Column("user_reflection", sa.Text, nullable=True),
        sa.Column("emotion_score", sa.Float, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── spiritual_insights ────────────────────────────────────────────────
    op.create_table(
        "spiritual_insights",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("insight_type", sa.String(128), nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("period_start", sa.DateTime(timezone=True), nullable=True),
        sa.Column("period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )


def downgrade() -> None:
    op.drop_table("spiritual_insights")
    op.drop_table("scripture_encounters")
    op.drop_table("prayers")
    op.drop_table("sessions")
    op.drop_table("users")

    sa.Enum(name="session_type").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="subscription_tier").drop(op.get_bind(), checkfirst=True)
