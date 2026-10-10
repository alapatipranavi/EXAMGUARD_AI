import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr
from app.models.user import UserRole


class AdminExaminerListItem(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.EXAMINER
    is_active: bool
    college_id: Optional[uuid.UUID] = None
    college_name: Optional[str] = None
    college_code: Optional[str] = None
    total_exams_count: int = 0
    published_exams_count: int = 0
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AdminExaminerSummaryMetrics(BaseModel):
    total_examiners: int
    active_examiners: int
    inactive_examiners: int
    unassigned_college: int


class PaginatedAdminExaminerResponse(BaseModel):
    items: List[AdminExaminerListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: AdminExaminerSummaryMetrics


class AdminExaminerRecentExamItem(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    status: str
    duration_minutes: int
    total_marks: float
    passing_marks: float
    target_type: Optional[str] = None
    created_at: datetime
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminExaminerDetailResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole = UserRole.EXAMINER
    is_active: bool
    college_id: Optional[uuid.UUID] = None
    college_name: Optional[str] = None
    college_code: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Exam Activity Information
    total_exams_created: int = 0
    published_exams_count: int = 0
    draft_exams_count: int = 0
    completed_exams_count: int = 0
    recent_exams: List[AdminExaminerRecentExamItem] = []

    model_config = ConfigDict(from_attributes=True)
