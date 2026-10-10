from fastapi import APIRouter, Depends
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.question import (
    AIGenerateRequest, AIGeneratedDraftsResponse,
    AIAssistRequest, AIAssistResponse
)
from app.services.ai_question_service import ai_question_service

router = APIRouter()


@router.post("/generate", response_model=AIGeneratedDraftsResponse)
def generate_questions(
    request_data: AIGenerateRequest,
    current_user: User = Depends(get_current_user)
):
    """Generates transient AI question drafts for Examiner review."""
    return ai_question_service.generate_drafts(request_data, current_user)


@router.post("/assist", response_model=AIAssistResponse)
def assist_question(
    request_data: AIAssistRequest,
    current_user: User = Depends(get_current_user)
):
    """Provides AI assistant suggestions for manual question editing."""
    return ai_question_service.assist_question(request_data, current_user)
