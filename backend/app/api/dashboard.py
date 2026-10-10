from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import get_current_user
from app.schemas.question import DashboardSummaryResponse
from app.repositories.question_repository import question_repository

router = APIRouter()


@router.get("/summary", response_model=DashboardSummaryResponse)
def get_dashboard_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Returns role-specific metrics for the authenticated user's dashboard."""
    role_name = current_user.role.value if isinstance(current_user.role, UserRole) else str(current_user.role)
    user_display_name = f"{current_user.first_name} {current_user.last_name}".strip()

    if current_user.role == UserRole.EXAMINER:
        stats = question_repository.get_examiner_stats(db, current_user.id)
    elif current_user.role == UserRole.ADMIN:
        stats = question_repository.get_admin_stats(db)
    else:  # STUDENT
        from app.repositories.student_exam_repository import student_exam_repository
        from app.models.exam_session import SessionStatus

        published_exams, _ = student_exam_repository.list_published_exams(db, page_size=1000)
        sessions = student_exam_repository.get_sessions_for_student(db, current_user.id)

        session_map = {}
        for s in sessions:
            if s.exam_id not in session_map or s.created_at > session_map[s.exam_id].created_at:
                session_map[s.exam_id] = s

        in_prog = 0
        completed = 0
        available = 0

        for exam in published_exams:
            s = session_map.get(exam.id)
            if not s:
                available += 1
            elif s.status in [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]:
                in_prog += 1
            else:
                completed += 1

        stats = {
            "upcoming_exams": available,
            "available_exams": available,
            "in_progress_exams": in_prog,
            "completed_exams": completed,
            "average_score": None,
            "integrity_status": "Clear / Good Standing",
        }

    return DashboardSummaryResponse(
        role=role_name,
        user_name=user_display_name,
        user_email=current_user.email,
        stats=stats,
        recent_activity=[]
    )
