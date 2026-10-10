import math
import statistics
import uuid
from datetime import datetime
from typing import Optional, List, Dict, Set
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import or_

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamQuestion
from app.models.exam_session import ExamSession, SessionStatus
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.answer import StudentAnswer
from app.models.evaluation import (
    ExamSessionEvaluation,
    EvaluationResult,
    EvaluationStatus,
    PassFailStatus,
)
from app.schemas.evaluation import StudentResultResponse, PaginatedStudentResultResponse
from app.schemas.analytics import (
    ExamBasicInfo,
    AnalyticsSummary,
    ScorePerformance,
    ScoreDistribution,
    PassFailDistribution,
    FinalizedPerformance,
    QuestionPerformanceItem,
    DifficultyPerformanceItem,
    TopicPerformanceItem,
    PendingReviewItem,
    ExamAnalyticsResponse,
)
from app.services.evaluation_service import evaluation_service


class AnalyticsService:
    def get_exam_analytics(
        self,
        db: Session,
        exam_id: uuid.UUID,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        search: Optional[str] = None,
        pass_fail: Optional[str] = None,
        session_status: Optional[str] = None,
    ) -> ExamAnalyticsResponse:
        """
        Computes server-side aggregated performance analytics for a specific exam.
        Strict RBAC: Only exam owner (or Admin) can access.
        """
        # 1. Exam Existence & RBAC Checks
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

        if current_user.role == UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Students cannot access exam analytics.",
            )

        # 2. Ensure all submitted/completed sessions have evaluation records
        submitted_sessions = (
            db.query(ExamSession)
            .filter(
                ExamSession.exam_id == exam_id,
                ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED, SessionStatus.EXPIRED, SessionStatus.TERMINATED]),
            )
            .all()
        )
        for s in submitted_sessions:
            eval_record = db.query(ExamSessionEvaluation).filter(ExamSessionEvaluation.session_id == s.id).first()
            if not eval_record:
                evaluation_service.evaluate_exam_session(db, session_id=s.id)

        # 3. Query all session evaluations for this exam with eager loading
        eval_records = (
            db.query(ExamSessionEvaluation)
            .options(
                joinedload(ExamSessionEvaluation.session),
                joinedload(ExamSessionEvaluation.student),
            )
            .filter(ExamSessionEvaluation.exam_id == exam_id)
            .all()
        )

        total_sessions = len(eval_records)
        evaluated_sessions = len([
            r for r in eval_records
            if r.status in [EvaluationStatus.COMPLETED, EvaluationStatus.AI_EVALUATED, EvaluationStatus.MANUAL_REVIEW, EvaluationStatus.FINALIZED]
        ])
        pending_reviews_count = len([
            r for r in eval_records
            if r.status in [EvaluationStatus.PENDING_REVIEW, EvaluationStatus.AI_EVALUATED, EvaluationStatus.MANUAL_REVIEW]
        ])
        finalized_count = len([r for r in eval_records if r.status == EvaluationStatus.FINALIZED])

        scores = [float(r.total_score) for r in eval_records]
        percentages = [float(r.percentage) for r in eval_records]

        avg_score = round(sum(scores) / total_sessions, 2) if total_sessions > 0 else 0.0
        avg_pct = round(sum(percentages) / total_sessions, 2) if total_sessions > 0 else 0.0

        pass_count = len([r for r in eval_records if r.pass_fail_status == PassFailStatus.PASSED])
        fail_count = len([r for r in eval_records if r.pass_fail_status == PassFailStatus.FAILED])
        pass_rate = round((pass_count / total_sessions) * 100.0, 2) if total_sessions > 0 else 0.0

        summary = AnalyticsSummary(
            total_sessions=total_sessions,
            evaluated_sessions=evaluated_sessions,
            pending_reviews=pending_reviews_count,
            finalized_evaluations=finalized_count,
            average_score=avg_score,
            average_percentage=avg_pct,
            pass_count=pass_count,
            fail_count=fail_count,
            pass_rate=pass_rate,
        )

        # 4. Score Performance & Median
        highest_pct = round(max(percentages), 2) if percentages else 0.0
        lowest_pct = round(min(percentages), 2) if percentages else 0.0
        median_pct = round(float(statistics.median(percentages)), 2) if percentages else 0.0

        score_performance = ScorePerformance(
            average_percentage=avg_pct,
            highest_percentage=highest_pct,
            lowest_percentage=lowest_pct,
            median_percentage=median_pct,
        )

        # 5. Score Distribution Buckets
        score_distribution = ScoreDistribution(
            bucket_0_20=len([p for p in percentages if 0.0 <= p <= 20.0]),
            bucket_21_40=len([p for p in percentages if 20.0 < p <= 40.0]),
            bucket_41_60=len([p for p in percentages if 40.0 < p <= 60.0]),
            bucket_61_80=len([p for p in percentages if 60.0 < p <= 80.0]),
            bucket_81_100=len([p for p in percentages if 80.0 < p <= 100.0]),
        )

        # 6. Pass / Fail Distribution
        pass_fail_distribution = PassFailDistribution(
            passed=pass_count,
            failed=fail_count,
            pending_review=pending_reviews_count,
        )

        # 7. Finalized Evaluation Stats
        fin_records = [r for r in eval_records if r.status == EvaluationStatus.FINALIZED]
        fin_count = len(fin_records)
        fin_scores = [float(r.total_score) for r in fin_records]
        fin_pcts = [float(r.percentage) for r in fin_records]
        fin_pass = len([r for r in fin_records if r.pass_fail_status == PassFailStatus.PASSED])
        fin_fail = len([r for r in fin_records if r.pass_fail_status == PassFailStatus.FAILED])

        finalized_performance = FinalizedPerformance(
            finalized_sessions=fin_count,
            average_finalized_score=round(sum(fin_scores) / fin_count, 2) if fin_count > 0 else 0.0,
            average_finalized_percentage=round(sum(fin_pcts) / fin_count, 2) if fin_count > 0 else 0.0,
            finalized_pass_count=fin_pass,
            finalized_fail_count=fin_fail,
            finalized_pass_rate=round((fin_pass / fin_count) * 100.0, 2) if fin_count > 0 else 0.0,
        )

        # 8. Question-level performance breakdown
        sorted_eqs = sorted(exam.exam_questions, key=lambda x: x.question_order)
        question_performance: List[QuestionPerformanceItem] = []
        difficulty_map: Dict[DifficultyLevel, List[float]] = {
            DifficultyLevel.EASY: [],
            DifficultyLevel.MEDIUM: [],
            DifficultyLevel.HARD: [],
        }
        topic_map: Dict[str, List[float]] = {}

        session_ids = [r.session_id for r in eval_records]

        # Prefetch student answers for all sessions in this exam
        all_answers: List[StudentAnswer] = []
        if session_ids:
            all_answers = (
                db.query(StudentAnswer)
                .options(
                    joinedload(StudentAnswer.selected_options),
                    joinedload(StudentAnswer.evaluation_result),
                )
                .filter(StudentAnswer.session_id.in_(session_ids))
                .all()
            )

        answers_by_question: Dict[uuid.UUID, List[StudentAnswer]] = {}
        for ans in all_answers:
            answers_by_question.setdefault(ans.question_id, []).append(ans)

        for eq in sorted_eqs:
            q = eq.question
            if not q:
                continue

            q_marks = (
                float(eq.marks_override)
                if eq.marks_override is not None
                else float(q.marks)
            )

            q_answers = answers_by_question.get(q.id, [])
            attempted = [
                a for a in q_answers
                if bool(a.selected_options or (a.text_answer and a.text_answer.strip()) or a.answer_image_url)
            ]
            attempted_count = len(attempted)
            unanswered_count = max(0, total_sessions - attempted_count)

            q_scores = [
                float(a.evaluation_result.final_score)
                for a in q_answers
                if a.evaluation_result is not None
            ]
            q_avg_score = round(sum(q_scores) / len(q_scores), 2) if q_scores else 0.0
            q_avg_pct = round((q_avg_score / q_marks) * 100.0, 2) if q_marks > 0 else 0.0

            correct_cnt: Optional[int] = None
            incorrect_cnt: Optional[int] = None
            accuracy_pct: Optional[float] = None
            eval_cnt: Optional[int] = None
            pending_review_cnt: Optional[int] = None

            if q.question_type in [QuestionType.MCQ, QuestionType.MULTI_SELECT]:
                correct_cnt = len([
                    a for a in q_answers
                    if a.evaluation_result and float(a.evaluation_result.final_score) > 0
                ])
                incorrect_cnt = attempted_count - correct_cnt
                accuracy_pct = round((correct_cnt / attempted_count) * 100.0, 2) if attempted_count > 0 else 0.0
            else:
                eval_cnt = len([
                    a for a in q_answers
                    if a.evaluation_result and a.evaluation_result.status in [EvaluationStatus.AI_EVALUATED, EvaluationStatus.MANUAL_REVIEW, EvaluationStatus.FINALIZED]
                ])
                pending_review_cnt = len([
                    a for a in q_answers
                    if a.evaluation_result and a.evaluation_result.status in [EvaluationStatus.PENDING_REVIEW, EvaluationStatus.AI_EVALUATED, EvaluationStatus.MANUAL_REVIEW]
                ])

            question_performance.append(
                QuestionPerformanceItem(
                    question_id=q.id,
                    question_order=eq.question_order,
                    question_text=q.question_text,
                    question_type=q.question_type,
                    marks=q_marks,
                    topic=q.topic if q.topic and q.topic.strip() else None,
                    difficulty=q.difficulty or DifficultyLevel.MEDIUM,
                    attempted_count=attempted_count,
                    unanswered_count=unanswered_count,
                    correct_count=correct_cnt,
                    incorrect_count=incorrect_cnt,
                    accuracy_percentage=accuracy_pct,
                    evaluated_count=eval_cnt,
                    pending_review_count=pending_review_cnt,
                    average_score=q_avg_score,
                    average_percentage=q_avg_pct,
                )
            )

            # Accumulate Difficulty / Topic stats
            diff_key = q.difficulty or DifficultyLevel.MEDIUM
            difficulty_map.setdefault(diff_key, []).append(q_avg_pct)

            if q.topic and q.topic.strip():
                top_key = q.topic.strip()
                topic_map.setdefault(top_key, []).append(q_avg_pct)

        # 9. Difficulty Performance
        difficulty_performance: List[DifficultyPerformanceItem] = []
        for diff_enum in [DifficultyLevel.EASY, DifficultyLevel.MEDIUM, DifficultyLevel.HARD]:
            pct_list = difficulty_map.get(diff_enum, [])
            difficulty_performance.append(
                DifficultyPerformanceItem(
                    difficulty=diff_enum,
                    question_count=len(pct_list),
                    average_percentage=round(sum(pct_list) / len(pct_list), 2) if pct_list else 0.0,
                )
            )

        # 10. Topic Performance
        topic_performance: List[TopicPerformanceItem] = []
        for topic_name, pct_list in topic_map.items():
            topic_performance.append(
                TopicPerformanceItem(
                    topic=topic_name,
                    question_count=len(pct_list),
                    average_percentage=round(sum(pct_list) / len(pct_list), 2) if pct_list else 0.0,
                )
            )

        # 11. Pending Reviews List
        pending_reviews: List[PendingReviewItem] = []
        for r in eval_records:
            if r.status in [EvaluationStatus.PENDING_REVIEW, EvaluationStatus.AI_EVALUATED, EvaluationStatus.MANUAL_REVIEW]:
                st = r.student
                st_name = f"{st.first_name} {st.last_name}" if st else "Unknown Student"
                st_email = st.email if st else ""
                sess = r.session

                # Count pending subjective questions for this session
                unfinalized_q_count = 0
                if sess and sess.answers:
                    for ans in sess.answers:
                        if ans.evaluation_result and ans.evaluation_result.status != EvaluationStatus.FINALIZED:
                            unfinalized_q_count += 1

                pending_reviews.append(
                    PendingReviewItem(
                        session_id=r.session_id,
                        student_id=r.student_id,
                        student_name=st_name,
                        student_email=st_email,
                        pending_question_count=max(1, unfinalized_q_count),
                        current_score=float(r.total_score),
                        maximum_marks=float(r.maximum_marks),
                        submitted_at=sess.submitted_at if sess else None,
                        status=r.status,
                    )
                )

        # 12. Student Performance Table (Filtered & Paginated)
        filtered_records = eval_records

        if search and search.strip():
            search_term = search.strip().lower()
            filtered_records = [
                r for r in filtered_records
                if (
                    (r.student and (search_term in r.student.first_name.lower() or search_term in r.student.last_name.lower() or search_term in r.student.email.lower()))
                    or search_term in (r.exam.title if r.exam else "").lower()
                )
            ]

        if pass_fail and pass_fail.strip():
            pf_upper = pass_fail.strip().upper()
            filtered_records = [r for r in filtered_records if r.pass_fail_status.value == pf_upper]

        if session_status and session_status.strip():
            st_upper = session_status.strip().upper()
            filtered_records = [r for r in filtered_records if r.status.value == st_upper]

        total_student_items = len(filtered_records)
        total_pages = math.ceil(total_student_items / page_size) if total_student_items > 0 else 0

        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        paged_records = filtered_records[start_idx:end_idx]

        student_items: List[StudentResultResponse] = []
        for r in paged_records:
            st = r.student
            sess = r.session
            student_items.append(
                StudentResultResponse(
                    id=r.id,
                    session_id=r.session_id,
                    exam_id=r.exam_id,
                    exam_title=exam.title,
                    exam_subject=exam.subject,
                    student_id=r.student_id,
                    student_name=f"{st.first_name} {st.last_name}" if st else "Unknown Student",
                    student_email=st.email if st else "",
                    submitted_at=sess.submitted_at if sess else None,
                    total_questions=r.total_questions,
                    answered_questions=r.answered_questions,
                    unanswered_questions=r.unanswered_questions,
                    correct_answers=r.correct_answers,
                    incorrect_answers=r.incorrect_answers,
                    objective_marks=float(r.objective_marks),
                    subjective_marks=float(r.subjective_marks),
                    negative_marks=float(r.negative_marks),
                    total_score=float(r.total_score),
                    maximum_marks=float(r.maximum_marks),
                    percentage=float(r.percentage),
                    passing_marks=float(r.passing_marks),
                    pass_fail_status=r.pass_fail_status,
                    status=r.status,
                )
            )

        student_performance = PaginatedStudentResultResponse(
            items=student_items,
            total=total_student_items,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
        )

        return ExamAnalyticsResponse(
            exam_info=ExamBasicInfo(
                id=exam.id,
                title=exam.title,
                subject=exam.subject,
                status=exam.status.value if hasattr(exam.status, 'value') else str(exam.status),
                total_marks=float(exam.total_marks),
                passing_marks=float(exam.passing_marks),
            ),
            summary=summary,
            score_performance=score_performance,
            score_distribution=score_distribution,
            pass_fail_distribution=pass_fail_distribution,
            finalized_performance=finalized_performance,
            question_performance=question_performance,
            difficulty_performance=difficulty_performance,
            topic_performance=topic_performance,
            pending_reviews=pending_reviews,
            student_performance=student_performance,
        )


analytics_service = AnalyticsService()
