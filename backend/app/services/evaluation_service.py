import logging
import math
import uuid
from datetime import datetime, timezone
from typing import Optional, List, Dict, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamQuestion
from app.models.exam_session import ExamSession, SessionStatus
from app.models.question import Question, QuestionType, QuestionOption
from app.models.answer import StudentAnswer, AnswerSelectedOption
from app.models.evaluation import (
    EvaluationResult,
    EvaluatorType,
    ExamSessionEvaluation,
    EvaluationStatus,
    PassFailStatus,
)
from app.services.ai_subjective_evaluation_service import ai_subjective_evaluation_service

logger = logging.getLogger(__name__)


class EvaluationService:
    def recalculate_session_evaluation(
        self, db: Session, session_id: uuid.UUID
    ) -> ExamSessionEvaluation:
        """
        Recalculates aggregate session evaluation metrics from individual question EvaluationResult records.
        Updates objective_marks, subjective_marks, negative_marks, total_score, percentage, pass_fail_status, and status.
        """
        session = (
            db.query(ExamSession)
            .options(
                joinedload(ExamSession.exam).joinedload(Exam.exam_questions).joinedload(ExamQuestion.question),
                joinedload(ExamSession.answers).joinedload(StudentAnswer.evaluation_result),
                joinedload(ExamSession.evaluation),
            )
            .filter(ExamSession.id == session_id)
            .first()
        )

        if not session or not session.exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session or associated exam not found.",
            )

        exam = session.exam
        answers_map: Dict[uuid.UUID, StudentAnswer] = {
            ans.question_id: ans for ans in session.answers
        }

        total_questions = len(exam.exam_questions)
        answered_questions = 0
        unanswered_questions = 0
        correct_answers = 0
        incorrect_answers = 0

        objective_marks = 0.0
        subjective_marks = 0.0
        negative_marks = 0.0
        maximum_marks = 0.0

        subj_statuses: List[EvaluationStatus] = []

        sorted_eqs = sorted(exam.exam_questions, key=lambda x: x.question_order)

        for eq in sorted_eqs:
            q = eq.question
            if not q:
                continue

            q_marks = (
                float(eq.marks_override)
                if eq.marks_override is not None
                else float(q.marks)
            )
            maximum_marks += q_marks

            student_ans = answers_map.get(q.id)

            is_answered = False
            if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                is_answered = bool(student_ans and len(student_ans.selected_options) > 0)
            else:
                is_answered = bool(
                    student_ans
                    and (student_ans.text_answer or student_ans.answer_image_url)
                )

            if is_answered:
                answered_questions += 1
            else:
                unanswered_questions += 1

            if student_ans and student_ans.evaluation_result:
                eval_res = student_ans.evaluation_result
                score = float(eval_res.final_score)

                if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                    if score > 0:
                        objective_marks += score
                        correct_answers += 1
                    elif score < 0:
                        negative_marks += abs(score)
                        incorrect_answers += 1
                    else:
                        if is_answered:
                            incorrect_answers += 1
                else:
                    # Subjective questions
                    subjective_marks += score
                    if score >= q_marks:
                        correct_answers += 1
                    elif score > 0:
                        correct_answers += 1
                    else:
                        if is_answered:
                            incorrect_answers += 1

                    subj_statuses.append(eval_res.status)

        total_score = round(objective_marks + subjective_marks - negative_marks, 2)
        percentage = (
            round((total_score / maximum_marks) * 100.0, 2)
            if maximum_marks > 0
            else 0.0
        )

        passing_marks = float(exam.passing_marks)
        is_passed = total_score >= passing_marks
        pass_fail = PassFailStatus.PASSED if is_passed else PassFailStatus.FAILED

        # Session status calculation
        if not subj_statuses:
            session_status = EvaluationStatus.COMPLETED
        elif all(st == EvaluationStatus.FINALIZED for st in subj_statuses):
            session_status = EvaluationStatus.FINALIZED
        elif any(st == EvaluationStatus.MANUAL_REVIEW for st in subj_statuses):
            session_status = EvaluationStatus.MANUAL_REVIEW
        elif any(st == EvaluationStatus.PENDING_REVIEW for st in subj_statuses):
            session_status = EvaluationStatus.PENDING_REVIEW
        elif any(st == EvaluationStatus.AI_EVALUATED for st in subj_statuses):
            session_status = EvaluationStatus.AI_EVALUATED
        else:
            session_status = EvaluationStatus.PENDING_REVIEW

        session_eval = (
            db.query(ExamSessionEvaluation)
            .filter(ExamSessionEvaluation.session_id == session.id)
            .first()
        )

        if session_eval:
            session_eval.exam_id = session.exam_id
            session_eval.student_id = session.student_id
            session_eval.total_questions = total_questions
            session_eval.answered_questions = answered_questions
            session_eval.unanswered_questions = unanswered_questions
            session_eval.correct_answers = correct_answers
            session_eval.incorrect_answers = incorrect_answers
            session_eval.objective_marks = round(objective_marks, 2)
            session_eval.subjective_marks = round(subjective_marks, 2)
            session_eval.negative_marks = round(negative_marks, 2)
            session_eval.total_score = round(total_score, 2)
            session_eval.maximum_marks = round(maximum_marks, 2)
            session_eval.percentage = percentage
            session_eval.passing_marks = round(passing_marks, 2)
            session_eval.pass_fail_status = pass_fail
            session_eval.status = session_status
        else:
            session_eval = ExamSessionEvaluation(
                id=uuid.uuid4(),
                session_id=session.id,
                exam_id=session.exam_id,
                student_id=session.student_id,
                total_questions=total_questions,
                answered_questions=answered_questions,
                unanswered_questions=unanswered_questions,
                correct_answers=correct_answers,
                incorrect_answers=incorrect_answers,
                objective_marks=round(objective_marks, 2),
                subjective_marks=round(subjective_marks, 2),
                negative_marks=round(negative_marks, 2),
                total_score=round(total_score, 2),
                maximum_marks=round(maximum_marks, 2),
                percentage=percentage,
                passing_marks=round(passing_marks, 2),
                pass_fail_status=pass_fail,
                status=session_status,
            )
            db.add(session_eval)

        db.commit()
        db.refresh(session_eval)
        return session_eval

    def evaluate_exam_session(
        self, db: Session, session_id: uuid.UUID
    ) -> ExamSessionEvaluation:
        """
        Evaluates a submitted exam session on the server-side:
        - Objective question types (MCQ, MULTI_SELECT) evaluated deterministically.
        - Subjective question types (SHORT_ANSWER, LONG_ANSWER) evaluated via Gemini AI service.
        - HANDWRITTEN questions set to PENDING_REVIEW for manual examiner evaluation.
        - Preserves existing manual examiner reviews/finalizations.
        Evaluation is idempotent.
        """
        session = (
            db.query(ExamSession)
            .options(
                joinedload(ExamSession.exam).joinedload(Exam.exam_questions).joinedload(ExamQuestion.question).joinedload(Question.options),
                joinedload(ExamSession.answers).joinedload(StudentAnswer.selected_options),
                joinedload(ExamSession.answers).joinedload(StudentAnswer.evaluation_result),
                joinedload(ExamSession.evaluation),
            )
            .filter(ExamSession.id == session_id)
            .first()
        )

        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.status not in [
            SessionStatus.SUBMITTED,
            SessionStatus.AUTO_SUBMITTED,
            SessionStatus.EXPIRED,
            SessionStatus.TERMINATED,
        ]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only submitted or completed sessions can be evaluated.",
            )

        exam = session.exam
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam associated with session not found.",
            )

        answer_map: Dict[uuid.UUID, StudentAnswer] = {
            ans.question_id: ans for ans in session.answers
        }

        sorted_eqs = sorted(exam.exam_questions, key=lambda x: x.question_order)

        for eq in sorted_eqs:
            q = eq.question
            if not q:
                continue

            q_marks = (
                float(eq.marks_override)
                if eq.marks_override is not None
                else float(q.marks)
            )

            q_negative = (
                float(q.negative_marks)
                if exam.negative_marking_enabled
                else 0.0
            )

            student_ans = answer_map.get(q.id)

            selected_option_ids: List[uuid.UUID] = []
            if student_ans:
                selected_option_ids = [so.option_id for so in student_ans.selected_options]

            is_answered = False
            if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                is_answered = len(selected_option_ids) > 0
            else:
                is_answered = bool(
                    student_ans
                    and (student_ans.text_answer or student_ans.answer_image_url)
                )

            # Ensure StudentAnswer row exists
            if not student_ans:
                student_ans = StudentAnswer(
                    id=uuid.uuid4(),
                    session_id=session.id,
                    question_id=q.id,
                )
                db.add(student_ans)
                db.flush()
                answer_map[q.id] = student_ans

            existing_eval = (
                db.query(EvaluationResult)
                .filter(EvaluationResult.answer_id == student_ans.id)
                .first()
            )

            # If examiner has already saved manual review or finalized, preserve examiner work
            if existing_eval and existing_eval.status in (EvaluationStatus.MANUAL_REVIEW, EvaluationStatus.FINALIZED):
                continue

            score_for_q = 0.0
            suggested_score_for_q = 0.0
            justification = ""
            evaluator_type = EvaluatorType.AUTOMATED
            eval_status = EvaluationStatus.COMPLETED
            matched_concepts = None
            missed_concepts = None
            confidence = None

            if q.question_type == QuestionType.MCQ:
                correct_options = [opt for opt in q.options if opt.is_correct]
                correct_opt_id = correct_options[0].id if correct_options else None

                if not is_answered:
                    score_for_q = 0.0
                    suggested_score_for_q = 0.0
                    justification = "Unanswered MCQ"
                else:
                    user_selected_id = selected_option_ids[0]
                    if correct_opt_id and user_selected_id == correct_opt_id:
                        score_for_q = q_marks
                        suggested_score_for_q = q_marks
                        justification = "Correct MCQ selection"
                    else:
                        score_for_q = -q_negative
                        suggested_score_for_q = 0.0
                        justification = f"Incorrect MCQ selection. Applied negative marks: {q_negative}"

            elif q.question_type == QuestionType.MULTI_SELECT:
                correct_set: Set[uuid.UUID] = {opt.id for opt in q.options if opt.is_correct}

                if not is_answered:
                    score_for_q = 0.0
                    suggested_score_for_q = 0.0
                    justification = "Unanswered MULTI_SELECT"
                else:
                    user_selected_set: Set[uuid.UUID] = set(selected_option_ids)
                    if correct_set and user_selected_set == correct_set:
                        score_for_q = q_marks
                        suggested_score_for_q = q_marks
                        justification = "Correct MULTI_SELECT selection (exact match)"
                    else:
                        score_for_q = -q_negative
                        suggested_score_for_q = 0.0
                        justification = f"Incorrect MULTI_SELECT selection. Applied negative marks: {q_negative}"

            elif q.question_type in (QuestionType.SHORT_ANSWER, QuestionType.LONG_ANSWER):
                text_ans = student_ans.text_answer if student_ans else None
                ai_eval = ai_subjective_evaluation_service.evaluate_answer(
                    question_text=q.question_text,
                    question_type=q.question_type.value,
                    student_answer=text_ans,
                    model_answer=q.model_answer,
                    explanation=q.explanation,
                    max_marks=q_marks,
                )

                if ai_eval is not None:
                    evaluator_type = EvaluatorType.AI
                    eval_status = EvaluationStatus.AI_EVALUATED
                    score_for_q = ai_eval.score
                    suggested_score_for_q = ai_eval.score
                    justification = ai_eval.reason or ai_eval.feedback or "Evaluated by AI"
                    matched_concepts = {
                        "key_points_covered": ai_eval.key_points_covered,
                        "metrics": {
                            "correctness": ai_eval.correctness,
                            "relevance": ai_eval.relevance,
                            "completeness": ai_eval.completeness,
                        },
                    }
                    missed_concepts = {"missing_key_points": ai_eval.missing_key_points}
                    confidence = round(
                        (ai_eval.correctness + ai_eval.relevance + ai_eval.completeness) / 3.0,
                        2,
                    )
                else:
                    eval_status = EvaluationStatus.PENDING_REVIEW
                    evaluator_type = EvaluatorType.AUTOMATED
                    score_for_q = 0.0
                    suggested_score_for_q = 0.0
                    justification = "Pending manual/AI review"

            else:
                # HANDWRITTEN
                ocr_text = student_ans.text_answer if student_ans else None
                ocr_status_val = student_ans.ocr_status if student_ans else None

                if ocr_text and ocr_text.strip() and ocr_status_val == "OCR_SUCCESS":
                    ai_eval = ai_subjective_evaluation_service.evaluate_answer(
                        question_text=q.question_text,
                        question_type=q.question_type.value,
                        student_answer=ocr_text,
                        model_answer=q.model_answer,
                        explanation=q.explanation,
                        max_marks=q_marks,
                    )
                    if ai_eval is not None:
                        evaluator_type = EvaluatorType.AI
                        eval_status = EvaluationStatus.AI_EVALUATED
                        score_for_q = ai_eval.score
                        suggested_score_for_q = ai_eval.score
                        justification = f"[Handwritten OCR Completed] {ai_eval.reason or ai_eval.feedback or 'Evaluated by AI'}"
                        matched_concepts = {
                            "key_points_covered": ai_eval.key_points_covered,
                            "metrics": {
                                "correctness": ai_eval.correctness,
                                "relevance": ai_eval.relevance,
                                "completeness": ai_eval.completeness,
                            },
                        }
                        missed_concepts = {"missing_key_points": ai_eval.missing_key_points}
                        confidence = round(
                            (ai_eval.correctness + ai_eval.relevance + ai_eval.completeness) / 3.0,
                            2,
                        )
                    else:
                        eval_status = EvaluationStatus.PENDING_REVIEW
                        evaluator_type = EvaluatorType.AUTOMATED
                        score_for_q = 0.0
                        suggested_score_for_q = 0.0
                        justification = "Handwritten OCR completed. Pending AI/Examiner review."
                else:
                    eval_status = EvaluationStatus.PENDING_REVIEW
                    evaluator_type = EvaluatorType.AUTOMATED
                    score_for_q = 0.0
                    suggested_score_for_q = 0.0
                    justification = f"Pending manual examiner review ({ocr_status_val or 'OCR_PENDING'})"

            if existing_eval:
                existing_eval.evaluator_type = evaluator_type
                existing_eval.suggested_score = suggested_score_for_q
                existing_eval.final_score = score_for_q
                existing_eval.justification = justification
                existing_eval.matched_concepts = matched_concepts
                existing_eval.missed_concepts = missed_concepts
                existing_eval.confidence = confidence
                existing_eval.status = eval_status
            else:
                new_eval = EvaluationResult(
                    id=uuid.uuid4(),
                    answer_id=student_ans.id,
                    evaluator_type=evaluator_type,
                    suggested_score=suggested_score_for_q,
                    final_score=score_for_q,
                    justification=justification,
                    matched_concepts=matched_concepts,
                    missed_concepts=missed_concepts,
                    confidence=confidence,
                    status=eval_status,
                )
                db.add(new_eval)

        db.commit()

        # Recalculate session aggregate totals
        return self.recalculate_session_evaluation(db, session_id=session.id)

    def review_subjective_answer(
        self,
        db: Session,
        exam_id: uuid.UUID,
        session_id: uuid.UUID,
        answer_id: uuid.UUID,
        current_user: User,
        final_score: float,
        comment: Optional[str] = None,
        is_finalized: bool = False,
    ) -> ExamSessionEvaluation:
        """
        Allows authenticated Examiner to review/finalize subjective answer evaluation.
        Verifies exam ownership, session relationship, score range bounds, and locks finalized evaluations.
        Recalculates total exam session evaluation upon saving/finalizing.
        """
        # RBAC Check: Only EXAMINER can review answers
        if current_user.role != UserRole.EXAMINER:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied: Only Examiners are authorized to review exam answers.",
            )

        exam = db.query(Exam).filter(Exam.id == exam_id).first()
        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found.",
            )

        # Strict Ownership Check: Examiner must own the exam
        if exam.created_by != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. You do not own this exam.",
            )

        session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
        if not session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam session not found.",
            )

        if session.exam_id != exam_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Session does not belong to the specified exam.",
            )

        answer = db.query(StudentAnswer).filter(StudentAnswer.id == answer_id).first()
        if not answer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student answer not found.",
            )

        if answer.session_id != session_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Answer does not belong to the specified session.",
            )

        # Get question details for marks limits
        eq = (
            db.query(ExamQuestion)
            .filter(ExamQuestion.exam_id == exam_id, ExamQuestion.question_id == answer.question_id)
            .first()
        )
        q = eq.question if eq else db.query(Question).filter(Question.id == answer.question_id).first()

        if not q:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Question associated with answer not found.",
            )

        # Objective questions cannot be manually edited in this stage
        if q.question_type in (QuestionType.MCQ, QuestionType.MULTI_SELECT):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Objective question evaluations cannot be manually edited.",
            )

        max_marks = float(eq.marks_override) if (eq and eq.marks_override is not None) else float(q.marks)

        # Validate numeric score: 0 <= final_score <= max_marks, not NaN/Inf
        if math.isnan(final_score) or math.isinf(final_score):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Final score must be a valid number.",
            )

        if final_score < 0.0 or final_score > max_marks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Final score must be between 0 and {max_marks}.",
            )

        eval_res = (
            db.query(EvaluationResult)
            .filter(EvaluationResult.answer_id == answer_id)
            .first()
        )

        if not eval_res:
            eval_res = EvaluationResult(
                id=uuid.uuid4(),
                answer_id=answer.id,
                evaluator_type=EvaluatorType.EXAMINER,
                suggested_score=0.0,
                final_score=round(final_score, 2),
                justification="Manual examiner evaluation",
                examiner_comment=comment.strip() if comment and comment.strip() else None,
                status=EvaluationStatus.FINALIZED if is_finalized else EvaluationStatus.MANUAL_REVIEW,
                reviewed_by=current_user.id if is_finalized else None,
                reviewed_at=datetime.now(timezone.utc) if is_finalized else None,
            )
            db.add(eval_res)
        else:
            # Check if evaluation is already FINALIZED
            if eval_res.status == EvaluationStatus.FINALIZED:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Finalized evaluations are read-only and cannot be modified.",
                )

            eval_res.evaluator_type = EvaluatorType.EXAMINER
            eval_res.final_score = round(final_score, 2)
            eval_res.examiner_comment = comment.strip() if comment and comment.strip() else None

            if is_finalized:
                eval_res.status = EvaluationStatus.FINALIZED
                eval_res.reviewed_by = current_user.id
                eval_res.reviewed_at = datetime.now(timezone.utc)
            else:
                eval_res.status = EvaluationStatus.MANUAL_REVIEW

        db.commit()

        # Recalculate and return session evaluation summary
        return self.recalculate_session_evaluation(db, session_id=session_id)


evaluation_service = EvaluationService()
