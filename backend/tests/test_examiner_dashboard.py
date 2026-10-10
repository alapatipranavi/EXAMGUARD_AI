import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus, ExamTargetType, ExamQuestion
from app.models.exam_session import ExamSession, SessionStatus
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.evaluation import ExamSessionEvaluation, PassFailStatus, EvaluationStatus
from app.repositories.user_repository import user_repository
from app.repositories.academic_repository import academic_repository
from app.core.security import hash_password, create_access_token


def create_user(db, email: str, role: UserRole, first_name: str = "Test", last_name: str = "User") -> User:
    return user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first_name,
        last_name=last_name,
        role=role,
    )


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


def create_question(db, examiner: User) -> Question:
    q = Question(
        question_text="Sample Examiner Question?",
        subject="Computer Science",
        question_type=QuestionType.MCQ,
        difficulty=DifficultyLevel.EASY,
        marks=10.0,
        created_by=examiner.id,
        is_active=True,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


def setup_examiner_environment(db):
    col_a = academic_repository.create_college(db, "Alpha Engineering Institute", "AEI")
    dept_a = academic_repository.create_department(db, col_a.id, "Computer Science & Tech", "CST")
    sec_a = academic_repository.create_section(db, dept_a.id, 2, "Section A", "SEC-A")

    col_b = academic_repository.create_college(db, "Beta Institute of Tech", "BIT")
    dept_b = academic_repository.create_department(db, col_b.id, "Information Tech", "IT")
    sec_b = academic_repository.create_section(db, dept_b.id, 2, "Section B", "SEC-B")

    examiner_1 = create_user(db, "ex1_dash@example.com", UserRole.EXAMINER, first_name="Sarah", last_name="Connor")
    academic_repository.update_user_college(db, examiner_1, col_a.id)

    examiner_2 = create_user(db, "ex2_dash@example.com", UserRole.EXAMINER, first_name="John", last_name="Doe")
    academic_repository.update_user_college(db, examiner_2, col_b.id)

    student_1 = create_user(db, "student1_dash@example.com", UserRole.STUDENT, first_name="Alice", last_name="Student")
    academic_repository.update_student_academic_profile(db, student_1, col_a.id, dept_a.id, 2, sec_a.id)

    student_2 = create_user(db, "student2_dash@example.com", UserRole.STUDENT, first_name="Bob", last_name="Student")
    academic_repository.update_student_academic_profile(db, student_2, col_b.id, dept_b.id, 2, sec_b.id)

    return {
        "col_a": col_a,
        "dept_a": dept_a,
        "sec_a": sec_a,
        "col_b": col_b,
        "dept_b": dept_b,
        "sec_b": sec_b,
        "examiner_1": examiner_1,
        "examiner_2": examiner_2,
        "student_1": student_1,
        "student_2": student_2,
    }


# ============================================================================
# 1. EXAMINER DASHBOARD AUTHENTICATION & RBAC (Scenarios 1, 2, 10)
# ============================================================================

def test_examiner_dashboard_unauthenticated_returns_401(client):
    res = client.get("/api/examiner/dashboard")
    assert res.status_code == 401


def test_student_access_examiner_dashboard_returns_403(client, db):
    student = create_user(db, "student_forbidden@example.com", UserRole.STUDENT)
    res = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(student))
    assert res.status_code == 403


def test_examiner_receives_own_dashboard(client, db):
    env = setup_examiner_environment(db)
    ex1 = env["examiner_1"]
    res = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(ex1))
    assert res.status_code == 200
    data = res.json()
    assert "Sarah Connor" in data["greeting_name"]
    assert data["academic_scope"]["college_name"] == "Alpha Engineering Institute"
    assert data["academic_scope"]["college_code"] == "AEI"


# ============================================================================
# 2. EXAMINER ISOLATION & COLLEGE SCOPING (Scenarios 4, 5)
# ============================================================================

def test_examiner_isolation_cannot_access_another_examiner_data(client, db):
    env = setup_examiner_environment(db)
    ex1 = env["examiner_1"]
    ex2 = env["examiner_2"]

    # Examiner 1 creates an exam
    exam_1 = Exam(
        title="Examiner 1 Exclusive Exam",
        subject="Computer Science",
        created_by=ex1.id,
        duration_minutes=60,
        total_marks=50.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam_1)
    db.commit()

    # Examiner 2 checks dashboard
    res2 = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(ex2))
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["summary"]["total_exams"] == 0
    assert len(data2["exams"]) == 0

    # Examiner 1 checks dashboard
    res1 = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(ex1))
    assert res1.status_code == 200
    data1 = res1.json()
    assert data1["summary"]["total_exams"] == 1
    assert data1["exams"][0]["id"] == str(exam_1.id)


def test_college_scoping_on_examiner_dashboard(client, db):
    env = setup_examiner_environment(db)
    ex1 = env["examiner_1"]
    col_a = env["col_a"]

    # Examiner without assigned college
    ex_no_col = create_user(db, "ex_nocollege@example.com", UserRole.EXAMINER, first_name="No", last_name="College")
    res_nocol = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(ex_no_col))
    assert res_nocol.status_code == 200
    data_nocol = res_nocol.json()
    assert data_nocol["academic_scope"]["college_id"] is None
    assert data_nocol["academic_scope"]["college_name"] is None


# ============================================================================
# 3. SUMMARY COUNTS & EXAM LISTING (Scenarios 6, 7, 8)
# ============================================================================

def test_summary_counts_and_pending_reviews(client, db):
    env = setup_examiner_environment(db)
    ex1 = env["examiner_1"]
    student1 = env["student_1"]

    # Create published exam
    exam_pub = Exam(
        title="Midterm Assessment",
        subject="Computer Science",
        created_by=ex1.id,
        duration_minutes=60,
        total_marks=100.0,
        status=ExamStatus.PUBLISHED,
        target_type=ExamTargetType.COLLEGE,
    )
    # Create draft exam
    exam_draft = Exam(
        title="Draft Quiz",
        subject="Computer Science",
        created_by=ex1.id,
        duration_minutes=30,
        total_marks=20.0,
        status=ExamStatus.DRAFT,
    )
    db.add_all([exam_pub, exam_draft])
    db.commit()

    # Active session for student 1
    session = ExamSession(
        exam_id=exam_pub.id,
        student_id=student1.id,
        status=SessionStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()

    # Pending evaluation review
    eval_rec = ExamSessionEvaluation(
        session_id=session.id,
        exam_id=exam_pub.id,
        student_id=student1.id,
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

    res = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(ex1))
    assert res.status_code == 200
    data = res.json()

    assert data["summary"]["total_exams"] == 2
    assert data["summary"]["published_exams"] == 1
    assert data["summary"]["active_sessions"] == 1
    assert data["summary"]["pending_reviews"] == 1

    # Check pending review item
    assert len(data["pending_reviews"]) == 1
    rev = data["pending_reviews"][0]
    assert rev["session_id"] == str(session.id)
    assert rev["exam_title"] == "Midterm Assessment"
    assert rev["student_name"] == "Alice Student"


# ============================================================================
# 4. EMPTY STATE (Scenario 9)
# ============================================================================

def test_empty_state_for_new_examiner(client, db):
    new_ex = create_user(db, "brand_new_ex@example.com", UserRole.EXAMINER, first_name="Fresh", last_name="Examiner")
    res = client.get("/api/examiner/dashboard", cookies=get_auth_cookies(new_ex))
    assert res.status_code == 200
    data = res.json()

    assert data["summary"]["total_exams"] == 0
    assert data["summary"]["published_exams"] == 0
    assert data["summary"]["active_sessions"] == 0
    assert data["summary"]["pending_reviews"] == 0
    assert data["exams"] == []
    assert data["pending_reviews"] == []
    assert data["recent_activity"] == []
