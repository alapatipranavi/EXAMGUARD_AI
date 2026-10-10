import uuid
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class FaceRegistrationInput(BaseModel):
    face_embedding: List[float] = Field(..., min_length=16, description="Normalized face landmark descriptor vector")
    consent_given: bool = Field(..., description="Student explicit consent for storing face reference for identity verification")
    descriptor_version: Optional[int] = Field(default=2, description="Descriptor algorithm calibration version")


class FaceRegistrationResponse(BaseModel):
    is_face_registered: bool
    face_registered_at: datetime
    message: str
    descriptor_version: int = 2


class IdentityStatusResponse(BaseModel):
    is_face_registered: bool
    face_registered_at: Optional[datetime] = None
    descriptor_version: Optional[int] = None
    requires_re_enrollment: bool = False
    current_system_version: int = 2


class IdentityVerificationInput(BaseModel):
    face_embedding: List[float] = Field(..., min_length=16, description="Live frame face landmark descriptor vector")
    descriptor_version: Optional[int] = Field(default=2, description="Live frame descriptor algorithm version")


class IdentityVerificationResponse(BaseModel):
    verified: bool
    status: str  # "VERIFIED", "IDENTITY_MISMATCH", "CONFIRMED_MISMATCH"
    message: str
    mismatch_duration_seconds: Optional[float] = None
    similarity: Optional[float] = None
    descriptor_version: Optional[int] = None
