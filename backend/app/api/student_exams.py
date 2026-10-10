import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import get_current_user, require_roles
from app.schemas.student_exam import (
    PaginatedStudentExamResponse,
    StudentExamDetail,
    ExamSessionResponse,
    StudentAnswerSaveInput,
    HandwrittenAnswerInput,
    HandwrittenAnswerProcessResponse,
    ReviewToggleInput,
    StudentAnswerResponse,
    StudentDashboardResponse,
)
from app.services.student_exam_service import student_exam_service

router = APIRouter()


@router.get("/student/dashboard", response_model=StudentDashboardResponse)
def get_student_dashboard(
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Retrieves complete student dashboard data including summary, academic profile, active session, targeted exams, and recent results."""
    return student_exam_service.get_student_dashboard(db, current_user=current_user)


@router.get("/student/exams", response_model=PaginatedStudentExamResponse)
def list_student_exams(
    search: Optional[str] = Query(None, description="Search by title, subject, description"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Lists published exams available to the student."""
    return student_exam_service.list_student_exams(
        db, current_user=current_user, search=search, subject=subject, page=page, page_size=page_size
    )


@router.get("/student/exams/{exam_id}", response_model=StudentExamDetail)
def get_student_exam_detail(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Retrieves student-safe preview details for a published exam."""
    return student_exam_service.get_student_exam_detail(db, exam_id=exam_id, current_user=current_user)


@router.post("/student/exams/{exam_id}/start", response_model=ExamSessionResponse)
def start_or_resume_exam_session(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Starts a new exam session or resumes an existing active session."""
    return student_exam_service.start_or_resume_session(db, exam_id=exam_id, current_user=current_user)


# Session detail endpoints (supporting both /exam-sessions and /student/sessions)
@router.get("/exam-sessions/{session_id}", response_model=ExamSessionResponse)
@router.get("/student/sessions/{session_id}", response_model=ExamSessionResponse)
def get_session_details(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Retrieves current active exam session state and remaining time."""
    return student_exam_service.get_session_details(db, session_id=session_id, current_user=current_user)


@router.put("/exam-sessions/{session_id}/answers/{question_id}", response_model=StudentAnswerResponse)
@router.put("/student/sessions/{session_id}/answers/{question_id}", response_model=StudentAnswerResponse)
def save_student_answer(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: StudentAnswerSaveInput,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Saves or updates a student answer for a specific question in an active session."""
    return student_exam_service.save_answer(
        db, session_id=session_id, question_id=question_id, input_data=payload, current_user=current_user
    )


@router.put("/exam-sessions/{session_id}/questions/{question_id}/review", response_model=ExamSessionResponse)
@router.put("/student/sessions/{session_id}/questions/{question_id}/review", response_model=ExamSessionResponse)
def toggle_mark_for_review(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: ReviewToggleInput,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Toggles a question's marked-for-review state in an active session."""
    return student_exam_service.toggle_mark_for_review(
        db, session_id=session_id, question_id=question_id, input_data=payload, current_user=current_user
    )


@router.post("/exam-sessions/{session_id}/answers/{question_id}/handwritten", response_model=HandwrittenAnswerProcessResponse)
@router.post("/student/sessions/{session_id}/answers/{question_id}/handwritten", response_model=HandwrittenAnswerProcessResponse)
def submit_handwritten_answer(
    session_id: uuid.UUID,
    question_id: uuid.UUID,
    payload: HandwrittenAnswerInput,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Processes uploaded handwritten answer image: stores artifact, runs OCR, and triggers evaluation pipeline."""
    return student_exam_service.process_handwritten_answer(
        db, session_id=session_id, question_id=question_id, input_data=payload, current_user=current_user
    )


@router.post("/exam-sessions/{session_id}/submit", response_model=ExamSessionResponse)
@router.post("/student/sessions/{session_id}/submit", response_model=ExamSessionResponse)
def submit_exam_session(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Submits an active exam session and locks answers."""
    return student_exam_service.submit_exam_session(db, session_id=session_id, current_user=current_user)
