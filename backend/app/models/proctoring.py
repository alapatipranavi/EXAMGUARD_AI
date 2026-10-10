import enum
import uuid
from datetime import datetime
from typing import Optional, Any, Dict, TYPE_CHECKING
from sqlalchemy import (
    DateTime, Numeric, ForeignKey, Enum as SQLEnum, CheckConstraint, Index, func
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.exam_session import ExamSession


class ProctoringEventType(str, enum.Enum):
    # Camera & Microphone
    CAMERA_PERMISSION_DENIED = "CAMERA_PERMISSION_DENIED"
    CAMERA_READY = "CAMERA_READY"
    CAMERA_DISCONNECTED = "CAMERA_DISCONNECTED"
    MICROPHONE_PERMISSION_DENIED = "MICROPHONE_PERMISSION_DENIED"
    MICROPHONE_READY = "MICROPHONE_READY"
    MICROPHONE_DISCONNECTED = "MICROPHONE_DISCONNECTED"

    # Face Presence
    FACE_NOT_DETECTED = "FACE_NOT_DETECTED"
    FACE_DETECTED = "FACE_DETECTED"
    MULTIPLE_FACES_DETECTED = "MULTIPLE_FACES_DETECTED"

    # Browser & Environment
    TAB_HIDDEN = "TAB_HIDDEN"
    TAB_VISIBLE = "TAB_VISIBLE"
    FULLSCREEN_ENTERED = "FULLSCREEN_ENTERED"
    FULLSCREEN_EXITED = "FULLSCREEN_EXITED"
    TAB_SWITCH_LIMIT_EXCEEDED = "TAB_SWITCH_LIMIT_EXCEEDED"

    # Object & Environment Detection
    PHONE_DETECTED = "PHONE_DETECTED"
    LAPTOP_DETECTED = "LAPTOP_DETECTED"
    BOOK_DETECTED = "BOOK_DETECTED"
    ADDITIONAL_PERSON_DETECTED = "ADDITIONAL_PERSON_DETECTED"
    OBJECT_DETECTION_STARTED = "OBJECT_DETECTION_STARTED"
    OBJECT_DETECTION_UNAVAILABLE = "OBJECT_DETECTION_UNAVAILABLE"

    # Pre-Exam Lifecycle Events
    PRE_EXAM_CHECK_STARTED = "PRE_EXAM_CHECK_STARTED"
    PRE_EXAM_CHECK_COMPLETED = "PRE_EXAM_CHECK_COMPLETED"

    # Behavioural Intelligence Events (Stage 9.3)
    QUESTION_VIEWED = "QUESTION_VIEWED"
    ANSWER_CREATED = "ANSWER_CREATED"
    ANSWER_CHANGED = "ANSWER_CHANGED"
    ANSWER_CLEARED = "ANSWER_CLEARED"
    QUESTION_NAVIGATION = "QUESTION_NAVIGATION"
    RAPID_ANSWER_CHANGES = "RAPID_ANSWER_CHANGES"
    UNUSUAL_TIMING = "UNUSUAL_TIMING"
    NAVIGATION_ANOMALY = "NAVIGATION_ANOMALY"
    BEHAVIOURAL_ANOMALY = "BEHAVIOURAL_ANOMALY"

    # Identity Verification Events (Stage 9.4)
    IDENTITY_VERIFIED = "IDENTITY_VERIFIED"
    IDENTITY_VERIFICATION_FAILED = "IDENTITY_VERIFICATION_FAILED"
    IDENTITY_MISMATCH_STARTED = "IDENTITY_MISMATCH_STARTED"
    IDENTITY_VERIFICATION_RESTORED = "IDENTITY_VERIFICATION_RESTORED"
    IDENTITY_MISMATCH_CONFIRMED = "IDENTITY_MISMATCH_CONFIRMED"


    # Compatibility Legacy Types
    FACE_MISSING = "FACE_MISSING"
    MULTIPLE_FACES = "MULTIPLE_FACES"
    GAZE_DEVIATION = "GAZE_DEVIATION"
    TAB_SWITCH = "TAB_SWITCH"
    WINDOW_BLUR = "WINDOW_BLUR"
    CAMERA_ISSUE = "CAMERA_ISSUE"
    LIGHTING_ISSUE = "LIGHTING_ISSUE"
    OTHER = "OTHER"


class EventSeverity(str, enum.Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"



class ProctoringEvent(Base):
    __tablename__ = "proctoring_events"
    __table_args__ = (
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_proctor_event_duration_positive"),
        CheckConstraint("confidence IS NULL OR (confidence >= 0 AND confidence <= 1)", name="ck_proctor_event_confidence_range"),
        Index("idx_proctoring_session_time", "session_id", "occurred_at"),
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
    event_type: Mapped[ProctoringEventType] = mapped_column(
        SQLEnum(ProctoringEventType, name="proctoring_event_type_enum", create_type=True),
        nullable=False
    )
    severity: Mapped[EventSeverity] = mapped_column(
        SQLEnum(EventSeverity, name="event_severity_enum", create_type=True),
        default=EventSeverity.MEDIUM,
        nullable=False
    )
    occurred_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True
    )
    duration_seconds: Mapped[Optional[float]] = mapped_column(
        Numeric(6, 2),
        nullable=True
    )
    confidence: Mapped[Optional[float]] = mapped_column(
        Numeric(3, 2),
        nullable=True
    )
    event_metadata: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )

    # Relationships
    session: Mapped["ExamSession"] = relationship(
        "ExamSession",
        back_populates="proctoring_events"
    )
