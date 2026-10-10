import uuid
from typing import Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.exam_session import ExamSession
from app.core.dependencies import get_current_user, require_roles
from app.schemas.identity import (
    FaceRegistrationInput,
    FaceRegistrationResponse,
    IdentityStatusResponse,
    IdentityVerificationInput,
    IdentityVerificationResponse,
)
from app.services.identity_service import identity_service

router = APIRouter()


@router.get("/student/identity/status", response_model=IdentityStatusResponse)
def get_identity_status(current_user: User = Depends(get_current_user)):
    """Returns identity face registration status and version compatibility for active student."""
    return identity_service.get_identity_status(current_user=current_user)


@router.post("/student/identity/register-face", response_model=FaceRegistrationResponse)
def register_student_face(
    payload: FaceRegistrationInput,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """
    Registers or updates face reference template for authenticated student.
    Requires explicit consent. Biometric data is stored securely in backend DB.
    """
    res = identity_service.register_student_face(
        db=db,
        student_user=current_user,
        face_embedding=payload.face_embedding,
        consent_given=payload.consent_given,
        descriptor_version=payload.descriptor_version or 2,
    )
    return res


@router.delete("/student/identity/face")
def clear_student_face(
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Clears registered face reference template for authenticated student."""
    return identity_service.clear_student_face(db=db, student_user=current_user)


@router.post("/student/sessions/{session_id}/verify-identity", response_model=IdentityVerificationResponse)
def verify_session_identity(
    session_id: uuid.UUID,
    payload: IdentityVerificationInput,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """
    Verifies live camera face embedding against authenticated student's registered face reference template.
    Returns neutral verification status.
    """
    session = (
        db.query(ExamSession)
        .filter(ExamSession.id == session_id, ExamSession.student_id == current_user.id)
        .first()
    )
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam session not found or does not belong to active student."
        )

    res = identity_service.verify_session_identity(
        db=db,
        session=session,
        student_user=current_user,
        live_embedding=payload.face_embedding,
        descriptor_version=payload.descriptor_version or 2,
    )
    return res
