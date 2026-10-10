import uuid
from datetime import datetime
from typing import List, Optional, TYPE_CHECKING
from sqlalchemy import (
    String, Text, DateTime, Numeric, ForeignKey, UniqueConstraint, func
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.exam_session import ExamSession
    from app.models.question import Question, QuestionOption
    from app.models.evaluation import EvaluationResult


class StudentAnswer(Base):
    __tablename__ = "student_answers"
    __table_args__ = (
        UniqueConstraint("session_id", "question_id", name="uq_session_question_answer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("exam_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("questions.id", ondelete="RESTRICT"),
        nullable=False,
        index=True
    )
    text_answer: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    answer_image_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True
    )
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    ocr_status: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
        default="OCR_NOT_REQUIRED"
    )
    ocr_confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    ocr_processed_at: Mapped[Optional[datetime]] = mapped_column(
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
        back_populates="answers"
    )
    question: Mapped["Question"] = relationship(
        "Question",
        back_populates="answers"
    )
    selected_options: Mapped[List["AnswerSelectedOption"]] = relationship(
        "AnswerSelectedOption",
        back_populates="answer",
        cascade="all, delete-orphan"
    )
    evaluation_result: Mapped[Optional["EvaluationResult"]] = relationship(
        "EvaluationResult",
        back_populates="answer",
        uselist=False,
        cascade="all, delete-orphan"
    )


class AnswerSelectedOption(Base):
    __tablename__ = "answer_selected_options"
    __table_args__ = (
        UniqueConstraint("answer_id", "option_id", name="uq_answer_selected_option"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4
    )
    answer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("student_answers.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    option_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("question_options.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    answer: Mapped["StudentAnswer"] = relationship(
        "StudentAnswer",
        back_populates="selected_options"
    )
    option: Mapped["QuestionOption"] = relationship(
        "QuestionOption"
    )
