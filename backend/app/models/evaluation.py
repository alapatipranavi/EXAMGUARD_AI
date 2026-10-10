import enum
import uuid
from datetime import datetime
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import (
    Text, DateTime, Numeric, Integer, ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.exam import Exam
    from app.models.exam_session import ExamSession
    from app.models.answer import StudentAnswer


class EvaluatorType(str, enum.Enum):
    AUTOMATED = "AUTOMATED"
    AI = "AI"
    EXAMINER = "EXAMINER"


class EvaluationStatus(str, enum.Enum):
    COMPLETED = "COMPLETED"
    PENDING_REVIEW = "PENDING_REVIEW"
    FAILED = "FAILED"
    AI_EVALUATED = "AI_EVALUATED"
    MANUAL_REVIEW = "MANUAL_REVIEW"
    FINALIZED = "FINALIZED"


class PassFailStatus(str, enum.Enum):
    PASSED = "PASSED"
    FAILED = "FAILED"


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"
    __table_args__ = (
        CheckConstraint("suggested_score IS NULL OR suggested_score >= 0", name="ck_eval_suggested_score_positive"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_eval_confidence_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_answers.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    evaluator_type: Mapped[EvaluatorType] = mapped_column(
        SQLEnum(EvaluatorType, name="evaluator_type_enum", create_type=True),
        nullable=False
    )
    suggested_score: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
        nullable=True
    )
    final_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    justification: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    examiner_comment: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        SQLEnum(EvaluationStatus, name="evaluation_status_enum", create_type=False),
        nullable=False,
        default=EvaluationStatus.COMPLETED
    )
    matched_concepts: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    missed_concepts: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    answer: Mapped["StudentAnswer"] = relationship(
        "StudentAnswer",
        back_populates="evaluation_result"
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="evaluations_reviewed",
        foreign_keys=[reviewed_by]
    )


class ExamSessionEvaluation(Base):
    __tablename__ = "exam_session_evaluations"
    __table_args__ = (
        UniqueConstraint("session_id", name="uq_session_evaluation"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
        index=True
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    total_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    answered_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    unanswered_questions: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    correct_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    incorrect_answers: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    objective_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0.0)
    subjective_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0.0)
    negative_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0.0)
    total_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0.0)
    maximum_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0.0)
    percentage: Mapped[float] = mapped_column(Numeric(5, 2), nullable=False, default=0.0)
    passing_marks: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False, default=0.0)

    pass_fail_status: Mapped[PassFailStatus] = mapped_column(
        SQLEnum(PassFailStatus, name="pass_fail_status_enum", create_type=True),
        nullable=False,
        default=PassFailStatus.FAILED
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        SQLEnum(EvaluationStatus, name="evaluation_status_enum", create_type=True),
        nullable=False,
        default=EvaluationStatus.COMPLETED
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )

    # Relationships
    session: Mapped["ExamSession"] = relationship("ExamSession", back_populates="evaluation")
    exam: Mapped["Exam"] = relationship("Exam")
    student: Mapped["User"] = relationship("User")

