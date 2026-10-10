"""Add question source column

Revision ID: 2026_09_17_0002
Revises: 2026_09_14_0001
Create Date: 2026-09-17 11:37:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_09_17_0002'
down_revision: Union[str, None] = '2026_09_14_0001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    question_source_enum = postgresql.ENUM('MANUAL', 'AI_GENERATED', 'CSV_IMPORT', 'PDF_IMPORT', name='question_source_enum')
    question_source_enum.create(op.get_bind(), checkfirst=True)

    op.add_column(
        'questions',
        sa.Column(
            'source',
            sa.Enum('MANUAL', 'AI_GENERATED', 'CSV_IMPORT', 'PDF_IMPORT', name='question_source_enum'),
            server_default='MANUAL',
            nullable=False
        )
    )


def downgrade() -> None:
    op.drop_column('questions', 'source')
    question_source_enum = postgresql.ENUM(name='question_source_enum')
    question_source_enum.drop(op.get_bind(), checkfirst=True)
