import math
import uuid
from datetime import datetime
from typing import Optional, List
from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.db.session import get_db
from app.models.user import User, UserRole
from app.models.exam import Exam
from app.models.exam_session import ExamSession, SessionStatus
from app.models.answer import StudentAnswer
from app.models.question import Question, QuestionType
from app.models.evaluation import ExamSessionEvaluation, EvaluationResult, EvaluationStatus
from app.core.dependencies import get_current_user, require_roles
from app.schemas.evaluation import (
    StudentResultResponse,
    PaginatedStudentResultResponse,
    QuestionEvaluationDetail,
    SubjectiveReviewInput,
    SubjectiveFinalizeInput,
)
from app.services.evaluation_service import evaluation_service

router = APIRouter()


def _to_result_response(
    db: Session,
    eval_record: ExamSessionEvaluation,
    include_questions: bool = False,
) -> StudentResultResponse:
    session = eval_record.session
    exam = eval_record.exam or (session.exam if session else None)
    student = eval_record.student or (session.student if session else None)

    exam_title = exam.title if exam else "Unknown Exam"
    exam_subject = exam.subject if exam else "General"
    student_name = f"{student.first_name} {student.last_name}" if student else "Unknown Student"
    student_email = student.email if student else ""

    question_details: Optional[List[QuestionEvaluationDetail]] = None

    if include_questions and session and exam:
        question_details = []
        sorted_eqs = sorted(exam.exam_questions, key=lambda x: x.question_order)
        answers_map = {ans.question_id: ans for ans in session.answers}

        for eq in sorted_eqs:
            q = eq.question
            if not q:
                continue

            q_marks = (
                float(eq.marks_override)
                if eq.marks_override is not None
                else float(q.marks)
            )
            student_ans = answers_map.get(q.id)

            is_answered = False
            earned_score = 0.0
            suggested_score: Optional[float] = None
            is_correct: Optional[bool] = None
            justification: Optional[str] = None
            examiner_comment: Optional[str] = None
            answer_id: Optional[uuid.UUID] = None
            matched_concepts = None
            missed_concepts = None
            eval_type_str: Optional[str] = None
            eval_status: Optional[EvaluationStatus] = None
            reviewed_by: Optional[uuid.UUID] = None
            reviewer_name: Optional[str] = None
            reviewed_at: Optional[datetime] = None

            if student_ans:
                answer_id = student_ans.id
                selected_opts = [so.option_id for so in student_ans.selected_options]
                text_ans = student_ans.text_answer
                if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                    is_answered = len(selected_opts) > 0
                else:
                    is_answered = bool(student_ans.text_answer or student_ans.answer_image_url)

                if student_ans.evaluation_result:
                    er = student_ans.evaluation_result
                    earned_score = float(er.final_score)
                    suggested_score = float(er.suggested_score) if er.suggested_score is not None else None
                    justification = er.justification
                    examiner_comment = er.examiner_comment
                    matched_concepts = er.matched_concepts
                    missed_concepts = er.missed_concepts
                    eval_status = er.status
                    reviewed_by = er.reviewed_by
                    reviewed_at = er.reviewed_at

                    if er.reviewer:
                        reviewer_name = f"{er.reviewer.first_name} {er.reviewer.last_name}"

                    if er.evaluator_type:
                        eval_type_str = er.evaluator_type.value

                    if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                        if earned_score > 0:
                            is_correct = True
                        elif is_answered:
                            is_correct = False
                    else:
                        if earned_score >= q_marks:
                            is_correct = True
                        elif earned_score > 0:
                            is_correct = True
                        elif is_answered:
                            is_correct = False

            question_details.append(
                QuestionEvaluationDetail(
                    answer_id=answer_id,
                    question_id=q.id,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    marks=q_marks,
                    earned_score=earned_score,
                    suggested_score=suggested_score,
                    is_answered=is_answered,
                    is_correct=is_correct,
                    justification=justification,
                    examiner_comment=examiner_comment,
                    text_answer=student_ans.text_answer if student_ans else None,
                    answer_image_url=student_ans.answer_image_url if student_ans else None,
                    ocr_status=student_ans.ocr_status if student_ans else None,
                    ocr_confidence=float(student_ans.ocr_confidence) if (student_ans and student_ans.ocr_confidence is not None) else None,
                    ocr_processed_at=student_ans.ocr_processed_at if student_ans else None,
                    model_answer=q.model_answer,
                    explanation=q.explanation,
                    selected_option_ids=[so.option_id for so in student_ans.selected_options] if (student_ans and student_ans.selected_options) else None,
                    matched_concepts=matched_concepts,
                    missed_concepts=missed_concepts,
                    evaluator_type=eval_type_str,
                    status=eval_status,
                    reviewed_by=reviewed_by,
                    reviewer_name=reviewer_name,
                    reviewed_at=reviewed_at,
                )
            )

    return StudentResultResponse(
        id=eval_record.id,
        session_id=eval_record.session_id,
        exam_id=eval_record.exam_id,
        exam_title=exam_title,
        exam_subject=exam_subject,
        student_id=eval_record.student_id,
        student_name=student_name,
        student_email=student_email,
        submitted_at=session.submitted_at if session else eval_record.created_at,
        total_questions=eval_record.total_questions,
        answered_questions=eval_record.answered_questions,
        unanswered_questions=eval_record.unanswered_questions,
        correct_answers=eval_record.correct_answers,
        incorrect_answers=eval_record.incorrect_answers,
        objective_marks=float(eval_record.objective_marks),
        subjective_marks=float(getattr(eval_record, "subjective_marks", 0.0)),
        negative_marks=float(eval_record.negative_marks),
        total_score=float(eval_record.total_score),
        maximum_marks=float(eval_record.maximum_marks),
        percentage=float(eval_record.percentage),
        passing_marks=float(eval_record.passing_marks),
        pass_fail_status=eval_record.pass_fail_status,
        status=eval_record.status,
        question_evaluations=question_details,
    )


@router.get("/student/results", response_model=PaginatedStudentResultResponse)
def get_student_results(
    search: Optional[str] = Query(None, description="Search by exam title or subject"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Returns evaluation results for exams completed by the authenticated student."""
    query = (
        db.query(ExamSessionEvaluation)
        .join(ExamSessionEvaluation.exam)
        .join(ExamSessionEvaluation.session)
        .options(
            joinedload(ExamSessionEvaluation.exam),
            joinedload(ExamSessionEvaluation.session),
            joinedload(ExamSessionEvaluation.student),
        )
        .filter(ExamSessionEvaluation.student_id == current_user.id)
    )

    if search:
        search_term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Exam.title.ilike(search_term),
                Exam.subject.ilike(search_term),
            )
        )

    total = query.count()
    items_raw = (
        query.order_by(ExamSessionEvaluation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_to_result_response(db, r, include_questions=False) for r in items_raw]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedStudentResultResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/student/results/{session_id}", response_model=StudentResultResponse)
def get_student_result_detail(
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.STUDENT)),
    db: Session = Depends(get_db),
):
    """Retrieves detailed result breakdown for a specific session belonging to the student."""
    session = db.query(ExamSession).filter(ExamSession.id == session_id).first()
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

    eval_record = (
        db.query(ExamSessionEvaluation)
        .filter(ExamSessionEvaluation.session_id == session_id)
        .first()
    )

    if not eval_record:
        eval_record = evaluation_service.evaluate_exam_session(db, session_id=session_id)

    return _to_result_response(db, eval_record, include_questions=True)


@router.get("/exams/{exam_id}/results", response_model=PaginatedStudentResultResponse)
def get_examiner_exam_results(
    exam_id: uuid.UUID,
    search: Optional[str] = Query(None, description="Search by student name or email"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Returns all student evaluation results for an exam owned by the examiner."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found.",
        )

    if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access denied. You do not own this exam.",
        )

    query = (
        db.query(ExamSessionEvaluation)
        .join(ExamSessionEvaluation.student)
        .options(
            joinedload(ExamSessionEvaluation.exam),
            joinedload(ExamSessionEvaluation.session),
            joinedload(ExamSessionEvaluation.student),
        )
        .filter(ExamSessionEvaluation.exam_id == exam_id)
    )

    if search:
        search_term = f"%{search.strip()}%"
        from app.models.user import User as UserModel
        query = query.filter(
            or_(
                UserModel.first_name.ilike(search_term),
                UserModel.last_name.ilike(search_term),
                UserModel.email.ilike(search_term),
            )
        )

    total = query.count()
    items_raw = (
        query.order_by(ExamSessionEvaluation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_to_result_response(db, r, include_questions=False) for r in items_raw]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedStudentResultResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.get("/exams/{exam_id}/results/{session_id}", response_model=StudentResultResponse)
def get_examiner_exam_result_detail(
    exam_id: uuid.UUID,
    session_id: uuid.UUID,
    current_user: User = Depends(require_roles(UserRole.EXAMINER, UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    """Retrieves detailed result breakdown for a specific session belonging to an exam owned by the examiner."""
    exam = db.query(Exam).filter(Exam.id == exam_id).first()
    if not exam:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Exam not found.",
        )

    if current_user.role == UserRole.EXAMINER and exam.created_by != current_user.id:
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

    eval_record = (
        db.query(ExamSessionEvaluation)
        .filter(ExamSessionEvaluation.session_id == session_id)
        .first()
    )

    if not eval_record:
        eval_record = evaluation_service.evaluate_exam_session(db, session_id=session_id)

    return _to_result_response(db, eval_record, include_questions=True)


@router.patch("/exams/{exam_id}/results/{session_id}/answers/{answer_id}/review", response_model=StudentResultResponse)
def review_subjective_answer(
    exam_id: uuid.UUID,
    session_id: uuid.UUID,
    answer_id: uuid.UUID,
    payload: SubjectiveReviewInput,
    current_user: User = Depends(require_roles(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    """
    Endpoint for Examiners to save a draft review or finalize a subjective question evaluation.
    """
    updated_session_eval = evaluation_service.review_subjective_answer(
        db=db,
        exam_id=exam_id,
        session_id=session_id,
        answer_id=answer_id,
        current_user=current_user,
        final_score=payload.final_score,
        comment=payload.comment,
        is_finalized=bool(payload.is_finalized),
    )
    return _to_result_response(db, updated_session_eval, include_questions=True)


@router.post("/exams/{exam_id}/results/{session_id}/answers/{answer_id}/finalize", response_model=StudentResultResponse)
def finalize_subjective_answer(
    exam_id: uuid.UUID,
    session_id: uuid.UUID,
    answer_id: uuid.UUID,
    payload: SubjectiveFinalizeInput,
    current_user: User = Depends(require_roles(UserRole.EXAMINER)),
    db: Session = Depends(get_db),
):
    """
    Endpoint for Examiners to finalize a subjective question evaluation.
    """
    updated_session_eval = evaluation_service.review_subjective_answer(
        db=db,
        exam_id=exam_id,
        session_id=session_id,
        answer_id=answer_id,
        current_user=current_user,
        final_score=payload.final_score,
        comment=payload.comment,
        is_finalized=True,
    )
    return _to_result_response(db, updated_session_eval, include_questions=True)


@router.get("/results", response_model=PaginatedStudentResultResponse)
def get_all_results_for_current_user(
    search: Optional[str] = Query(None, description="Search by exam title, subject, or student"),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Generic results endpoint returning results tailored to current user role."""
    if current_user.role == UserRole.STUDENT:
        return get_student_results(
            search=search, page=page, page_size=page_size, current_user=current_user, db=db
        )

    query = (
        db.query(ExamSessionEvaluation)
        .join(ExamSessionEvaluation.exam)
        .join(ExamSessionEvaluation.student)
        .options(
            joinedload(ExamSessionEvaluation.exam),
            joinedload(ExamSessionEvaluation.session),
            joinedload(ExamSessionEvaluation.student),
        )
    )

    if current_user.role == UserRole.EXAMINER:
        query = query.filter(Exam.created_by == current_user.id)

    if search:
        search_term = f"%{search.strip()}%"
        from app.models.user import User as UserModel
        query = query.filter(
            or_(
                Exam.title.ilike(search_term),
                Exam.subject.ilike(search_term),
                UserModel.first_name.ilike(search_term),
                UserModel.last_name.ilike(search_term),
                UserModel.email.ilike(search_term),
            )
        )

    total = query.count()
    items_raw = (
        query.order_by(ExamSessionEvaluation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    items = [_to_result_response(db, r, include_questions=False) for r in items_raw]
    total_pages = math.ceil(total / page_size) if total > 0 else 0

    return PaginatedStudentResultResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )
