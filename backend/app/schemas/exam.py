import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

from app.models.exam import ExamStatus, ExamTargetType
from app.schemas.question import QuestionResponse


class ExamQuestionInput(BaseModel):
    question_id: uuid.UUID
    question_order: int = Field(..., ge=1)
    marks_override: Optional[float] = Field(None, gt=0)


class ExamQuestionResponse(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    question_id: uuid.UUID
    question_order: int
    marks_override: Optional[float] = None
    question: QuestionResponse

    model_config = ConfigDict(from_attributes=True)


class ExamCreate(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: Optional[str] = None
    subject: str = Field(..., min_length=1, max_length=100)
    instructions: Optional[str] = None
    duration_minutes: int = Field(..., gt=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    passing_marks: float = Field(0.0, ge=0)
    negative_marking_enabled: bool = False
    randomize_questions: bool = False
    randomize_options: bool = False
    proctoring_enabled: bool = True
    max_tab_switches: int = Field(3, ge=0, le=20)
    target_type: Optional[ExamTargetType] = None
    target_department_id: Optional[uuid.UUID] = None
    target_year_of_study: Optional[int] = Field(None, ge=1, le=4)
    target_section_id: Optional[uuid.UUID] = None
    target_student_ids: Optional[List[uuid.UUID]] = None
    questions: List[ExamQuestionInput] = Field(default_factory=list)


class ExamUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1, max_length=255)
    description: Optional[str] = None
    subject: Optional[str] = Field(None, min_length=1, max_length=100)
    instructions: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, gt=0)
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    passing_marks: Optional[float] = Field(None, ge=0)
    negative_marking_enabled: Optional[bool] = None
    randomize_questions: Optional[bool] = None
    randomize_options: Optional[bool] = None
    proctoring_enabled: Optional[bool] = None
    max_tab_switches: Optional[int] = Field(None, ge=0, le=20)
    target_type: Optional[ExamTargetType] = None
    target_department_id: Optional[uuid.UUID] = None
    target_year_of_study: Optional[int] = Field(None, ge=1, le=4)
    target_section_id: Optional[uuid.UUID] = None
    target_student_ids: Optional[List[uuid.UUID]] = None
    questions: Optional[List[ExamQuestionInput]] = None


class ExamResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    subject: str
    instructions: Optional[str] = None
    created_by: uuid.UUID
    duration_minutes: int
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    total_marks: float
    passing_marks: float
    negative_marking_enabled: bool
    randomize_questions: bool
    randomize_options: bool
    proctoring_enabled: bool
    max_tab_switches: int = 3
    status: ExamStatus
    target_type: Optional[ExamTargetType] = None
    target_department_id: Optional[uuid.UUID] = None
    target_year_of_study: Optional[int] = None
    target_section_id: Optional[uuid.UUID] = None
    target_student_ids: List[uuid.UUID] = Field(default_factory=list)
    eligible_students_count: Optional[int] = None

    created_at: datetime
    updated_at: datetime
    questions: List[ExamQuestionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class PaginatedExamResponse(BaseModel):
    items: List[ExamResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
