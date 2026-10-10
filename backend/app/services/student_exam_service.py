import os
import math
import uuid
import random
import base64
import logging
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamStatus, ExamQuestion
from app.models.exam_session import ExamSession, SessionStatus
from app.models.question import Question, QuestionType
from app.models.answer import StudentAnswer
from app.models.evaluation import EvaluationResult, EvaluatorType, EvaluationStatus
from app.repositories.student_exam_repository import student_exam_repository
from app.services.evaluation_service import evaluation_service
from app.services.handwritten_ocr_service import handwritten_ocr_service, OCRStatus
from app.services.ai_subjective_evaluation_service import ai_subjective_evaluation_service
from app.schemas.student_exam import (
    StudentExamItem,
    PaginatedStudentExamResponse,
    StudentExamDetail,
    StudentQuestionResponse,
    StudentQuestionOptionResponse,
    StudentAnswerSaveInput,
    HandwrittenAnswerInput,
    HandwrittenAnswerProcessResponse,
    ReviewToggleInput,
    StudentAnswerResponse,
    ExamSessionResponse,
)

logger = logging.getLogger(__name__)


def _ensure_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class StudentExamService:
    def _verify_student_role(self, current_user: User) -> None:
        """Enforces that the current user is a STUDENT."""
        if current_user.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only students can perform this action.",
            )

    def list_student_exams(
        self,
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedStudentExamResponse:
        self._verify_student_role(current_user)
        from app.repositories.academic_repository import academic_repository

        raw_exams, _ = student_exam_repository.list_published_exams(
            db, search=search, subject=subject, page=1, page_size=1000
        )

        exams = [e for e in raw_exams if academic_repository.is_student_authorized_for_exam(db, current_user, e)]
        total = len(exams)

        start_idx = (page - 1) * page_size
        paginated_exams = exams[start_idx:start_idx + page_size]

        student_sessions = student_exam_repository.get_sessions_for_student(db, current_user.id)
        session_map = {}
        for s in student_sessions:
            if s.exam_id not in session_map or s.created_at > session_map[s.exam_id].created_at:
                session_map[s.exam_id] = s

        items = []
        for exam in paginated_exams:
            session = session_map.get(exam.id)
            if not session:
                sess_status = "AVAILABLE"
                active_sid = None
                id_status = None
            elif session.status in [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]:
                sess_status = "IN_PROGRESS"
                active_sid = session.id
                id_status = session.identity_verification_status or "UNVERIFIED"
            else:
                sess_status = "COMPLETED"
                active_sid = session.id
                id_status = session.identity_verification_status or "UNVERIFIED"

            items.append(
                StudentExamItem(
                    id=exam.id,
                    title=exam.title,
                    description=exam.description,
                    subject=exam.subject,
                    duration_minutes=exam.duration_minutes,
                    total_marks=float(exam.total_marks),
                    passing_marks=float(exam.passing_marks),
                    question_count=len(exam.exam_questions),
                    start_at=exam.start_at,
                    end_at=exam.end_at,
                    status=exam.status,
                    student_session_status=sess_status,
                    active_session_id=active_sid,
                    identity_verification_status=id_status,
                )
            )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        return PaginatedStudentExamResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

    def get_student_exam_detail(
        self, db: Session, exam_id: uuid.UUID, current_user: User
    ) -> StudentExamDetail:
        self._verify_student_role(current_user)
        from app.repositories.academic_repository import academic_repository

        exam = student_exam_repository.get_published_exam_by_id(db, exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found or not published.",
            )

        if not academic_repository.is_student_authorized_for_exam(db, current_user, exam):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not in the target audience for this examination.",
            )

        session = student_exam_repository.get_latest_session(db, exam_id, current_user.id)
        if not session:
            sess_status = "AVAILABLE"
            active_sid = None
            id_status = None
        elif session.status in [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]:
            sess_status = "IN_PROGRESS"
            active_sid = session.id
            id_status = session.identity_verification_status or "UNVERIFIED"
        else:
            sess_status = "COMPLETED"
            active_sid = session.id
            id_status = session.identity_verification_status or "UNVERIFIED"

        return StudentExamDetail(
            id=exam.id,
            title=exam.title,
            description=exam.description,
            subject=exam.subject,
            instructions=exam.instructions,
            duration_minutes=exam.duration_minutes,
            total_marks=float(exam.total_marks),
            passing_marks=float(exam.passing_marks),
            question_count=len(exam.exam_questions),
            start_at=exam.start_at,
            end_at=exam.end_at,
            negative_marking_enabled=exam.negative_marking_enabled,
            randomize_questions=exam.randomize_questions,
            randomize_options=exam.randomize_options,
            proctoring_enabled=exam.proctoring_enabled,
            max_tab_switches=exam.max_tab_switches,
            status=exam.status,
            student_session_status=sess_status,
            active_session_id=active_sid,
            identity_verification_status=id_status,
        )


    def start_or_resume_session(
        self, db: Session, exam_id: uuid.UUID, current_user: User
    ) -> ExamSessionResponse:
        self._verify_student_role(current_user)

        exam = student_exam_repository.get_published_exam_by_id(db, exam_id)
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found or not published.",
            )

        from app.repositories.academic_repository import academic_repository
        if not academic_repository.is_student_authorized_for_exam(db, current_user, exam):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You are not in the target audience for this examination.",
            )

        if not exam.exam_questions:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam has no questions.",
            )

        now = datetime.now(timezone.utc)
        if exam.start_at and now < exam.start_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam schedule has not started yet.",
            )
        if exam.end_at and now > exam.end_at:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam schedule has already ended.",
            )

        # Check existing active session
        active_session = student_exam_repository.get_active_session(db, exam_id, current_user.id)
        if active_session:
            # Stage 14.1 Security Hardening:
            # Re-entering or resuming an active exam session requires fresh live identity verification.
            # Reset identity_verification_status to UNVERIFIED so pre-exam verification cannot be bypassed on session resume.
            active_session.identity_verification_status = "UNVERIFIED"
            db.commit()
            db.refresh(active_session)
            return self.get_session_details(db, active_session.id, current_user, require_verified_identity=False)

        # Check if already completed
        latest_session = student_exam_repository.get_latest_session(db, exam_id, current_user.id)
        if latest_session and latest_session.status not in [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already completed/submitted this exam.",
            )

        # Order questions
        eqs = list(exam.exam_questions)
        eqs.sort(key=lambda x: x.question_order)
        q_ids = [eq.question_id for eq in eqs]

        if exam.randomize_questions:
            random.shuffle(q_ids)

        new_session = student_exam_repository.create_session(
            db, exam.id, current_user.id, exam.duration_minutes, q_ids
        )

        return self.get_session_details(db, new_session.id, current_user, require_verified_identity=False)

    def get_session_details(
        self, db: Session, session_id: uuid.UUID, current_user: User, require_verified_identity: bool = True
    ) -> ExamSessionResponse:
        self._verify_student_role(current_user)

        session = student_exam_repository.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session.",
            )

        if require_verified_identity and session.identity_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "IDENTITY_VERIFICATION_REQUIRED",
                    "message": "Student identity verification is required before entering the examination."
                }
            )

        now = datetime.now(timezone.utc)
        expires_at = _ensure_utc(session.expires_at)
        if (
            expires_at
            and now > expires_at
            and session.status == SessionStatus.IN_PROGRESS
        ):
            session = student_exam_repository.expire_session(db, session)

        remaining_sec = 0
        if expires_at and session.status == SessionStatus.IN_PROGRESS:
            diff = (expires_at - now).total_seconds()
            remaining_sec = max(0, int(diff))

        # Build questions order from session_metadata or exam order
        eq_map = {eq.question_id: eq for eq in session.exam.exam_questions}
        ordered_qids = []

        if session.session_metadata and "question_order" in session.session_metadata:
            for qstr in session.session_metadata["question_order"]:
                try:
                    ordered_qids.append(uuid.UUID(qstr))
                except ValueError:
                    pass

        if not ordered_qids:
            sorted_eqs = sorted(session.exam.exam_questions, key=lambda x: x.question_order)
            ordered_qids = [eq.question_id for eq in sorted_eqs]

        questions_response = []
        for idx, qid in enumerate(ordered_qids, start=1):
            eq = eq_map.get(qid)
            if not eq or not eq.question:
                continue

            q = eq.question
            marks = float(eq.marks_override) if eq.marks_override is not None else float(q.marks)

            options_response = []
            opts = list(q.options)
            opts.sort(key=lambda o: o.option_order)
            if session.exam.randomize_options:
                opts = list(opts)
                random.seed(str(session.id) + str(q.id))
                random.shuffle(opts)

            for opt in opts:
                options_response.append(
                    StudentQuestionOptionResponse(
                        id=opt.id,
                        option_text=opt.option_text,
                        option_order=opt.option_order,
                    )
                )

            questions_response.append(
                StudentQuestionResponse(
                    id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    difficulty=q.difficulty,
                    marks=marks,
                    question_order=idx,
                    options=options_response,
                )
            )

        # Build answers response
        answers_response = []
        for ans in session.answers:
            sel_opt_ids = [so.option_id for so in ans.selected_options]
            answers_response.append(
                StudentAnswerResponse(
                    question_id=ans.question_id,
                    selected_option_ids=sel_opt_ids,
                    text_answer=ans.text_answer,
                    answer_image_url=ans.answer_image_url,
                    ocr_status=ans.ocr_status,
                    ocr_confidence=float(ans.ocr_confidence) if ans.ocr_confidence is not None else None,
                    ocr_processed_at=ans.ocr_processed_at,
                    updated_at=ans.updated_at,
                )
            )

        marked_qids = []
        if session.session_metadata and "marked_for_review" in session.session_metadata:
            for qstr in session.session_metadata["marked_for_review"]:
                try:
                    marked_qids.append(uuid.UUID(qstr))
                except ValueError:
                    pass

        tab_switch_count = 0
        if session.session_metadata and "tab_switch_count" in session.session_metadata:
            try:
                tab_switch_count = int(session.session_metadata["tab_switch_count"])
            except (ValueError, TypeError):
                tab_switch_count = 0

        return ExamSessionResponse(
            id=session.id,
            exam_id=session.exam_id,
            exam_title=session.exam.title,
            exam_subject=session.exam.subject,
            duration_minutes=session.exam.duration_minutes,
            status=session.status,
            started_at=session.started_at,
            submitted_at=session.submitted_at,
            expires_at=session.expires_at,
            remaining_seconds=remaining_sec,
            max_tab_switches=session.exam.max_tab_switches,
            tab_switch_count=tab_switch_count,
            is_flagged=session.is_flagged,
            flag_reason=session.flag_reason,
            identity_verification_status=session.identity_verification_status or "UNVERIFIED",
            marked_for_review_question_ids=marked_qids,
            questions=questions_response,
            answers=answers_response,
        )


    def toggle_mark_for_review(
        self,
        db: Session,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        input_data: ReviewToggleInput,
        current_user: User,
    ) -> ExamSessionResponse:
        self._verify_student_role(current_user)

        session = student_exam_repository.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session.",
            )

        if session.identity_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "IDENTITY_VERIFICATION_REQUIRED",
                    "message": "Student identity verification is required before entering the examination."
                }
            )

        if session.status != SessionStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify review state for a submitted or expired exam session.",
            )

        now = datetime.now(timezone.utc)
        expires_at = _ensure_utc(session.expires_at)
        if expires_at and now > expires_at:
            student_exam_repository.expire_session(db, session)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam time has expired.",
            )

        # Verify question belongs to session's exam
        exam_qids = {eq.question_id for eq in session.exam.exam_questions}
        if question_id not in exam_qids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to this exam session.",
            )

        updated_session = student_exam_repository.toggle_mark_for_review(
            db, session=session, question_id=question_id, marked=input_data.marked
        )
        return self.get_session_details(db, updated_session.id, current_user)

    def save_answer(
        self,
        db: Session,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        input_data: StudentAnswerSaveInput,
        current_user: User,
    ) -> StudentAnswerResponse:
        self._verify_student_role(current_user)

        session = student_exam_repository.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session.",
            )

        if session.identity_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "IDENTITY_VERIFICATION_REQUIRED",
                    "message": "Student identity verification is required before entering the examination."
                }
            )

        if session.status != SessionStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot modify answers for a submitted or expired exam session.",
            )

        now = datetime.now(timezone.utc)
        expires_at = _ensure_utc(session.expires_at)
        if expires_at and now > expires_at:
            student_exam_repository.expire_session(db, session)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam time has expired.",
            )

        # Verify question belongs to session's exam
        exam_qids = {eq.question_id for eq in session.exam.exam_questions}
        if question_id not in exam_qids:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to this exam session.",
            )

        saved_answer = student_exam_repository.save_answer(
            db,
            session_id=session_id,
            question_id=question_id,
            selected_option_ids=input_data.selected_option_ids or [],
            text_answer=input_data.text_answer,
        )

        # If clearing answer
        if not input_data.selected_option_ids and not (input_data.text_answer and input_data.text_answer.strip()):
            saved_answer.answer_image_url = None
            saved_answer.ocr_status = "OCR_NOT_REQUIRED"
            saved_answer.ocr_confidence = None
            saved_answer.ocr_processed_at = None
            db.commit()
            db.refresh(saved_answer)

        sel_opt_ids = [so.option_id for so in saved_answer.selected_options]

        return StudentAnswerResponse(
            question_id=saved_answer.question_id,
            selected_option_ids=sel_opt_ids,
            text_answer=saved_answer.text_answer,
            answer_image_url=saved_answer.answer_image_url,
            ocr_status=saved_answer.ocr_status,
            ocr_confidence=float(saved_answer.ocr_confidence) if saved_answer.ocr_confidence is not None else None,
            ocr_processed_at=saved_answer.ocr_processed_at,
            updated_at=saved_answer.updated_at,
        )

    def process_handwritten_answer(
        self,
        db: Session,
        session_id: uuid.UUID,
        question_id: uuid.UUID,
        input_data: HandwrittenAnswerInput,
        current_user: User,
    ) -> HandwrittenAnswerProcessResponse:
        self._verify_student_role(current_user)

        session = student_exam_repository.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session.",
            )

        if session.identity_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "IDENTITY_VERIFICATION_REQUIRED",
                    "message": "Student identity verification is required before entering the examination."
                }
            )

        if session.status != SessionStatus.IN_PROGRESS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot submit handwritten answer for a submitted or expired exam session.",
            )

        now = datetime.now(timezone.utc)
        expires_at = _ensure_utc(session.expires_at)
        if expires_at and now > expires_at:
            student_exam_repository.expire_session(db, session)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam time has expired.",
            )

        eq = (
            db.query(ExamQuestion)
            .filter(ExamQuestion.exam_id == session.exam_id, ExamQuestion.question_id == question_id)
            .first()
        )
        if not eq or not eq.question:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question does not belong to this exam session.",
            )

        q = eq.question
        if q.question_type != QuestionType.HANDWRITTEN:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Question type is not HANDWRITTEN.",
            )

        # Save image file locally
        uploads_dir = os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads", "handwritten"
        )
        os.makedirs(uploads_dir, exist_ok=True)

        filename = f"{session.id}_{question_id}_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(uploads_dir, filename)

        try:
            raw_b64 = input_data.image_data
            if "," in raw_b64:
                raw_b64 = raw_b64.split(",", 1)[1]
            img_bytes = base64.b64decode(raw_b64)
            with open(filepath, "wb") as f:
                f.write(img_bytes)
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image capture payload: {str(e)}",
            )

        rel_image_url = f"/uploads/handwritten/{filename}"

        # Perform OCR
        ocr_res = handwritten_ocr_service.extract_text(input_data.image_data)

        # Get or create StudentAnswer
        saved_answer = (
            db.query(StudentAnswer)
            .filter(StudentAnswer.session_id == session_id, StudentAnswer.question_id == question_id)
            .first()
        )
        if not saved_answer:
            saved_answer = StudentAnswer(
                id=uuid.uuid4(),
                session_id=session_id,
                question_id=question_id,
            )
            db.add(saved_answer)
            db.flush()

        saved_answer.answer_image_url = rel_image_url
        saved_answer.ocr_status = ocr_res.status.value
        saved_answer.ocr_confidence = ocr_res.confidence
        saved_answer.ocr_processed_at = datetime.now(timezone.utc)
        saved_answer.text_answer = ocr_res.extracted_text if ocr_res.extracted_text else None

        # Evaluation Result integration
        eval_res = (
            db.query(EvaluationResult)
            .filter(EvaluationResult.answer_id == saved_answer.id)
            .first()
        )

        q_marks = float(eq.marks_override) if eq.marks_override is not None else float(q.marks)
        eval_status_str = "PENDING_REVIEW"

        if ocr_res.status == OCRStatus.OCR_SUCCESS and ocr_res.extracted_text.strip():
            ai_eval = ai_subjective_evaluation_service.evaluate_answer(
                question_text=q.question_text,
                question_type=q.question_type.value,
                student_answer=ocr_res.extracted_text,
                model_answer=q.model_answer,
                explanation=q.explanation,
                max_marks=q_marks,
            )

            if ai_eval is not None:
                eval_status_str = "AI_EVALUATED"
                ai_score = ai_eval.score
                ai_reason = f"[Handwritten OCR Completed] {ai_eval.reason or ai_eval.feedback or 'Evaluated by AI'}"

                if not eval_res:
                    eval_res = EvaluationResult(
                        id=uuid.uuid4(),
                        answer_id=saved_answer.id,
                        evaluator_type=EvaluatorType.AI,
                        suggested_score=ai_score,
                        final_score=ai_score,
                        justification=ai_reason,
                        confidence=ocr_res.confidence,
                        status=EvaluationStatus.AI_EVALUATED,
                    )
                    db.add(eval_res)
                elif eval_res.status not in (EvaluationStatus.MANUAL_REVIEW, EvaluationStatus.FINALIZED):
                    eval_res.evaluator_type = EvaluatorType.AI
                    eval_res.suggested_score = ai_score
                    eval_res.final_score = ai_score
                    eval_res.justification = ai_reason
                    eval_res.status = EvaluationStatus.AI_EVALUATED
            else:
                eval_status_str = "PENDING_REVIEW"
                if not eval_res:
                    eval_res = EvaluationResult(
                        id=uuid.uuid4(),
                        answer_id=saved_answer.id,
                        evaluator_type=EvaluatorType.AUTOMATED,
                        suggested_score=0.0,
                        final_score=0.0,
                        justification="OCR completed. Pending AI/Examiner review.",
                        status=EvaluationStatus.PENDING_REVIEW,
                    )
                    db.add(eval_res)
                elif eval_res.status not in (EvaluationStatus.MANUAL_REVIEW, EvaluationStatus.FINALIZED):
                    eval_res.status = EvaluationStatus.PENDING_REVIEW
        else:
            eval_status_str = "PENDING_REVIEW"
            justification = f"Handwritten answer pending manual examiner review ({ocr_res.status.value})."
            if not eval_res:
                eval_res = EvaluationResult(
                    id=uuid.uuid4(),
                    answer_id=saved_answer.id,
                    evaluator_type=EvaluatorType.AUTOMATED,
                    suggested_score=0.0,
                    final_score=0.0,
                    justification=justification,
                    status=EvaluationStatus.PENDING_REVIEW,
                )
                db.add(eval_res)
            elif eval_res.status not in (EvaluationStatus.MANUAL_REVIEW, EvaluationStatus.FINALIZED):
                eval_res.status = EvaluationStatus.PENDING_REVIEW

        db.commit()
        db.refresh(saved_answer)

        try:
            evaluation_service.recalculate_session_evaluation(db, session_id=session_id)
        except Exception as err:
            logger.warning(f"Failed session evaluation recalculation: {err}")

        msg = (
            "Handwritten answer uploaded and processed successfully."
            if ocr_res.status == OCRStatus.OCR_SUCCESS
            else "Handwritten answer saved for examiner review."
        )

        return HandwrittenAnswerProcessResponse(
            question_id=question_id,
            answer_image_url=saved_answer.answer_image_url,
            ocr_status=ocr_res.status.value,
            ocr_confidence=ocr_res.confidence,
            extracted_text=ocr_res.extracted_text or "",
            evaluation_status=eval_status_str,
            message=msg,
        )

    def submit_exam_session(
        self, db: Session, session_id: uuid.UUID, current_user: User
    ) -> ExamSessionResponse:
        self._verify_student_role(current_user)

        session = student_exam_repository.get_session_by_id(db, session_id)
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.student_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam session.",
            )

        if session.identity_verification_status != "VERIFIED":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "code": "IDENTITY_VERIFICATION_REQUIRED",
                    "message": "Student identity verification is required before entering the examination."
                }
            )

        if session.status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED, SessionStatus.EXPIRED, SessionStatus.TERMINATED]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Exam session has already been submitted or completed.",
            )

        submitted_session = student_exam_repository.submit_session(db, session)

        # Trigger objective evaluation safely without failing submission if error occurs
        try:
            evaluation_service.evaluate_exam_session(db, session_id=submitted_session.id)
        except Exception as err:
            import logging
            logging.getLogger(__name__).error(
                f"Evaluation failed for session {submitted_session.id}: {err}", exc_info=True
            )

        return self.get_session_details(db, submitted_session.id, current_user)

    def get_student_dashboard(self, db: Session, current_user: User):
        self._verify_student_role(current_user)
        from sqlalchemy import select
        from app.repositories.academic_repository import academic_repository
        from app.models.academic import College, Department, Section
        from app.models.evaluation import ExamSessionEvaluation
        from app.schemas.student_exam import (
            StudentDashboardSummary,
            StudentAcademicProfile,
            UpcomingExamDashboardItem,
            InProgressExamSessionInfo,
            RecentResultDashboardItem,
            StudentDashboardResponse,
        )

        # 1. Academic Profile
        col_name, col_code = None, None
        dept_name, dept_code = None, None
        sec_name, sec_code = None, None

        if current_user.college_id:
            col = db.scalar(select(College).where(College.id == current_user.college_id))
            if col:
                col_name, col_code = col.name, col.code

        if current_user.department_id:
            dept = db.scalar(select(Department).where(Department.id == current_user.department_id))
            if dept:
                dept_name, dept_code = dept.name, dept.code

        if current_user.section_id:
            sec = db.scalar(select(Section).where(Section.id == current_user.section_id))
            if sec:
                sec_name, sec_code = sec.name, sec.code

        acad_profile = StudentAcademicProfile(
            college_id=current_user.college_id,
            college_name=col_name,
            college_code=col_code,
            department_id=current_user.department_id,
            department_name=dept_name,
            department_code=dept_code,
            year_of_study=current_user.year_of_study,
            section_id=current_user.section_id,
            section_name=sec_name,
            section_code=sec_code,
        )

        # 2. Targeted Exams & Student Sessions
        raw_exams, _ = student_exam_repository.list_published_exams(db, page=1, page_size=1000)
        authorized_exams = [
            e for e in raw_exams if academic_repository.is_student_authorized_for_exam(db, current_user, e)
        ]

        student_sessions = student_exam_repository.get_sessions_for_student(db, current_user.id)
        session_map = {}
        for s in student_sessions:
            if s.exam_id not in session_map or s.created_at > session_map[s.exam_id].created_at:
                session_map[s.exam_id] = s

        # 3. Active / In-Progress Exam Session
        in_progress_info = None
        active_session = None

        for s in student_sessions:
            if s.status in [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]:
                active_session = s
                break

        if active_session:
            sess_details = self.get_session_details(db, active_session.id, current_user, require_verified_identity=False)
            exam = active_session.exam

            answered_cnt = 0
            marked_cnt = len(sess_details.marked_for_review_question_ids or [])

            for ans in active_session.answers:
                has_opts = len(ans.selected_options) > 0
                has_text = bool(ans.text_answer and ans.text_answer.strip())
                has_img = bool(ans.answer_image_url)
                if has_opts or has_text or has_img:
                    answered_cnt += 1

            start_t = active_session.started_at or active_session.created_at

            in_progress_info = InProgressExamSessionInfo(
                session_id=active_session.id,
                exam_id=exam.id,
                exam_title=exam.title,
                exam_subject=exam.subject,
                duration_minutes=exam.duration_minutes,
                start_time=start_t,
                end_time=sess_details.expires_at,
                remaining_seconds=sess_details.remaining_seconds,
                total_questions=len(exam.exam_questions),
                answered_count=answered_cnt,
                marked_for_review_count=marked_cnt,
            )

        # 4. Upcoming / Available Examinations
        upcoming_items = []
        for exam in authorized_exams:
            s = session_map.get(exam.id)
            if not s or s.status in [SessionStatus.CREATED, SessionStatus.IN_PROGRESS]:
                q_count = len(exam.exam_questions)
                total_marks = sum(
                    float(eq.marks_override) if eq.marks_override is not None else float(eq.question.marks)
                    for eq in exam.exam_questions if eq.question
                )
                act_sid = s.id if s else None
                upcoming_items.append(
                    UpcomingExamDashboardItem(
                        id=exam.id,
                        title=exam.title,
                        subject=exam.subject,
                        description=exam.description,
                        duration_minutes=exam.duration_minutes,
                        start_at=exam.start_at,
                        end_at=exam.end_at,
                        question_count=q_count,
                        total_marks=total_marks,
                        status="IN_PROGRESS" if s else "AVAILABLE",
                        active_session_id=act_sid,
                    )
                )

        # 5. Recent Results
        eval_query = (
            db.query(ExamSessionEvaluation)
            .filter(ExamSessionEvaluation.student_id == current_user.id)
            .order_by(ExamSessionEvaluation.created_at.desc())
            .limit(10)
        )
        evaluations = eval_query.all()

        recent_results = []
        for ev in evaluations:
            exam = ev.exam or (ev.session.exam if ev.session else None)
            exam_title = exam.title if exam else "Exam"
            exam_subject = exam.subject if exam else "General"
            submitted_at = ev.session.submitted_at if ev.session else ev.created_at

            pass_fail_val = ev.pass_fail_status.value if hasattr(ev.pass_fail_status, "value") else str(ev.pass_fail_status)
            status_val = ev.status.value if hasattr(ev.status, "value") else str(ev.status)

            recent_results.append(
                RecentResultDashboardItem(
                    evaluation_id=ev.id,
                    session_id=ev.session_id,
                    exam_id=ev.exam_id,
                    exam_title=exam_title,
                    exam_subject=exam_subject,
                    total_score=float(ev.total_score),
                    maximum_marks=float(ev.maximum_marks),
                    percentage=float(ev.percentage),
                    pass_fail_status=pass_fail_val,
                    status=status_val,
                    submitted_at=submitted_at or ev.created_at,
                )
            )

        # 6. Summary Counts
        completed_cnt = sum(
            1 for s in student_sessions
            if s.status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED, SessionStatus.EXPIRED, SessionStatus.TERMINATED]
        )
        summary = StudentDashboardSummary(
            upcoming_exams=len(upcoming_items),
            in_progress_exams=1 if in_progress_info else 0,
            completed_exams=completed_cnt,
            results_available=len(recent_results),
        )

        greeting_name = f"{current_user.first_name} {current_user.last_name}".strip()

        return StudentDashboardResponse(
            greeting_name=greeting_name,
            summary=summary,
            academic_profile=acad_profile,
            in_progress_exam=in_progress_info,
            upcoming_exams=upcoming_items,
            recent_results=recent_results,
        )


student_exam_service = StudentExamService()
