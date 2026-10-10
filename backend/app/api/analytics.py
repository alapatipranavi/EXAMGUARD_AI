import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import require_roles
from app.schemas.analytics import ExamAnalyticsResponse
from app.services.analytics_service import analytics_service

router = APIRouter()


@router.get("/exams/{exam_id}/analytics", response_model=ExamAnalyticsResponse)
def get_exam_analytics(
    exam_id: uuid.UUID,
    search: Optional[str] = Query(None, description="Search student performance by name or email"),
    pass_fail: Optional[str] = Query(None, description="Filter student performance by PASSED or FAILED"),
    session_status: Optional[str] = Query(None, description="Filter student performance by evaluation status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Returns server-side aggregated performance analytics, score distribution, question accuracy,
    topic/difficulty performance, and pending reviews for an exam owned by the examiner.
    """
    return analytics_service.get_exam_analytics(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        search=search,
        pass_fail=pass_fail,
        session_status=session_status,
    )
