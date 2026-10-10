"""Add Stage 9.2 object detection event types

Revision ID: 2026_09_29_0009
Revises: 2026_09_28_0008
Create Date: 2026-09-29 12:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '2026_09_29_0009'
down_revision: Union[str, None] = '2026_09_28_0008'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    new_event_types = [
        'PHONE_DETECTED',
        'LAPTOP_DETECTED',
        'ADDITIONAL_PERSON_DETECTED',
        'OBJECT_DETECTION_STARTED',
        'OBJECT_DETECTION_UNAVAILABLE',
    ]

    for et in new_event_types:
        op.execute(sa.text(f"ALTER TYPE proctoring_event_type_enum ADD VALUE IF NOT EXISTS '{et}'"))


def downgrade() -> None:
    pass
