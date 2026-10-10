"""Add Stage 7 proctoring event types

Revision ID: 2026_09_22_0004
Revises: 2026_09_19_0003
Create Date: 2026-09-22 21:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '2026_09_22_0004'
down_revision: Union[str, None] = '2026_09_19_0003'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add new values to proctoring_event_type_enum in PostgreSQL
    new_event_types = [
        'CAMERA_PERMISSION_DENIED',
        'CAMERA_READY',
        'CAMERA_DISCONNECTED',
        'MICROPHONE_PERMISSION_DENIED',
        'MICROPHONE_READY',
        'MICROPHONE_DISCONNECTED',
        'FACE_NOT_DETECTED',
        'FACE_DETECTED',
        'MULTIPLE_FACES_DETECTED',
        'TAB_HIDDEN',
        'TAB_VISIBLE',
        'FULLSCREEN_ENTERED',
        'FULLSCREEN_EXITED',
    ]

    for et in new_event_types:
        op.execute(sa.text(f"ALTER TYPE proctoring_event_type_enum ADD VALUE IF NOT EXISTS '{et}'"))


def downgrade() -> None:
    pass
