import enum
import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Text, Boolean, DateTime, Numeric, Integer, ForeignKey,
    Enum as SQLEnum, CheckConstraint, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.question import Question
    from app.models.exam_session import ExamSession
    from app.models.integrity import CrossStudentAnalysis
    from app.models.academic import Department, Section


class ExamStatus(str, enum.Enum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    SCHEDULED = "SCHEDULED"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"
    ARCHIVED = "ARCHIVED"


class ExamTargetType(str, enum.Enum):
    COLLEGE = "COLLEGE"
    DEPARTMENT = "DEPARTMENT"
    YEAR = "YEAR"
    SECTION = "SECTION"
    SPECIFIC_STUDENTS = "SPECIFIC_STUDENTS"


class Exam(Base):
    __tablename__ = "exams"
    __table_args__ = (
        CheckConstraint("duration_minutes > 0", name="ck_exam_positive_duration"),
        CheckConstraint("total_marks >= 0", name="ck_exam_non_negative_total_marks"),
        CheckConstraint("max_tab_switches >= 0 AND max_tab_switches <= 20", name="ck_exam_max_tab_switches_range"),
    )


    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    instructions: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    subject: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False
    )
    created_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    duration_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    start_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    end_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True
    )
    total_marks: Mapped[float] = mapped_column(
        Numeric(6, 2),
        default=0.00,
        nullable=False
    )
    passing_marks: Mapped[float] = mapped_column(
        Numeric(6, 2),
        default=0.00,
        nullable=False
    )
    negative_marking_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    randomize_questions: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    randomize_options: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
    )
    proctoring_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    max_tab_switches: Mapped[int] = mapped_column(
        Integer,
        default=3,
        server_default='3',
        nullable=False
    )

    status: Mapped[ExamStatus] = mapped_column(
        SQLEnum(ExamStatus, name="exam_status_enum", create_type=True),
        default=ExamStatus.DRAFT,
        nullable=False
    )
    target_type: Mapped[Optional[ExamTargetType]] = mapped_column(
        SQLEnum(ExamTargetType, name="exam_target_type_enum", create_type=True),
        nullable=True
    )
    target_department_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("departments.id", ondelete="SET NULL"),
        nullable=True,
        index=True
    )
    target_year_of_study: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True
    )
    target_section_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sections.id", ondelete="SET NULL"),
        nullable=True,
        index=True
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
    creator: Mapped["User"] = relationship(
        "User",
        back_populates="exams_created",
        foreign_keys=[created_by]
    )
    exam_questions: Mapped[List["ExamQuestion"]] = relationship(
        "ExamQuestion",
        back_populates="exam",
        cascade="all, delete-orphan",
        order_by="ExamQuestion.question_order"
    )
    sessions: Mapped[List["ExamSession"]] = relationship(
        "ExamSession",
        back_populates="exam",
        foreign_keys="[ExamSession.exam_id]"
    )
    cross_student_analyses: Mapped[List["CrossStudentAnalysis"]] = relationship(
        "CrossStudentAnalysis",
        back_populates="exam",
        cascade="all, delete-orphan"
    )
    target_department: Mapped[Optional["Department"]] = relationship(
        "Department",
        foreign_keys=[target_department_id]
    )
    target_section: Mapped[Optional["Section"]] = relationship(
        "Section",
        foreign_keys=[target_section_id]
    )
    target_students: Mapped[List["ExamTargetStudent"]] = relationship(
        "ExamTargetStudent",
        back_populates="exam",
        cascade="all, delete-orphan"
    )

    @property
    def questions(self) -> List["ExamQuestion"]:
        return self.exam_questions


class ExamQuestion(Base):
    __tablename__ = "exam_questions"
    __table_args__ = (
        UniqueConstraint("exam_id", "question_id", name="uq_exam_question_pair"),
        UniqueConstraint("exam_id", "question_order", name="uq_exam_question_order"),
        CheckConstraint("marks_override IS NULL OR marks_override > 0", name="ck_exam_question_marks_override"),
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
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    question_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    marks_override: Mapped[Optional[float]] = mapped_column(
        Numeric(5, 2),
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
        back_populates="exam_questions"
    )
    question: Mapped["Question"] = relationship(
        "Question",
        back_populates="exam_questions"
    )


class ExamTargetStudent(Base):
    __tablename__ = "exam_target_students"
    __table_args__ = (
        UniqueConstraint("exam_id", "student_id", name="uq_exam_target_student_pair"),
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
    student_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    exam: Mapped["Exam"] = relationship("Exam", back_populates="target_students")
    student: Mapped["User"] = relationship("User")

