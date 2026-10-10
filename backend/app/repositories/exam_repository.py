import uuid
from typing import List, Optional, Tuple
from sqlalchemy.orm import Session, selectinload, joinedload
from sqlalchemy import select, func, or_

from app.models.exam import Exam, ExamQuestion, ExamStatus
from app.models.question import Question
from app.schemas.exam import ExamCreate, ExamUpdate, ExamQuestionInput


class ExamRepository:
    @staticmethod
    def calculate_total_marks(db: Session, question_inputs: List[ExamQuestionInput], creator_id: uuid.UUID) -> float:
        """Calculates total marks server-side based on question marks or marks_override."""
        if not question_inputs:
            return 0.0

        q_ids = [qi.question_id for qi in question_inputs]
        questions_by_id = {
            q.id: q for q in db.scalars(
                select(Question).where(
                    Question.id.in_(q_ids),
                    Question.created_by == creator_id,
                    Question.is_active == True
                )
            ).all()
        }

        total = 0.0
        for qi in question_inputs:
            q = questions_by_id.get(qi.question_id)
            if q:
                marks = qi.marks_override if qi.marks_override is not None else float(q.marks)
                total += marks
        return round(total, 2)

    @staticmethod
    def create_exam(
        db: Session,
        exam_data: ExamCreate,
        creator_id: uuid.UUID,
        total_marks: float
    ) -> Exam:
        """Creates a new Exam record and links initial ExamQuestions within a single transaction."""
        exam = Exam(
            title=exam_data.title.strip(),
            description=exam_data.description.strip() if exam_data.description else None,
            subject=exam_data.subject.strip(),
            instructions=exam_data.instructions.strip() if exam_data.instructions else None,
            created_by=creator_id,
            duration_minutes=exam_data.duration_minutes,
            start_at=exam_data.start_at,
            end_at=exam_data.end_at,
            total_marks=total_marks,
            passing_marks=exam_data.passing_marks,
            negative_marking_enabled=exam_data.negative_marking_enabled,
            randomize_questions=exam_data.randomize_questions,
            randomize_options=exam_data.randomize_options,
            proctoring_enabled=exam_data.proctoring_enabled,
            max_tab_switches=exam_data.max_tab_switches if exam_data.max_tab_switches is not None else 3,
            status=ExamStatus.DRAFT,
            target_type=exam_data.target_type,
            target_department_id=exam_data.target_department_id,
            target_year_of_study=exam_data.target_year_of_study,
            target_section_id=exam_data.target_section_id
        )
        db.add(exam)
        db.flush()

        if exam_data.questions:
            # Preserve order provided
            for idx, qi in enumerate(sorted(exam_data.questions, key=lambda x: x.question_order)):
                eq = ExamQuestion(
                    exam_id=exam.id,
                    question_id=qi.question_id,
                    question_order=idx + 1,
                    marks_override=qi.marks_override
                )
                db.add(eq)

        if exam_data.target_student_ids:
            from app.models.exam import ExamTargetStudent
            for sid in set(exam_data.target_student_ids):
                target_stub = ExamTargetStudent(exam_id=exam.id, student_id=sid)
                db.add(target_stub)

        db.commit()
        db.refresh(exam)
        return ExamRepository.get_exam_by_id(db, exam.id)

    @staticmethod
    def get_exam_by_id(db: Session, exam_id: uuid.UUID) -> Optional[Exam]:
        """Fetches Exam by ID with eagerly loaded questions and question options."""
        stmt = (
            select(Exam)
            .where(Exam.id == exam_id)
            .options(
                selectinload(Exam.exam_questions).selectinload(ExamQuestion.question).selectinload(Question.options)
            )
        )
        return db.scalar(stmt)

    @staticmethod
    def list_exams(
        db: Session,
        creator_id: Optional[uuid.UUID] = None,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        status: Optional[ExamStatus] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Exam], int]:
        """Lists exams owned by creator_id (or all platform exams if None) with filtering and pagination."""
        query = select(Exam)
        if creator_id is not None:
            query = query.where(Exam.created_by == creator_id)

        if search:
            pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Exam.title.ilike(pattern),
                    Exam.subject.ilike(pattern),
                    Exam.description.ilike(pattern)
                )
            )

        if subject:
            query = query.where(Exam.subject.ilike(f"%{subject.strip()}%"))

        if status:
            query = query.where(Exam.status == status)

        # Count total
        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        # Paginate & order by newest created
        offset = (page - 1) * page_size
        paginated_query = (
            query.order_by(Exam.created_at.desc())
            .offset(offset)
            .limit(page_size)
            .options(
                selectinload(Exam.exam_questions).selectinload(ExamQuestion.question).selectinload(Question.options)
            )
        )

        exams = db.scalars(paginated_query).all()
        return list(exams), total

    @staticmethod
    def update_exam(
        db: Session,
        exam: Exam,
        update_data: ExamUpdate,
        calculated_total_marks: Optional[float] = None
    ) -> Exam:
        """Updates DRAFT exam fields and linked questions transactionally."""
        if update_data.title is not None:
            exam.title = update_data.title.strip()
        if update_data.description is not None:
            exam.description = update_data.description.strip() if update_data.description else None
        if update_data.subject is not None:
            exam.subject = update_data.subject.strip()
        if update_data.instructions is not None:
            exam.instructions = update_data.instructions.strip() if update_data.instructions else None
        if update_data.duration_minutes is not None:
            exam.duration_minutes = update_data.duration_minutes
        if update_data.start_at is not None:
            exam.start_at = update_data.start_at
        if update_data.end_at is not None:
            exam.end_at = update_data.end_at
        if update_data.passing_marks is not None:
            exam.passing_marks = update_data.passing_marks
        if update_data.negative_marking_enabled is not None:
            exam.negative_marking_enabled = update_data.negative_marking_enabled
        if update_data.randomize_questions is not None:
            exam.randomize_questions = update_data.randomize_questions
        if update_data.randomize_options is not None:
            exam.randomize_options = update_data.randomize_options
        if update_data.proctoring_enabled is not None:
            exam.proctoring_enabled = update_data.proctoring_enabled
        if update_data.max_tab_switches is not None:
            exam.max_tab_switches = update_data.max_tab_switches
        if update_data.target_type is not None:
            exam.target_type = update_data.target_type
        if update_data.target_department_id is not None:
            exam.target_department_id = update_data.target_department_id
        if update_data.target_year_of_study is not None:
            exam.target_year_of_study = update_data.target_year_of_study
        if update_data.target_section_id is not None:
            exam.target_section_id = update_data.target_section_id

        if update_data.questions is not None:
            # Clear existing questions
            db.query(ExamQuestion).filter(ExamQuestion.exam_id == exam.id).delete(synchronize_session=False)

            # Insert updated questions with preserved ordering
            for idx, qi in enumerate(sorted(update_data.questions, key=lambda x: x.question_order)):
                eq = ExamQuestion(
                    exam_id=exam.id,
                    question_id=qi.question_id,
                    question_order=idx + 1,
                    marks_override=qi.marks_override
                )
                db.add(eq)

            if calculated_total_marks is not None:
                exam.total_marks = calculated_total_marks

        if update_data.target_student_ids is not None:
            from app.models.exam import ExamTargetStudent
            db.query(ExamTargetStudent).filter(ExamTargetStudent.exam_id == exam.id).delete(synchronize_session=False)
            for sid in set(update_data.target_student_ids):
                db.add(ExamTargetStudent(exam_id=exam.id, student_id=sid))

        db.commit()
        db.refresh(exam)
        return ExamRepository.get_exam_by_id(db, exam.id)

    @staticmethod
    def update_status(db: Session, exam: Exam, new_status: ExamStatus) -> Exam:
        """Updates exam status lifecycle field."""
        exam.status = new_status
        db.commit()
        db.refresh(exam)
        return ExamRepository.get_exam_by_id(db, exam.id)

    @staticmethod
    def delete_exam(db: Session, exam: Exam) -> None:
        """Permanently deletes a draft exam and its associated exam_questions."""
        db.delete(exam)
        db.commit()
