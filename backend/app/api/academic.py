import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select, and_

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.academic import College, Department, Section
from app.core.dependencies import get_current_user, get_current_user_optional, require_roles
from app.repositories.academic_repository import academic_repository
from app.repositories.user_repository import user_repository
from app.schemas.auth import UserResponse
from app.schemas.academic import (
    CollegeCreate,
    CollegeUpdate,
    CollegeResponse,
    DepartmentCreate,
    DepartmentUpdate,
    DepartmentResponse,
    SectionCreate,
    SectionUpdate,
    SectionResponse,
    StudentAcademicProfileUpdate,
    UserCollegeUpdate,
)

router = APIRouter()


# ============================================================================
# 1. ADMIN COLLEGE ENDPOINTS
# ============================================================================

@router.get("/admin/colleges", response_model=List[CollegeResponse])
def list_colleges_admin(
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists all colleges (Admin only)."""
    return academic_repository.list_colleges(db, is_active=is_active)


@router.post("/admin/colleges", response_model=CollegeResponse, status_code=status.HTTP_201_CREATED)
def create_college(
    payload: CollegeCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Creates a new College (Admin only)."""
    existing = academic_repository.get_college_by_code(db, payload.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"College code '{payload.code.upper()}' already exists.",
        )
    return academic_repository.create_college(db, payload.name, payload.code)


@router.put("/admin/colleges/{college_id}", response_model=CollegeResponse)
def update_college(
    college_id: uuid.UUID,
    payload: CollegeUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Updates a College record (Admin only)."""
    college = academic_repository.get_college_by_id(db, college_id)
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="College not found.",
        )
    if payload.code and payload.code.upper() != college.code:
        existing = academic_repository.get_college_by_code(db, payload.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"College code '{payload.code.upper()}' already exists.",
            )
    return academic_repository.update_college(
        db, college, name=payload.name, code=payload.code, is_active=payload.is_active
    )


# ============================================================================
# 2. ADMIN DEPARTMENT ENDPOINTS
# ============================================================================

@router.get("/admin/departments", response_model=List[DepartmentResponse])
def list_departments_admin(
    college_id: Optional[uuid.UUID] = Query(None),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists departments with optional college filter (Admin only)."""
    return academic_repository.list_departments(db, college_id=college_id, is_active=is_active)


@router.post("/admin/departments", response_model=DepartmentResponse, status_code=status.HTTP_201_CREATED)
def create_department(
    payload: DepartmentCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Creates a new Department under a College (Admin only)."""
    college = academic_repository.get_college_by_id(db, payload.college_id)
    if not college:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent college not found.",
        )

    existing = academic_repository.get_department_by_code(db, payload.college_id, payload.code)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Department code '{payload.code.upper()}' already exists in this college.",
        )
    return academic_repository.create_department(db, payload.college_id, payload.name, payload.code)


@router.put("/admin/departments/{department_id}", response_model=DepartmentResponse)
def update_department(
    department_id: uuid.UUID,
    payload: DepartmentUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Updates a Department record (Admin only)."""
    dept = academic_repository.get_department_by_id(db, department_id)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Department not found.",
        )

    if payload.code and payload.code.upper() != dept.code:
        existing = academic_repository.get_department_by_code(db, dept.college_id, payload.code)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Department code '{payload.code.upper()}' already exists in this college.",
            )
    return academic_repository.update_department(
        db, dept, name=payload.name, code=payload.code, is_active=payload.is_active
    )


# ============================================================================
# 3. ADMIN SECTION ENDPOINTS
# ============================================================================

@router.get("/admin/sections", response_model=List[SectionResponse])
def list_sections_admin(
    department_id: Optional[uuid.UUID] = Query(None),
    year_of_study: Optional[int] = Query(None, ge=1, le=4),
    is_active: Optional[bool] = Query(None),
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Lists sections with optional department and year filter (Admin only)."""
    return academic_repository.list_sections(
        db, department_id=department_id, year_of_study=year_of_study, is_active=is_active
    )


@router.post("/admin/sections", response_model=SectionResponse, status_code=status.HTTP_201_CREATED)
def create_section(
    payload: SectionCreate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Creates a new Section under a Department and Year of Study (Admin only)."""
    dept = academic_repository.get_department_by_id(db, payload.department_id)
    if not dept:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent department not found.",
        )

    return academic_repository.create_section(
        db, payload.department_id, payload.year_of_study, payload.name, payload.code
    )


@router.put("/admin/sections/{section_id}", response_model=SectionResponse)
def update_section(
    section_id: uuid.UUID,
    payload: SectionUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Updates a Section record (Admin only)."""
    section = academic_repository.get_section_by_id(db, section_id)
    if not section:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Section not found.",
        )
    return academic_repository.update_section(
        db, section, name=payload.name, code=payload.code, is_active=payload.is_active
    )


# ============================================================================
# 4. ADMIN USER ACADEMIC MAPPING & EXAMINER COLLEGE ASSIGNMENT
# ============================================================================

@router.put("/admin/students/{student_id}/academic-profile", response_model=UserResponse)
def update_student_academic_profile(
    student_id: uuid.UUID,
    payload: StudentAcademicProfileUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Assigns or updates a student's academic profile (Admin only)."""
    student = user_repository.get_by_id(db, student_id)
    if not student or student.role != UserRole.STUDENT:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Student account not found.",
        )

    if payload.college_id:
        c = academic_repository.get_college_by_id(db, payload.college_id)
        if not c:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid college_id.")

    if payload.department_id:
        d = academic_repository.get_department_by_id(db, payload.department_id)
        if not d:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid department_id.")
        if payload.college_id and d.college_id != payload.college_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Department does not belong to selected college.")

    if payload.section_id:
        sec = academic_repository.get_section_by_id(db, payload.section_id)
        if not sec:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid section_id.")

    return academic_repository.update_student_academic_profile(
        db=db,
        student=student,
        college_id=payload.college_id,
        department_id=payload.department_id,
        year_of_study=payload.year_of_study,
        section_id=payload.section_id,
    )


@router.put("/admin/users/{user_id}/college", response_model=UserResponse)
def update_user_college(
    user_id: uuid.UUID,
    payload: UserCollegeUpdate,
    current_user: User = Depends(require_roles(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Assigns or updates an Examiner's (or User's) College (Admin only)."""
    target_user = user_repository.get_by_id(db, user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found.",
        )

    if payload.college_id:
        c = academic_repository.get_college_by_id(db, payload.college_id)
        if not c:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid college_id.")

    return academic_repository.update_user_college(db, target_user, payload.college_id)


# ============================================================================
# 5. PUBLIC / EXAMINER ACADEMIC LOOKUP ENDPOINTS
# ============================================================================

@router.get("/academic/colleges", response_model=List[CollegeResponse])
def get_public_colleges(
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Returns active colleges for dropdown selection."""
    return academic_repository.list_colleges(db, is_active=True)


@router.get("/academic/departments", response_model=List[DepartmentResponse])
def get_public_departments(
    college_id: Optional[uuid.UUID] = Query(None),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Returns active departments. If Examiner, defaults to Examiner's college if college_id not provided."""
    target_college = college_id
    if not target_college and current_user and current_user.role == UserRole.EXAMINER and current_user.college_id:
        target_college = current_user.college_id

    return academic_repository.list_departments(db, college_id=target_college, is_active=True)


@router.get("/academic/sections", response_model=List[SectionResponse])
def get_public_sections(
    department_id: Optional[uuid.UUID] = Query(None),
    year_of_study: Optional[int] = Query(None, ge=1, le=4),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_db),
):
    """Returns active sections for a department and year."""
    return academic_repository.list_sections(db, department_id=department_id, year_of_study=year_of_study, is_active=True)


@router.get("/academic/students", response_model=List[UserResponse])
def get_college_students(
    search: Optional[str] = Query(None),
    department_id: Optional[uuid.UUID] = Query(None),
    year_of_study: Optional[int] = Query(None, ge=1, le=4),
    section_id: Optional[uuid.UUID] = Query(None),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Returns students in the Examiner's college for target selection (Examiner/Admin only)."""
    query = db.query(User).filter(
        and_(
            User.role == UserRole.STUDENT,
            User.is_active == True
        )
    )

    if current_user.role == UserRole.EXAMINER and current_user.college_id:
        query = query.filter(User.college_id == current_user.college_id)

    if department_id:
        query = query.filter(User.department_id == department_id)
    if year_of_study:
        query = query.filter(User.year_of_study == year_of_study)
    if section_id:
        query = query.filter(User.section_id == section_id)
    if search:
        search_fmt = f"%{search.strip()}%"
        query = query.filter(
            (User.first_name.ilike(search_fmt)) |
            (User.last_name.ilike(search_fmt)) |
            (User.email.ilike(search_fmt))
        )

    students = query.order_by(User.first_name.asc(), User.last_name.asc()).limit(100).all()
    return [UserResponse.model_validate(s) for s in students]
