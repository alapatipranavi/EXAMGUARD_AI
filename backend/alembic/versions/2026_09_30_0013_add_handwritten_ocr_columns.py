"""Add Stage 11 Handwritten OCR columns to student_answers table

Revision ID: 2026_09_30_0013
Revises: 2026_09_29_0012
Create Date: 2026-09-30 14:45:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2026_09_30_0013'
down_revision: Union[str, None] = '2026_09_29_0012'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('student_answers', sa.Column('ocr_status', sa.String(length=64), server_default='OCR_NOT_REQUIRED', nullable=True))
    op.add_column('student_answers', sa.Column('ocr_confidence', sa.Numeric(precision=3, scale=2), nullable=True))
    op.add_column('student_answers', sa.Column('ocr_processed_at', sa.DateTime(timezone=True), nullable=True))


def downgrade() -> None:
    op.drop_column('student_answers', 'ocr_processed_at')
    op.drop_column('student_answers', 'ocr_confidence')
    op.drop_column('student_answers', 'ocr_status')
