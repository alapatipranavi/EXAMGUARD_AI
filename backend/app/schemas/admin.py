import uuid
from typing import List, Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole
from app.schemas.auth import UserResponse


class AdminUserCreate(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    role: UserRole = UserRole.EXAMINER

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminUserRoleUpdate(BaseModel):
    role: UserRole


class PaginatedUserResponse(BaseModel):
    items: List[UserResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


class AdminDashboardSummary(BaseModel):
    total_students: int
    total_examiners: int
    total_exams: int
    active_sessions: int
    completed_exams: int
    pending_reviews: int
    total_colleges: int
    total_departments: int


class AdminUserMetrics(BaseModel):
    total_students: int
    total_examiners: int
    active_students: int
    active_examiners: int
    inactive_users: int


class AdminAcademicMetrics(BaseModel):
    total_colleges: int
    total_departments: int
    total_sections: int
    students_with_academic_profiles: int


class AdminExamBreakdown(BaseModel):
    draft: int
    published: int
    scheduled: int
    active: int
    completed: int
    archived: int


class AdminActivityItem(BaseModel):
    id: str
    event_type: str
    description: str
    timestamp: datetime
    user_name: Optional[str] = None
    target_name: Optional[str] = None


class AdminSystemStatus(BaseModel):
    backend: str = "online"
    database: str = "connected"
    version: str = "1.0.0"


class AdminDashboardResponse(BaseModel):
    greeting_name: str
    summary: AdminDashboardSummary
    users: AdminUserMetrics
    academic: AdminAcademicMetrics
    examinations: AdminExamBreakdown
    recent_activity: List[AdminActivityItem]
    system_status: AdminSystemStatus

