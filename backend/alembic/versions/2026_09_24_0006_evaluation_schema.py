"""Add objective evaluation schema and session evaluation summary table

Revision ID: 2026_09_24_0006
Revises: 2026_09_23_0005
Create Date: 2026-09-24 16:35:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_09_24_0006'
down_revision: Union[str, None] = '2026_09_23_0005'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums
    pass_fail_enum = postgresql.ENUM('PASSED', 'FAILED', name='pass_fail_status_enum')
    pass_fail_enum.create(op.get_bind(), checkfirst=True)

    eval_status_enum = postgresql.ENUM('COMPLETED', 'PENDING_REVIEW', 'FAILED', name='evaluation_status_enum')
    eval_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Drop check constraint ck_eval_final_score_positive from evaluation_results if present
    try:
        op.drop_constraint('ck_eval_final_score_positive', 'evaluation_results', type_='check')
    except Exception:
        pass

    # 3. Create exam_session_evaluations table
    op.create_table(
        'exam_session_evaluations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exam_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('total_questions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('answered_questions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unanswered_questions', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('correct_answers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('incorrect_answers', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('objective_marks', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00'),
        sa.Column('negative_marks', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00'),
        sa.Column('total_score', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00'),
        sa.Column('maximum_marks', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00'),
        sa.Column('percentage', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('passing_marks', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00'),
        sa.Column('pass_fail_status', postgresql.ENUM('PASSED', 'FAILED', name='pass_fail_status_enum', create_type=False), nullable=False, server_default='FAILED'),
        sa.Column('status', postgresql.ENUM('COMPLETED', 'PENDING_REVIEW', 'FAILED', name='evaluation_status_enum', create_type=False), nullable=False, server_default='COMPLETED'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('session_id', name='uq_session_evaluation'),
    )
    op.create_index('ix_exam_session_evaluations_session_id', 'exam_session_evaluations', ['session_id'])
    op.create_index('ix_exam_session_evaluations_exam_id', 'exam_session_evaluations', ['exam_id'])
    op.create_index('ix_exam_session_evaluations_student_id', 'exam_session_evaluations', ['student_id'])


def downgrade() -> None:
    op.drop_table('exam_session_evaluations')

    op.execute('DROP TYPE IF EXISTS evaluation_status_enum;')
    op.execute('DROP TYPE IF EXISTS pass_fail_status_enum;')
