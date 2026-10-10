import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import require_roles
from app.schemas.integrity import PaginatedExamIntegrityResponse, SessionIntegrityDetailResponse
from app.schemas.student_integrity import (
    StudentIntegrityOverviewResponse,
    StudentSessionIntegrityDetailResponse,
)
from app.services.integrity_service import integrity_service

router = APIRouter()


@router.get("/student/integrity", response_model=StudentIntegrityOverviewResponse)
def get_student_integrity_overview(
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """
    Returns authenticated student's aggregated integrity metrics and exam-wise integrity history.
    Strictly restricted to the authenticated student's own records.
    """
    return integrity_service.get_student_integrity_overview(db=db, current_user=current_user)


@router.get("/student/integrity/{session_id}", response_model=StudentSessionIntegrityDetailResponse)
@router.get("/student/integrity/sessions/{session_id}", response_model=StudentSessionIntegrityDetailResponse)
def get_student_session_integrity_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """
    Returns detailed proctoring and integrity assessment for an authenticated student's exam session.
    Strictly restricted to sessions owned by the authenticated student.
    """
    return integrity_service.get_student_session_integrity_detail(
        db=db, session_id=session_id, current_user=current_user
    )



@router.get("/exams/{exam_id}/integrity", response_model=PaginatedExamIntegrityResponse)
def get_exam_integrity_summary(
    exam_id: uuid.UUID,
    search: Optional[str] = Query(None, description="Search student by name or email"),
    risk_level: Optional[str] = Query(None, description="Filter by risk level: LOW, MODERATE, HIGH"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated exam-level integrity score summary, risk distribution,
    and filterable/paginated student session integrity assessments.
    Access restricted to Examiner (exam owner) and Admin.
    """
    return integrity_service.get_exam_integrity_summary(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        risk_level_filter=risk_level,
    )


@router.get("/exams/{exam_id}/sessions/{session_id}/integrity", response_model=SessionIntegrityDetailResponse)
def get_session_integrity_detail(
    exam_id: uuid.UUID,
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Returns detailed multi-signal integrity assessment, evidence items, and chronological timeline
    for a specific student exam session.
    Access restricted to Examiner (exam owner) and Admin.
    """
    return integrity_service.get_session_integrity_detail(
        db=db,
        exam_id=exam_id,
        session_id=session_id,
        current_user=current_user,
    )
