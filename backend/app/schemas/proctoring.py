import uuid
from datetime import datetime
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, ConfigDict, computed_field

from app.models.proctoring import ProctoringEventType, EventSeverity


class ProctoringEventCreate(BaseModel):
    event_type: ProctoringEventType
    severity: Optional[EventSeverity] = EventSeverity.MEDIUM
    event_metadata: Optional[Dict[str, Any]] = None
    metadata_json: Optional[Dict[str, Any]] = None
    duration_seconds: Optional[float] = None

    model_config = ConfigDict(populate_by_name=True)


class ProctoringEventResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    event_type: ProctoringEventType
    severity: EventSeverity = EventSeverity.MEDIUM
    occurred_at: datetime
    duration_seconds: Optional[float] = None
    event_metadata: Optional[Dict[str, Any]] = None
    auto_submitted: bool = False
    is_flagged: bool = False
    flag_reason: Optional[str] = None
    tab_switch_count: int = 0
    max_tab_switches: int = 3

    @computed_field
    @property
    def timestamp(self) -> datetime:
        return self.occurred_at

    @computed_field
    @property
    def metadata_json(self) -> Optional[Dict[str, Any]]:
        return self.event_metadata

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExaminerProctoringEventItem(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    student_id: uuid.UUID
    student_name: str
    student_email: str
    event_type: ProctoringEventType
    severity: EventSeverity = EventSeverity.MEDIUM
    occurred_at: datetime
    duration_seconds: Optional[float] = None
    event_metadata: Optional[Dict[str, Any]] = None
    tab_switch_count: int = 0
    max_tab_switches: int = 3
    session_status: str = "IN_PROGRESS"
    is_flagged: bool = False
    flag_reason: Optional[str] = None

    @computed_field
    @property
    def timestamp(self) -> datetime:
        return self.occurred_at

    @computed_field
    @property
    def metadata_json(self) -> Optional[Dict[str, Any]]:
        return self.event_metadata

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class ExamProctoringSummary(BaseModel):
    total_events: int = 0
    students_monitored: int = 0
    flagged_sessions: int = 0
    auto_submitted_sessions: int = 0


class PaginatedExaminerProctoringEvents(BaseModel):
    items: List[ExaminerProctoringEventItem]
    total: int
    page: int
    page_size: int
    total_pages: int = 1
    summary: Optional[ExamProctoringSummary] = None
