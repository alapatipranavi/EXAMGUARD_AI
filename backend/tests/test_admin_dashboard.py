import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus, ExamTargetType
from app.models.exam_session import ExamSession, SessionStatus
from app.models.evaluation import ExamSessionEvaluation, PassFailStatus, EvaluationStatus
from app.models.academic import College, Department, Section
from app.repositories.user_repository import user_repository
from app.repositories.academic_repository import academic_repository
from app.core.security import hash_password, create_access_token


def create_user(db, email: str, role: UserRole, first_name: str = "Test", last_name: str = "User", is_active: bool = True) -> User:
    u = user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    if not is_active:
        u.is_active = False
        db.commit()
        db.refresh(u)
    return u


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


def setup_admin_environment(db):
    col_1 = academic_repository.create_college(db, "State University of Tech", "SUT")
    dept_1 = academic_repository.create_department(db, col_1.id, "Computer Engineering", "CE")
    sec_1 = academic_repository.create_section(db, dept_1.id, 1, "Section A", "SEC-A")

    col_2 = academic_repository.create_college(db, "National Science Academy", "NSA")
    dept_2 = academic_repository.create_department(db, col_2.id, "Data Science", "DS")

    admin = create_user(db, "admin_dash@example.com", UserRole.ADMIN, first_name="Super", last_name="Admin")
    examiner = create_user(db, "examiner_admin_test@example.com", UserRole.EXAMINER, first_name="Eve", last_name="Faculty")
    student = create_user(db, "student_admin_test@example.com", UserRole.STUDENT, first_name="Sam", last_name="Pupil")
    academic_repository.update_student_academic_profile(db, student, col_1.id, dept_1.id, 1, sec_1.id)

    inactive_student = create_user(db, "inactive_student@example.com", UserRole.STUDENT, first_name="Dan", last_name="Inactive", is_active=False)

    return {
        "col_1": col_1,
        "dept_1": dept_1,
        "sec_1": sec_1,
        "col_2": col_2,
        "dept_2": dept_2,
        "admin": admin,
        "examiner": examiner,
        "student": student,
        "inactive_student": inactive_student,
    }


# ============================================================================
# 1. ADMIN DASHBOARD AUTHENTICATION & SECURITY (Scenarios 1, 2, 3, 10)
# ============================================================================

def test_admin_dashboard_unauthenticated_returns_401(client):
    res = client.get("/api/admin/dashboard")
    assert res.status_code == 401


def test_student_access_admin_dashboard_returns_403(client, db):
    student = create_user(db, "student_forbidden_admin@example.com", UserRole.STUDENT)
    res = client.get("/api/admin/dashboard", cookies=get_auth_cookies(student))
    assert res.status_code == 403


def test_examiner_access_admin_dashboard_returns_403(client, db):
    examiner = create_user(db, "examiner_forbidden_admin@example.com", UserRole.EXAMINER)
    res = client.get("/api/admin/dashboard", cookies=get_auth_cookies(examiner))
    assert res.status_code == 403


def test_admin_data_security_no_sensitive_info_leaked(client, db):
    env = setup_admin_environment(db)
    admin = env["admin"]
    res = client.get("/api/admin/dashboard", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    body = res.text
    assert "Password123!" not in body
    assert "password_hash" not in body
    assert "access_token" not in body


# ============================================================================
# 2. METRICS & ACADEMIC STRUCTURE (Scenarios 4, 5, 6, 7, 8, 9)
# ============================================================================

def test_admin_dashboard_summary_and_metrics(client, db):
    env = setup_admin_environment(db)
    admin = env["admin"]
    examiner = env["examiner"]
    student = env["student"]

    # Create Exams in various statuses
    exam_pub = Exam(
        title="Published Midterm",
        subject="Computer Engineering",
        created_by=examiner.id,
        duration_minutes=60,
        total_marks=100.0,
        status=ExamStatus.PUBLISHED,
    )
    exam_draft = Exam(
        title="Draft Quiz",
        subject="Computer Engineering",
        created_by=examiner.id,
        duration_minutes=30,
        total_marks=20.0,
        status=ExamStatus.DRAFT,
    )
    db.add_all([exam_pub, exam_draft])
    db.commit()

    # Create exam session & evaluation
    session = ExamSession(
        exam_id=exam_pub.id,
        student_id=student.id,
        status=SessionStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()

    eval_rec = ExamSessionEvaluation(
        session_id=session.id,
        exam_id=exam_pub.id,
        student_id=student.id,
        total_questions=5,
        answered_questions=5,
        total_score=40.0,
        maximum_marks=100.0,
        percentage=40.0,
        pass_fail_status=PassFailStatus.FAILED,
        status=EvaluationStatus.PENDING_REVIEW,
    )
    db.add(eval_rec)
    db.commit()

    res = client.get("/api/admin/dashboard", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()

    # Greeting
    assert "Super Admin" in data["greeting_name"]

    # User Metrics
    assert data["users"]["active_students"] >= 1
    assert data["users"]["active_examiners"] >= 1
    assert data["users"]["inactive_users"] >= 1

    # Academic Structure Metrics
    assert data["academic"]["total_colleges"] >= 2
    assert data["academic"]["total_departments"] >= 2
    assert data["academic"]["total_sections"] >= 1
    assert data["academic"]["students_with_academic_profiles"] >= 1

    # Examinations Breakdown
    assert data["examinations"]["draft"] >= 1
    assert data["examinations"]["published"] >= 1

    # Summary Counts
    assert data["summary"]["active_sessions"] >= 1
    assert data["summary"]["pending_reviews"] >= 1

    # System Health Status
    assert data["system_status"]["backend"] == "online"
    assert data["system_status"]["database"] == "connected"


def test_admin_dashboard_empty_activity_handled(client, db):
    admin = create_user(db, "fresh_admin@example.com", UserRole.ADMIN, first_name="New", last_name="Admin")
    res = client.get("/api/admin/dashboard", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert isinstance(data["recent_activity"], list)
    assert data["system_status"]["backend"] == "online"
