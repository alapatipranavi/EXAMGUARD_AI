import enum
import uuid
from datetime import datetime, timezone
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import String, Boolean, DateTime, Integer, ForeignKey, Enum as SQLEnum, func
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.question import Question
    from app.models.exam import Exam
    from app.models.exam_session import ExamSession
    from app.models.evaluation import EvaluationResult
    from app.models.integrity import IntegrityAnalysis
    from app.models.academic import College, Department, Section


class UserRole(str, enum.Enum):
    STUDENT = "STUDENT"
    EXAMINER = "EXAMINER"
    ADMIN = "ADMIN"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        index=True,
        nullable=False
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    first_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    last_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False
    )
    role: Mapped[UserRole] = mapped_column(
        SQLEnum(UserRole, name="user_role_enum", create_type=True),
        default=UserRole.STUDENT,
        nullable=False
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    is_face_registered: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default='false',
        nullable=False
    )
    face_registered_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    face_embedding: Mapped[Optional[List[float]]] = mapped_column(
        JSONB,
        nullable=True
    )
    face_descriptor_version: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        default=2
    )
    college_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("colleges.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    year_of_study: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    notification_preferences: Mapped[Optional[dict]] = mapped_column(
        JSONB,
        nullable=True,
        server_default='{"exam_reminders": true, "result_notifications": true, "integrity_alerts": true, "system_updates": true}'
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
    questions_created: Mapped[List["Question"]] = relationship(
        "Question",
        back_populates="creator",
        foreign_keys="[Question.created_by]"
    )
    exams_created: Mapped[List["Exam"]] = relationship(
        "Exam",
        back_populates="creator",
        foreign_keys="[Exam.created_by]"
    )
    exam_sessions: Mapped[List["ExamSession"]] = relationship(
        "ExamSession",
        back_populates="student",
        foreign_keys="[ExamSession.student_id]"
    )
    evaluations_reviewed: Mapped[List["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="reviewer",
        foreign_keys="[EvaluationResult.reviewed_by]"
    )
    integrity_analyses_reviewed: Mapped[List["IntegrityAnalysis"]] = relationship(
        "IntegrityAnalysis",
        back_populates="reviewer",
        foreign_keys="[IntegrityAnalysis.reviewed_by]"
    )
    college: Mapped[Optional["College"]] = relationship(
        "College",
        back_populates="users",
        foreign_keys=[college_id]
    )
    department: Mapped[Optional["Department"]] = relationship(
        "Department",
        back_populates="users",
        foreign_keys=[department_id]
    )
    section: Mapped[Optional["Section"]] = relationship(
        "Section",
        back_populates="users",
        foreign_keys=[section_id]
    )
