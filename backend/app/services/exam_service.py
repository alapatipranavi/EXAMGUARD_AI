import math
import uuid
from typing import List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.models.exam import Exam, ExamStatus
from app.models.question import Question
from app.models.user import User, UserRole
from app.schemas.exam import ExamCreate, ExamUpdate, ExamQuestionInput, PaginatedExamResponse, ExamResponse
from app.repositories.exam_repository import ExamRepository
from app.repositories.academic_repository import academic_repository


class ExamService:
    @staticmethod
    def build_exam_response(db: Session, exam: Exam) -> ExamResponse:
        """Converts an Exam model into ExamResponse with populated target_student_ids and eligible_students_count."""
        target_student_ids = [ts.student_id for ts in exam.target_students] if exam.target_students else []

        examiner = db.scalar(select(User).where(User.id == exam.created_by))
        college_id = examiner.college_id if examiner else None

        eligible_count = academic_repository.count_eligible_students(
            db=db,
            college_id=college_id,
            target_type=exam.target_type,
            department_id=exam.target_department_id,
            year_of_study=exam.target_year_of_study,
            section_id=exam.target_section_id,
            specific_student_ids=target_student_ids
        )

        response = ExamResponse.model_validate(exam)
        response.target_student_ids = target_student_ids
        response.eligible_students_count = eligible_count
        return response
    @staticmethod
    def _verify_examiner_role(current_user: User):
        """Ensures the authenticated user has Examiner role."""
        if current_user.role != UserRole.EXAMINER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exam management features are restricted to Examiners."
            )

    @staticmethod
    def _verify_exam_ownership(exam: Optional[Exam], current_user: User) -> Exam:
        """Ensures the exam exists and belongs to the authenticated Examiner."""
        if not exam or exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found."
            )
        return exam

    @staticmethod
    def _validate_question_selection(db: Session, question_inputs: List[ExamQuestionInput], creator_id: uuid.UUID):
        """Verifies that selected questions are unique, active, and owned by the Examiner."""
        if not question_inputs:
            return

        # Check for duplicates in payload
        q_ids = [qi.question_id for qi in question_inputs]
        if len(q_ids) != len(set(q_ids)):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Duplicate questions cannot be added to the same exam."
            )

        # Query database for matching active questions owned by creator_id
        valid_questions = db.scalars(
            select(Question).where(
                Question.id.in_(q_ids),
                Question.created_by == creator_id,
                Question.is_active == True
            )
        ).all()

        valid_ids = {q.id for q in valid_questions}
        missing_ids = set(q_ids) - valid_ids
        if missing_ids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="One or more selected questions are invalid, inactive, or owned by another Examiner."
            )

    @staticmethod
    def _validate_examiner_targeting_scope(
        db: Session,
        current_user: User,
        target_department_id: Optional[uuid.UUID] = None,
        target_section_id: Optional[uuid.UUID] = None,
        target_student_ids: Optional[List[uuid.UUID]] = None
    ):
        """Ensures that an Examiner with a college_id cannot target departments, sections, or students from another college."""
        if current_user.role == UserRole.EXAMINER and current_user.college_id:
            if target_department_id:
                dept = academic_repository.get_department_by_id(db, target_department_id)
                if not dept or dept.college_id != current_user.college_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Examiners cannot target departments outside their assigned college."
                    )

            if target_section_id:
                sec = academic_repository.get_section_by_id(db, target_section_id)
                if not sec or not sec.department or sec.department.college_id != current_user.college_id:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Examiners cannot target sections outside their assigned college."
                    )

            if target_student_ids:
                students = db.scalars(
                    select(User).where(User.id.in_(target_student_ids))
                ).all()
                for st in students:
                    if st.college_id != current_user.college_id:
                        raise HTTPException(
                            status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f"Examiners cannot target student '{st.email}' who belongs to another college."
                        )

    @staticmethod
    def create_exam(db: Session, exam_data: ExamCreate, current_user: User) -> ExamResponse:
        """Creates a new Exam in DRAFT status."""
        ExamService._verify_examiner_role(current_user)

        if not exam_data.title.strip() or not exam_data.subject.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam title and subject are required."
            )

        if exam_data.duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam duration must be greater than 0 minutes."
            )

        if exam_data.start_at and exam_data.end_at and exam_data.end_at <= exam_data.start_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam end time must be after start time."
            )

        # Validate examiner college targeting scope
        ExamService._validate_examiner_targeting_scope(
            db=db,
            current_user=current_user,
            target_department_id=exam_data.target_department_id,
            target_section_id=exam_data.target_section_id,
            target_student_ids=exam_data.target_student_ids,
        )

        # Validate question selection & calculate server-side total marks
        ExamService._validate_question_selection(db, exam_data.questions, current_user.id)
        calculated_total_marks = ExamRepository.calculate_total_marks(db, exam_data.questions, current_user.id)

        if exam_data.passing_marks < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passing marks cannot be negative."
            )

        if calculated_total_marks > 0 and exam_data.passing_marks > calculated_total_marks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Passing marks ({exam_data.passing_marks}) cannot exceed total marks ({calculated_total_marks})."
            )

        created_exam = ExamRepository.create_exam(
            db=db,
            exam_data=exam_data,
            creator_id=current_user.id,
            total_marks=calculated_total_marks
        )
        return ExamService.build_exam_response(db, created_exam)

    @staticmethod
    def get_exam(db: Session, exam_id: uuid.UUID, current_user: User) -> ExamResponse:
        """Retrieves an exam owned by the authenticated Examiner or viewed by Admin."""
        if current_user.role not in [UserRole.EXAMINER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exam management features are restricted to Examiners and Administrators."
            )
        exam = ExamRepository.get_exam_by_id(db, exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found."
            )
        if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found."
            )
        return ExamService.build_exam_response(db, exam)

    @staticmethod
    def list_exams(
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        status_filter: Optional[ExamStatus] = None,
        page: int = 1,
        page_size: int = 10
    ) -> PaginatedExamResponse:
        """Lists exams owned by current Examiner, or all platform exams if Admin."""
        if current_user.role not in [UserRole.EXAMINER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Exam management features are restricted to Examiners and Administrators."
            )

        creator_id = current_user.id if current_user.role == UserRole.EXAMINER else None

        exams, total = ExamRepository.list_exams(
            db=db,
            creator_id=creator_id,
            search=search,
            subject=subject,
            status=status_filter,
            page=page,
            page_size=page_size
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 1
        return PaginatedExamResponse(
            items=[ExamService.build_exam_response(db, e) for e in exams],
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def update_exam(db: Session, exam_id: uuid.UUID, update_data: ExamUpdate, current_user: User) -> ExamResponse:
        """Updates a DRAFT exam record."""
        ExamService._verify_examiner_role(current_user)
        exam = ExamRepository.get_exam_by_id(db, exam_id)
        exam = ExamService._verify_exam_ownership(exam, current_user)

        if exam.status != ExamStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exams in {exam.status.value} status cannot be edited. Only DRAFT exams can be modified."
            )

        # Validate examiner college targeting scope
        ExamService._validate_examiner_targeting_scope(
            db=db,
            current_user=current_user,
            target_department_id=update_data.target_department_id,
            target_section_id=update_data.target_section_id,
            target_student_ids=update_data.target_student_ids,
        )

        calculated_total_marks = None
        if update_data.questions is not None:
            ExamService._validate_question_selection(db, update_data.questions, current_user.id)
            calculated_total_marks = ExamRepository.calculate_total_marks(db, update_data.questions, current_user.id)

        target_total = calculated_total_marks if calculated_total_marks is not None else float(exam.total_marks)
        target_passing = update_data.passing_marks if update_data.passing_marks is not None else float(exam.passing_marks)

        if target_passing < 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Passing marks cannot be negative."
            )

        if target_total > 0 and target_passing > target_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Passing marks ({target_passing}) cannot exceed total marks ({target_total})."
            )

        target_start = update_data.start_at if update_data.start_at is not None else exam.start_at
        target_end = update_data.end_at if update_data.end_at is not None else exam.end_at
        if target_start and target_end and target_end <= target_start:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam end time must be after start time."
            )

        updated_exam = ExamRepository.update_exam(
            db=db,
            exam=exam,
            update_data=update_data,
            calculated_total_marks=calculated_total_marks
        )
        return ExamService.build_exam_response(db, updated_exam)

    @staticmethod
    def publish_exam(db: Session, exam_id: uuid.UUID, current_user: User) -> ExamResponse:
        """Validates and publishes a DRAFT exam."""
        ExamService._verify_examiner_role(current_user)
        exam = ExamRepository.get_exam_by_id(db, exam_id)
        exam = ExamService._verify_exam_ownership(exam, current_user)

        if exam.status != ExamStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exam is already in {exam.status.value} status."
            )

        # Strict Publish Validation Rules
        if not exam.title or not exam.title.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish exam: Title is required."
            )

        if not exam.subject or not exam.subject.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish exam: Subject is required."
            )

        if exam.duration_minutes <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish exam: Duration must be greater than 0 minutes."
            )

        if not exam.exam_questions or len(exam.exam_questions) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish exam: At least one active question must be selected."
            )

        # Re-validate all linked questions: must all be active & owned by current_user
        q_inputs = [
            ExamQuestionInput(question_id=eq.question_id, question_order=eq.question_order, marks_override=float(eq.marks_override) if eq.marks_override else None)
            for eq in exam.exam_questions
        ]
        ExamService._validate_question_selection(db, q_inputs, current_user.id)

        current_total = ExamRepository.calculate_total_marks(db, q_inputs, current_user.id)
        if current_total <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot publish exam: Total marks must be greater than 0."
            )

        if float(exam.passing_marks) > current_total:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot publish exam: Passing marks ({exam.passing_marks}) exceed total marks ({current_total})."
            )

        target_status = ExamStatus.PUBLISHED
        published_exam = ExamRepository.update_status(db, exam, target_status)
        return ExamService.build_exam_response(db, published_exam)

    @staticmethod
    def archive_exam(db: Session, exam_id: uuid.UUID, current_user: User) -> ExamResponse:
        """Archives an exam (soft delete)."""
        ExamService._verify_examiner_role(current_user)
        exam = ExamRepository.get_exam_by_id(db, exam_id)
        exam = ExamService._verify_exam_ownership(exam, current_user)

        if exam.status == ExamStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam is already archived."
            )

        archived_exam = ExamRepository.update_status(db, exam, ExamStatus.ARCHIVED)
        return ExamService.build_exam_response(db, archived_exam)

    @staticmethod
    def unarchive_exam(db: Session, exam_id: uuid.UUID, current_user: User) -> ExamResponse:
        """Unarchives an archived exam and reverts its status to DRAFT."""
        ExamService._verify_examiner_role(current_user)
        exam = ExamRepository.get_exam_by_id(db, exam_id)
        exam = ExamService._verify_exam_ownership(exam, current_user)

        if exam.status != ExamStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot unarchive exam in {exam.status.value} status. Only ARCHIVED exams can be unarchived."
            )

        unarchived_exam = ExamRepository.update_status(db, exam, ExamStatus.DRAFT)
        return ExamService.build_exam_response(db, unarchived_exam)

    @staticmethod
    def delete_exam(db: Session, exam_id: uuid.UUID, current_user: User) -> None:
        """Permanently deletes a DRAFT exam and its associated exam_questions."""
        ExamService._verify_examiner_role(current_user)
        exam = ExamRepository.get_exam_by_id(db, exam_id)
        exam = ExamService._verify_exam_ownership(exam, current_user)

        if exam.status == ExamStatus.PUBLISHED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Published exams cannot be deleted. Archive the exam instead."
            )

        if exam.status == ExamStatus.ARCHIVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Archived exams cannot be deleted."
            )

        if exam.status != ExamStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Exams in {exam.status.value} status cannot be deleted."
            )

        ExamRepository.delete_exam(db, exam)


exam_service = ExamService()
