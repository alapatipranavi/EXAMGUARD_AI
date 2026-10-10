import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, model_validator

from app.models.question import QuestionType, DifficultyLevel, QuestionSource


class QuestionOptionCreate(BaseModel):
    option_text: str = Field(..., min_length=1, description="Option text cannot be empty")
    option_order: int = Field(..., ge=1)
    is_correct: bool = False


class QuestionOptionResponse(BaseModel):
    id: uuid.UUID
    question_id: uuid.UUID
    option_text: str
    option_order: int
    is_correct: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class QuestionCreate(BaseModel):
    question_text: str = Field(..., min_length=1, max_length=10000)
    subject: str = Field(..., min_length=1, max_length=100)
    topic: Optional[str] = Field(default=None, max_length=100)
    question_type: QuestionType
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    source: QuestionSource = QuestionSource.MANUAL
    marks: float = Field(..., gt=0, description="Marks must be greater than 0")
    negative_marks: float = Field(default=0.0, ge=0, description="Negative marks must be >= 0")
    model_answer: Optional[str] = None
    explanation: Optional[str] = None
    options: Optional[List[QuestionOptionCreate]] = None

    @model_validator(mode="after")
    def validate_question_options(self):
        q_type = self.question_type
        opts = self.options or []

        if q_type == QuestionType.MCQ:
            if len(opts) < 2:
                raise ValueError("MCQ questions require at least 2 options.")
            correct_count = sum(1 for o in opts if o.is_correct)
            if correct_count != 1:
                raise ValueError(f"MCQ questions require exactly 1 correct option (found {correct_count}).")

        elif q_type == QuestionType.MULTI_SELECT:
            if len(opts) < 2:
                raise ValueError("MULTI_SELECT questions require at least 2 options.")
            correct_count = sum(1 for o in opts if o.is_correct)
            if correct_count < 2:
                raise ValueError(f"MULTI_SELECT questions require at least 2 correct options (found {correct_count}).")

        elif q_type in (QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER, QuestionType.HANDWRITTEN):
            self.options = None

        return self


class QuestionUpdate(BaseModel):
    question_text: Optional[str] = Field(default=None, min_length=1, max_length=10000)
    subject: Optional[str] = Field(default=None, min_length=1, max_length=100)
    topic: Optional[str] = Field(default=None, max_length=100)
    question_type: Optional[QuestionType] = None
    difficulty: Optional[DifficultyLevel] = None
    source: Optional[QuestionSource] = None
    marks: Optional[float] = Field(default=None, gt=0)
    negative_marks: Optional[float] = Field(default=None, ge=0)
    model_answer: Optional[str] = None
    explanation: Optional[str] = None
    options: Optional[List[QuestionOptionCreate]] = None


class QuestionResponse(BaseModel):
    id: uuid.UUID
    question_text: str
    question_type: QuestionType
    subject: str
    topic: Optional[str] = None
    difficulty: DifficultyLevel
    source: QuestionSource = QuestionSource.MANUAL
    marks: float
    negative_marks: float
    model_answer: Optional[str] = None
    explanation: Optional[str] = None
    created_by: Optional[uuid.UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime
    options: List[QuestionOptionResponse] = []

    model_config = {"from_attributes": True}


class PaginatedQuestionResponse(BaseModel):
    items: List[QuestionResponse]
    total: int
    page: int
    page_size: int
    total_pages: int


# ==========================================
# DASHBOARD SUMMARY SCHEMAS
# ==========================================

class DashboardSummaryResponse(BaseModel):
    role: str
    user_name: str
    user_email: str
    stats: Dict[str, Any]
    recent_activity: List[Dict[str, Any]] = []


# ==========================================
# AI GENERATION & ASSISTANT SCHEMAS
# ==========================================

class AIGenerateRequest(BaseModel):
    subject: str = Field(..., min_length=1, max_length=100)
    topic: str = Field(..., min_length=1, max_length=100)
    question_types: List[QuestionType] = Field(..., min_length=1)
    difficulty: DifficultyLevel = DifficultyLevel.MEDIUM
    count: int = Field(default=5, ge=1, le=20)
    marks: float = Field(default=2.0, gt=0)
    learning_objective: Optional[str] = None
    additional_instructions: Optional[str] = None


class AIGeneratedDraftOption(BaseModel):
    option_text: str
    option_order: int
    is_correct: bool


class AIGeneratedDraft(BaseModel):
    draft_id: str
    question_text: str
    subject: str
    topic: Optional[str] = None
    question_type: QuestionType
    difficulty: DifficultyLevel
    marks: float
    negative_marks: float = 0.0
    model_answer: Optional[str] = None
    explanation: Optional[str] = None
    options: List[AIGeneratedDraftOption] = []
    source: QuestionSource = QuestionSource.AI_GENERATED


class AIGeneratedDraftsResponse(BaseModel):
    subject: str
    topic: str
    drafts: List[AIGeneratedDraft]


class AIAssistRequest(BaseModel):
    action: str = Field(..., description="Action: improve, generate_options, suggest_explanation, suggest_model_answer, increase_difficulty, simplify, make_application_based, generate_similar")
    question_text: str = Field(..., min_length=1)
    subject: Optional[str] = None
    topic: Optional[str] = None
    question_type: QuestionType = QuestionType.MCQ
    current_options: Optional[List[QuestionOptionCreate]] = None
    current_model_answer: Optional[str] = None


class AIAssistResponse(BaseModel):
    action: str
    improved_question_text: Optional[str] = None
    suggested_options: Optional[List[QuestionOptionCreate]] = None
    suggested_explanation: Optional[str] = None
    suggested_model_answer: Optional[str] = None


# ==========================================
# IMPORT SCHEMAS (CSV & PDF)
# ==========================================

class ImportRowValidation(BaseModel):
    row_number: int
    is_valid: bool
    error_message: Optional[str] = None
    question: Optional[QuestionCreate] = None
    raw_data: Dict[str, Any] = {}
    needs_review: bool = False


class CSVImportParseResponse(BaseModel):
    total_rows: int
    valid_rows_count: int
    invalid_rows_count: int
    rows: List[ImportRowValidation]


class PDFExtractedQuestion(BaseModel):
    item_number: int
    extracted_text: str
    detected_type: QuestionType
    detected_subject: str
    detected_topic: Optional[str] = None
    detected_difficulty: DifficultyLevel
    detected_marks: float
    detected_options: List[QuestionOptionCreate] = []
    detected_answer: Optional[str] = None
    confidence_score: float = 0.8
    needs_review: bool = False
    is_valid: bool = True
    validation_error: Optional[str] = None


class PDFImportParseResponse(BaseModel):
    total_extracted: int
    items: List[PDFExtractedQuestion]


class ConfirmImportRequest(BaseModel):
    source: QuestionSource = Field(..., description="Must be CSV_IMPORT or PDF_IMPORT")
    questions: List[QuestionCreate]
