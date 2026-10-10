import pytest
import uuid
from datetime import datetime, timezone
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus, ExamQuestion
from app.models.question import Question, QuestionType
from app.models.exam_session import ExamSession, SessionStatus
from app.models.answer import StudentAnswer
from app.models.evaluation import ExamSessionEvaluation, EvaluationStatus, PassFailStatus
from app.repositories.user_repository import user_repository
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


@pytest.fixture
def test_setup(db):
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_ov_{uid}@example.com", UserRole.ADMIN, "System", "Admin")
    examiner1 = create_user(db, f"examiner1_ov_{uid}@example.com", UserRole.EXAMINER, "Alice", "Examiner")
    examiner2 = create_user(db, f"examiner2_ov_{uid}@example.com", UserRole.EXAMINER, "Bob", "Examiner")
    student1 = create_user(db, f"student1_ov_{uid}@example.com", UserRole.STUDENT, "Charlie", "Student")
    student2 = create_user(db, f"student2_ov_{uid}@example.com", UserRole.STUDENT, "David", "Student")

    # Exam owned by examiner1
    exam = Exam(
        title=f"Distributed Systems {uid}",
        subject="Computer Science",
        duration_minutes=60,
        total_marks=100.0,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
        created_by=examiner1.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # Questions
    q1 = Question(
        question_text="What is Paxos consensus?",
        question_type=QuestionType.MCQ,
        subject="Computer Science",
        marks=50.0,
        created_by=examiner1.id,
    )
    q2 = Question(
        question_text="What is Raft consensus?",
        question_type=QuestionType.MCQ,
        subject="Computer Science",
        marks=50.0,
        created_by=examiner1.id,
    )
    db.add_all([q1, q2])
    db.commit()
    db.refresh(q1)
    db.refresh(q2)

    eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, question_order=1)
    eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, question_order=2)
    db.add_all([eq1, eq2])

    # Sessions for student1 and student2
    sess1 = ExamSession(exam_id=exam.id, student_id=student1.id, status=SessionStatus.SUBMITTED)
    sess2 = ExamSession(exam_id=exam.id, student_id=student2.id, status=SessionStatus.SUBMITTED)
    db.add_all([sess1, sess2])
    db.commit()
    db.refresh(sess1)
    db.refresh(sess2)

    # Answers for cross-student similarity
    ans1 = StudentAnswer(session_id=sess1.id, question_id=q1.id, text_answer="Paxos reaches consensus through two phases: prepare and accept.")
    ans2 = StudentAnswer(session_id=sess2.id, question_id=q1.id, text_answer="Paxos reaches consensus through two phases: prepare and accept.")
    db.add_all([ans1, ans2])

    # Evaluations
    eval1 = ExamSessionEvaluation(
        session_id=sess1.id,
        exam_id=exam.id,
        student_id=student1.id,
        total_score=50.0,
        pass_fail_status=PassFailStatus.PASSED,
        status=EvaluationStatus.FINALIZED,
    )
    eval2 = ExamSessionEvaluation(
        session_id=sess2.id,
        exam_id=exam.id,
        student_id=student2.id,
        total_score=50.0,
        pass_fail_status=PassFailStatus.PASSED,
        status=EvaluationStatus.FINALIZED,
    )
    db.add_all([eval1, eval2])
    db.commit()

    return {
        "admin": admin,
        "examiner1": examiner1,
        "examiner2": examiner2,
        "student1": student1,
        "student2": student2,
        "exam": exam,
        "sess1": sess1,
        "sess2": sess2,
    }


# ============================================================================
# 1. EXAM LIST FOR ADMIN & ROLE AWARENESS
# ============================================================================

def test_admin_can_list_platform_exams_via_api(client, test_setup):
    """Admin can list platform exams via GET /api/exams without Examiner-only block."""
    admin = test_setup["admin"]
    exam = test_setup["exam"]

    res = client.get("/api/exams", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert any(item["id"] == str(exam.id) for item in data["items"])


def test_student_cannot_list_exams_forbidden(client, test_setup):
    """Student receives 403 Forbidden on GET /api/exams."""
    student = test_setup["student1"]
    res = client.get("/api/exams", cookies=get_auth_cookies(student))
    assert res.status_code == 403


# ============================================================================
# 2. ADMIN ANALYTICS OVERSIGHT TESTS
# ============================================================================

def test_admin_analytics_oversight_success(client, test_setup):
    """Admin can access exam analytics for any exam on the platform."""
    admin = test_setup["admin"]
    exam = test_setup["exam"]

    res = client.get(f"/api/exams/{exam.id}/analytics", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert "summary" in data
    assert "score_performance" in data
    assert data["exam_info"]["id"] == str(exam.id)


def test_examiner_analytics_authorization(client, test_setup):
    """Examiner 1 (owner) can access, but Examiner 2 (unauthorized) receives 403."""
    ex1 = test_setup["examiner1"]
    ex2 = test_setup["examiner2"]
    exam = test_setup["exam"]

    # Owner -> 200
    res1 = client.get(f"/api/exams/{exam.id}/analytics", cookies=get_auth_cookies(ex1))
    assert res1.status_code == 200

    # Non-owner -> 403
    res2 = client.get(f"/api/exams/{exam.id}/analytics", cookies=get_auth_cookies(ex2))
    assert res2.status_code == 403


def test_student_analytics_forbidden(client, test_setup):
    """Student receives 403 on exam analytics."""
    st = test_setup["student1"]
    exam = test_setup["exam"]

    res = client.get(f"/api/exams/{exam.id}/analytics", cookies=get_auth_cookies(st))
    assert res.status_code == 403


def test_admin_analytics_does_not_mutate_exam_ownership(client, db, test_setup):
    """Admin viewing analytics does not alter exam created_by."""
    admin = test_setup["admin"]
    exam = test_setup["exam"]
    original_creator = exam.created_by

    client.get(f"/api/exams/{exam.id}/analytics", cookies=get_auth_cookies(admin))

    db.expire_all()
    refreshed = db.query(Exam).filter(Exam.id == exam.id).first()
    assert refreshed.created_by == original_creator


# ============================================================================
# 3. ADMIN INTEGRITY MONITORING TESTS
# ============================================================================

def test_admin_integrity_monitoring_summary_and_detail(client, test_setup):
    """Admin can view exam integrity summary and session integrity detail."""
    admin = test_setup["admin"]
    exam = test_setup["exam"]
    sess1 = test_setup["sess1"]

    # Exam Integrity Summary -> 200
    res_sum = client.get(f"/api/exams/{exam.id}/integrity", cookies=get_auth_cookies(admin))
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert "average_integrity_score" in data_sum
    assert "items" in data_sum

    # Session Detail -> 200
    res_det = client.get(f"/api/exams/{exam.id}/sessions/{sess1.id}/integrity", cookies=get_auth_cookies(admin))
    assert res_det.status_code == 200
    data_det = res_det.json()
    assert data_det["session_id"] == str(sess1.id)
    assert "integrity_score" in data_det
    assert "risk_level" in data_det


def test_examiner_integrity_monitoring_authorization(client, test_setup):
    """Examiner 1 (owner) can view, but Examiner 2 receives 403."""
    ex1 = test_setup["examiner1"]
    ex2 = test_setup["examiner2"]
    exam = test_setup["exam"]
    sess1 = test_setup["sess1"]

    # Ex1 (owner) -> 200
    assert client.get(f"/api/exams/{exam.id}/integrity", cookies=get_auth_cookies(ex1)).status_code == 200
    assert client.get(f"/api/exams/{exam.id}/sessions/{sess1.id}/integrity", cookies=get_auth_cookies(ex1)).status_code == 200

    # Ex2 (unauthorized) -> 403
    assert client.get(f"/api/exams/{exam.id}/integrity", cookies=get_auth_cookies(ex2)).status_code == 403
    assert client.get(f"/api/exams/{exam.id}/sessions/{sess1.id}/integrity", cookies=get_auth_cookies(ex2)).status_code == 403


def test_student_examiner_integrity_forbidden(client, test_setup):
    """Student receives 403 when trying to access examiner integrity endpoints."""
    st = test_setup["student1"]
    exam = test_setup["exam"]
    sess1 = test_setup["sess1"]

    assert client.get(f"/api/exams/{exam.id}/integrity", cookies=get_auth_cookies(st)).status_code == 403
    assert client.get(f"/api/exams/{exam.id}/sessions/{sess1.id}/integrity", cookies=get_auth_cookies(st)).status_code == 403


# ============================================================================
# 4. ADMIN CROSS-STUDENT INTEGRITY TESTS
# ============================================================================

def test_admin_cross_student_run_and_view(client, test_setup):
    """Admin can run cross-student analysis and view results."""
    admin = test_setup["admin"]
    exam = test_setup["exam"]

    # Admin runs analysis -> 200
    res_run = client.post(f"/api/exams/{exam.id}/cross-student-analysis/run", cookies=get_auth_cookies(admin))
    assert res_run.status_code == 200

    # Admin views summary -> 200
    res_sum = client.get(f"/api/exams/{exam.id}/cross-student-analysis", cookies=get_auth_cookies(admin))
    assert res_sum.status_code == 200
    data_sum = res_sum.json()
    assert "analyzed_students_count" in data_sum
    assert "total_pairs_count" in data_sum
    assert "items" in data_sum

    if data_sum["items"]:
        analysis_id = data_sum["items"][0]["id"]
        res_pair = client.get(
            f"/api/exams/{exam.id}/cross-student-analysis/{analysis_id}",
            cookies=get_auth_cookies(admin),
        )
        assert res_pair.status_code == 200
        assert res_pair.json()["id"] == analysis_id


def test_examiner_cross_student_authorization(client, test_setup):
    """Examiner 1 (owner) can run/view, but Examiner 2 receives 403."""
    ex1 = test_setup["examiner1"]
    ex2 = test_setup["examiner2"]
    exam = test_setup["exam"]

    # Ex1 (owner) can view -> 200
    assert client.get(f"/api/exams/{exam.id}/cross-student-analysis", cookies=get_auth_cookies(ex1)).status_code == 200

    # Ex2 (unauthorized) cannot run or view -> 403
    assert client.post(f"/api/exams/{exam.id}/cross-student-analysis/run", cookies=get_auth_cookies(ex2)).status_code == 403
    assert client.get(f"/api/exams/{exam.id}/cross-student-analysis", cookies=get_auth_cookies(ex2)).status_code == 403


def test_student_cross_student_forbidden(client, test_setup):
    """Student receives 403 on cross-student analysis endpoints."""
    st = test_setup["student1"]
    exam = test_setup["exam"]

    assert client.post(f"/api/exams/{exam.id}/cross-student-analysis/run", cookies=get_auth_cookies(st)).status_code == 403
    assert client.get(f"/api/exams/{exam.id}/cross-student-analysis", cookies=get_auth_cookies(st)).status_code == 403
