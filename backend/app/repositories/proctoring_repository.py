import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple, Any, Dict
from sqlalchemy import select, func
from sqlalchemy.orm import Session, joinedload

from app.models.proctoring import ProctoringEvent, ProctoringEventType, EventSeverity
from app.models.exam_session import ExamSession, SessionStatus
from app.models.user import User


class ProctoringRepository:
    def get_session_for_update(self, db: Session, session_id: uuid.UUID) -> Optional[ExamSession]:
        """Locks the ExamSession row in the database using FOR UPDATE for concurrency-safe atomic operations."""
        stmt = (
            select(ExamSession)
            .where(ExamSession.id == session_id)
            .with_for_update()
        )
        return db.scalar(stmt)

    def create_event(
        self,
        db: Session,
        session_id: uuid.UUID,
        event_type: ProctoringEventType,
        severity: EventSeverity = EventSeverity.MEDIUM,
        metadata_json: Optional[Dict[str, Any]] = None,
        duration_seconds: Optional[float] = None,
    ) -> ProctoringEvent:
        """Creates a new proctoring event."""
        event = ProctoringEvent(
            session_id=session_id,
            event_type=event_type,
            severity=severity,
            event_metadata=metadata_json or {},
            duration_seconds=duration_seconds,
            occurred_at=datetime.now(timezone.utc),
        )

        db.add(event)
        db.commit()
        db.refresh(event)
        return event

    def get_recent_identical_event(
        self,
        db: Session,
        session_id: uuid.UUID,
        event_type: ProctoringEventType,
        seconds_window: int = 30,
    ) -> Optional[ProctoringEvent]:
        """Checks if an identical event type was logged for this session within seconds_window."""
        cutoff = datetime.now(timezone.utc) - timedelta(seconds=seconds_window)
        stmt = (
            select(ProctoringEvent)
            .where(ProctoringEvent.session_id == session_id)
            .where(ProctoringEvent.event_type == event_type)
            .where(ProctoringEvent.occurred_at >= cutoff)
            .order_by(ProctoringEvent.occurred_at.desc())
        )
        return db.scalar(stmt)

    def is_duplicate_event(
        self,
        db: Session,
        session_id: uuid.UUID,
        event_type: ProctoringEventType,
        window_seconds: int = 30,
    ) -> bool:
        return self.get_recent_identical_event(db, session_id, event_type, window_seconds) is not None

    def get_last_event_by_type(
        self,
        db: Session,
        session_id: uuid.UUID,
        event_type: ProctoringEventType,
    ) -> Optional[ProctoringEvent]:
        return self.get_recent_identical_event(db, session_id, event_type, seconds_window=86400)

    def list_events_for_exam(
        self,
        db: Session,
        exam_id: uuid.UUID,
        session_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        event_type: Optional[ProctoringEventType] = None,
        severity: Optional[EventSeverity] = None,
        session_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 20,
    ) -> Tuple[List[ProctoringEvent], int]:
        """Fetches proctoring events for a specific exam owned by an examiner with filtering options."""
        stmt = (
            select(ProctoringEvent)
            .join(ProctoringEvent.session)
            .options(
                joinedload(ProctoringEvent.session).joinedload(ExamSession.student)
            )
            .where(ExamSession.exam_id == exam_id)
        )

        if session_id:
            stmt = stmt.where(ProctoringEvent.session_id == session_id)

        if student_id:
            stmt = stmt.where(ExamSession.student_id == student_id)

        if event_type:
            stmt = stmt.where(ProctoringEvent.event_type == event_type)

        if severity:
            stmt = stmt.where(ProctoringEvent.severity == severity)

        if session_status:
            if session_status.upper() == "FLAGGED":
                stmt = stmt.where(ExamSession.is_flagged == True)
            elif session_status.upper() in SessionStatus.__members__:
                stmt = stmt.where(ExamSession.status == SessionStatus[session_status.upper()])

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(ProctoringEvent.occurred_at.desc()).offset((page - 1) * page_size).limit(page_size)
        events = list(db.scalars(stmt).all())

        return events, total

    def get_exam_proctoring_summary(self, db: Session, exam_id: uuid.UUID) -> Dict[str, int]:
        """Calculates factual proctoring summary metrics for an exam."""
        total_events_stmt = (
            select(func.count(ProctoringEvent.id))
            .join(ProctoringEvent.session)
            .where(ExamSession.exam_id == exam_id)
        )
        total_events = db.scalar(total_events_stmt) or 0

        students_stmt = (
            select(func.count(func.distinct(ExamSession.student_id)))
            .where(ExamSession.exam_id == exam_id)
        )
        students_monitored = db.scalar(students_stmt) or 0

        flagged_stmt = (
            select(func.count(ExamSession.id))
            .where(ExamSession.exam_id == exam_id)
            .where(ExamSession.is_flagged == True)
        )
        flagged_sessions = db.scalar(flagged_stmt) or 0

        auto_sub_stmt = (
            select(func.count(ExamSession.id))
            .where(ExamSession.exam_id == exam_id)
            .where(ExamSession.status == SessionStatus.AUTO_SUBMITTED)
        )
        auto_submitted_sessions = db.scalar(auto_sub_stmt) or 0

        return {
            "total_events": total_events,
            "students_monitored": students_monitored,
            "flagged_sessions": flagged_sessions,
            "auto_submitted_sessions": auto_submitted_sessions,
        }


proctoring_repository = ProctoringRepository()
