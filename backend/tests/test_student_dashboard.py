import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus, ExamTargetType
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
        question_text="Dashboard Test Question?",
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


def setup_dashboard_environment(db):
    col_a = academic_repository.create_college(db, "Alpha College of Tech", "ACT")
    dept_a = academic_repository.create_department(db, col_a.id, "Computer Science", "CSE")
    sec_a = academic_repository.create_section(db, dept_a.id, 2, "Section A", "SEC-A")

    col_b = academic_repository.create_college(db, "Beta College of Science", "BCS")
    dept_b = academic_repository.create_department(db, col_b.id, "Physics", "PHY")
    sec_b = academic_repository.create_section(db, dept_b.id, 2, "Section B", "SEC-B")

    student_a = create_user(db, "student_a_dash@example.com", UserRole.STUDENT, first_name="Alice", last_name="Smith")
    academic_repository.update_student_academic_profile(db, student_a, col_a.id, dept_a.id, 2, sec_a.id)

    student_b = create_user(db, "student_b_dash@example.com", UserRole.STUDENT, first_name="Bob", last_name="Jones")
    academic_repository.update_student_academic_profile(db, student_b, col_b.id, dept_b.id, 2, sec_b.id)

    examiner_a = create_user(db, "examiner_a_dash@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner_a, col_a.id)

    return {
        "col_a": col_a,
        "dept_a": dept_a,
        "sec_a": sec_a,
        "col_b": col_b,
        "dept_b": dept_b,
        "sec_b": sec_b,
        "student_a": student_a,
        "student_b": student_b,
        "examiner_a": examiner_a,
    }


# ============================================================================
# 1. STUDENT DASHBOARD AUTHENTICATION & SECURITY (Scenarios 1, 2, 10)
# ============================================================================

def test_1_student_dashboard_authentication(client, db):
    # Unauthenticated returns 401
    res = client.get("/api/student/dashboard")
    assert res.status_code == 401

    # Examiner role returns 403
    examiner = create_user(db, "ex_forbidden@example.com", UserRole.EXAMINER)
    res_ex = client.get("/api/student/dashboard", cookies=get_auth_cookies(examiner))
    assert res_ex.status_code == 403


def test_2_student_receives_only_their_own_dashboard_data(client, db):
    env = setup_dashboard_environment(db)
    student_a = env["student_a"]
    cookies_a = get_auth_cookies(student_a)

    res = client.get("/api/student/dashboard", cookies=cookies_a)
    assert res.status_code == 200
    data = res.json()
    assert "Alice Smith" in data["greeting_name"]
    assert data["academic_profile"]["college_name"] == "Alpha College of Tech"


def test_10_another_student_data_cannot_be_accessed(client, db):
    env = setup_dashboard_environment(db)
    student_b = env["student_b"]
    cookies_b = get_auth_cookies(student_b)

    res = client.get("/api/student/dashboard", cookies=cookies_b)
    assert res.status_code == 200
    data = res.json()
    assert "Bob Jones" in data["greeting_name"]
    assert data["academic_profile"]["college_name"] == "Beta College of Science"
    assert "Alice Smith" not in data["greeting_name"]


# ============================================================================
# 2. TARGETED EXAMS & AUTHORIZATION (Scenarios 3, 4)
# ============================================================================

def test_3_upcoming_targeted_exams_returned(client, db):
    env = setup_dashboard_environment(db)
    examiner = env["examiner_a"]
    student_a = env["student_a"]
    q = create_question(db, examiner)

    ex_cookies = get_auth_cookies(examiner)
    payload = {
        "title": "CSE Specialization Exam",
        "subject": "Computer Science",
        "duration_minutes": 60,
        "target_type": "DEPARTMENT",
        "target_department_id": str(env["dept_a"].id),
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res_create = client.post("/api/exams", json=payload, cookies=ex_cookies)
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    # Student A sees it in upcoming_exams
    st_cookies = get_auth_cookies(student_a)
    dash_res = client.get("/api/student/dashboard", cookies=st_cookies)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert any(ex["id"] == exam_id for ex in data["upcoming_exams"])
    assert data["summary"]["upcoming_exams"] >= 1


def test_4_unauthorized_exams_not_returned(client, db):
    env = setup_dashboard_environment(db)
    examiner = env["examiner_a"]
    student_b = env["student_b"]
    q = create_question(db, examiner)

    ex_cookies = get_auth_cookies(examiner)
    payload = {
        "title": "Dept A Only Confidential Exam",
        "subject": "Computer Science",
        "duration_minutes": 60,
        "target_type": "DEPARTMENT",
        "target_department_id": str(env["dept_a"].id),
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res_create = client.post("/api/exams", json=payload, cookies=ex_cookies)
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    # Student B (Beta College / Physics) does NOT see it
    st_b_cookies = get_auth_cookies(student_b)
    dash_res = client.get("/api/student/dashboard", cookies=st_b_cookies)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert not any(ex["id"] == exam_id for ex in data["upcoming_exams"])


# ============================================================================
# 3. IN-PROGRESS SESSION HANDLING (Scenarios 5, 6)
# ============================================================================

def test_5_in_progress_session_returned_correctly(client, db):
    env = setup_dashboard_environment(db)
    examiner = env["examiner_a"]
    student_a = env["student_a"]
    q = create_question(db, examiner)

    ex_cookies = get_auth_cookies(examiner)
    payload = {
        "title": "Active In-Progress Exam",
        "subject": "Computer Science",
        "duration_minutes": 60,
        "target_type": "COLLEGE",
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res_create = client.post("/api/exams", json=payload, cookies=ex_cookies)
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    # Student A starts exam
    st_cookies = get_auth_cookies(student_a)
    start_res = client.post(f"/api/student/exams/{exam_id}/start", cookies=st_cookies)
    assert start_res.status_code == 200
    session_id = start_res.json()["id"]

    # Dashboard returns in_progress_exam
    dash_res = client.get("/api/student/dashboard", cookies=st_cookies)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert data["in_progress_exam"] is not None
    assert data["in_progress_exam"]["session_id"] == session_id
    assert data["in_progress_exam"]["exam_title"] == "Active In-Progress Exam"
    assert data["summary"]["in_progress_exams"] == 1


def test_6_existing_session_not_duplicated(client, db):
    env = setup_dashboard_environment(db)
    examiner = env["examiner_a"]
    student_a = env["student_a"]
    q = create_question(db, examiner)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Single Session Exam",
            "subject": "Computer Science",
            "duration_minutes": 45,
            "target_type": "COLLEGE",
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    st_cookies = get_auth_cookies(student_a)
    client.post(f"/api/student/exams/{exam_id}/start", cookies=st_cookies)

    # Call dashboard multiple times
    res1 = client.get("/api/student/dashboard", cookies=st_cookies)
    res2 = client.get("/api/student/dashboard", cookies=st_cookies)

    assert res1.json()["in_progress_exam"]["session_id"] == res2.json()["in_progress_exam"]["session_id"]
    assert res1.json()["summary"]["in_progress_exams"] == 1


# ============================================================================
# 4. RECENT & PENDING RESULTS (Scenarios 7, 8, 9)
# ============================================================================

def test_7_recent_results_returned_correctly(client, db):
    env = setup_dashboard_environment(db)
    examiner = env["examiner_a"]
    student_a = env["student_a"]
    q = create_question(db, examiner)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Completed Exam",
            "subject": "Data Structures",
            "duration_minutes": 30,
            "target_type": "COLLEGE",
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    st_cookies = get_auth_cookies(student_a)
    session_res = client.post(f"/api/student/exams/{exam_id}/start", cookies=st_cookies)
    session_id = session_res.json()["id"]

    # Verify session identity so submission succeeds
    sess_obj = db.query(ExamSession).filter(ExamSession.id == uuid.UUID(session_id)).first()
    sess_obj.identity_verification_status = "VERIFIED"
    db.commit()

    # Submit exam
    sub_res = client.post(f"/api/student/sessions/{session_id}/submit", cookies=st_cookies)
    assert sub_res.status_code == 200

    # Dashboard returns recent result
    dash_res = client.get("/api/student/dashboard", cookies=st_cookies)
    assert dash_res.status_code == 200
    data = dash_res.json()
    assert len(data["recent_results"]) >= 1
    recent = data["recent_results"][0]
    assert recent["exam_title"] == "Completed Exam"
    assert recent["session_id"] == session_id


def test_8_pending_results_represented_correctly(client, db):
    env = setup_dashboard_environment(db)
    student_a = env["student_a"]

    # Create session evaluation in NEEDS_SUBJECTIVE_REVIEW status
    exam = Exam(
        title="Subjective Pending Exam",
        subject="Ethics",
        duration_minutes=60,
        passing_marks=5.0,
        created_by=env["examiner_a"].id,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session = ExamSession(
        exam_id=exam.id,
        student_id=student_a.id,
        status=SessionStatus.SUBMITTED,
        identity_verification_status="VERIFIED",
    )
    db.add(session)
    db.commit()

    evaluation = ExamSessionEvaluation(
        session_id=session.id,
        exam_id=exam.id,
        student_id=student_a.id,
        total_questions=2,
        answered_questions=2,
        unanswered_questions=0,
        correct_answers=1,
        incorrect_answers=0,
        objective_marks=5.0,
        subjective_marks=0.0,
        negative_marks=0.0,
        total_score=5.0,
        maximum_marks=10.0,
        percentage=50.0,
        passing_marks=5.0,
        pass_fail_status=PassFailStatus.PASSED,
        status=EvaluationStatus.PENDING_REVIEW,
    )
    db.add(evaluation)
    db.commit()

    st_cookies = get_auth_cookies(student_a)
    dash_res = client.get("/api/student/dashboard", cookies=st_cookies)
    assert dash_res.status_code == 200
    data = dash_res.json()
    res_item = next(r for r in data["recent_results"] if r["evaluation_id"] == str(evaluation.id))
    assert res_item["status"] in ["PENDING_REVIEW", "NEEDS_SUBJECTIVE_REVIEW"]


def test_9_academic_profile_is_returned(client, db):
    env = setup_dashboard_environment(db)
    student_a = env["student_a"]
    st_cookies = get_auth_cookies(student_a)

    dash_res = client.get("/api/student/dashboard", cookies=st_cookies)
    assert dash_res.status_code == 200
    data = dash_res.json()
    profile = data["academic_profile"]
    assert profile["college_name"] == "Alpha College of Tech"
    assert profile["college_code"] == "ACT"
    assert profile["department_name"] == "Computer Science"
    assert profile["department_code"] == "CSE"
    assert profile["year_of_study"] == 2
    assert profile["section_name"] == "Section A"
    assert profile["section_code"] == "SEC-A"
