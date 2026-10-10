from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import require_roles
from app.schemas.examiner import ExaminerDashboardResponse
from app.services.examiner_service import examiner_service

router = APIRouter()


@router.get("/examiner/dashboard", response_model=ExaminerDashboardResponse)
def get_examiner_dashboard(
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieves complete Examiner dashboard data including summary, academic scope, exams, pending reviews, and recent activity."""
    return examiner_service.get_examiner_dashboard(db, current_user=current_user)
