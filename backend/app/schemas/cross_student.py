import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class CrossStudentEvidenceItem(BaseModel):
    evidence_type: str
    title: str
    description: str


class CrossStudentTextMatchItem(BaseModel):
    question_id: uuid.UUID
    question_number: int
    question_text: str
    student_a_text: str
    student_b_text: str
    similarity_score: float  # Percentage (0-100)


class CrossStudentWrongAnswerItem(BaseModel):
    question_id: uuid.UUID
    question_number: int
    question_text: str
    student_a_option: str
    student_b_option: str
    correct_option: str


class CrossStudentPairSummaryItem(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    source_session_id: uuid.UUID
    target_session_id: uuid.UUID
    source_student_id: uuid.UUID
    source_student_name: str
    source_student_email: str
    target_student_id: uuid.UUID
    target_student_name: str
    target_student_email: str
    similarity_score: float
    answer_similarity: float
    wrong_answer_similarity: float
    timing_similarity: Optional[float] = None
    answer_change_similarity: Optional[float] = None
    navigation_similarity: Optional[float] = None
    same_incorrect_answers_count: int = 0
    same_correct_answers_count: int = 0
    category: str  # LOW_SIMILARITY, MODERATE_SIMILARITY, HIGH_SIMILARITY
    cluster_id: Optional[str] = None


class CrossStudentClusterStudentItem(BaseModel):
    student_id: uuid.UUID
    student_name: str
    student_email: str
    session_id: uuid.UUID


class CrossStudentClusterItem(BaseModel):
    cluster_id: str
    student_count: int
    average_similarity: float
    students: List[CrossStudentClusterStudentItem]
    key_evidence: List[str]


class CrossStudentPairDetailResponse(BaseModel):
    id: uuid.UUID
    exam_id: uuid.UUID
    exam_title: str
    source_session_id: uuid.UUID
    target_session_id: uuid.UUID
    source_student_id: uuid.UUID
    source_student_name: str
    source_student_email: str
    target_student_id: uuid.UUID
    target_student_name: str
    target_student_email: str
    similarity_score: float
    category: str
    answer_similarity: float
    wrong_answer_similarity: float
    timing_similarity: Optional[float] = None
    answer_change_similarity: Optional[float] = None
    navigation_similarity: Optional[float] = None
    same_incorrect_answers_count: int = 0
    same_correct_answers_count: int = 0
    total_comparable_questions: int = 0
    evidence_items: List[str] = []
    common_wrong_answers: List[CrossStudentWrongAnswerItem] = []
    text_matches: List[CrossStudentTextMatchItem] = []
    per_question_timing: List[Dict[str, Any]] = []
    answer_change_sequences: List[Dict[str, Any]] = []
    navigation_sequences: List[Dict[str, Any]] = []
    generated_at: datetime


class PaginatedCrossStudentAnalysisResponse(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    analyzed_students_count: int
    total_pairs_count: int
    high_similarity_pairs_count: int
    moderate_similarity_pairs_count: int
    low_similarity_pairs_count: int
    last_analyzed_at: Optional[datetime] = None
    clusters: List[CrossStudentClusterItem] = []
    items: List[CrossStudentPairSummaryItem] = []
    total: int
    page: int
    page_size: int
    pages: int
