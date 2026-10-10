import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, ConfigDict

from app.models.exam import ExamStatus
from app.models.question import QuestionType, DifficultyLevel
from app.models.exam_session import SessionStatus


class StudentQuestionOptionResponse(BaseModel):
    id: uuid.UUID
    option_text: str
    option_order: int

    model_config = ConfigDict(from_attributes=True)


class StudentQuestionResponse(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: QuestionType
    difficulty: DifficultyLevel
    marks: float
    question_order: int
    options: List[StudentQuestionOptionResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StudentExamItem(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    subject: str
    duration_minutes: int
    total_marks: float
    passing_marks: float
    question_count: int
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    status: ExamStatus
    student_session_status: str  # "AVAILABLE", "IN_PROGRESS", "COMPLETED"
    active_session_id: Optional[uuid.UUID] = None
    identity_verification_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedStudentExamResponse(BaseModel):
    items: List[StudentExamItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class StudentExamDetail(BaseModel):
    id: uuid.UUID
    title: str
    description: Optional[str] = None
    subject: str
    instructions: Optional[str] = None
    duration_minutes: int
    total_marks: float
    passing_marks: float
    question_count: int
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    negative_marking_enabled: bool
    randomize_questions: bool
    randomize_options: bool
    proctoring_enabled: bool
    max_tab_switches: int = 3
    status: ExamStatus
    student_session_status: str  # "AVAILABLE", "IN_PROGRESS", "COMPLETED"
    active_session_id: Optional[uuid.UUID] = None
    identity_verification_status: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class StudentAnswerSaveInput(BaseModel):
    selected_option_ids: Optional[List[uuid.UUID]] = Field(default_factory=list)
    text_answer: Optional[str] = None


class HandwrittenAnswerInput(BaseModel):
    image_data: str = Field(..., description="Base64 encoded image string (data:image/png;base64,...)")


class HandwrittenAnswerProcessResponse(BaseModel):
    question_id: uuid.UUID
    answer_image_url: str
    ocr_status: str
    ocr_confidence: Optional[float] = None
    extracted_text: str
    evaluation_status: str
    message: str


class ReviewToggleInput(BaseModel):
    marked: bool


class StudentAnswerResponse(BaseModel):
    question_id: uuid.UUID
    selected_option_ids: List[uuid.UUID] = Field(default_factory=list)
    text_answer: Optional[str] = None
    answer_image_url: Optional[str] = None
    ocr_status: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_processed_at: Optional[datetime] = None
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExamSessionResponse(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: str
    duration_minutes: int
    status: SessionStatus
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    expires_at: Optional[datetime] = None
    remaining_seconds: int
    max_tab_switches: int = 3
    tab_switch_count: int = 0
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    identity_verification_status: Optional[str] = "UNVERIFIED"
    marked_for_review_question_ids: List[uuid.UUID] = Field(default_factory=list)
    questions: List[StudentQuestionResponse] = Field(default_factory=list)
    answers: List[StudentAnswerResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class StudentDashboardSummary(BaseModel):
    upcoming_exams: int = 0
    in_progress_exams: int = 0
    completed_exams: int = 0
    results_available: int = 0


class StudentAcademicProfile(BaseModel):
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


class UpcomingExamDashboardItem(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    description: Optional[str] = None
    duration_minutes: int
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    question_count: int
    total_marks: float
    status: str  # "AVAILABLE", "UPCOMING", etc.
    active_session_id: Optional[uuid.UUID] = None

    model_config = ConfigDict(from_attributes=True)


class InProgressExamSessionInfo(BaseModel):
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: str
    duration_minutes: int
    start_time: datetime
    end_time: Optional[datetime] = None
    remaining_seconds: int
    total_questions: int
    answered_count: int
    marked_for_review_count: int

    model_config = ConfigDict(from_attributes=True)


class RecentResultDashboardItem(BaseModel):
    evaluation_id: uuid.UUID
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: str
    total_score: float
    maximum_marks: float
    percentage: float
    pass_fail_status: str
    status: str
    submitted_at: datetime

    model_config = ConfigDict(from_attributes=True)


class StudentDashboardResponse(BaseModel):
    greeting_name: str
    summary: StudentDashboardSummary
    academic_profile: StudentAcademicProfile
    in_progress_exam: Optional[InProgressExamSessionInfo] = None
    upcoming_exams: List[UpcomingExamDashboardItem] = Field(default_factory=list)
    recent_results: List[RecentResultDashboardItem] = Field(default_factory=list)


