import uuid
from typing import List, Optional, Tuple, Dict, Any
from sqlalchemy.orm import Session, selectinload
from sqlalchemy import select, func, or_

from app.models.question import Question, QuestionOption, QuestionType, DifficultyLevel, QuestionSource
from app.models.user import User, UserRole
from app.schemas.question import QuestionCreate, QuestionOptionCreate


class QuestionRepository:
    @staticmethod
    def create_question(db: Session, question_data: QuestionCreate, creator_id: uuid.UUID) -> Question:
        """Creates a new Question record and associated options within a single database transaction."""
        question = Question(
            question_text=question_data.question_text,
            question_type=question_data.question_type,
            subject=question_data.subject,
            topic=question_data.topic,
            difficulty=question_data.difficulty,
            source=question_data.source or QuestionSource.MANUAL,
            marks=question_data.marks,
            negative_marks=question_data.negative_marks,
            model_answer=question_data.model_answer,
            explanation=question_data.explanation,
            created_by=creator_id,
            is_active=True
        )
        db.add(question)
        db.flush()

        if question_data.options:
            for opt in question_data.options:
                option_record = QuestionOption(
                    question_id=question.id,
                    option_text=opt.option_text,
                    option_order=opt.option_order,
                    is_correct=opt.is_correct
                )
                db.add(option_record)

        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def bulk_create_questions(db: Session, questions_data: List[QuestionCreate], creator_id: uuid.UUID) -> List[Question]:
        """Bulk inserts multiple Question records within a single atomic transaction."""
        created_questions = []
        for q_data in questions_data:
            question = Question(
                question_text=q_data.question_text,
                question_type=q_data.question_type,
                subject=q_data.subject,
                topic=q_data.topic,
                difficulty=q_data.difficulty,
                source=q_data.source,
                marks=q_data.marks,
                negative_marks=q_data.negative_marks,
                model_answer=q_data.model_answer,
                explanation=q_data.explanation,
                created_by=creator_id,
                is_active=True
            )
            db.add(question)
            db.flush()

            if q_data.options:
                for opt in q_data.options:
                    option_record = QuestionOption(
                        question_id=question.id,
                        option_text=opt.option_text,
                        option_order=opt.option_order,
                        is_correct=opt.is_correct
                    )
                    db.add(option_record)

            created_questions.append(question)

        db.commit()
        for q in created_questions:
            db.refresh(q)
        return created_questions

    @staticmethod
    def get_by_id(db: Session, question_id: uuid.UUID) -> Optional[Question]:
        """Fetches a Question entity by ID eager loading options."""
        statement = (
            select(Question)
            .where(Question.id == question_id)
            .options(selectinload(Question.options))
        )
        return db.scalar(statement)

    @staticmethod
    def list_questions(
        db: Session,
        creator_id: uuid.UUID,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        topic: Optional[str] = None,
        question_type: Optional[QuestionType] = None,
        difficulty: Optional[DifficultyLevel] = None,
        source: Optional[QuestionSource] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10
    ) -> Tuple[List[Question], int]:
        """Queries questions owned by creator_id with server-side filtering and database pagination."""
        query = select(Question).where(Question.created_by == creator_id)

        if is_active is not None:
            query = query.where(Question.is_active == is_active)

        if subject:
            query = query.where(Question.subject.ilike(f"%{subject.strip()}%"))

        if topic:
            query = query.where(Question.topic.ilike(f"%{topic.strip()}%"))

        if question_type:
            query = query.where(Question.question_type == question_type)

        if difficulty:
            query = query.where(Question.difficulty == difficulty)

        if source:
            query = query.where(Question.source == source)

        if search and search.strip():
            search_pattern = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Question.question_text.ilike(search_pattern),
                    Question.subject.ilike(search_pattern),
                    Question.topic.ilike(search_pattern)
                )
            )

        count_query = select(func.count()).select_from(query.subquery())
        total = db.scalar(count_query) or 0

        offset = (page - 1) * page_size
        items_query = (
            query
            .options(selectinload(Question.options))
            .order_by(Question.created_at.desc())
            .offset(offset)
            .limit(page_size)
        )
        items = list(db.scalars(items_query).all())

        return items, total

    @staticmethod
    def get_examiner_stats(db: Session, examiner_id: uuid.UUID) -> Dict[str, Any]:
        """Returns Question Bank and Exam summary metrics for an Examiner."""
        from app.models.exam import Exam, ExamStatus

        total_q = db.scalar(select(func.count(Question.id)).where(Question.created_by == examiner_id)) or 0
        active_q = db.scalar(select(func.count(Question.id)).where(Question.created_by == examiner_id, Question.is_active == True)) or 0
        archived_q = total_q - active_q

        # Real Exam Stats
        total_e = db.scalar(select(func.count(Exam.id)).where(Exam.created_by == examiner_id)) or 0
        draft_e = db.scalar(select(func.count(Exam.id)).where(Exam.created_by == examiner_id, Exam.status == ExamStatus.DRAFT)) or 0
        published_e = db.scalar(select(func.count(Exam.id)).where(Exam.created_by == examiner_id, Exam.status == ExamStatus.PUBLISHED)) or 0
        archived_e = db.scalar(select(func.count(Exam.id)).where(Exam.created_by == examiner_id, Exam.status == ExamStatus.ARCHIVED)) or 0

        # Question types breakdown
        types_res = db.execute(
            select(Question.question_type, func.count(Question.id))
            .where(Question.created_by == examiner_id)
            .group_by(Question.question_type)
        ).all()
        types_breakdown = {str(row[0]): row[1] for row in types_res}

        # Sources breakdown
        sources_res = db.execute(
            select(Question.source, func.count(Question.id))
            .where(Question.created_by == examiner_id)
            .group_by(Question.source)
        ).all()
        sources_breakdown = {str(row[0]): row[1] for row in sources_res}

        return {
            "total_questions": total_q,
            "active_questions": active_q,
            "archived_questions": archived_q,
            "total_exams": total_e,
            "draft_exams": draft_e,
            "published_exams": published_e,
            "archived_exams": archived_e,
            "types_breakdown": types_breakdown,
            "sources_breakdown": sources_breakdown,
        }

    @staticmethod
    def get_admin_stats(db: Session) -> Dict[str, Any]:
        """Returns system platform user counts for Admin dashboard."""
        total_students = db.scalar(select(func.count(User.id)).where(User.role == UserRole.STUDENT)) or 0
        total_examiners = db.scalar(select(func.count(User.id)).where(User.role == UserRole.EXAMINER)) or 0

        return {
            "total_students": total_students,
            "total_examiners": total_examiners,
            "active_exams": 0,
            "completed_exams": 0,
        }

    @staticmethod
    def update_question(
        db: Session,
        question: Question,
        update_fields: dict,
        new_options: Optional[List[QuestionOptionCreate]] = None
    ) -> Question:
        """Updates scalar fields and replaces options in a transaction."""
        for key, value in update_fields.items():
            if value is not None:
                setattr(question, key, value)

        if new_options is not None:
            for opt in list(question.options):
                db.delete(opt)
            db.flush()

            for opt_data in new_options:
                new_opt = QuestionOption(
                    question_id=question.id,
                    option_text=opt_data.option_text,
                    option_order=opt_data.option_order,
                    is_correct=opt_data.is_correct
                )
                db.add(new_opt)

        db.commit()
        db.refresh(question)
        return question

    @staticmethod
    def archive_question(db: Session, question: Question) -> Question:
        """Soft-deletes a question by setting is_active = False."""
        question.is_active = False
        db.commit()
        db.refresh(question)
        return question


question_repository = QuestionRepository()
