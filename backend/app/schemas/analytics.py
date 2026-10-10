import uuid
from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel

from app.models.question import QuestionType, DifficultyLevel
from app.models.evaluation import EvaluationStatus, PassFailStatus
from app.schemas.evaluation import PaginatedStudentResultResponse


class ExamBasicInfo(BaseModel):
    id: uuid.UUID
    title: str
    subject: str
    status: str
    total_marks: float
    passing_marks: float


class AnalyticsSummary(BaseModel):
    total_sessions: int = 0
    evaluated_sessions: int = 0
    pending_reviews: int = 0
    finalized_evaluations: int = 0
    average_score: float = 0.0
    average_percentage: float = 0.0
    pass_count: int = 0
    fail_count: int = 0
    pass_rate: float = 0.0


class ScorePerformance(BaseModel):
    average_percentage: float = 0.0
    highest_percentage: float = 0.0
    lowest_percentage: float = 0.0
    median_percentage: float = 0.0


class ScoreDistribution(BaseModel):
    bucket_0_20: int = 0
    bucket_21_40: int = 0
    bucket_41_60: int = 0
    bucket_61_80: int = 0
    bucket_81_100: int = 0


class PassFailDistribution(BaseModel):
    passed: int = 0
    failed: int = 0
    pending_review: int = 0


class FinalizedPerformance(BaseModel):
    finalized_sessions: int = 0
    average_finalized_score: float = 0.0
    average_finalized_percentage: float = 0.0
    finalized_pass_count: int = 0
    finalized_fail_count: int = 0
    finalized_pass_rate: float = 0.0


class QuestionPerformanceItem(BaseModel):
    question_id: uuid.UUID
    question_order: int
    question_text: str
    question_type: QuestionType
    marks: float
    topic: Optional[str] = None
    difficulty: DifficultyLevel
    attempted_count: int = 0
    unanswered_count: int = 0
    correct_count: Optional[int] = None
    incorrect_count: Optional[int] = None
    accuracy_percentage: Optional[float] = None
    evaluated_count: Optional[int] = None
    pending_review_count: Optional[int] = None
    average_score: float = 0.0
    average_percentage: float = 0.0


class DifficultyPerformanceItem(BaseModel):
    difficulty: DifficultyLevel
    question_count: int = 0
    average_percentage: float = 0.0


class TopicPerformanceItem(BaseModel):
    topic: str
    question_count: int = 0
    average_percentage: float = 0.0


class PendingReviewItem(BaseModel):
    session_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    pending_question_count: int = 0
    current_score: float = 0.0
    maximum_marks: float = 0.0
    submitted_at: Optional[datetime] = None
    status: EvaluationStatus


class ExamAnalyticsResponse(BaseModel):
    exam_info: ExamBasicInfo
    summary: AnalyticsSummary
    score_performance: ScorePerformance
    score_distribution: ScoreDistribution
    pass_fail_distribution: PassFailDistribution
    finalized_performance: FinalizedPerformance
    question_performance: List[QuestionPerformanceItem]
    difficulty_performance: List[DifficultyPerformanceItem]
    topic_performance: List[TopicPerformanceItem]
    pending_reviews: List[PendingReviewItem]
    student_performance: PaginatedStudentResultResponse

    model_config = {"from_attributes": True}
