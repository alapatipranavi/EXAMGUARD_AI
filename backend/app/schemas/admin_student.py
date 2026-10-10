import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from app.models.user import UserRole


class AdminStudentListItem(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.STUDENT
    is_active: bool
    college_id: Optional[uuid.UUID] = None
    college_name: Optional[str] = None
    college_code: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    year_of_study: Optional[int] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    section_code: Optional[str] = None
    is_face_registered: bool = False
    face_registered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminStudentSummaryMetrics(BaseModel):
    total_students: int
    active_students: int
    inactive_students: int
    unassigned_academic_profiles: int


class PaginatedAdminStudentResponse(BaseModel):
    items: List[AdminStudentListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: AdminStudentSummaryMetrics


class AdminStudentRecentSessionItem(BaseModel):
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: str
    status: str
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    percentage: Optional[float] = None
    pass_fail_status: Optional[str] = None


class AdminStudentDetailResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.STUDENT
    is_active: bool
    college_id: Optional[uuid.UUID] = None
    college_name: Optional[str] = None
    college_code: Optional[str] = None
    department_id: Optional[uuid.UUID] = None
    department_name: Optional[str] = None
    department_code: Optional[str] = None
    year_of_study: Optional[int] = None
    section_id: Optional[uuid.UUID] = None
    section_name: Optional[str] = None
    section_code: Optional[str] = None
    is_face_registered: bool = False
    face_registered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    # Lightweight Exam Activity Information
    exams_assigned_count: int = 0
    exams_attempted_count: int = 0
    exams_completed_count: int = 0
    recent_sessions: List[AdminStudentRecentSessionItem] = []

    model_config = ConfigDict(from_attributes=True)
