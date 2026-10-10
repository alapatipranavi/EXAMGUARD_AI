import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel


class ExaminerDashboardSummary(BaseModel):
    total_exams: int
    published_exams: int
    active_sessions: int
    pending_reviews: int


class ExaminerAcademicScope(BaseModel):
    college_id: Optional[uuid.UUID] = None
    college_name: Optional[str] = None
    college_code: Optional[str] = None


class ExaminerExamItem(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    status: str
    duration_minutes: int
    total_marks: float
    question_count: int
    start_at: Optional[datetime] = None
    end_at: Optional[datetime] = None
    target_type: Optional[str] = None
    target_summary: Optional[str] = None
    eligible_student_count: int = 0
    attempt_count: int = 0
    created_at: datetime


class ExaminerPendingReviewItem(BaseModel):
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    student_id: uuid.UUID
    student_name: str
    student_email: str
    pending_question_count: int
    status: str
    submitted_at: Optional[datetime] = None


class ExaminerRecentActivityItem(BaseModel):
    id: str
    event_type: str
    description: str
    student_name: Optional[str] = None
    exam_title: str
    timestamp: datetime
    session_id: Optional[uuid.UUID] = None
    exam_id: Optional[uuid.UUID] = None


class ExaminerDashboardResponse(BaseModel):
    greeting_name: str
    summary: ExaminerDashboardSummary
    academic_scope: ExaminerAcademicScope
    exams: List[ExaminerExamItem]
    pending_reviews: List[ExaminerPendingReviewItem]
    recent_activity: List[ExaminerRecentActivityItem]
