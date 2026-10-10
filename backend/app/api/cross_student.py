import uuid
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.core.dependencies import require_roles
from app.schemas.cross_student import (
    PaginatedCrossStudentAnalysisResponse,
    CrossStudentPairDetailResponse,
)
from app.services.cross_student_service import cross_student_service

router = APIRouter()


@router.post("/exams/{exam_id}/cross-student-analysis/run")
def run_cross_student_analysis(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Executes pairwise cross-student integrity analysis across all submitted sessions for the specified exam.
    Idempotent operation: Clears and replaces previous analysis records for the exam.
    Access restricted to Examiner (exam owner) and Admin.
    """
    return cross_student_service.run_analysis_for_exam(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
    )


@router.get("/exams/{exam_id}/cross-student-analysis", response_model=PaginatedCrossStudentAnalysisResponse)
def get_cross_student_analysis_summary(
    exam_id: uuid.UUID,
    min_similarity: Optional[float] = Query(None, description="Filter pairs by minimum overall similarity score (0-100)"),
    cluster_id: Optional[str] = Query(None, description="Filter pairs by candidate cluster ID (e.g. Cluster 1)"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Returns aggregated exam-level cross-student similarity summary, candidate clusters,
    and filterable/paginated pairwise similarity records.
    Access restricted to Examiner (exam owner) and Admin.
    """
    return cross_student_service.get_analysis_summary(
        db=db,
        exam_id=exam_id,
        current_user=current_user,
        page=page,
        page_size=page_size,
        min_similarity=min_similarity,
        cluster_id=cluster_id,
    )


@router.get("/exams/{exam_id}/cross-student-analysis/{analysis_id}", response_model=CrossStudentPairDetailResponse)
def get_cross_student_pair_detail(
    exam_id: uuid.UUID,
    analysis_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """
    Returns detailed explainable evidence, question-level answer comparisons, and timing/behaviour
    sequences for a specific pairwise cross-student similarity record.
    Access restricted to Examiner (exam owner) and Admin.
    """
    return cross_student_service.get_pair_detail(
        db=db,
        exam_id=exam_id,
        analysis_id=analysis_id,
        current_user=current_user,
    )
