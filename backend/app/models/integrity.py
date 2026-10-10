import enum
import uuid
from datetime import datetime
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import (
    Text, DateTime, Numeric, ForeignKey, Enum as SQLEnum, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.exam import Exam
    from app.models.exam_session import ExamSession


class AnalysisStatus(str, enum.Enum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    REVIEW_FLAGGED = "REVIEW_FLAGGED"
    VERIFIED = "VERIFIED"


class IntegrityAnalysis(Base):
    __tablename__ = "integrity_analyses"
    __table_args__ = (
        CheckConstraint("integrity_score >= 0 AND integrity_score <= 100", name="ck_integrity_score_range"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_integrity_confidence_range"),
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
    integrity_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    analysis_status: Mapped[AnalysisStatus] = mapped_column(
        SQLEnum(AnalysisStatus, name="analysis_status_enum", create_type=True),
        default=AnalysisStatus.PENDING,
        nullable=False
    )
    summary: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    contributing_signals: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
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
    session: Mapped["ExamSession"] = relationship(
        "ExamSession",
        back_populates="integrity_analysis"
    )
    reviewer: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="integrity_analyses_reviewed",
        foreign_keys=[reviewed_by]
    )


class CrossStudentAnalysis(Base):
    __tablename__ = "cross_student_analyses"
    __table_args__ = (
        CheckConstraint("source_session_id != target_session_id", name="ck_cross_analysis_no_self_comparison"),
        UniqueConstraint("source_session_id", "target_session_id", name="uq_cross_analysis_session_pair"),
        CheckConstraint("similarity_score >= 0 AND similarity_score <= 100", name="ck_cross_similarity_score_range"),
        CheckConstraint("timing_correlation IS NULL OR (timing_correlation >= 0 AND timing_correlation <= 1)", name="ck_cross_timing_corr_range"),
        CheckConstraint("answer_correlation IS NULL OR (answer_correlation >= 0 AND answer_correlation <= 1)", name="ck_cross_answer_corr_range"),
        CheckConstraint("behaviour_correlation IS NULL OR (behaviour_correlation >= 0 AND behaviour_correlation <= 1)", name="ck_cross_behaviour_corr_range"),
        CheckConstraint("overall_confidence IS NULL OR (overall_confidence >= 0 AND overall_confidence <= 1)", name="ck_cross_overall_conf_range"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    source_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    target_session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    similarity_score: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    timing_correlation: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    answer_correlation: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    behaviour_correlation: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    overall_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    analysis_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    exam: Mapped["Exam"] = relationship(
        "Exam",
        back_populates="cross_student_analyses"
    )
    source_session: Mapped["ExamSession"] = relationship(
        "ExamSession",
        back_populates="source_cross_analyses",
        foreign_keys=[source_session_id]
    )
    target_session: Mapped["ExamSession"] = relationship(
        "ExamSession",
        back_populates="target_cross_analyses",
        foreign_keys=[target_session_id]
    )
