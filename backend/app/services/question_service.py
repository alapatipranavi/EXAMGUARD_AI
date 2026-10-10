import uuid
import math
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.question import Question, QuestionType, QuestionSource
from app.schemas.question import (
    QuestionCreate, QuestionUpdate, QuestionResponse, PaginatedQuestionResponse
)
from app.repositories.question_repository import question_repository


class QuestionService:
    @staticmethod
    def _verify_examiner_role(current_user: User):
        """Ensures the authenticated user has the EXAMINER role. Rejects ADMIN and STUDENT."""
        if current_user.role != UserRole.EXAMINER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Question management is restricted to Examiners."
            )

    @staticmethod
    def _verify_question_ownership(question: Question, current_user: User):
        """Ensures the question belongs to the authenticated Examiner."""
        if question.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: you do not own this question."
            )

    @staticmethod
    def create_question(db: Session, question_data: QuestionCreate, current_user: User) -> Question:
        """Creates a new Question owned by the current Examiner."""
        QuestionService._verify_examiner_role(current_user)
        return question_repository.create_question(db, question_data, current_user.id)

    @staticmethod
    def get_question(db: Session, question_id: uuid.UUID, current_user: User) -> Question:
        """Fetches a Question entity ensuring ownership."""
        QuestionService._verify_examiner_role(current_user)
        question = question_repository.get_by_id(db, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found."
            )
        QuestionService._verify_question_ownership(question, current_user)
        return question

    @staticmethod
    def list_questions(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        question_type: Optional[QuestionType] = None,
        difficulty: Optional[str] = None,
        source: Optional[QuestionSource] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10
    ) -> PaginatedQuestionResponse:
        """Returns paginated questions owned by current Examiner."""
        QuestionService._verify_examiner_role(current_user)

        items, total = question_repository.list_questions(
            db=db,
            creator_id=current_user.id,
            search=search,
            subject=subject,
            topic=topic,
            question_type=question_type,
            difficulty=difficulty,
            source=source,
            is_active=is_active,
            page=page,
            page_size=page_size
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedQuestionResponse(
            items=[QuestionResponse.model_validate(q) for q in items],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def update_question(
        db: Session,
        question_id: uuid.UUID,
        update_data: QuestionUpdate,
        current_user: User
    ) -> Question:
        """Updates scalar fields & options of a question owned by current Examiner."""
        QuestionService._verify_examiner_role(current_user)
        question = question_repository.get_by_id(db, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found."
            )
        QuestionService._verify_question_ownership(question, current_user)

        # Validate options against question_type
        effective_type = update_data.question_type or question.question_type
        effective_options = update_data.options if update_data.options is not None else [
            opt for opt in question.options
        ]

        if effective_type == QuestionType.MCQ:
            if len(effective_options) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MCQ questions require at least 2 options."
                )
            correct_count = sum(1 for o in effective_options if getattr(o, "is_correct", False))
            if correct_count != 1:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"MCQ questions require exactly 1 correct option (found {correct_count})."
                )

        elif effective_type == QuestionType.MULTI_SELECT:
            if len(effective_options) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="MULTI_SELECT questions require at least 2 options."
                )
            correct_count = sum(1 for o in effective_options if getattr(o, "is_correct", False))
            if correct_count < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"MULTI_SELECT questions require at least 2 correct options (found {correct_count})."
                )

        elif effective_type in (QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER, QuestionType.HANDWRITTEN):
            update_data.options = None

        update_dict = update_data.model_dump(exclude_unset=True, exclude={"options"})
        return question_repository.update_question(db, question, update_dict, update_data.options)

    @staticmethod
    def archive_question(db: Session, question_id: uuid.UUID, current_user: User) -> Question:
        """Soft-deletes a question setting is_active = False."""
        QuestionService._verify_examiner_role(current_user)
        question = question_repository.get_by_id(db, question_id)
        if not question:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question not found."
            )
        QuestionService._verify_question_ownership(question, current_user)

        return question_repository.archive_question(db, question)


question_service = QuestionService()
