import enum
import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, ForeignKey, Enum as SQLEnum, Index, func

from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.exam import Exam
    from app.models.answer import StudentAnswer
    from app.models.evaluation import ExamSessionEvaluation
    from app.models.proctoring import ProctoringEvent
    from app.models.integrity import IntegrityAnalysis, CrossStudentAnalysis


class SessionStatus(str, enum.Enum):
    CREATED = "CREATED"
    IN_PROGRESS = "IN_PROGRESS"
    SUBMITTED = "SUBMITTED"
    AUTO_SUBMITTED = "AUTO_SUBMITTED"
    EXPIRED = "EXPIRED"
    TERMINATED = "TERMINATED"


class ExamSession(Base):
    __tablename__ = "exam_sessions"
    __table_args__ = (
        Index("idx_exam_session_exam_student", "exam_id", "student_id"),
        Index("idx_exam_session_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    exam_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exams.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    started_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    status: Mapped[SessionStatus] = mapped_column(
        SQLEnum(SessionStatus, name="session_status_enum", create_type=True),
        default=SessionStatus.CREATED,
        nullable=False
    )
    session_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    is_flagged: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default='false',
        nullable=False
    )
    flag_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True
    )
    identity_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    identity_verification_status: Mapped[Optional[str]] = mapped_column(
        String(50),
        default='UNVERIFIED',
        server_default="'UNVERIFIED'",
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
    exam: Mapped["Exam"] = relationship(
        "Exam",
        back_populates="sessions",
        foreign_keys=[exam_id]
    )
    student: Mapped["User"] = relationship(
        "User",
        back_populates="exam_sessions",
        foreign_keys=[student_id]
    )
    answers: Mapped[List["StudentAnswer"]] = relationship(
        "StudentAnswer",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    proctoring_events: Mapped[List["ProctoringEvent"]] = relationship(
        "ProctoringEvent",
        back_populates="session",
        cascade="all, delete-orphan"
    )
    integrity_analysis: Mapped[Optional["IntegrityAnalysis"]] = relationship(
        "IntegrityAnalysis",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )
    evaluation: Mapped[Optional["ExamSessionEvaluation"]] = relationship(
        "ExamSessionEvaluation",
        back_populates="session",
        uselist=False,
        cascade="all, delete-orphan"
    )
    source_cross_analyses: Mapped[List["CrossStudentAnalysis"]] = relationship(
        "CrossStudentAnalysis",
        back_populates="source_session",
        foreign_keys="[CrossStudentAnalysis.source_session_id]",
        cascade="all, delete-orphan"
    )
    target_cross_analyses: Mapped[List["CrossStudentAnalysis"]] = relationship(
        "CrossStudentAnalysis",
        back_populates="target_session",
        foreign_keys="[CrossStudentAnalysis.target_session_id]",
        cascade="all, delete-orphan"
    )
