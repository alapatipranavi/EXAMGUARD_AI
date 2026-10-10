import uuid
from datetime import datetime
from typing import Optional, List, Dict
from pydantic import BaseModel, Field


class StudentIntegritySummary(BaseModel):
    exams_monitored: int = Field(0, description="Total number of monitored examinations")
    exams_completed: int = Field(0, description="Number of completed / submitted examinations")
    average_integrity_score: float = Field(100.0, description="Average integrity score across monitored examinations")
    high_risk_count: int = Field(0, description="Number of exams with high risk assessment")
    moderate_risk_count: int = Field(0, description="Number of exams with moderate risk assessment")
    low_risk_count: int = Field(0, description="Number of exams with low risk assessment")


class StudentExamIntegrityItem(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    session_id: uuid.UUID
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    integrity_score: float
    risk_level: str
    event_count: int
    status: str


class StudentIntegrityOverviewResponse(BaseModel):
    summary: StudentIntegritySummary
    exams: List[StudentExamIntegrityItem]


class StudentProctoringEventItem(BaseModel):
    event_type: str
    title: str
    occurred_at: Optional[datetime] = None
    description: str
    severity: str


class StudentBehaviouralMetrics(BaseModel):
    metrics_available: bool = False
    questions_visited: Optional[int] = None
    questions_answered: Optional[int] = None
    answer_changes: Optional[int] = None
    answers_cleared: Optional[int] = None
    navigation_count: Optional[int] = None
    backtracking_count: Optional[int] = None
    avg_question_time: Optional[float] = None
    median_question_time: Optional[float] = None
    rapid_change_clusters: Optional[int] = None


class StudentEnvironmentMonitoring(BaseModel):
    phone_detected_count: int = 0
    laptop_detected_count: int = 0
    book_detected_count: int = 0
    additional_person_count: int = 0
    status: str = "NORMAL"
    explanation: str = "No unauthorized objects or devices were flagged during this examination."


class StudentSessionIntegrityDetailResponse(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: Optional[str] = None
    session_id: uuid.UUID
    session_status: str
    started_at: Optional[datetime] = None
    submitted_at: Optional[datetime] = None
    integrity_score: float
    risk_level: str
    status_explanation: str
    event_count: int
    event_summary: Dict[str, int]
    events: List[StudentProctoringEventItem]
    behavioural_metrics: StudentBehaviouralMetrics
    environment_monitoring: StudentEnvironmentMonitoring
