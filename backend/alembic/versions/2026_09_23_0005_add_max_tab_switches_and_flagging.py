"""Add max_tab_switches to exams and is_flagged flag_reason to exam_sessions

Revision ID: 2026_09_23_0005
Revises: 2026_09_22_0004
Create Date: 2026-09-23 15:30:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2026_09_23_0005'
down_revision = '2026_09_22_0004'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add max_tab_switches to exams
    op.add_column(
        'exams',
        sa.Column('max_tab_switches', sa.Integer(), nullable=False, server_default='3')
    )
    op.create_check_constraint(
        'ck_exam_max_tab_switches_range',
        'exams',
        'max_tab_switches >= 0 AND max_tab_switches <= 20'
    )

    # Add is_flagged and flag_reason to exam_sessions
    op.add_column(
        'exam_sessions',
        sa.Column('is_flagged', sa.Boolean(), nullable=False, server_default='false')
    )
    op.add_column(
        'exam_sessions',
        sa.Column('flag_reason', sa.String(length=255), nullable=True)
    )

    # Add TAB_SWITCH_LIMIT_EXCEEDED to proctoring_event_type_enum in postgresql
    op.execute("ALTER TYPE proctoring_event_type_enum ADD VALUE IF NOT EXISTS 'TAB_SWITCH_LIMIT_EXCEEDED'")


def downgrade() -> None:
    op.drop_column('exam_sessions', 'flag_reason')
    op.drop_column('exam_sessions', 'is_flagged')
    op.drop_constraint('ck_exam_max_tab_switches_range', 'exams', type_='check')
    op.drop_column('exams', 'max_tab_switches')
