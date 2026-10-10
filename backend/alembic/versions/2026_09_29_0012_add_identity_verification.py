"""Add Stage 9.4 Student Identity Verification columns and enum values

Revision ID: 2026_09_29_0012
Revises: 2026_09_29_0011
Create Date: 2026-09-29 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision: str = '2026_09_29_0012'
down_revision: Union[str, None] = '2026_09_29_0011'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Update proctoring event type enum
    identity_event_types = [
        'IDENTITY_VERIFIED',
        'IDENTITY_VERIFICATION_FAILED',
        'IDENTITY_MISMATCH_STARTED',
        'IDENTITY_VERIFICATION_RESTORED',
        'IDENTITY_MISMATCH_CONFIRMED',
    ]

    for et in identity_event_types:
        op.execute(sa.text(f"ALTER TYPE proctoring_event_type_enum ADD VALUE IF NOT EXISTS '{et}'"))

    # 2. Add columns to users table
    op.add_column('users', sa.Column('is_face_registered', sa.Boolean(), server_default='false', nullable=False))
    op.add_column('users', sa.Column('face_registered_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('users', sa.Column('face_embedding', JSONB(), nullable=True))

    # 3. Add columns to exam_sessions table
    op.add_column('exam_sessions', sa.Column('identity_verified_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('exam_sessions', sa.Column('identity_verification_status', sa.String(length=50), server_default='UNVERIFIED', nullable=True))


def downgrade() -> None:
    op.drop_column('exam_sessions', 'identity_verification_status')
    op.drop_column('exam_sessions', 'identity_verified_at')
    op.drop_column('users', 'face_embedding')
    op.drop_column('users', 'face_registered_at')
    op.drop_column('users', 'is_face_registered')
