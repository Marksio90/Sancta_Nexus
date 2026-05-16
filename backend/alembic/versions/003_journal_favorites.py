"""Journal entries and favorite passages.

Revision ID: 003
Revises: 002
Create Date: 2026-05-14

Dodaje:
- tabela journal_entries (dziennik duchowy)
- tabela favorite_passages (ulubione fragmenty Pisma)
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "003"
down_revision: str | None = "002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ── journal_entries ───────────────────────────────────────────────────────
    op.create_table(
        "journal_entries",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("title", sa.String(256), nullable=True),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tags", sa.String(512), nullable=True),
        sa.Column("mood", sa.String(64), nullable=True),
        sa.Column("scripture_reference", sa.String(128), nullable=True),
        sa.Column("lectio_session_id", sa.String(128), nullable=True),
        sa.Column("program_id", sa.String(128), nullable=True),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
            index=True,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )

    # ── favorite_passages ─────────────────────────────────────────────────────
    op.create_table(
        "favorite_passages",
        sa.Column("id", UUID(as_uuid=False), primary_key=True),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("book", sa.String(64), nullable=False),
        sa.Column("chapter", sa.Integer, nullable=False),
        sa.Column("verse_start", sa.Integer, nullable=False),
        sa.Column("verse_end", sa.Integer, nullable=False),
        sa.Column("reference", sa.String(128), nullable=False),
        sa.Column("excerpt", sa.String(512), nullable=True),
        sa.Column("note", sa.Text, nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint(
            "user_id", "book", "chapter", "verse_start", "verse_end",
            name="uq_favorite_passage",
        ),
    )


def downgrade() -> None:
    op.drop_table("favorite_passages")
    op.drop_table("journal_entries")
