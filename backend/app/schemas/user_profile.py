import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from app.models.user import UserRole


class UserProfileResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    is_face_registered: bool = False
    face_registered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime
    
    # Academic & Institutional Scope
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

    model_config = ConfigDict(from_attributes=True)


class UserProfileUpdate(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(default="", max_length=100)

    model_config = ConfigDict(extra="forbid")

    @field_validator("first_name")
    @classmethod
    def validate_first_name(cls, v: str) -> str:
        stripped = v.strip()
        if not stripped:
            raise ValueError("First name cannot be empty or only whitespace.")
        return stripped

    @field_validator("last_name")
    @classmethod
    def validate_last_name(cls, v: Optional[str]) -> str:
        if v is None:
            return ""
        return v.strip()


class UserPasswordChange(BaseModel):
    current_password: str = Field(..., min_length=1, description="Current account password")
    new_password: str = Field(..., min_length=8, description="New password (minimum 8 characters)")

    model_config = ConfigDict(extra="forbid")

    @field_validator("new_password")
    @classmethod
    def validate_new_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("New password must be at least 8 characters long.")
        return v


class NotificationSettings(BaseModel):
    exam_reminders: bool = True
    result_notifications: bool = True
    integrity_alerts: bool = True
    system_updates: bool = True

    model_config = ConfigDict(extra="ignore")
