import uuid
from typing import List, Optional, Dict
from datetime import datetime
from pydantic import BaseModel, ConfigDict
from app.models.exam import ExamStatus, ExamTargetType


class AdminExamListItem(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    status: ExamStatus
    duration_minutes: int
    total_marks: float
    passing_marks: float
    question_count: int = 0
    created_by: uuid.UUID
    examiner_name: str
    examiner_email: str
    examiner_college_name: Optional[str] = None
    examiner_college_code: Optional[str] = None
    target_type: Optional[ExamTargetType] = None
    target_description: str
    eligible_students_count: int = 0
    sessions_count: int = 0
    completed_sessions_count: int = 0
    created_at: datetime
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class AdminExamSummaryMetrics(BaseModel):
    total_exams: int
    published_active_exams: int
    completed_exams: int
    draft_exams: int


class PaginatedAdminExamResponse(BaseModel):
    items: List[AdminExamListItem]
    total: int
    page: int
    page_size: int
    total_pages: int
    summary: AdminExamSummaryMetrics


class AdminExamDetailResponse(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    description: Optional[str] = None
    instructions: Optional[str] = None
    status: ExamStatus
    duration_minutes: int
    total_marks: float
    passing_marks: float
    negative_marking_enabled: bool = False
    randomize_questions: bool = False
    randomize_options: bool = False
    proctoring_enabled: bool = True
    max_tab_switches: int = 3
    created_at: datetime
    updated_at: datetime
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None

    # Examiner details
    created_by: uuid.UUID
    examiner_name: str
    examiner_email: str
    examiner_college_name: Optional[str] = None
    examiner_college_code: Optional[str] = None

    # Target audience details
    target_type: Optional[ExamTargetType] = None
    target_description: str
    target_college_name: Optional[str] = None
    target_department_name: Optional[str] = None
    target_year_of_study: Optional[int] = None
    target_section_name: Optional[str] = None
    target_specific_students_count: int = 0
    eligible_students_count: int = 0

    # Activity statistics
    total_sessions_count: int = 0
    completed_sessions_count: int = 0
    in_progress_sessions_count: int = 0
    other_sessions_count: int = 0

    # Question statistics
    question_count: int = 0
    mcq_count: int = 0
    multi_select_count: int = 0
    short_answer_count: int = 0
    long_answer_count: int = 0
    handwritten_count: int = 0

    model_config = ConfigDict(from_attributes=True)
