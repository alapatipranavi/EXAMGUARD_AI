"""Add Stage 9.3 Behavioural Intelligence event types

Revision ID: 2026_09_29_0011
Revises: 2026_09_29_0010
Create Date: 2026-09-29 15:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2026_09_29_0011'
down_revision: Union[str, None] = '2026_09_29_0010'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    new_event_types = [
        'QUESTION_VIEWED',
        'ANSWER_CREATED',
        'ANSWER_CHANGED',
        'ANSWER_CLEARED',
        'QUESTION_NAVIGATION',
        'RAPID_ANSWER_CHANGES',
        'UNUSUAL_TIMING',
        'NAVIGATION_ANOMALY',
        'BEHAVIOURAL_ANOMALY',
    ]

    for et in new_event_types:
        op.execute(sa.text(f"ALTER TYPE proctoring_event_type_enum ADD VALUE IF NOT EXISTS '{et}'"))


def downgrade() -> None:
    pass
