import uuid
import random
from datetime import datetime, timezone, timedelta
from typing import List, Optional, Tuple
from sqlalchemy import select, func, or_
from sqlalchemy.orm import Session, joinedload

from app.models.exam import Exam, ExamStatus, ExamQuestion
from app.models.exam_session import ExamSession, SessionStatus
from app.models.answer import StudentAnswer, AnswerSelectedOption
from app.models.question import Question, QuestionOption


class StudentExamRepository:
    def list_published_exams(
        self,
        db: Session,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> Tuple[List[Exam], int]:
        """Lists published exams that have at least one question."""
        stmt = (
            select(Exam)
            .where(Exam.status == ExamStatus.PUBLISHED)
            .where(Exam.exam_questions.any())
        )

        if search:
            pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Exam.title.ilike(pattern),
                    Exam.subject.ilike(pattern),
                    Exam.description.ilike(pattern),
                )
            )

        if subject:
            stmt = stmt.where(Exam.subject.ilike(f"%{subject}%"))

        count_stmt = select(func.count()).select_from(stmt.subquery())
        total = db.scalar(count_stmt) or 0

        stmt = stmt.order_by(Exam.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        exams = list(db.scalars(stmt).all())

        return exams, total

    def get_published_exam_by_id(self, db: Session, exam_id: uuid.UUID) -> Optional[Exam]:
        """Fetches a published exam with its questions."""
        stmt = (
            select(Exam)
            .options(
                joinedload(Exam.exam_questions).joinedload(ExamQuestion.question).joinedload(Question.options)
            )
            .where(Exam.id == exam_id)
            .where(Exam.status == ExamStatus.PUBLISHED)
        )
        return db.scalar(stmt)

    def get_sessions_for_student(self, db: Session, student_id: uuid.UUID) -> List[ExamSession]:
        """Fetches all exam sessions for a student."""
        stmt = select(ExamSession).where(ExamSession.student_id == student_id)
        return list(db.scalars(stmt).all())

    def get_active_session(self, db: Session, exam_id: uuid.UUID, student_id: uuid.UUID) -> Optional[ExamSession]:
        """Gets active session (IN_PROGRESS or CREATED) for a student and exam."""
        stmt = (
            select(ExamSession)
            .where(ExamSession.exam_id == exam_id)
            .where(ExamSession.student_id == student_id)
            .where(ExamSession.status.in_([SessionStatus.CREATED, SessionStatus.IN_PROGRESS]))
            .order_by(ExamSession.created_at.desc())
        )
        return db.scalar(stmt)

    def get_latest_session(self, db: Session, exam_id: uuid.UUID, student_id: uuid.UUID) -> Optional[ExamSession]:
        """Gets latest session for a student and exam regardless of status."""
        stmt = (
            select(ExamSession)
            .where(ExamSession.exam_id == exam_id)
            .where(ExamSession.student_id == student_id)
            .order_by(ExamSession.created_at.desc())
        )
        return db.scalar(stmt)

    def get_session_by_id(self, db: Session, session_id: uuid.UUID) -> Optional[ExamSession]:
        """Gets session by ID with relationships preloaded."""
        stmt = (
            select(ExamSession)
            .options(
                joinedload(ExamSession.exam).joinedload(Exam.exam_questions).joinedload(ExamQuestion.question).joinedload(Question.options),
                joinedload(ExamSession.answers).joinedload(StudentAnswer.selected_options),
            )
            .where(ExamSession.id == session_id)
        )
        return db.scalar(stmt)

    def create_session(
        self,
        db: Session,
        exam_id: uuid.UUID,
        student_id: uuid.UUID,
        duration_minutes: int,
        question_ids_order: List[uuid.UUID],
    ) -> ExamSession:
        """Creates a new exam session."""
        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(minutes=duration_minutes)

        metadata = {
            "question_order": [str(qid) for qid in question_ids_order]
        }

        session = ExamSession(
            exam_id=exam_id,
            student_id=student_id,
            started_at=now,
            expires_at=expires_at,
            status=SessionStatus.IN_PROGRESS,
            session_metadata=metadata,
        )

        db.add(session)
        db.commit()
        db.refresh(session)
        return session

    def save_answer(
        self,
        db: Session,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        selected_option_ids: List[uuid.UUID],
        text_answer: Optional[str],
    ) -> StudentAnswer:
        """Upserts a student answer for a specific question in a session."""
        stmt = (
            select(StudentAnswer)
            .where(StudentAnswer.session_id == session_id)
            .where(StudentAnswer.question_id == question_id)
        )
        answer = db.scalar(stmt)

        now = datetime.now(timezone.utc)

        if not answer:
            answer = StudentAnswer(
                session_id=session_id,
                question_id=question_id,
                text_answer=text_answer,
                submitted_at=now,
            )
            db.add(answer)
            db.flush()
        else:
            answer.text_answer = text_answer
            answer.updated_at = now

        # Delete existing selected options
        db.query(AnswerSelectedOption).filter(AnswerSelectedOption.answer_id == answer.id).delete(synchronize_session=False)

        # Add new selected options
        for opt_id in selected_option_ids:
            sel_opt = AnswerSelectedOption(
                answer_id=answer.id,
                option_id=opt_id,
            )
            db.add(sel_opt)

        db.commit()
        db.refresh(answer)
        return answer

    def submit_session(self, db: Session, session: ExamSession, auto_submitted: bool = False) -> ExamSession:
        """Submits an exam session."""
        now = datetime.now(timezone.utc)
        session.status = SessionStatus.AUTO_SUBMITTED if auto_submitted else SessionStatus.SUBMITTED
        session.submitted_at = now
        session.updated_at = now

        db.commit()
        db.refresh(session)
        return session

    def expire_session(self, db: Session, session: ExamSession) -> ExamSession:
        """Marks an expired session as AUTO_SUBMITTED or EXPIRED."""
        now = datetime.now(timezone.utc)
        session.status = SessionStatus.EXPIRED
        session.submitted_at = session.expires_at or now
        session.updated_at = now

        db.commit()
        db.refresh(session)
        return session

    def toggle_mark_for_review(
        self, db: Session, session: ExamSession, question_id: uuid.UUID, marked: bool
    ) -> ExamSession:
        """Toggles a question's marked-for-review state in session metadata."""
        meta = dict(session.session_metadata or {})
        marked_list = list(meta.get("marked_for_review", []))
        qstr = str(question_id)

        if marked:
            if qstr not in marked_list:
                marked_list.append(qstr)
        else:
            if qstr in marked_list:
                marked_list.remove(qstr)

        meta["marked_for_review"] = marked_list
        session.session_metadata = meta

        db.commit()
        db.refresh(session)
        return session


student_exam_repository = StudentExamRepository()
