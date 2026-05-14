"""Intention moderation: new enum values and moderation columns.

Revision ID: 004
Revises: 003
Create Date: 2026-05-14

Adds PENDING_MODERATION and REJECTED to IntentionStatus enum,
plus moderation-related columns on prayer_intentions.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import UUID

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Extend enum — PostgreSQL supports IF NOT EXISTS for ADD VALUE
    op.execute("ALTER TYPE intention_status ADD VALUE IF NOT EXISTS 'pending_moderation'")
    op.execute("ALTER TYPE intention_status ADD VALUE IF NOT EXISTS 'rejected'")

    op.add_column('prayer_intentions', sa.Column('moderator_id', UUID(as_uuid=False), nullable=True))
    op.add_column('prayer_intentions', sa.Column('moderated_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('prayer_intentions', sa.Column('rejection_reason', sa.String(500), nullable=True))
    op.add_column('prayer_intentions', sa.Column('group_id', UUID(as_uuid=False), nullable=True))

    op.create_foreign_key(
        'fk_intention_moderator', 'prayer_intentions', 'users',
        ['moderator_id'], ['id'], ondelete='SET NULL',
    )
    op.create_foreign_key(
        'fk_intention_group', 'prayer_intentions', 'prayer_groups',
        ['group_id'], ['id'], ondelete='SET NULL',
    )


def downgrade() -> None:
    op.drop_constraint('fk_intention_group', 'prayer_intentions', type_='foreignkey')
    op.drop_constraint('fk_intention_moderator', 'prayer_intentions', type_='foreignkey')
    op.drop_column('prayer_intentions', 'group_id')
    op.drop_column('prayer_intentions', 'rejection_reason')
    op.drop_column('prayer_intentions', 'moderated_at')
    op.drop_column('prayer_intentions', 'moderator_id')
    # Note: cannot remove enum values in PostgreSQL without dropping the type
