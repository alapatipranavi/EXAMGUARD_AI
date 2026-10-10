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
    from app.models.exam import ExamQuestion
    from app.models.answer import StudentAnswer


class QuestionType(str, enum.Enum):
    MCQ = "MCQ"
    MULTI_SELECT = "MULTI_SELECT"
    SHORT_ANSWER = "SHORT_ANSWER"
    LONG_ANSWER = "LONG_ANSWER"
    HANDWRITTEN = "HANDWRITTEN"


class DifficultyLevel(str, enum.Enum):
    EASY = "EASY"
    MEDIUM = "MEDIUM"
    HARD = "HARD"


class QuestionSource(str, enum.Enum):
    MANUAL = "MANUAL"
    AI_GENERATED = "AI_GENERATED"
    CSV_IMPORT = "CSV_IMPORT"
    PDF_IMPORT = "PDF_IMPORT"


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (
        CheckConstraint("marks > 0", name="ck_question_positive_marks"),
        CheckConstraint("negative_marks >= 0", name="ck_question_non_negative_negative_marks"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    question_type: Mapped[QuestionType] = mapped_column(
        SQLEnum(QuestionType, name="question_type_enum", create_type=True),
        nullable=False
    )
    subject: Mapped[str] = mapped_column(
        String(100),
        index=True,
        nullable=False
    )
    topic: Mapped[Optional[str]] = mapped_column(
        String(100),
        index=True,
        nullable=True
    )
    difficulty: Mapped[DifficultyLevel] = mapped_column(
        SQLEnum(DifficultyLevel, name="difficulty_level_enum", create_type=True),
        default=DifficultyLevel.MEDIUM,
        nullable=False
    )
    marks: Mapped[float] = mapped_column(
        Numeric(5, 2),
        nullable=False
    )
    negative_marks: Mapped[float] = mapped_column(
        Numeric(5, 2),
        default=0.00,
        nullable=False
    )
    model_answer: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    source: Mapped[QuestionSource] = mapped_column(
        SQLEnum(QuestionSource, name="question_source_enum", create_type=True),
        default=QuestionSource.MANUAL,
        nullable=False
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
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
    creator: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="questions_created",
        foreign_keys=[created_by]
    )
    options: Mapped[List["QuestionOption"]] = relationship(
        "QuestionOption",
        back_populates="question",
        cascade="all, delete-orphan",
        order_by="QuestionOption.option_order"
    )
    exam_questions: Mapped[List["ExamQuestion"]] = relationship(
        "ExamQuestion",
        back_populates="question",
        foreign_keys="[ExamQuestion.question_id]"
    )
    answers: Mapped[List["StudentAnswer"]] = relationship(
        "StudentAnswer",
        back_populates="question",
        foreign_keys="[StudentAnswer.question_id]"
    )


class QuestionOption(Base):
    __tablename__ = "question_options"
    __table_args__ = (
        UniqueConstraint("question_id", "option_order", name="uq_question_option_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    option_text: Mapped[str] = mapped_column(
        Text,
        nullable=False
    )
    option_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False
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
    question: Mapped["Question"] = relationship(
        "Question",
        back_populates="options"
    )
