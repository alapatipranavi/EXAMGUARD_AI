import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import select, and_, func
from fastapi import HTTPException, status

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamStatus, ExamTargetType
from app.models.exam_session import ExamSession, SessionStatus
from app.models.evaluation import ExamSessionEvaluation, EvaluationStatus
from app.models.academic import College
from app.repositories.academic_repository import academic_repository
from app.schemas.examiner import (
    ExaminerDashboardSummary,
    ExaminerAcademicScope,
    ExaminerExamItem,
    ExaminerPendingReviewItem,
    ExaminerRecentActivityItem,
    ExaminerDashboardResponse,
)


class ExaminerService:
    def get_examiner_dashboard(self, db: Session, current_user: User) -> ExaminerDashboardResponse:
        """Retrieves complete Examiner dashboard metrics, scope, exams, pending reviews, and recent activity."""
        # 1. Security Check: Must be EXAMINER or ADMIN
        if current_user.role not in [UserRole.EXAMINER, UserRole.ADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Examiners can access the Examiner Dashboard."
            )

        greeting_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Examiner"

        # 2. Academic Scope
        college_id = current_user.college_id
        col_name, col_code = None, None
        if college_id:
            col = db.scalar(select(College).where(College.id == college_id))
            if col:
                col_name, col_code = col.name, col.code

        academic_scope = ExaminerAcademicScope(
            college_id=college_id,
            college_name=col_name,
            college_code=col_code,
        )

        # 3. Query Examiner's Created Exams
        raw_exams = list(
            db.scalars(
                select(Exam)
                .where(Exam.created_by == current_user.id)
                .order_by(Exam.created_at.desc())
            ).all()
        )
        exam_ids = [e.id for e in raw_exams]

        # 4. Compute Summary Metrics
        total_exams = len(raw_exams)
        published_exams = len([
            e for e in raw_exams
            if e.status in [ExamStatus.PUBLISHED, ExamStatus.ACTIVE, ExamStatus.SCHEDULED]
        ])

        active_sessions_count = 0
        if exam_ids:
            active_sessions_count = db.scalar(
                select(func.count(ExamSession.id)).where(
                    and_(
                        ExamSession.exam_id.in_(exam_ids),
                        ExamSession.status.in_([SessionStatus.IN_PROGRESS, SessionStatus.CREATED])
                    )
                )
            ) or 0

        # Pending Reviews Query
        pending_review_items: List[ExaminerPendingReviewItem] = []
        if exam_ids:
            pending_evals = list(
                db.scalars(
                    select(ExamSessionEvaluation)
                    .where(
                        and_(
                            ExamSessionEvaluation.exam_id.in_(exam_ids),
                            ExamSessionEvaluation.status.in_([
                                EvaluationStatus.PENDING_REVIEW,
                                EvaluationStatus.AI_EVALUATED,
                                EvaluationStatus.MANUAL_REVIEW
                            ])
                        )
                    )
                    .order_by(ExamSessionEvaluation.created_at.desc())
                ).all()
            )

            for pe in pending_evals:
                student = pe.student
                exam = pe.exam
                session = pe.session

                st_name = f"{student.first_name} {student.last_name}" if student else "Unknown Student"
                st_email = student.email if student else ""
                ex_title = exam.title if exam else "Exam"

                # Count unfinalized questions for session
                unfinalized_count = 0
                if session and session.answers:
                    for ans in session.answers:
                        if ans.evaluation_result and ans.evaluation_result.status != EvaluationStatus.FINALIZED:
                            unfinalized_count += 1

                pending_review_items.append(
                    ExaminerPendingReviewItem(
                        session_id=pe.session_id,
                        exam_id=pe.exam_id,
                        exam_title=ex_title,
                        student_id=pe.student_id,
                        student_name=st_name,
                        student_email=st_email,
                        pending_question_count=max(1, unfinalized_count),
                        status=pe.status.value if hasattr(pe.status, "value") else str(pe.status),
                        submitted_at=session.submitted_at if session else pe.created_at,
                    )
                )

        pending_reviews_count = len(pending_review_items)

        summary = ExaminerDashboardSummary(
            total_exams=total_exams,
            published_exams=published_exams,
            active_sessions=active_sessions_count,
            pending_reviews=pending_reviews_count,
        )

        # 5. Build Exam Items for Dashboard
        exam_items: List[ExaminerExamItem] = []
        for e in raw_exams:
            # Count questions
            q_count = len(e.exam_questions)

            # Target summary string
            target_str = "All College Students"
            if e.target_type == ExamTargetType.COLLEGE or not e.target_type:
                target_str = "Entire College"
            elif e.target_type == ExamTargetType.DEPARTMENT:
                dept = e.target_department
                target_str = f"Dept: {dept.name} ({dept.code})" if dept else "Department"
            elif e.target_type == ExamTargetType.YEAR:
                y = e.target_year_of_study
                suffix = "st" if y == 1 else "nd" if y == 2 else "rd" if y == 3 else "th"
                yr_str = f"{y}{suffix} Year" if y else "All Years"
                dept = e.target_department
                target_str = f"{yr_str} ({dept.code})" if dept else yr_str
            elif e.target_type == ExamTargetType.SECTION:
                sec = e.target_section
                target_str = f"Section: {sec.name}" if sec else "Section"
            elif e.target_type == ExamTargetType.SPECIFIC_STUDENTS:
                target_str = f"{len(e.target_students)} Selected Students"

            # Eligible student count
            spec_ids = [ts.student_id for ts in e.target_students] if e.target_type == ExamTargetType.SPECIFIC_STUDENTS else None
            eligible_count = academic_repository.count_eligible_students(
                db,
                college_id=college_id,
                target_type=e.target_type,
                department_id=e.target_department_id,
                year_of_study=e.target_year_of_study,
                section_id=e.target_section_id,
                specific_student_ids=spec_ids,
            )

            # Attempt count
            attempts = db.scalar(
                select(func.count(ExamSession.id)).where(ExamSession.exam_id == e.id)
            ) or 0

            exam_items.append(
                ExaminerExamItem(
                    id=e.id,
                    title=e.title,
                    subject=e.subject,
                    status=e.status.value if hasattr(e.status, "value") else str(e.status),
                    duration_minutes=e.duration_minutes,
                    total_marks=float(e.total_marks),
                    question_count=q_count,
                    start_at=e.start_at,
                    end_at=e.end_at,
                    target_type=e.target_type.value if e.target_type else None,
                    target_summary=target_str,
                    eligible_student_count=eligible_count,
                    attempt_count=attempts,
                    created_at=e.created_at,
                )
            )

        # 6. Build Recent Activity Feed
        recent_activity: List[ExaminerRecentActivityItem] = []
        if exam_ids:
            recent_sessions = list(
                db.scalars(
                    select(ExamSession)
                    .where(ExamSession.exam_id.in_(exam_ids))
                    .order_by(ExamSession.updated_at.desc())
                    .limit(10)
                ).all()
            )

            for s in recent_sessions:
                student = s.student
                exam = s.exam
                st_name = f"{student.first_name} {student.last_name}" if student else "Student"
                ex_title = exam.title if exam else "Exam"

                if s.status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]:
                    event_type = "SESSION_SUBMITTED"
                    desc = f"{st_name} submitted exam session for '{ex_title}'"
                    ts = s.submitted_at or s.updated_at
                elif s.status == SessionStatus.IN_PROGRESS:
                    event_type = "SESSION_STARTED"
                    desc = f"{st_name} started exam session for '{ex_title}'"
                    ts = s.started_at or s.updated_at
                else:
                    event_type = "SESSION_ACTIVITY"
                    desc = f"Session status '{s.status.value}' for {st_name} on '{ex_title}'"
                    ts = s.updated_at

                recent_activity.append(
                    ExaminerRecentActivityItem(
                        id=str(s.id),
                        event_type=event_type,
                        description=desc,
                        student_name=st_name,
                        exam_title=ex_title,
                        timestamp=ts,
                        session_id=s.id,
                        exam_id=s.exam_id,
                    )
                )

        return ExaminerDashboardResponse(
            greeting_name=greeting_name,
            summary=summary,
            academic_scope=academic_scope,
            exams=exam_items,
            pending_reviews=pending_review_items,
            recent_activity=recent_activity,
        )


examiner_service = ExaminerService()
