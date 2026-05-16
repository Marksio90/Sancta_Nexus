"""Add diocese licensing and parish invite codes.

Revision ID: 006
Revises: 005
Create Date: 2026-05-16

Changes:
  1. Creates diocese_licenses table (B2B SaaS — diocese annual contracts).
  2. Adds invite_code column to prayer_groups (parish invite system).
  3. Adds diocese_id FK column to users (diocese member activation).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "006"
down_revision: str | None = "005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Diocese licenses table
    op.create_table(
        "diocese_licenses",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column("name", sa.String(300), nullable=False),
        sa.Column("country", sa.String(2), nullable=False, server_default="PL"),
        sa.Column("diocese_code", sa.String(50), nullable=False),
        sa.Column("contact_email", sa.String(320), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(200), nullable=True),
        sa.Column("max_users", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("license_starts_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("license_expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index(
        "ix_diocese_licenses_diocese_code",
        "diocese_licenses",
        ["diocese_code"],
        unique=True,
    )

    # 2. invite_code on prayer_groups
    op.add_column(
        "prayer_groups",
        sa.Column("invite_code", sa.String(16), nullable=True),
    )
    op.create_index(
        "ix_prayer_groups_invite_code",
        "prayer_groups",
        ["invite_code"],
        unique=True,
    )

    # 3. diocese_id FK on users
    op.add_column(
        "users",
        sa.Column(
            "diocese_id",
            UUID(as_uuid=False),
            sa.ForeignKey("diocese_licenses.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.create_index("ix_users_diocese_id", "users", ["diocese_id"])


def downgrade() -> None:
    op.drop_index("ix_users_diocese_id", table_name="users")
    op.drop_column("users", "diocese_id")

    op.drop_index("ix_prayer_groups_invite_code", table_name="prayer_groups")
    op.drop_column("prayer_groups", "invite_code")

    op.drop_index("ix_diocese_licenses_diocese_code", table_name="diocese_licenses")
    op.drop_table("diocese_licenses")
