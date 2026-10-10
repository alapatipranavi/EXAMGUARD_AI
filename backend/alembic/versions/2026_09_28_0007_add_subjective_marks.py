"""Add subjective_marks column to exam_session_evaluations table

Revision ID: 2026_09_28_0007
Revises: 2026_09_24_0006
Create Date: 2026-09-28 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_09_28_0007'
down_revision: Union[str, None] = '2026_09_24_0006'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'exam_session_evaluations',
        sa.Column('subjective_marks', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00')
    )


def downgrade() -> None:
    op.drop_column('exam_session_evaluations', 'subjective_marks')
