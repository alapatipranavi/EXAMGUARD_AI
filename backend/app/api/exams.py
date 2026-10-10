import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.exam import ExamStatus
from app.schemas.exam import (
    ExamCreate, ExamUpdate, ExamResponse, PaginatedExamResponse
)
from app.services.exam_service import exam_service
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post("", response_model=ExamResponse, status_code=status.HTTP_201_CREATED)
def create_exam(
    exam_data: ExamCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new Exam in DRAFT status for the authenticated Examiner."""
    return exam_service.create_exam(db, exam_data, current_user)


@router.get("", response_model=PaginatedExamResponse)
def list_exams(
    search: Optional[str] = Query(None, description="Search across title, subject, description"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    status: Optional[ExamStatus] = Query(None, description="Filter by exam status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists exams created by the authenticated Examiner."""
    return exam_service.list_exams(
        db=db,
        current_user=current_user,
        search=search,
        subject=subject,
        status_filter=status,
        page=page,
        page_size=page_size
    )


@router.get("/{exam_id}", response_model=ExamResponse)
def get_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches exam detail owned by the authenticated Examiner."""
    return exam_service.get_exam(db, exam_id, current_user)


@router.patch("/{exam_id}", response_model=ExamResponse)
def update_exam(
    exam_id: uuid.UUID,
    update_data: ExamUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates fields and selected questions for a DRAFT exam."""
    return exam_service.update_exam(db, exam_id, update_data, current_user)


@router.post("/{exam_id}/publish", response_model=ExamResponse)
def publish_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Validates and publishes a DRAFT exam."""
    return exam_service.publish_exam(db, exam_id, current_user)


@router.post("/{exam_id}/archive", response_model=ExamResponse)
def archive_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Archives an exam (soft delete)."""
    return exam_service.archive_exam(db, exam_id, current_user)


@router.post("/{exam_id}/unarchive", response_model=ExamResponse)
def unarchive_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Unarchives an archived exam and reverts its status to DRAFT."""
    return exam_service.unarchive_exam(db, exam_id, current_user)


@router.delete("/{exam_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_exam(
    exam_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Permanently deletes a DRAFT exam."""
    exam_service.delete_exam(db, exam_id, current_user)
    return None
