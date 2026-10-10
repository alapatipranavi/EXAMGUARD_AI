import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus
from app.models.exam_session import ExamSession, SessionStatus
from app.models.proctoring import ProctoringEvent, ProctoringEventType, EventSeverity
from app.models.answer import StudentAnswer
from app.models.question import Question, QuestionType
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


def create_test_exam(db, examiner: User, title: str = "Operating Systems") -> Exam:
    exam = Exam(
        title=title,
        subject="Computer Science",
        description="Core concepts examination",
        duration_minutes=60,
        passing_marks=50.0,
        status=ExamStatus.PUBLISHED,
        created_by=examiner.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)
    return exam


def create_test_session(db, exam: Exam, student: User, status: SessionStatus = SessionStatus.SUBMITTED) -> ExamSession:
    now = datetime.now(timezone.utc)
    session = ExamSession(
        exam_id=exam.id,
        student_id=student.id,
        status=status,
        started_at=now - timedelta(minutes=45),
        submitted_at=now if status in [SessionStatus.SUBMITTED, SessionStatus.AUTO_SUBMITTED] else None,
        expires_at=now + timedelta(minutes=15),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def create_proctoring_event(
    db, session: ExamSession, event_type: ProctoringEventType, severity: EventSeverity = EventSeverity.MEDIUM, offset_seconds: int = 10
):
    ev = ProctoringEvent(
        session_id=session.id,
        event_type=event_type,
        severity=severity,
        occurred_at=(session.started_at or datetime.now(timezone.utc)) + timedelta(seconds=offset_seconds),
    )
    db.add(ev)
    db.commit()
    db.refresh(ev)
    return ev


# ==============================================================================
# 1. AUTHENTICATION & RBAC TESTS
# ==============================================================================

def test_student_integrity_unauthenticated(client):
    """Unauthenticated requests are rejected with 401 Unauthorized."""
    res1 = client.get("/api/student/integrity")
    assert res1.status_code == 401

    fake_id = uuid.uuid4()
    res2 = client.get(f"/api/student/integrity/{fake_id}")
    assert res2.status_code == 401


def test_student_integrity_rbac_examiner_forbidden(db, client):
    """Examiners cannot access student integrity endpoints (403 Forbidden)."""
    examiner = create_user(db, "examiner_integrity_test@example.com", UserRole.EXAMINER)
    cookies = get_auth_cookies(examiner)

    res = client.get("/api/student/integrity", cookies=cookies)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


def test_student_integrity_rbac_admin_forbidden(db, client):
    """Admins cannot access student integrity endpoints (403 Forbidden)."""
    admin = create_user(db, "admin_integrity_test@example.com", UserRole.ADMIN)
    cookies = get_auth_cookies(admin)

    res = client.get("/api/student/integrity", cookies=cookies)
    assert res.status_code == 403
    assert "not authorized" in res.json()["detail"].lower()


# ==============================================================================
# 2. EMPTY STATE TESTS
# ==============================================================================

def test_student_integrity_empty_state(db, client):
    """Student with no exam history receives valid empty response."""
    student = create_user(db, "empty_student@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(student)

    res = client.get("/api/student/integrity", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["summary"]["exams_monitored"] == 0
    assert data["summary"]["exams_completed"] == 0
    assert data["summary"]["average_integrity_score"] == 100.0
    assert data["summary"]["high_risk_count"] == 0
    assert data["summary"]["moderate_risk_count"] == 0
    assert data["summary"]["low_risk_count"] == 0
    assert data["exams"] == []


# ==============================================================================
# 3. OVERVIEW & EXAM HISTORY TESTS
# ==============================================================================

def test_student_integrity_overview_with_history(db, client):
    """Student retrieves own integrity overview and sorted exam history."""
    examiner = create_user(db, "prof_overview@example.com", UserRole.EXAMINER)
    student = create_user(db, "student_overview@example.com", UserRole.STUDENT)

    exam1 = create_test_exam(db, examiner, title="Database Systems")
    exam2 = create_test_exam(db, examiner, title="Algorithms")

    # Session 1: Clean session (score 100, LOW risk)
    sess1 = create_test_session(db, exam1, student, SessionStatus.SUBMITTED)

    # Session 2: Multiple tab switches (deductions -> MODERATE risk)
    sess2 = create_test_session(db, exam2, student, SessionStatus.SUBMITTED)
    create_proctoring_event(db, sess2, ProctoringEventType.TAB_SWITCH, EventSeverity.WARNING, 15)
    create_proctoring_event(db, sess2, ProctoringEventType.TAB_SWITCH, EventSeverity.WARNING, 30)
    create_proctoring_event(db, sess2, ProctoringEventType.TAB_SWITCH, EventSeverity.WARNING, 45)
    create_proctoring_event(db, sess2, ProctoringEventType.FULLSCREEN_EXITED, EventSeverity.WARNING, 60)

    cookies = get_auth_cookies(student)
    res = client.get("/api/student/integrity", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    summary = data["summary"]
    assert summary["exams_monitored"] == 2
    assert summary["exams_completed"] == 2
    assert summary["low_risk_count"] >= 1

    exams = data["exams"]
    assert len(exams) == 2
    # Verify exam titles and IDs
    titles = [e["exam_title"] for e in exams]
    assert "Database Systems" in titles
    assert "Algorithms" in titles


# ==============================================================================
# 4. SESSION DETAIL & EVENT BREAKDOWN TESTS
# ==============================================================================

def test_student_session_integrity_detail(db, client):
    """Detailed integrity endpoint returns proctoring timeline, event summary, and environment alerts."""
    examiner = create_user(db, "prof_detail@example.com", UserRole.EXAMINER)
    student = create_user(db, "student_detail@example.com", UserRole.STUDENT)
    exam = create_test_exam(db, examiner, title="Distributed Systems")
    session = create_test_session(db, exam, student, SessionStatus.SUBMITTED)

    # Add diverse proctoring events
    create_proctoring_event(db, session, ProctoringEventType.TAB_SWITCH, EventSeverity.MEDIUM, 10)
    create_proctoring_event(db, session, ProctoringEventType.FACE_NOT_DETECTED, EventSeverity.HIGH, 25)
    create_proctoring_event(db, session, ProctoringEventType.PHONE_DETECTED, EventSeverity.HIGH, 40)

    cookies = get_auth_cookies(student)
    res = client.get(f"/api/student/integrity/{session.id}", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["exam_title"] == "Distributed Systems"
    assert data["session_id"] == str(session.id)
    assert data["session_status"] == "SUBMITTED"
    assert data["integrity_score"] < 100.0
    assert data["risk_level"] in ["LOW", "MODERATE", "HIGH"]
    assert "Integrity monitoring" in data["status_explanation"]

    # Verify event counts
    ev_summary = data["event_summary"]
    assert ev_summary["tab_switches"] == 1
    assert ev_summary["face_absence"] == 1
    assert ev_summary["phone_detected"] == 1
    assert ev_summary["total_events"] == 3

    # Verify environment monitoring section
    env = data["environment_monitoring"]
    assert env["phone_detected_count"] == 1
    assert env["status"] == "ALERTS_RECORDED"

    # Verify timeline events list
    events = data["events"]
    assert len(events) == 3
    event_types = [e["event_type"] for e in events]
    assert "TAB_SWITCH" in event_types
    assert "FACE_NOT_DETECTED" in event_types
    assert "PHONE_DETECTED" in event_types


# ==============================================================================
# 5. BEHAVIOURAL METRICS INTEGRATION TESTS
# ==============================================================================

def test_student_session_behavioural_metrics(db, client):
    """Behavioural metrics from Stage 9.3 are surfaced to the student."""
    examiner = create_user(db, "prof_beh@example.com", UserRole.EXAMINER)
    student = create_user(db, "student_beh@example.com", UserRole.STUDENT)
    exam = create_test_exam(db, examiner, title="Network Security")
    session = create_test_session(db, exam, student, SessionStatus.SUBMITTED)

    # Add questions and answers
    q1 = Question(question_text="What is TCP?", question_type=QuestionType.SHORT_ANSWER, subject="Computer Science", marks=5, created_by=examiner.id)
    q2 = Question(question_text="What is UDP?", question_type=QuestionType.SHORT_ANSWER, subject="Computer Science", marks=5, created_by=examiner.id)
    db.add_all([q1, q2])
    db.commit()

    ans1 = StudentAnswer(session_id=session.id, question_id=q1.id, text_answer="Transmission Control Protocol")
    db.add(ans1)
    db.commit()

    # Add behavioural navigation events
    create_proctoring_event(db, session, ProctoringEventType.QUESTION_VIEWED, EventSeverity.INFO, 5)
    create_proctoring_event(db, session, ProctoringEventType.ANSWER_CREATED, EventSeverity.INFO, 15)
    create_proctoring_event(db, session, ProctoringEventType.QUESTION_NAVIGATION, EventSeverity.INFO, 20)

    cookies = get_auth_cookies(student)
    res = client.get(f"/api/student/integrity/{session.id}", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    beh = data["behavioural_metrics"]
    assert beh["metrics_available"] is True
    assert beh["questions_answered"] >= 1


# ==============================================================================
# 6. IDOR & SECURITY ISOLATION TESTS (CRITICAL)
# ==============================================================================

def test_student_cannot_access_other_student_session(db, client):
    """Student A cannot access Student B's exam session integrity detail (403 Forbidden)."""
    examiner = create_user(db, "prof_security@example.com", UserRole.EXAMINER)
    student_a = create_user(db, "student_a@example.com", UserRole.STUDENT)
    student_b = create_user(db, "student_b@example.com", UserRole.STUDENT)

    exam = create_test_exam(db, examiner, title="Software Engineering")
    session_b = create_test_session(db, exam, student_b, SessionStatus.SUBMITTED)

    # Student A attempts to access Student B's session ID
    cookies_a = get_auth_cookies(student_a)
    res = client.get(f"/api/student/integrity/{session_b.id}", cookies=cookies_a)
    assert res.status_code == 403
    assert "not own" in res.json()["detail"].lower()


def test_student_cannot_access_nonexistent_session(db, client):
    """Accessing non-existent session ID returns 404 Not Found."""
    student = create_user(db, "student_notfound@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(student)

    fake_session_id = uuid.uuid4()
    res = client.get(f"/api/student/integrity/{fake_session_id}", cookies=cookies)
    assert res.status_code == 404
