import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class CollegeCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)


class CollegeUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None


class CollegeResponse(BaseModel):
    id: uuid.UUID
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class DepartmentCreate(BaseModel):
    college_id: uuid.UUID
    name: str = Field(..., min_length=1, max_length=255)
    code: str = Field(..., min_length=1, max_length=50)


class DepartmentUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=255)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None


class DepartmentResponse(BaseModel):
    id: uuid.UUID
    college_id: uuid.UUID
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class SectionCreate(BaseModel):
    department_id: uuid.UUID
    year_of_study: int = Field(..., ge=1, le=4)
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)


class SectionUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    is_active: Optional[bool] = None


class SectionResponse(BaseModel):
    id: uuid.UUID
    department_id: uuid.UUID
    year_of_study: int
    name: str
    code: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StudentAcademicProfileUpdate(BaseModel):
    college_id: Optional[uuid.UUID] = None
    department_id: Optional[uuid.UUID] = None
    year_of_study: Optional[int] = Field(None, ge=1, le=4)
    section_id: Optional[uuid.UUID] = None


class UserCollegeUpdate(BaseModel):
    college_id: Optional[uuid.UUID] = None
