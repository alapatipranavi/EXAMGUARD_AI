"""Add face descriptor version to users

Revision ID: 2026_10_09_0015
Revises: 2026_10_05_0014
Create Date: 2026-10-09 20:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '2026_10_09_0015'
down_revision: Union[str, None] = '2026_10_05_0014'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Add face_descriptor_version column to users
    # Existing registered users defaulted to version 1 (legacy uncentered)
    op.add_column(
        'users',
        sa.Column(
            'face_descriptor_version',
            sa.Integer(),
            nullable=True,
            server_default=sa.text('1')
        )
    )
    # Set existing registered users to 1
    op.execute("UPDATE users SET face_descriptor_version = 1 WHERE is_face_registered = true AND face_descriptor_version IS NULL")


def downgrade() -> None:
    op.drop_column('users', 'face_descriptor_version')
