import uuid
from datetime import datetime
import math
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy import select, and_, or_, func, text
from fastapi import HTTPException, status

from app.core.config import settings
from app.models.user import User, UserRole
from app.models.exam import Exam, ExamStatus, ExamTargetType, ExamQuestion, ExamTargetStudent
from app.models.question import Question, QuestionType
from app.models.exam_session import ExamSession, SessionStatus
from app.models.evaluation import ExamSessionEvaluation, EvaluationStatus
from app.models.academic import College, Department, Section
from app.schemas.admin import (
    AdminDashboardSummary,
    AdminUserMetrics,
    AdminAcademicMetrics,
    AdminExamBreakdown,
    AdminActivityItem,
    AdminSystemStatus,
    AdminDashboardResponse,
)
from app.schemas.admin_student import (
    AdminStudentListItem,
    AdminStudentSummaryMetrics,
    PaginatedAdminStudentResponse,
    AdminStudentRecentSessionItem,
    AdminStudentDetailResponse,
)
from app.schemas.admin_examiner import (
    AdminExaminerListItem,
    AdminExaminerSummaryMetrics,
    PaginatedAdminExaminerResponse,
    AdminExaminerRecentExamItem,
    AdminExaminerDetailResponse,
)
from app.schemas.admin_exam import (
    AdminExamListItem,
    AdminExamSummaryMetrics,
    PaginatedAdminExamResponse,
    AdminExamDetailResponse,
)
from app.repositories.academic_repository import academic_repository
from app.repositories.student_exam_repository import student_exam_repository


class AdminService:
    def get_admin_dashboard(self, db: Session, current_user: User) -> AdminDashboardResponse:
        """Retrieves system-wide metrics, user breakdown, academic structure, exam overview, platform activity, and health status for Admin."""
        # 1. Security Check: Must be ADMIN
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only System Administrators can access the Admin Dashboard."
            )

        greeting_name = f"{current_user.first_name} {current_user.last_name}".strip() or "Administrator"

        # 2. User Metrics
        all_users = list(db.scalars(select(User)).all())

        active_students = len([u for u in all_users if u.role == UserRole.STUDENT and u.is_active])
        active_examiners = len([u for u in all_users if u.role == UserRole.EXAMINER and u.is_active])
        total_students = len([u for u in all_users if u.role == UserRole.STUDENT])
        total_examiners = len([u for u in all_users if u.role == UserRole.EXAMINER])
        inactive_users = len([u for u in all_users if not u.is_active])

        user_metrics = AdminUserMetrics(
            total_students=total_students,
            total_examiners=total_examiners,
            active_students=active_students,
            active_examiners=active_examiners,
            inactive_users=inactive_users,
        )

        # 3. Academic Structure Metrics
        total_colleges = db.scalar(select(func.count(College.id))) or 0
        total_departments = db.scalar(select(func.count(Department.id))) or 0
        total_sections = db.scalar(select(func.count(Section.id))) or 0
        students_with_profiles = len([
            u for u in all_users
            if u.role == UserRole.STUDENT and (u.college_id is not None or u.department_id is not None)
        ])

        academic_metrics = AdminAcademicMetrics(
            total_colleges=total_colleges,
            total_departments=total_departments,
            total_sections=total_sections,
            students_with_academic_profiles=students_with_profiles,
        )

        # 4. Examination Breakdown & Session Metrics
        all_exams = list(db.scalars(select(Exam)).all())
        total_exams = len(all_exams)

        draft_count = len([e for e in all_exams if e.status == ExamStatus.DRAFT])
        published_count = len([e for e in all_exams if e.status == ExamStatus.PUBLISHED])
        scheduled_count = len([e for e in all_exams if e.status == ExamStatus.SCHEDULED])
        active_exam_count = len([e for e in all_exams if e.status == ExamStatus.ACTIVE])
        completed_exam_count = len([e for e in all_exams if e.status == ExamStatus.COMPLETED])
        archived_count = len([e for e in all_exams if e.status == ExamStatus.ARCHIVED])

        exam_breakdown = AdminExamBreakdown(
            draft=draft_count,
            published=published_count,
            scheduled=scheduled_count,
            active=active_exam_count,
            completed=completed_exam_count,
            archived=archived_count,
        )

        # Session Metrics
        active_sessions_count = db.scalar(
            select(func.count(ExamSession.id)).where(
                ExamSession.status.in_([SessionStatus.IN_PROGRESS, SessionStatus.CREATED])
            )
        ) or 0

        completed_sessions_count = db.scalar(
            select(func.count(ExamSession.id)).where(
                ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED])
            )
        ) or 0

        pending_reviews_count = db.scalar(
            select(func.count(ExamSessionEvaluation.id)).where(
                ExamSessionEvaluation.status.in_([
                    EvaluationStatus.PENDING_REVIEW,
                    EvaluationStatus.AI_EVALUATED,
                    EvaluationStatus.MANUAL_REVIEW
                ])
            )
        ) or 0

        summary = AdminDashboardSummary(
            total_students=active_students,
            total_examiners=active_examiners,
            total_exams=total_exams,
            active_sessions=active_sessions_count,
            completed_exams=completed_sessions_count,
            pending_reviews=pending_reviews_count,
            total_colleges=total_colleges,
            total_departments=total_departments,
        )

        # 5. Derive Recent Platform Activity
        activity_items: List[AdminActivityItem] = []

        # Recent user registrations / provisioning
        recent_users = list(
            db.scalars(
                select(User).order_by(User.created_at.desc()).limit(5)
            ).all()
        )
        for u in recent_users:
            role_str = u.role.value if hasattr(u.role, 'value') else str(u.role)
            activity_items.append(
                AdminActivityItem(
                    id=f"user_{u.id}",
                    event_type="USER_PROVISIONED" if u.role == UserRole.EXAMINER else "USER_REGISTERED",
                    description=f"{role_str.capitalize()} account created for {u.first_name} {u.last_name} ({u.email})",
                    timestamp=u.created_at,
                    user_name=f"{u.first_name} {u.last_name}",
                )
            )

        # Recent exams created/published
        recent_exams = list(
            db.scalars(
                select(Exam).order_by(Exam.created_at.desc()).limit(5)
            ).all()
        )
        for e in recent_exams:
            status_str = e.status.value if hasattr(e.status, 'value') else str(e.status)
            creator = e.creator
            creator_name = f"{creator.first_name} {creator.last_name}" if creator else "Examiner"
            activity_items.append(
                AdminActivityItem(
                    id=f"exam_{e.id}",
                    event_type="EXAM_PUBLISHED" if e.status == ExamStatus.PUBLISHED else "EXAM_CREATED",
                    description=f"Exam '{e.title}' [{status_str}] created by {creator_name}",
                    timestamp=e.created_at,
                    target_name=e.title,
                )
            )

        # Recent exam session submissions
        recent_sessions = list(
            db.scalars(
                select(ExamSession)
                .where(ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]))
                .order_by(ExamSession.updated_at.desc())
                .limit(5)
            ).all()
        )
        for s in recent_sessions:
            st = s.student
            ex = s.exam
            st_name = f"{st.first_name} {st.last_name}" if st else "Student"
            ex_title = ex.title if ex else "Exam"
            activity_items.append(
                AdminActivityItem(
                    id=f"session_{s.id}",
                    event_type="SESSION_SUBMITTED",
                    description=f"Student {st_name} completed exam session for '{ex_title}'",
                    timestamp=s.submitted_at or s.updated_at,
                    user_name=st_name,
                    target_name=ex_title,
                )
            )

        # Sort combined activity items by timestamp desc and take top 10
        activity_items.sort(key=lambda x: x.timestamp, reverse=True)
        recent_activity = activity_items[:10]

        # 6. System Health Check
        db_status = "connected"
        try:
            db.execute(text("SELECT 1"))
        except Exception:
            db_status = "degraded"

        system_status = AdminSystemStatus(
            backend="online",
            database=db_status,
            version=getattr(settings, "PROJECT_VERSION", "1.0.0"),
        )

        return AdminDashboardResponse(
            greeting_name=greeting_name,
            summary=summary,
            users=user_metrics,
            academic=academic_metrics,
            examinations=exam_breakdown,
            recent_activity=recent_activity,
            system_status=system_status,
        )

    def list_students(
        self,
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        college_id: Optional[uuid.UUID] = None,
        department_id: Optional[uuid.UUID] = None,
        year_of_study: Optional[int] = None,
        section_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAdminStudentResponse:
        """Lists students with academic hierarchy filters, search, and pagination (Admin only)."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can view student management.",
            )

        query = (
            db.query(User)
            .options(
                joinedload(User.college),
                joinedload(User.department),
                joinedload(User.section),
            )
            .filter(User.role == UserRole.STUDENT)
        )

        if search:
            search_fmt = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_fmt),
                    User.last_name.ilike(search_fmt),
                    User.email.ilike(search_fmt),
                )
            )

        if college_id is not None:
            query = query.filter(User.college_id == college_id)

        if department_id is not None:
            query = query.filter(User.department_id == department_id)

        if year_of_study is not None:
            query = query.filter(User.year_of_study == year_of_study)

        if section_id is not None:
            query = query.filter(User.section_id == section_id)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        total = query.count()
        students = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Global Student Summary Metrics
        total_students_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.STUDENT)) or 0
        active_students_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.STUDENT, User.is_active == True)) or 0
        inactive_students_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.STUDENT, User.is_active == False)) or 0
        unassigned_profiles_count = db.scalar(
            select(func.count(User.id)).where(
                User.role == UserRole.STUDENT,
                or_(User.college_id == None, User.department_id == None),
            )
        ) or 0

        summary = AdminStudentSummaryMetrics(
            total_students=total_students_count,
            active_students=active_students_count,
            inactive_students=inactive_students_count,
            unassigned_academic_profiles=unassigned_profiles_count,
        )

        items = []
        for s in students:
            items.append(
                AdminStudentListItem(
                    id=s.id,
                    email=s.email,
                    first_name=s.first_name,
                    last_name=s.last_name,
                    role=s.role,
                    is_active=s.is_active,
                    college_id=s.college_id,
                    college_name=s.college.name if s.college else None,
                    college_code=s.college.code if s.college else None,
                    department_id=s.department_id,
                    department_name=s.department.name if s.department else None,
                    department_code=s.department.code if s.department else None,
                    year_of_study=s.year_of_study,
                    section_id=s.section_id,
                    section_name=s.section.name if s.section else None,
                    section_code=s.section.code if s.section else None,
                    is_face_registered=s.is_face_registered,
                    face_registered_at=s.face_registered_at,
                    created_at=s.created_at,
                    updated_at=s.updated_at,
                )
            )

        return PaginatedAdminStudentResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary,
        )

    def get_student_detail(
        self,
        db: Session,
        current_user: User,
        student_id: uuid.UUID,
    ) -> AdminStudentDetailResponse:
        """Retrieves detailed student profile and lightweight exam activity (Admin only)."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can view student details.",
            )

        student = (
            db.query(User)
            .options(
                joinedload(User.college),
                joinedload(User.department),
                joinedload(User.section),
            )
            .filter(User.id == student_id)
            .first()
        )

        if not student or student.role != UserRole.STUDENT:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Student not found.",
            )

        # 1. Exam Counts
        attempted_count = (
            db.scalar(
                select(func.count(ExamSession.id)).where(ExamSession.student_id == student.id)
            )
            or 0
        )

        completed_count = (
            db.scalar(
                select(func.count(ExamSession.id)).where(
                    ExamSession.student_id == student.id,
                    ExamSession.status.in_([SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]),
                )
            )
            or 0
        )

        # Assigned Exams Count
        published_exams, _ = student_exam_repository.list_published_exams(
            db, search=None, subject=None, page=1, page_size=1000
        )
        assigned_count = sum(
            1 for e in published_exams if academic_repository.is_student_authorized_for_exam(db, student, e)
        )

        # 2. Recent Exam Sessions (up to 5)
        recent_sessions_db = (
            db.query(ExamSession)
            .options(
                joinedload(ExamSession.exam),
                joinedload(ExamSession.evaluation),
            )
            .filter(ExamSession.student_id == student.id)
            .order_by(ExamSession.created_at.desc())
            .limit(5)
            .all()
        )

        recent_sessions: List[AdminStudentRecentSessionItem] = []
        for sess in recent_sessions_db:
            exam_title = sess.exam.title if sess.exam else "Unknown Exam"
            exam_subject = sess.exam.subject if sess.exam else "General"
            eval_pct = float(sess.evaluation.percentage) if sess.evaluation and sess.evaluation.percentage is not None else None
            eval_pf = sess.evaluation.pass_fail_status.value if sess.evaluation and hasattr(sess.evaluation.pass_fail_status, 'value') else (str(sess.evaluation.pass_fail_status) if sess.evaluation and sess.evaluation.pass_fail_status else None)

            recent_sessions.append(
                AdminStudentRecentSessionItem(
                    session_id=sess.id,
                    exam_id=sess.exam_id,
                    exam_title=exam_title,
                    exam_subject=exam_subject,
                    status=sess.status.value if hasattr(sess.status, 'value') else str(sess.status),
                    started_at=sess.started_at,
                    submitted_at=sess.submitted_at,
                    percentage=eval_pct,
                    pass_fail_status=eval_pf,
                )
            )

        return AdminStudentDetailResponse(
            id=student.id,
            email=student.email,
            first_name=student.first_name,
            last_name=student.last_name,
            role=student.role,
            is_active=student.is_active,
            college_id=student.college_id,
            college_name=student.college.name if student.college else None,
            college_code=student.college.code if student.college else None,
            department_id=student.department_id,
            department_name=student.department.name if student.department else None,
            department_code=student.department.code if student.department else None,
            year_of_study=student.year_of_study,
            section_id=student.section_id,
            section_name=student.section.name if student.section else None,
            section_code=student.section.code if student.section else None,
            is_face_registered=student.is_face_registered,
            face_registered_at=student.face_registered_at,
            created_at=student.created_at,
            updated_at=student.updated_at,
            exams_assigned_count=assigned_count,
            exams_attempted_count=attempted_count,
            exams_completed_count=completed_count,
            recent_sessions=recent_sessions,
        )

    def list_examiners(
        self,
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        college_id: Optional[uuid.UUID] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAdminExaminerResponse:
        """Lists examiners with college filter, status filter, search, and pagination (Admin only)."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can view examiner management.",
            )

        query = (
            db.query(User)
            .options(joinedload(User.college))
            .filter(User.role == UserRole.EXAMINER)
        )

        if search:
            search_fmt = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    User.first_name.ilike(search_fmt),
                    User.last_name.ilike(search_fmt),
                    User.email.ilike(search_fmt),
                )
            )

        if college_id is not None:
            query = query.filter(User.college_id == college_id)

        if is_active is not None:
            query = query.filter(User.is_active == is_active)

        total = query.count()
        examiners = (
            query.order_by(User.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Global Examiner Summary Metrics
        total_examiners_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.EXAMINER)) or 0
        active_examiners_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.EXAMINER, User.is_active == True)) or 0
        inactive_examiners_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.EXAMINER, User.is_active == False)) or 0
        unassigned_college_count = db.scalar(select(func.count(User.id)).where(User.role == UserRole.EXAMINER, User.college_id == None)) or 0

        summary = AdminExaminerSummaryMetrics(
            total_examiners=total_examiners_count,
            active_examiners=active_examiners_count,
            inactive_examiners=inactive_examiners_count,
            unassigned_college=unassigned_college_count,
        )

        items = []
        for ex in examiners:
            total_exams = db.scalar(select(func.count(Exam.id)).where(Exam.created_by == ex.id)) or 0
            published_exams = db.scalar(
                select(func.count(Exam.id)).where(
                    Exam.created_by == ex.id,
                    Exam.status.in_([ExamStatus.PUBLISHED, ExamStatus.ACTIVE, ExamStatus.SCHEDULED]),
                )
            ) or 0

            items.append(
                AdminExaminerListItem(
                    id=ex.id,
                    email=ex.email,
                    first_name=ex.first_name,
                    last_name=ex.last_name,
                    role=ex.role,
                    is_active=ex.is_active,
                    college_id=ex.college_id,
                    college_name=ex.college.name if ex.college else None,
                    college_code=ex.college.code if ex.college else None,
                    total_exams_count=total_exams,
                    published_exams_count=published_exams,
                    created_at=ex.created_at,
                    updated_at=ex.updated_at,
                )
            )

        return PaginatedAdminExaminerResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary,
        )

    def get_examiner_detail(
        self,
        db: Session,
        current_user: User,
        examiner_id: uuid.UUID,
    ) -> AdminExaminerDetailResponse:
        """Retrieves detailed examiner profile and examination ownership activity (Admin only)."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can view examiner details.",
            )

        examiner = (
            db.query(User)
            .options(joinedload(User.college))
            .filter(User.id == examiner_id)
            .first()
        )

        if not examiner or examiner.role != UserRole.EXAMINER:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Examiner not found.",
            )

        # Query all exams created by this examiner
        exams = (
            db.query(Exam)
            .filter(Exam.created_by == examiner.id)
            .order_by(Exam.created_at.desc())
            .all()
        )

        total_exams_created = len(exams)
        published_exams_count = len([
            e for e in exams if e.status in [ExamStatus.PUBLISHED, ExamStatus.ACTIVE, ExamStatus.SCHEDULED]
        ])
        draft_exams_count = len([e for e in exams if e.status == ExamStatus.DRAFT])
        completed_exams_count = len([e for e in exams if e.status == ExamStatus.COMPLETED])

        recent_exams = []
        for e in exams[:10]:
            recent_exams.append(
                AdminExaminerRecentExamItem(
                    id=e.id,
                    title=e.title,
                    subject=e.subject,
                    status=e.status.value if hasattr(e.status, "value") else str(e.status),
                    duration_minutes=e.duration_minutes,
                    total_marks=float(e.total_marks),
                    passing_marks=float(e.passing_marks),
                    target_type=e.target_type.value if e.target_type and hasattr(e.target_type, "value") else (str(e.target_type) if e.target_type else None),
                    created_at=e.created_at,
                    start_at=e.start_at,
                    end_at=e.end_at,
                )
            )

        return AdminExaminerDetailResponse(
            id=examiner.id,
            email=examiner.email,
            first_name=examiner.first_name,
            last_name=examiner.last_name,
            role=examiner.role,
            is_active=examiner.is_active,
            college_id=examiner.college_id,
            college_name=examiner.college.name if examiner.college else None,
            college_code=examiner.college.code if examiner.college else None,
            created_at=examiner.created_at,
            updated_at=examiner.updated_at,
            total_exams_created=total_exams_created,
            published_exams_count=published_exams_count,
            draft_exams_count=draft_exams_count,
            completed_exams_count=completed_exams_count,
            recent_exams=recent_exams,
        )

    @staticmethod
    def _format_target_description(exam: Exam) -> str:
        tt = exam.target_type
        if not tt or tt == ExamTargetType.COLLEGE:
            if exam.creator and exam.creator.college:
                col_name = exam.creator.college.code or exam.creator.college.name
                return f"Entire College ({col_name})"
            return "Entire College (All Students)"
        elif tt == ExamTargetType.DEPARTMENT:
            dept_name = exam.target_department.name if exam.target_department else "Selected Department"
            return f"Department: {dept_name}"
        elif tt == ExamTargetType.YEAR:
            dept_part = f" - {exam.target_department.name}" if exam.target_department else ""
            year_str = f"Year {exam.target_year_of_study}" if exam.target_year_of_study else "Specific Year"
            return f"{year_str}{dept_part}"
        elif tt == ExamTargetType.SECTION:
            sec_name = exam.target_section.name if exam.target_section else "Selected Section"
            year_part = f" (Year {exam.target_year_of_study})" if exam.target_year_of_study else ""
            return f"Section {sec_name}{year_part}"
        elif tt == ExamTargetType.SPECIFIC_STUDENTS:
            count = len(exam.target_students) if exam.target_students else 0
            return f"Specific Students ({count} assigned)"
        return "Open / General"

    def list_exams(
        self,
        db: Session,
        current_user: User,
        search: Optional[str] = None,
        subject: Optional[str] = None,
        examiner_id: Optional[uuid.UUID] = None,
        college_id: Optional[uuid.UUID] = None,
        status_filter: Optional[ExamStatus] = None,
        target_type: Optional[ExamTargetType] = None,
        page: int = 1,
        page_size: int = 10,
    ) -> PaginatedAdminExamResponse:
        """Lists platform exams with search, filters, pagination, and institutional metrics (Admin only)."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can view admin exam listings.",
            )

        query = db.query(Exam).join(User, Exam.created_by == User.id)

        if search:
            search_fmt = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Exam.title.ilike(search_fmt),
                    Exam.subject.ilike(search_fmt),
                    User.first_name.ilike(search_fmt),
                    User.last_name.ilike(search_fmt),
                    User.email.ilike(search_fmt),
                )
            )

        if subject:
            query = query.filter(Exam.subject.ilike(f"%{subject.strip()}%"))

        if examiner_id is not None:
            query = query.filter(Exam.created_by == examiner_id)

        if college_id is not None:
            query = query.filter(User.college_id == college_id)

        if status_filter is not None:
            query = query.filter(Exam.status == status_filter)

        if target_type is not None:
            query = query.filter(Exam.target_type == target_type)

        total = query.count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        # Institutional summary metrics
        total_exams_count = db.scalar(select(func.count(Exam.id))) or 0
        published_active_count = db.scalar(
            select(func.count(Exam.id)).where(
                Exam.status.in_([ExamStatus.PUBLISHED, ExamStatus.ACTIVE, ExamStatus.SCHEDULED])
            )
        ) or 0
        completed_count = db.scalar(
            select(func.count(Exam.id)).where(Exam.status == ExamStatus.COMPLETED)
        ) or 0
        draft_count = db.scalar(
            select(func.count(Exam.id)).where(Exam.status == ExamStatus.DRAFT)
        ) or 0

        summary = AdminExamSummaryMetrics(
            total_exams=total_exams_count,
            published_active_exams=published_active_count,
            completed_exams=completed_count,
            draft_exams=draft_count,
        )

        exams = (
            query.options(
                joinedload(Exam.creator).joinedload(User.college),
                joinedload(Exam.target_department),
                joinedload(Exam.target_section),
                selectinload(Exam.exam_questions),
                selectinload(Exam.sessions),
                selectinload(Exam.target_students),
            )
            .order_by(Exam.created_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        items: List[AdminExamListItem] = []
        for ex in exams:
            examiner = ex.creator
            examiner_name = f"{examiner.first_name} {examiner.last_name}".strip() if examiner else "Unknown"
            examiner_email = examiner.email if examiner else ""
            college_name = examiner.college.name if examiner and examiner.college else None
            college_code = examiner.college.code if examiner and examiner.college else None

            sessions_count = len(ex.sessions) if ex.sessions else 0
            completed_sessions = len([
                s for s in (ex.sessions or [])
                if s.status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]
            ])

            target_desc = self._format_target_description(ex)
            specific_ids = [ts.student_id for ts in ex.target_students] if (ex.target_type == ExamTargetType.SPECIFIC_STUDENTS and ex.target_students) else None

            eligible_students = academic_repository.count_eligible_students(
                db=db,
                college_id=examiner.college_id if examiner else None,
                target_type=ex.target_type,
                department_id=ex.target_department_id,
                year_of_study=ex.target_year_of_study,
                section_id=ex.target_section_id,
                specific_student_ids=specific_ids,
            )

            items.append(
                AdminExamListItem(
                    id=ex.id,
                    title=ex.title,
                    subject=ex.subject,
                    status=ex.status,
                    duration_minutes=ex.duration_minutes,
                    total_marks=float(ex.total_marks),
                    passing_marks=float(ex.passing_marks),
                    question_count=len(ex.exam_questions) if ex.exam_questions else 0,
                    created_by=ex.created_by,
                    examiner_name=examiner_name,
                    examiner_email=examiner_email,
                    examiner_college_name=college_name,
                    examiner_college_code=college_code,
                    target_type=ex.target_type,
                    target_description=target_desc,
                    eligible_students_count=eligible_students,
                    sessions_count=sessions_count,
                    completed_sessions_count=completed_sessions,
                    created_at=ex.created_at,
                    start_at=ex.start_at,
                    end_at=ex.end_at,
                )
            )

        return PaginatedAdminExamResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            summary=summary,
        )

    def get_exam_detail(
        self,
        db: Session,
        current_user: User,
        exam_id: uuid.UUID,
    ) -> AdminExamDetailResponse:
        """Retrieves in-depth examination configuration, audience targeting, and activity metrics (Admin only)."""
        if current_user.role != UserRole.ADMIN:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Only Administrators can view exam details.",
            )

        exam = (
            db.query(Exam)
            .options(
                joinedload(Exam.creator).joinedload(User.college),
                joinedload(Exam.target_department),
                joinedload(Exam.target_section),
                selectinload(Exam.exam_questions).joinedload(ExamQuestion.question),
                selectinload(Exam.sessions),
                selectinload(Exam.target_students),
            )
            .filter(Exam.id == exam_id)
            .first()
        )

        if not exam:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Exam not found.",
            )

        examiner = exam.creator
        examiner_name = f"{examiner.first_name} {examiner.last_name}".strip() if examiner else "Unknown"
        examiner_email = examiner.email if examiner else ""
        college_name = examiner.college.name if examiner and examiner.college else None
        college_code = examiner.college.code if examiner and examiner.college else None

        # Session activity
        sessions = exam.sessions or []
        total_sessions = len(sessions)
        completed_sessions = len([s for s in sessions if s.status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED]])
        in_progress_sessions = len([s for s in sessions if s.status == SessionStatus.IN_PROGRESS])
        other_sessions = total_sessions - completed_sessions - in_progress_sessions

        # Question type breakdown
        questions = exam.exam_questions or []
        mcq_count = 0
        multi_select_count = 0
        short_answer_count = 0
        long_answer_count = 0
        handwritten_count = 0

        for eq in questions:
            if eq.question:
                qt = eq.question.question_type
                if qt == QuestionType.MCQ:
                    mcq_count += 1
                elif qt == QuestionType.MULTI_SELECT:
                    multi_select_count += 1
                elif qt == QuestionType.SHORT_ANSWER:
                    short_answer_count += 1
                elif qt == QuestionType.LONG_ANSWER:
                    long_answer_count += 1
                elif qt == QuestionType.HANDWRITTEN:
                    handwritten_count += 1

        target_desc = self._format_target_description(exam)
        target_specific_count = len(exam.target_students) if exam.target_students else 0
        specific_ids = [ts.student_id for ts in exam.target_students] if (exam.target_type == ExamTargetType.SPECIFIC_STUDENTS and exam.target_students) else None

        eligible_students = academic_repository.count_eligible_students(
            db=db,
            college_id=examiner.college_id if examiner else None,
            target_type=exam.target_type,
            department_id=exam.target_department_id,
            year_of_study=exam.target_year_of_study,
            section_id=exam.target_section_id,
            specific_student_ids=specific_ids,
        )

        return AdminExamDetailResponse(
            id=exam.id,
            title=exam.title,
            subject=exam.subject,
            description=exam.description,
            instructions=exam.instructions,
            status=exam.status,
            duration_minutes=exam.duration_minutes,
            total_marks=float(exam.total_marks),
            passing_marks=float(exam.passing_marks),
            negative_marking_enabled=exam.negative_marking_enabled,
            randomize_questions=exam.randomize_questions,
            randomize_options=exam.randomize_options,
            proctoring_enabled=exam.proctoring_enabled,
            max_tab_switches=exam.max_tab_switches,
            created_at=exam.created_at,
            updated_at=exam.updated_at,
            start_at=exam.start_at,
            end_at=exam.end_at,
            created_by=exam.created_by,
            examiner_name=examiner_name,
            examiner_email=examiner_email,
            examiner_college_name=college_name,
            examiner_college_code=college_code,
            target_type=exam.target_type,
            target_description=target_desc,
            target_college_name=college_name,
            target_department_name=exam.target_department.name if exam.target_department else None,
            target_year_of_study=exam.target_year_of_study,
            target_section_name=exam.target_section.name if exam.target_section else None,
            target_specific_students_count=target_specific_count,
            eligible_students_count=eligible_students,
            total_sessions_count=total_sessions,
            completed_sessions_count=completed_sessions,
            in_progress_sessions_count=in_progress_sessions,
            other_sessions_count=other_sessions,
            question_count=len(questions),
            mcq_count=mcq_count,
            multi_select_count=multi_select_count,
            short_answer_count=short_answer_count,
            long_answer_count=long_answer_count,
            handwritten_count=handwritten_count,
        )


admin_service = AdminService()

