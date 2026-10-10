"""Add exam instructions and passing_marks columns

Revision ID: 2026_09_19_0003
Revises: 2026_09_17_0002
Create Date: 2026-09-19 15:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_09_19_0003'
down_revision: Union[str, None] = '2026_09_17_0002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE exam_status_enum ADD VALUE IF NOT EXISTS 'PUBLISHED';")
    op.add_column(
        'exams',
        sa.Column('instructions', sa.Text(), nullable=True)
    )
    op.add_column(
        'exams',
        sa.Column('passing_marks', sa.Numeric(precision=6, scale=2), server_default='0.00', nullable=False)
    )


def downgrade() -> None:
    op.drop_column('exams', 'passing_marks')
    op.drop_column('exams', 'instructions')
