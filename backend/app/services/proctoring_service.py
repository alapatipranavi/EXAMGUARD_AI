import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from datetime import datetime, timezone

from app.models.user import User, UserRole
from app.models.exam import Exam
from app.models.exam_session import ExamSession, SessionStatus
from app.models.proctoring import ProctoringEvent, ProctoringEventType, EventSeverity
from app.repositories.proctoring_repository import proctoring_repository
from app.repositories.student_exam_repository import student_exam_repository
from app.repositories.exam_repository import ExamRepository
from app.schemas.proctoring import (
    ProctoringEventCreate,
    ProctoringEventResponse,
    ExaminerProctoringEventItem,
    PaginatedExaminerProctoringEvents,
    ExamProctoringSummary,
)


class ProctoringService:
    def record_student_event(
        self,
        db: Session,
        session_id: uuid.UUID,
        input_data: ProctoringEventCreate,
        current_user: User,
    ) -> ProctoringEventResponse:
        """Records a proctoring event for an active student exam session."""
        if current_user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only students can record proctoring events.",
            )

        session = proctoring_repository.get_session_for_update(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only record events for your own exam session.",
            )

        now = datetime.now(timezone.utc)
        expires_at = session.expires_at
        if expires_at and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=timezone.utc)

        if session.status != SessionStatus.IN_PROGRESS or (expires_at and expires_at <= now):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Proctoring events can only be recorded for active IN_PROGRESS exam sessions.",
            )

        is_tab_hidden = (input_data.event_type in [ProctoringEventType.TAB_HIDDEN, ProctoringEventType.TAB_SWITCH])

        # 30-second deduplication check for non-TAB_HIDDEN events
        if not is_tab_hidden and proctoring_repository.is_duplicate_event(db, session_id, input_data.event_type, window_seconds=30):
            last_event = proctoring_repository.get_last_event_by_type(db, session_id, input_data.event_type)
            if last_event:
                resp = ProctoringEventResponse.model_validate(last_event)
                meta = session.session_metadata or {}
                resp.tab_switch_count = int(meta.get("tab_switch_count", 0))
                resp.max_tab_switches = session.exam.max_tab_switches
                resp.is_flagged = session.is_flagged
                resp.flag_reason = session.flag_reason
                resp.auto_submitted = (session.status == SessionStatus.AUTO_SUBMITTED)
                return resp

        event_meta = input_data.event_metadata or input_data.metadata_json or {}
        severity = input_data.severity or EventSeverity.MEDIUM

        meta_dict = dict(session.session_metadata or {})
        current_tab_switches = int(meta_dict.get("tab_switch_count", 0))

        if is_tab_hidden:
            current_tab_switches += 1
            meta_dict["tab_switch_count"] = current_tab_switches
            session.session_metadata = meta_dict

        max_allowed = session.exam.max_tab_switches
        auto_submitted = False

        if is_tab_hidden and current_tab_switches > max_allowed:
            session.status = SessionStatus.AUTO_SUBMITTED
            session.submitted_at = now
            session.is_flagged = True
            session.flag_reason = "TAB_SWITCH_LIMIT_EXCEEDED"
            auto_submitted = True

        event = proctoring_repository.create_event(
            db,
            session_id=session_id,
            event_type=input_data.event_type,
            severity=severity,
            metadata_json=event_meta,
            duration_seconds=input_data.duration_seconds,
        )

        if auto_submitted:
            proctoring_repository.create_event(
                db,
                session_id=session_id,
                event_type=ProctoringEventType.TAB_SWITCH_LIMIT_EXCEEDED,
                severity=EventSeverity.HIGH,
                metadata_json={
                    "tab_switch_count": current_tab_switches,
                    "max_tab_switches": max_allowed,
                    "reason": "Exceeded maximum allowed tab switches",
                },
            )

        resp = ProctoringEventResponse.model_validate(event)
        resp.auto_submitted = auto_submitted
        resp.is_flagged = session.is_flagged
        resp.flag_reason = session.flag_reason
        resp.tab_switch_count = current_tab_switches
        resp.max_tab_switches = max_allowed
        return resp

    def get_exam_proctoring_events(
        self,
        db: Session,
        exam_id: uuid.UUID,
        current_user: User,
        session_id: Optional[uuid.UUID] = None,
        student_id: Optional[uuid.UUID] = None,
        event_type: Optional[ProctoringEventType] = None,
        severity: Optional[EventSeverity] = None,
        session_status: Optional[str] = None,
        page: int = 1,
        page_size: int = 50,
    ) -> PaginatedExaminerProctoringEvents:
        """Retrieves proctoring events for an exam. Only accessible by the exam owner examiner or admin."""
        if current_user.role not in [UserRole.EXAMINER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Examiner or Admin role required.",
            )

        exam = ExamRepository.get_exam_by_id(db, exam_id)

        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found.",
            )

        if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You can only view proctoring events for your own exams.",
            )

        events, total = proctoring_repository.list_events_for_exam(
            db,
            exam_id=exam_id,
            session_id=session_id,
            student_id=student_id,
            event_type=event_type,
            severity=severity,
            session_status=session_status,
            page=page,
            page_size=page_size,
        )

        items = []
        for ev in events:
            sess = ev.session
            student = sess.student if sess else None
            student_name = f"{student.first_name} {student.last_name}" if student else "Unknown Student"
            student_email = student.email if student else "unknown@examguard.ai"

            meta = sess.session_metadata or {} if sess else {}
            tab_switches = int(meta.get("tab_switch_count", 0))
            max_switches = sess.exam.max_tab_switches if sess and sess.exam else 3
            sess_stat = sess.status.value if sess else "IN_PROGRESS"

            items.append(
                ExaminerProctoringEventItem(
                    id=ev.id,
                    session_id=ev.session_id,
                    student_id=student.id if student else (sess.student_id if sess else ev.session_id),
                    student_email=student_email,
                    student_name=student_name,
                    event_type=ev.event_type,
                    severity=ev.severity,
                    occurred_at=ev.occurred_at,
                    duration_seconds=float(ev.duration_seconds) if ev.duration_seconds is not None else None,
                    event_metadata=ev.event_metadata,
                    tab_switch_count=tab_switches,
                    max_tab_switches=max_switches,
                    session_status=sess_stat,
                    is_flagged=sess.is_flagged if sess else False,
                    flag_reason=sess.flag_reason if sess else None,
                )
            )

        summary_dict = proctoring_repository.get_exam_proctoring_summary(db, exam_id)
        summary = ExamProctoringSummary(**summary_dict)

        total_pages = (total + page_size - 1) // page_size if total > 0 else 1
        return PaginatedExaminerProctoringEvents(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary,
        )

    list_examiner_exam_events = get_exam_proctoring_events


proctoring_service = ProctoringService()
