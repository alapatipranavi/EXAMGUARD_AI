import uuid
import math
from typing import Optional
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.exam import ExamStatus, ExamTargetType
from app.core.dependencies import require_roles
from app.core.security import hash_password
from app.repositories.user_repository import user_repository
from app.schemas.auth import UserResponse
from app.schemas.admin import (
    AdminUserCreate,
    AdminUserStatusUpdate,
    AdminUserRoleUpdate,
    PaginatedUserResponse,
    AdminDashboardResponse,
)
from app.schemas.admin_student import (
    PaginatedAdminStudentResponse,
    AdminStudentDetailResponse,
)
from app.schemas.admin_examiner import (
    PaginatedAdminExaminerResponse,
    AdminExaminerDetailResponse,
)
from app.schemas.admin_exam import (
    PaginatedAdminExamResponse,
    AdminExamDetailResponse,
)
from app.services.admin_service import admin_service

router = APIRouter()


@router.get("/admin/dashboard", response_model=AdminDashboardResponse)
def get_admin_dashboard(
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieves system administration metrics, user breakdown, academic structure, exam overview, platform activity, and health status (Admin only)."""
    return admin_service.get_admin_dashboard(db, current_user=current_user)


# Support both GET /admin/users and GET /users for Admin User Management
@router.get("/admin/users", response_model=PaginatedUserResponse)
@router.get("/users", response_model=PaginatedUserResponse)
def list_users(
    search: Optional[str] = Query(None, description="Search by name or email"),
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    is_active: Optional[bool] = Query(None, description="Filter by account status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists system users with filtering and pagination (Admin only)."""
    query = db.query(User)

    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            or_(
                User.first_name.ilike(search_fmt),
                User.last_name.ilike(search_fmt),
                User.email.ilike(search_fmt),
            )
        )

    if role is not None:
        query = query.filter(User.role == role)

    if is_active is not None:
        query = query.filter(User.is_active == is_active)

    total = query.count()
    users = query.order_by(User.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedUserResponse(
        items=[UserResponse.model_validate(u) for u in users],
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


# Support both POST /admin/users and POST /users for Admin Provisioning
@router.post("/admin/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
@router.post("/users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user_by_admin(
    payload: AdminUserCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Provisions a new user account (EXAMINER or STUDENT) by an Admin."""
    if payload.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin accounts cannot be provisioned via user management API.",
        )

    existing_user = user_repository.get_by_email(db, payload.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email address is already registered.",
        )

    hashed_pwd = hash_password(payload.password)

    new_user = user_repository.create_user(
        db=db,
        email=payload.email,
        password_hash=hashed_pwd,
        first_name=payload.first_name,
        last_name=payload.last_name,
        role=payload.role,
    )

    return UserResponse.model_validate(new_user)


@router.put("/admin/users/{user_id}/status", response_model=UserResponse)
@router.put("/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: uuid.UUID,
    payload: AdminUserStatusUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Activates or deactivates a user account (Admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own active status.",
        )

    user = user_repository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    user.is_active = payload.is_active
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.put("/admin/users/{user_id}/role", response_model=UserResponse)
@router.put("/users/{user_id}/role", response_model=UserResponse)
def update_user_role(
    user_id: uuid.UUID,
    payload: AdminUserRoleUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Updates user role between STUDENT and EXAMINER (Admin only)."""
    if user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot modify your own role.",
        )

    if payload.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin roles cannot be assigned via user management API.",
        )

    user = user_repository.get_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if user.role == UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin account roles cannot be modified.",
        )

    user.role = payload.role
    db.commit()
    db.refresh(user)

    return UserResponse.model_validate(user)


@router.get("/admin/students", response_model=PaginatedAdminStudentResponse)
@router.get("/students", response_model=PaginatedAdminStudentResponse)
def list_students(
    search: Optional[str] = Query(None, description="Search by student name or email"),
    college_id: Optional[uuid.UUID] = Query(None, description="Filter by college"),
    department_id: Optional[uuid.UUID] = Query(None, description="Filter by department"),
    year_of_study: Optional[int] = Query(None, ge=1, le=4, description="Filter by year of study"),
    section_id: Optional[uuid.UUID] = Query(None, description="Filter by section"),
    is_active: Optional[bool] = Query(None, description="Filter by account status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists student accounts with academic hierarchy filters, search, and pagination (Admin only)."""
    return admin_service.list_students(
        db=db,
        current_user=current_user,
        search=search,
        college_id=college_id,
        department_id=department_id,
        year_of_study=year_of_study,
        section_id=section_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/students/{student_id}", response_model=AdminStudentDetailResponse)
@router.get("/students/{student_id}", response_model=AdminStudentDetailResponse)
def get_student_detail(
    student_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieves full student details and lightweight exam activity metrics (Admin only)."""
    return admin_service.get_student_detail(
        db=db,
        current_user=current_user,
        student_id=student_id,
    )


@router.get("/admin/examiners", response_model=PaginatedAdminExaminerResponse)
@router.get("/examiners", response_model=PaginatedAdminExaminerResponse)
def list_examiners(
    search: Optional[str] = Query(None, description="Search by examiner name or email"),
    college_id: Optional[uuid.UUID] = Query(None, description="Filter by assigned college"),
    is_active: Optional[bool] = Query(None, description="Filter by account status"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists examiner accounts with college filter, status filter, search, and pagination (Admin only)."""
    return admin_service.list_examiners(
        db=db,
        current_user=current_user,
        search=search,
        college_id=college_id,
        is_active=is_active,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/examiners/{examiner_id}", response_model=AdminExaminerDetailResponse)
@router.get("/examiners/{examiner_id}", response_model=AdminExaminerDetailResponse)
def get_examiner_detail(
    examiner_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieves full examiner details and examination activity metrics (Admin only)."""
    return admin_service.get_examiner_detail(
        db=db,
        current_user=current_user,
        examiner_id=examiner_id,
    )


@router.get("/admin/exams", response_model=PaginatedAdminExamResponse)
@router.get("/exams/admin", response_model=PaginatedAdminExamResponse)
def list_exams(
    search: Optional[str] = Query(None, description="Search by exam title, subject, or examiner name/email"),
    subject: Optional[str] = Query(None, description="Filter by subject"),
    examiner_id: Optional[uuid.UUID] = Query(None, description="Filter by examiner"),
    college_id: Optional[uuid.UUID] = Query(None, description="Filter by examiner's college"),
    status: Optional[ExamStatus] = Query(None, description="Filter by exam status"),
    target_type: Optional[ExamTargetType] = Query(None, description="Filter by audience target type"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists all platform exams with institution-wide filters and metrics (Admin only)."""
    return admin_service.list_exams(
        db=db,
        current_user=current_user,
        search=search,
        subject=subject,
        examiner_id=examiner_id,
        college_id=college_id,
        status_filter=status,
        target_type=target_type,
        page=page,
        page_size=page_size,
    )


@router.get("/admin/exams/{exam_id}", response_model=AdminExamDetailResponse)
@router.get("/exams/admin/{exam_id}", response_model=AdminExamDetailResponse)
def get_exam_detail(
    exam_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieves deep examination configuration, target breakdown, and student activity counts (Admin only)."""
    return admin_service.get_exam_detail(
        db=db,
        current_user=current_user,
        exam_id=exam_id,
    )



