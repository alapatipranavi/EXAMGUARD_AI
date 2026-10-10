import uuid
from datetime import datetime
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from app.models.integrity import AnalysisStatus


class IntegrityEvidenceItem(BaseModel):
    signal_type: str = Field(..., description="Type of signal, e.g., TAB_SWITCH, FACE_NOT_DETECTED")
    title: str = Field(..., description="Human-readable title")
    count: int = Field(..., description="Number of observed occurrences")
    severity: str = Field(..., description="Severity level: INFO, LOW, MEDIUM, WARNING, HIGH, CRITICAL")
    observation: str = Field(..., description="Neutral human-readable observation text")
    score_deduction: float = Field(..., description="Points deducted from integrity score")


class IntegrityTimelineItem(BaseModel):
    timestamp: Optional[datetime] = Field(None, description="Event timestamp")
    event_type: str = Field(..., description="Event classification")
    label: str = Field(..., description="Human-readable event title")
    details: Optional[str] = Field(None, description="Detailed context or description")
    severity: str = Field("INFO", description="Event severity")


class IntegritySignalsSummary(BaseModel):
    tab_switches: int = 0
    face_alerts: int = 0
    fullscreen_events: int = 0
    hardware_alerts: int = 0
    total_signals: int = 0


class SessionIntegrityDetailResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    exam_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    session_status: str
    integrity_score: float
    risk_level: str  # LOW, MODERATE, HIGH
    analysis_status: AnalysisStatus
    summary: str
    recommendation: str
    evidence: List[IntegrityEvidenceItem]
    timeline: List[IntegrityTimelineItem]
    signals_summary: IntegritySignalsSummary
    behavioural_summary: Optional[Dict[str, Any]] = None
    identity_summary: Optional[Dict[str, Any]] = None
    generated_at: datetime
    reviewed_at: Optional[datetime] = None


class ExamIntegritySummaryItem(BaseModel):
    session_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    session_status: str
    integrity_score: float
    risk_level: str
    analysis_status: AnalysisStatus
    total_signals: int
    tab_switches: int
    face_alerts: int
    is_flagged: bool
    submitted_at: Optional[datetime] = None


class PaginatedExamIntegrityResponse(BaseModel):
    exam_id: uuid.UUID
    exam_title: str
    exam_subject: str
    total_sessions: int
    average_integrity_score: float
    high_risk_count: int
    moderate_risk_count: int
    low_risk_count: int
    items: List[ExamIntegritySummaryItem]
    total: int
    page: int
    page_size: int
    pages: int
