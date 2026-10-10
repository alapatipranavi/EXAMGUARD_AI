import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.models.question import QuestionType, DifficultyLevel, QuestionSource
from app.schemas.question import (
    QuestionCreate, QuestionUpdate, QuestionResponse, PaginatedQuestionResponse
)
from app.services.question_service import question_service
from app.core.dependencies import get_current_user

router = APIRouter()


@router.post("", response_model=QuestionResponse, status_code=status.HTTP_201_CREATED)
def create_question(
    question_data: QuestionCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Creates a new question owned by the authenticated Examiner."""
    return question_service.create_question(db, question_data, current_user)


@router.get("", response_model=PaginatedQuestionResponse)
def list_questions(
    search: Optional[str] = Query(None, description="Search pattern across text, subject, topic"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    topic: Optional[str] = Query(None, description="Filter by topic"),
    question_type: Optional[QuestionType] = Query(None, description="Filter by question type"),
    difficulty: Optional[DifficultyLevel] = Query(None, description="Filter by difficulty"),
    source: Optional[QuestionSource] = Query(None, description="Filter by question source"),
    is_active: Optional[bool] = Query(None, description="Filter by active/archived status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(10, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Lists questions owned by current Examiner with database-level filtering and pagination."""
    return question_service.list_questions(
        db=db,
        current_user=current_user,
        search=search,
        subject=subject,
        topic=topic,
        question_type=question_type,
        difficulty=difficulty,
        source=source,
        is_active=is_active,
        page=page,
        page_size=page_size
    )


@router.get("/{question_id}", response_model=QuestionResponse)
def get_question(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Fetches question detail owned by the authenticated Examiner."""
    return question_service.get_question(db, question_id, current_user)


@router.patch("/{question_id}", response_model=QuestionResponse)
def update_question(
    question_id: uuid.UUID,
    update_data: QuestionUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Updates question fields or options for a question owned by the authenticated Examiner."""
    return question_service.update_question(db, question_id, update_data, current_user)


@router.delete("/{question_id}", response_model=QuestionResponse)
def archive_question(
    question_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Soft-deletes (archives) a question setting is_active = False."""
    return question_service.archive_question(db, question_id, current_user)
