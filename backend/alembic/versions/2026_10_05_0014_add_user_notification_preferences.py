"""Add user notification preferences

Revision ID: 2026_10_05_0014
Revises: 9c3015d05a51
Create Date: 2026-10-05 18:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_10_05_0014'
down_revision: Union[str, None] = '9c3015d05a51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'users',
        sa.Column(
            'notification_preferences',
            postgresql.JSONB(astext_type=sa.Text()),
            server_default=sa.text('\'{"exam_reminders": true, "result_notifications": true, "integrity_alerts": true, "system_updates": true}\''),
            nullable=True
        )
    )


def downgrade() -> None:
    op.drop_column('users', 'notification_preferences')
