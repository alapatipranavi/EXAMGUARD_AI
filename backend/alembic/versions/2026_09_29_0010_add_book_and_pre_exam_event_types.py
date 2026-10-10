"""Add BOOK_DETECTED, PRE_EXAM_CHECK_STARTED, PRE_EXAM_CHECK_COMPLETED event types

Revision ID: 2026_09_29_0010
Revises: 2026_09_29_0009
Create Date: 2026-09-29 14:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2026_09_29_0010'
down_revision: Union[str, None] = '2026_09_29_0009'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    new_event_types = [
        'BOOK_DETECTED',
        'PRE_EXAM_CHECK_STARTED',
        'PRE_EXAM_CHECK_COMPLETED',
    ]

    for et in new_event_types:
        op.execute(sa.text(f"ALTER TYPE proctoring_event_type_enum ADD VALUE IF NOT EXISTS '{et}'"))


def downgrade() -> None:
    pass
