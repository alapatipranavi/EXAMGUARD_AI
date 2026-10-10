import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field

from app.models.question import QuestionType
from app.models.evaluation import EvaluationStatus, PassFailStatus


class SubjectiveReviewInput(BaseModel):
    final_score: float = Field(description="Final score awarded by examiner")
    comment: Optional[str] = Field(default=None, description="Optional examiner review comment")
    is_finalized: Optional[bool] = Field(default=False, description="Set True to finalize evaluation")


class SubjectiveFinalizeInput(BaseModel):
    final_score: float = Field(description="Final score awarded by examiner")
    comment: Optional[str] = Field(default=None, description="Optional examiner review comment")


class QuestionEvaluationDetail(BaseModel):
    answer_id: Optional[uuid.UUID] = None
    question_id: uuid.UUID
    question_text: str
    question_type: QuestionType
    marks: float
    earned_score: float
    suggested_score: Optional[float] = None
    is_answered: bool
    is_correct: Optional[bool] = None
    justification: Optional[str] = None
    examiner_comment: Optional[str] = None
    text_answer: Optional[str] = None
    answer_image_url: Optional[str] = None
    ocr_status: Optional[str] = None
    ocr_confidence: Optional[float] = None
    ocr_processed_at: Optional[datetime] = None
    model_answer: Optional[str] = None
    explanation: Optional[str] = None
    selected_option_ids: Optional[List[uuid.UUID]] = None
    matched_concepts: Optional[Dict[str, Any]] = None
    missed_concepts: Optional[Dict[str, Any]] = None
    evaluator_type: Optional[str] = None
    status: Optional[EvaluationStatus] = None
    reviewed_by: Optional[uuid.UUID] = None
    reviewer_name: Optional[str] = None
    reviewed_at: Optional[datetime] = None


class StudentResultResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: str
    student_id: uuid.UUID
    student_name: str
    student_email: str
    submitted_at: Optional[datetime] = None
    total_questions: int
    answered_questions: int
    unanswered_questions: int
    correct_answers: int
    incorrect_answers: int
    objective_marks: float
    subjective_marks: float = 0.0
    negative_marks: float
    total_score: float
    maximum_marks: float
    percentage: float
    passing_marks: float
    pass_fail_status: PassFailStatus
    status: EvaluationStatus
    question_evaluations: Optional[List[QuestionEvaluationDetail]] = None

    model_config = {"from_attributes": True}


class PaginatedStudentResultResponse(BaseModel):
    items: List[StudentResultResponse]
    total: int
    page: int
    page_size: int
    total_pages: int
