"""Add subscriptions table for Stripe billing.

Revision ID: 005
Revises: 004
Create Date: 2026-05-15

Creates the subscriptions table that backs the Subscription ORM model
and stores Stripe customer / subscription IDs alongside the tier and
billing status for each user.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID

from alembic import op

revision: str = "005"
down_revision: str | None = "004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the subscription_tier_sub enum used exclusively by subscriptions
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE subscription_tier_sub AS ENUM (
                'free', 'pilgrim', 'disciple', 'mystic'
            );
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    op.create_table(
        "subscriptions",
        sa.Column("id", UUID(as_uuid=False), primary_key=True, nullable=False),
        sa.Column(
            "user_id",
            UUID(as_uuid=False),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stripe_customer_id", sa.String(64), nullable=True, unique=True),
        sa.Column("stripe_subscription_id", sa.String(64), nullable=True, unique=True),
        sa.Column("stripe_price_id", sa.String(64), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="free"),
        sa.Column(
            "tier",
            sa.Enum(
                "free", "pilgrim", "disciple", "mystic",
                name="subscription_tier_sub",
                create_type=False,
            ),
            nullable=False,
            server_default="free",
        ),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_index("ix_subscriptions_user_id", "subscriptions", ["user_id"])
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"])
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )


def downgrade() -> None:
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_stripe_customer_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_user_id", table_name="subscriptions")
    op.drop_table("subscriptions")
    op.execute("DROP TYPE IF EXISTS subscription_tier_sub")
