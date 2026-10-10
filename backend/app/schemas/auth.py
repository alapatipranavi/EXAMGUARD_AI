import uuid
from typing import Optional
from datetime import datetime
from pydantic import BaseModel, EmailStr, Field, field_validator
from app.models.user import UserRole


class UserRegister(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, description="Password must be at least 8 characters long")
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: Optional[str] = Field(default="", max_length=100)
    role: UserRole = UserRole.STUDENT
    college_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=4)
    section_id: Optional[uuid.UUID] = None

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        return v

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()


class UserResponse(BaseModel):
    id: uuid.UUID
    email: EmailStr
    first_name: str
    last_name: str
    role: UserRole
    is_active: bool
    college_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    year_of_study: Optional[int] = None
    section_id: Optional[uuid.UUID] = None
    is_face_registered: bool = False
    face_registered_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class LoginResponse(BaseModel):
    user: UserResponse
