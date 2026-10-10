"""Add examiner_comment, status to evaluation_results and extend evaluation_status_enum

Revision ID: 2026_09_28_0008
Revises: 2026_09_28_0007
Create Date: 2026-09-28 21:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '2026_09_28_0008'
down_revision: Union[str, None] = '2026_09_28_0007'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Extend evaluation_status_enum in Postgres
    bind = op.get_bind()
    if bind.dialect.name == 'postgresql':
        op.execute("ALTER TYPE evaluation_status_enum ADD VALUE IF NOT EXISTS 'AI_EVALUATED'")
        op.execute("ALTER TYPE evaluation_status_enum ADD VALUE IF NOT EXISTS 'MANUAL_REVIEW'")
        op.execute("ALTER TYPE evaluation_status_enum ADD VALUE IF NOT EXISTS 'FINALIZED'")

    # 2. Add examiner_comment column to evaluation_results
    op.add_column('evaluation_results', sa.Column('examiner_comment', sa.Text(), nullable=True))

    # 3. Add status column to evaluation_results
    eval_status_enum = postgresql.ENUM(
        'COMPLETED', 'PENDING_REVIEW', 'FAILED', 'AI_EVALUATED', 'MANUAL_REVIEW', 'FINALIZED',
        name='evaluation_status_enum', create_type=False
    )
    op.add_column('evaluation_results', sa.Column('status', eval_status_enum, nullable=False, server_default='COMPLETED'))


def downgrade() -> None:
    op.drop_column('evaluation_results', 'status')
    op.drop_column('evaluation_results', 'examiner_comment')
