from typing import List
from fastapi import APIRouter, Depends, UploadFile, File, status
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.models.user import User
from app.core.dependencies import get_current_user
from app.schemas.question import (
    CSVImportParseResponse, PDFImportParseResponse,
    ConfirmImportRequest, QuestionResponse
)
from app.services.question_import_service import question_import_service

router = APIRouter()


@router.post("/csv/parse", response_model=CSVImportParseResponse)
def parse_csv_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Parses and validates CSV file rows returning preview validation status."""
    content = file.file.read()
    return question_import_service.parse_csv(content, current_user)


@router.post("/pdf/parse", response_model=PDFImportParseResponse)
def parse_pdf_import(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Extracts questions from PDF file safely returning preview items for Examiner review."""
    content = file.file.read()
    return question_import_service.parse_pdf(content, current_user)


@router.post("/confirm", response_model=List[QuestionResponse], status_code=status.HTTP_201_CREATED)
def confirm_import(
    request_data: ConfirmImportRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk creates examiner-approved valid questions from CSV or PDF import."""
    return question_import_service.confirm_import(db, request_data, current_user)
