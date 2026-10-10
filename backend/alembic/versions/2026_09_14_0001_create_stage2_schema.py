"""Create initial Stage 2 database schema

Revision ID: 2026_09_14_0001
Revises: 
Create Date: 2026-09-14 21:23:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '2026_09_14_0001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create Enums explicitly
    user_role_enum = postgresql.ENUM('STUDENT', 'EXAMINER', 'ADMIN', name='user_role_enum')
    user_role_enum.create(op.get_bind(), checkfirst=True)

    question_type_enum = postgresql.ENUM('MCQ', 'MULTI_SELECT', 'SHORT_ANSWER', 'LONG_ANSWER', 'HANDWRITTEN', name='question_type_enum')
    question_type_enum.create(op.get_bind(), checkfirst=True)

    difficulty_level_enum = postgresql.ENUM('EASY', 'MEDIUM', 'HARD', name='difficulty_level_enum')
    difficulty_level_enum.create(op.get_bind(), checkfirst=True)

    exam_status_enum = postgresql.ENUM('DRAFT', 'SCHEDULED', 'ACTIVE', 'COMPLETED', 'ARCHIVED', name='exam_status_enum')
    exam_status_enum.create(op.get_bind(), checkfirst=True)

    session_status_enum = postgresql.ENUM('CREATED', 'IN_PROGRESS', 'SUBMITTED', 'AUTO_SUBMITTED', 'EXPIRED', 'TERMINATED', name='session_status_enum')
    session_status_enum.create(op.get_bind(), checkfirst=True)

    evaluator_type_enum = postgresql.ENUM('AUTOMATED', 'AI', 'EXAMINER', name='evaluator_type_enum')
    evaluator_type_enum.create(op.get_bind(), checkfirst=True)

    proctoring_event_type_enum = postgresql.ENUM('FACE_MISSING', 'MULTIPLE_FACES', 'GAZE_DEVIATION', 'TAB_SWITCH', 'WINDOW_BLUR', 'CAMERA_ISSUE', 'LIGHTING_ISSUE', 'OTHER', name='proctoring_event_type_enum')
    proctoring_event_type_enum.create(op.get_bind(), checkfirst=True)

    event_severity_enum = postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', 'INFO', 'WARNING', name='event_severity_enum')
    event_severity_enum.create(op.get_bind(), checkfirst=True)

    analysis_status_enum = postgresql.ENUM('PENDING', 'COMPLETED', 'REVIEW_FLAGGED', 'VERIFIED', name='analysis_status_enum')
    analysis_status_enum.create(op.get_bind(), checkfirst=True)

    # 2. Create Users Table
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('first_name', sa.String(length=100), nullable=False),
        sa.Column('last_name', sa.String(length=100), nullable=False),
        sa.Column('role', postgresql.ENUM('STUDENT', 'EXAMINER', 'ADMIN', name='user_role_enum', create_type=False), nullable=False, server_default='STUDENT'),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_users_email', 'users', ['email'], unique=True)

    # 3. Create Questions Table
    op.create_table(
        'questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('question_type', postgresql.ENUM('MCQ', 'MULTI_SELECT', 'SHORT_ANSWER', 'LONG_ANSWER', 'HANDWRITTEN', name='question_type_enum', create_type=False), nullable=False),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('topic', sa.String(length=100), nullable=True),
        sa.Column('difficulty', postgresql.ENUM('EASY', 'MEDIUM', 'HARD', name='difficulty_level_enum', create_type=False), nullable=False, server_default='MEDIUM'),
        sa.Column('marks', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('negative_marks', sa.Numeric(precision=5, scale=2), nullable=False, server_default='0.00'),
        sa.Column('model_answer', sa.Text(), nullable=True),
        sa.Column('explanation', sa.Text(), nullable=True),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('marks > 0', name='ck_question_positive_marks'),
        sa.CheckConstraint('negative_marks >= 0', name='ck_question_non_negative_negative_marks'),
    )
    op.create_index('ix_questions_subject', 'questions', ['subject'])
    op.create_index('ix_questions_topic', 'questions', ['topic'])

    # 4. Create Question Options Table
    op.create_table(
        'question_options',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('option_text', sa.Text(), nullable=False),
        sa.Column('option_order', sa.Integer(), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('question_id', 'option_order', name='uq_question_option_order'),
    )
    op.create_index('ix_question_options_question_id', 'question_options', ['question_id'])

    # 5. Create Exams Table
    op.create_table(
        'exams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('subject', sa.String(length=100), nullable=False),
        sa.Column('created_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('duration_minutes', sa.Integer(), nullable=False),
        sa.Column('start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('total_marks', sa.Numeric(precision=6, scale=2), nullable=False, server_default='0.00'),
        sa.Column('negative_marking_enabled', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('randomize_questions', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('randomize_options', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('proctoring_enabled', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('status', postgresql.ENUM('DRAFT', 'SCHEDULED', 'ACTIVE', 'COMPLETED', 'ARCHIVED', name='exam_status_enum', create_type=False), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('duration_minutes > 0', name='ck_exam_positive_duration'),
        sa.CheckConstraint('total_marks >= 0', name='ck_exam_non_negative_total_marks'),
    )
    op.create_index('ix_exams_subject', 'exams', ['subject'])
    op.create_index('ix_exams_created_by', 'exams', ['created_by'])

    # 6. Create Exam Questions Table
    op.create_table(
        'exam_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('question_order', sa.Integer(), nullable=False),
        sa.Column('marks_override', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('exam_id', 'question_id', name='uq_exam_question_pair'),
        sa.UniqueConstraint('exam_id', 'question_order', name='uq_exam_question_order'),
        sa.CheckConstraint('marks_override IS NULL OR marks_override > 0', name='ck_exam_question_marks_override'),
    )
    op.create_index('ix_exam_questions_exam_id', 'exam_questions', ['exam_id'])
    op.create_index('ix_exam_questions_question_id', 'exam_questions', ['question_id'])

    # 7. Create Exam Sessions Table
    op.create_table(
        'exam_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('student_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', postgresql.ENUM('CREATED', 'IN_PROGRESS', 'SUBMITTED', 'AUTO_SUBMITTED', 'EXPIRED', 'TERMINATED', name='session_status_enum', create_type=False), nullable=False, server_default='CREATED'),
        sa.Column('session_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index('ix_exam_sessions_exam_id', 'exam_sessions', ['exam_id'])
    op.create_index('ix_exam_sessions_student_id', 'exam_sessions', ['student_id'])
    op.create_index('idx_exam_session_exam_student', 'exam_sessions', ['exam_id', 'student_id'])
    op.create_index('idx_exam_session_status', 'exam_sessions', ['status'])

    # 8. Create Student Answers Table
    op.create_table(
        'student_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exam_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('questions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('text_answer', sa.Text(), nullable=True),
        sa.Column('answer_image_url', sa.String(length=512), nullable=True),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('session_id', 'question_id', name='uq_session_question_answer'),
    )
    op.create_index('ix_student_answers_session_id', 'student_answers', ['session_id'])
    op.create_index('ix_student_answers_question_id', 'student_answers', ['question_id'])

    # 9. Create Answer Selected Options Table
    op.create_table(
        'answer_selected_options',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_answers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('option_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('question_options.id', ondelete='CASCADE'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.UniqueConstraint('answer_id', 'option_id', name='uq_answer_selected_option'),
    )
    op.create_index('ix_answer_selected_options_answer_id', 'answer_selected_options', ['answer_id'])
    op.create_index('ix_answer_selected_options_option_id', 'answer_selected_options', ['option_id'])

    # 10. Create Evaluation Results Table
    op.create_table(
        'evaluation_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('answer_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('student_answers.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('evaluator_type', postgresql.ENUM('AUTOMATED', 'AI', 'EXAMINER', name='evaluator_type_enum', create_type=False), nullable=False),
        sa.Column('suggested_score', sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column('final_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('justification', sa.Text(), nullable=True),
        sa.Column('matched_concepts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('missed_concepts', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('suggested_score IS NULL OR suggested_score >= 0', name='ck_eval_suggested_score_positive'),
        sa.CheckConstraint('final_score >= 0', name='ck_eval_final_score_positive'),
        sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='ck_eval_confidence_range'),
    )
    op.create_index('ix_evaluation_results_answer_id', 'evaluation_results', ['answer_id'])

    # 11. Create Proctoring Events Table
    op.create_table(
        'proctoring_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exam_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('event_type', postgresql.ENUM('FACE_MISSING', 'MULTIPLE_FACES', 'GAZE_DEVIATION', 'TAB_SWITCH', 'WINDOW_BLUR', 'CAMERA_ISSUE', 'LIGHTING_ISSUE', 'OTHER', name='proctoring_event_type_enum', create_type=False), nullable=False),
        sa.Column('severity', postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', 'CRITICAL', name='event_severity_enum', create_type=False), nullable=False, server_default='MEDIUM'),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('duration_seconds', sa.Numeric(precision=6, scale=2), nullable=True),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('event_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('duration_seconds IS NULL OR duration_seconds >= 0', name='ck_proctor_event_duration_positive'),
        sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='ck_proctor_event_confidence_range'),
    )
    op.create_index('ix_proctoring_events_session_id', 'proctoring_events', ['session_id'])
    op.create_index('ix_proctoring_events_occurred_at', 'proctoring_events', ['occurred_at'])
    op.create_index('idx_proctoring_session_time', 'proctoring_events', ['session_id', 'occurred_at'])

    # 12. Create Integrity Analyses Table
    op.create_table(
        'integrity_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exam_sessions.id', ondelete='CASCADE'), nullable=False, unique=True),
        sa.Column('integrity_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('analysis_status', postgresql.ENUM('PENDING', 'COMPLETED', 'REVIEW_FLAGGED', 'VERIFIED', name='analysis_status_enum', create_type=False), nullable=False, server_default='PENDING'),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('contributing_signals', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('integrity_score >= 0 AND integrity_score <= 100', name='ck_integrity_score_range'),
        sa.CheckConstraint('confidence IS NULL OR (confidence >= 0 AND confidence <= 1)', name='ck_integrity_confidence_range'),
    )
    op.create_index('ix_integrity_analyses_session_id', 'integrity_analyses', ['session_id'])

    # 13. Create Cross Student Analyses Table
    op.create_table(
        'cross_student_analyses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exam_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('target_session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exam_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('similarity_score', sa.Numeric(precision=5, scale=2), nullable=False),
        sa.Column('timing_correlation', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('answer_correlation', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('behaviour_correlation', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('overall_confidence', sa.Numeric(precision=3, scale=2), nullable=True),
        sa.Column('analysis_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.CheckConstraint('source_session_id != target_session_id', name='ck_cross_analysis_no_self_comparison'),
        sa.UniqueConstraint('source_session_id', 'target_session_id', name='uq_cross_analysis_session_pair'),
        sa.CheckConstraint('similarity_score >= 0 AND similarity_score <= 100', name='ck_cross_similarity_score_range'),
        sa.CheckConstraint('timing_correlation IS NULL OR (timing_correlation >= 0 AND timing_correlation <= 1)', name='ck_cross_timing_corr_range'),
        sa.CheckConstraint('answer_correlation IS NULL OR (answer_correlation >= 0 AND answer_correlation <= 1)', name='ck_cross_answer_corr_range'),
        sa.CheckConstraint('behaviour_correlation IS NULL OR (behaviour_correlation >= 0 AND behaviour_correlation <= 1)', name='ck_cross_behaviour_corr_range'),
        sa.CheckConstraint('overall_confidence IS NULL OR (overall_confidence >= 0 AND overall_confidence <= 1)', name='ck_cross_overall_conf_range'),
    )
    op.create_index('ix_cross_student_analyses_exam_id', 'cross_student_analyses', ['exam_id'])
    op.create_index('ix_cross_student_analyses_source_session_id', 'cross_student_analyses', ['source_session_id'])
    op.create_index('ix_cross_student_analyses_target_session_id', 'cross_student_analyses', ['target_session_id'])


def downgrade() -> None:
    # Drop tables in reverse dependency order
    op.drop_table('cross_student_analyses')
    op.drop_table('integrity_analyses')
    op.drop_table('proctoring_events')
    op.drop_table('evaluation_results')
    op.drop_table('answer_selected_options')
    op.drop_table('student_answers')
    op.drop_table('exam_sessions')
    op.drop_table('exam_questions')
    op.drop_table('exams')
    op.drop_table('question_options')
    op.drop_table('questions')
    op.drop_table('users')

    # Drop enums
    op.execute('DROP TYPE IF EXISTS analysis_status_enum;')
    op.execute('DROP TYPE IF EXISTS event_severity_enum;')
    op.execute('DROP TYPE IF EXISTS proctoring_event_type_enum;')
    op.execute('DROP TYPE IF EXISTS evaluator_type_enum;')
    op.execute('DROP TYPE IF EXISTS session_status_enum;')
    op.execute('DROP TYPE IF EXISTS exam_status_enum;')
    op.execute('DROP TYPE IF EXISTS difficulty_level_enum;')
    op.execute('DROP TYPE IF EXISTS question_type_enum;')
    op.execute('DROP TYPE IF EXISTS user_role_enum;')
