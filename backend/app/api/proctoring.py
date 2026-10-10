import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.proctoring import ProctoringEventType, EventSeverity
from app.core.dependencies import get_current_user, require_roles
from app.schemas.proctoring import (
    ProctoringEventCreate,
    ProctoringEventResponse,
    PaginatedExaminerProctoringEvents,
)
from app.services.proctoring_service import proctoring_service

router = APIRouter()


@router.post("/exam-sessions/{session_id}/proctoring-events", response_model=ProctoringEventResponse)
@router.post("/student/sessions/{session_id}/proctoring-events", response_model=ProctoringEventResponse)
def record_proctoring_event(
    session_id: uuid.UUID,
    payload: ProctoringEventCreate,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Records an observable proctoring event for an active student exam session."""
    return proctoring_service.record_student_event(
        db, session_id=session_id, input_data=payload, current_user=current_user
    )


@router.get("/exams/{exam_id}/proctoring-events", response_model=PaginatedExaminerProctoringEvents)
def list_exam_proctoring_events(
    exam_id: uuid.UUID,
    session_id: Optional[uuid.UUID] = Query(None, description="Filter by session ID"),
    student_id: Optional[uuid.UUID] = Query(None, description="Filter by student ID"),
    event_type: Optional[ProctoringEventType] = Query(None, description="Filter by event type"),
    severity: Optional[EventSeverity] = Query(None, description="Filter by event severity"),
    session_status: Optional[str] = Query(None, description="Filter by session status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists proctoring events for an exam owned by the examiner."""
    return proctoring_service.list_examiner_exam_events(
        db,
        exam_id=exam_id,
        current_user=current_user,
        session_id=session_id,
        student_id=student_id,
        event_type=event_type,
        severity=severity,
        session_status=session_status,
        page=page,
        page_size=page_size,
    )
