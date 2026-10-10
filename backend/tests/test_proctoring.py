import uuid
import pytest
from datetime import datetime, timezone, timedelta

from app.models.user import User, UserRole
from app.models.proctoring import ProctoringEventType, EventSeverity
from app.models.exam import ExamStatus
from app.models.exam_session import ExamSession, SessionStatus
from app.repositories.exam_repository import ExamRepository
from app.repositories.question_repository import question_repository
from app.schemas.question import QuestionCreate, QuestionType, DifficultyLevel
from app.schemas.exam import ExamCreate, ExamQuestionInput
from app.core.security import create_access_token, hash_password



@pytest.fixture
def proctoring_context(db):
    """Sets up Users, Questions, Published Exams, and Active Sessions for testing proctoring."""
    # Examiner 1
    ex1 = db.query(User).filter(User.email == "ex1_proctor@examguard.ai").first()
    if not ex1:
        ex1 = User(
            email="ex1_proctor@examguard.ai",
            password_hash=hash_password("ExaminerPass123!"),
            first_name="Examiner",
            last_name="One",
            role=UserRole.EXAMINER,
            is_active=True,
        )
        db.add(ex1)

    # Examiner 2
    ex2 = db.query(User).filter(User.email == "ex2_proctor@examguard.ai").first()
    if not ex2:
        ex2 = User(
            email="ex2_proctor@examguard.ai",
            password_hash=hash_password("ExaminerPass123!"),
            first_name="Examiner",
            last_name="Two",
            role=UserRole.EXAMINER,
            is_active=True,
        )
        db.add(ex2)

    # Student 1
    st1 = db.query(User).filter(User.email == "st1_proctor@examguard.ai").first()
    if not st1:
        st1 = User(
            email="st1_proctor@examguard.ai",
            password_hash=hash_password("StudentPass123!"),
            first_name="Student",
            last_name="One",
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(st1)

    # Student 2
    st2 = db.query(User).filter(User.email == "st2_proctor@examguard.ai").first()
    if not st2:
        st2 = User(
            email="st2_proctor@examguard.ai",
            password_hash=hash_password("StudentPass123!"),
            first_name="Student",
            last_name="Two",
            role=UserRole.STUDENT,
            is_active=True,
        )
        db.add(st2)

    db.commit()

    # Question for Exam
    q_in = QuestionCreate(
        question_text="Proctoring test question?",
        subject="Computer Science",
        question_type=QuestionType.SHORT_ANSWER,
        difficulty=DifficultyLevel.MEDIUM,
        marks=5.0,
    )
    q = question_repository.create_question(db, q_in, creator_id=ex1.id)

    # Published Exam owned by Examiner 1
    exam1 = ExamRepository.create_exam(
        db,
        exam_data=ExamCreate(
            title="Proctored Final Exam",
            subject="Computer Science",
            duration_minutes=60,
            proctoring_enabled=True,
            questions=[ExamQuestionInput(question_id=q.id, question_order=1, marks_override=5.0)],
        ),
        creator_id=ex1.id,
        total_marks=5.0,
    )
    exam1 = ExamRepository.update_status(db, exam1, ExamStatus.PUBLISHED)

    # Published Exam owned by Examiner 2
    exam2 = ExamRepository.create_exam(
        db,
        exam_data=ExamCreate(
            title="Examiner 2 Exam",
            subject="Physics",
            duration_minutes=45,
            proctoring_enabled=True,
            questions=[ExamQuestionInput(question_id=q.id, question_order=1, marks_override=5.0)],
        ),
        creator_id=ex2.id,
        total_marks=5.0,
    )
    exam2 = ExamRepository.update_status(db, exam2, ExamStatus.PUBLISHED)



    # Tokens
    t_st1 = create_access_token({"sub": str(st1.id), "role": UserRole.STUDENT.value, "email": st1.email})
    t_st2 = create_access_token({"sub": str(st2.id), "role": UserRole.STUDENT.value, "email": st2.email})
    t_ex1 = create_access_token({"sub": str(ex1.id), "role": UserRole.EXAMINER.value, "email": ex1.email})
    t_ex2 = create_access_token({"sub": str(ex2.id), "role": UserRole.EXAMINER.value, "email": ex2.email})

    return {
        "st1": st1,
        "st2": st2,
        "ex1": ex1,
        "ex2": ex2,
        "exam1": exam1,
        "exam2": exam2,
        "h_st1": {"Authorization": f"Bearer {t_st1}"},
        "h_st2": {"Authorization": f"Bearer {t_st2}"},
        "h_ex1": {"Authorization": f"Bearer {t_ex1}"},
        "h_ex2": {"Authorization": f"Bearer {t_ex2}"},
    }


def test_student_can_create_proctoring_event_for_own_active_session(client, proctoring_context):
    ctx = proctoring_context

    # 1. Student 1 starts session
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    assert start_res.status_code == 200
    sess_id = start_res.json()["id"]

    # 2. Student 1 logs TAB_HIDDEN event
    payload = {
        "event_type": "TAB_HIDDEN",
        "severity": "WARNING",
        "event_metadata": {"visibility_state": "hidden"},
    }
    evt_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json=payload,
        headers=ctx["h_st1"],
    )
    assert evt_res.status_code == 200
    res_json = evt_res.json()
    assert res_json["event_type"] == "TAB_HIDDEN"
    assert res_json["severity"] == "WARNING"
    assert res_json["event_metadata"]["visibility_state"] == "hidden"


def test_student_cannot_create_event_for_another_student_session(client, proctoring_context):
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]

    # Student 2 attempts to record event for Student 1's session -> 403
    evt_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "FACE_NOT_DETECTED"},
        headers=ctx["h_st2"],
    )
    assert evt_res.status_code == 403


def test_non_student_cannot_record_proctoring_events(client, proctoring_context):
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]

    # Examiner attempts to post student event -> 403
    evt_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "FULLSCREEN_EXITED"},
        headers=ctx["h_ex1"],
    )
    assert evt_res.status_code == 403


def test_invalid_session_returns_404(client, proctoring_context):
    ctx = proctoring_context
    fake_id = str(uuid.uuid4())
    evt_res = client.post(
        f"/api/student/sessions/{fake_id}/proctoring-events",
        json={"event_type": "FACE_NOT_DETECTED"},
        headers=ctx["h_st1"],
    )
    assert evt_res.status_code == 404


def test_submitted_and_expired_session_rejects_proctoring_events(client, proctoring_context, db):
    from app.models.exam_session import ExamSession
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = uuid.UUID(start_res.json()["id"])

    session_db = db.query(ExamSession).filter(ExamSession.id == sess_id).first()
    session_db.identity_verification_status = "VERIFIED"
    db.commit()

    # Submit session
    client.post(f"/api/student/sessions/{sess_id}/submit", headers=ctx["h_st1"])

    # Attempt to post event after submission -> 400
    evt_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "TAB_HIDDEN"},
        headers=ctx["h_st1"],
    )
    assert evt_res.status_code == 400

    # Test expired session with Student 2
    start_res2 = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st2"])
    sess_id2 = uuid.UUID(start_res2.json()["id"])

    session_db2 = db.query(ExamSession).filter(ExamSession.id == sess_id2).first()
    session_db2.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    session_db2.identity_verification_status = "VERIFIED"
    db.commit()

    evt_res2 = client.post(
        f"/api/student/sessions/{sess_id2}/proctoring-events",
        json={"event_type": "CAMERA_DISCONNECTED"},
        headers=ctx["h_st2"],
    )
    assert evt_res2.status_code == 400


def test_examiner_can_view_events_for_owned_exam(client, proctoring_context):
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]

    client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "CAMERA_READY", "severity": "LOW"},
        headers=ctx["h_st1"],
    )

    # Examiner 1 fetches events for owned Exam 1 -> 200
    ex_res = client.get(f"/api/exams/{ctx['exam1'].id}/proctoring-events", headers=ctx["h_ex1"])
    assert ex_res.status_code == 200
    items = ex_res.json()["items"]
    assert len(items) >= 1
    assert items[0]["event_type"] == "CAMERA_READY"
    assert items[0]["student_email"] == ctx["st1"].email


def test_examiner_cannot_view_events_for_other_examiner_exam(client, proctoring_context):
    ctx = proctoring_context

    # Examiner 2 attempts to fetch events for Examiner 1's Exam 1 -> 403
    ex_res = client.get(f"/api/exams/{ctx['exam1'].id}/proctoring-events", headers=ctx["h_ex2"])
    assert ex_res.status_code == 403


def test_tab_switch_limit_exceeded_auto_submits_session(client, proctoring_context, db):
    from app.models.exam_session import ExamSession
    ctx = proctoring_context

    # Set max_tab_switches = 2 for exam1
    ctx["exam1"].max_tab_switches = 2
    db.commit()

    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = uuid.UUID(start_res.json()["id"])

    session_db = db.query(ExamSession).filter(ExamSession.id == sess_id).first()
    session_db.identity_verification_status = "VERIFIED"
    db.commit()

    # 1st tab switch
    e1 = client.post(f"/api/student/sessions/{sess_id}/proctoring-events", json={"event_type": "TAB_HIDDEN"}, headers=ctx["h_st1"]).json()
    assert e1["tab_switch_count"] == 1
    assert e1["auto_submitted"] is False

    # 2nd tab switch
    e2 = client.post(f"/api/student/sessions/{sess_id}/proctoring-events", json={"event_type": "TAB_HIDDEN"}, headers=ctx["h_st1"]).json()
    assert e2["tab_switch_count"] == 2
    assert e2["auto_submitted"] is False

    # 3rd tab switch -> exceeds 2 allowed switches
    e3 = client.post(f"/api/student/sessions/{sess_id}/proctoring-events", json={"event_type": "TAB_HIDDEN"}, headers=ctx["h_st1"]).json()
    assert e3["tab_switch_count"] == 3
    assert e3["auto_submitted"] is True
    assert e3["is_flagged"] is True
    assert e3["flag_reason"] == "TAB_SWITCH_LIMIT_EXCEEDED"

    # Verify session detail
    sess_res = client.get(f"/api/student/sessions/{sess_id}", headers=ctx["h_st1"]).json()
    assert sess_res["status"] == "AUTO_SUBMITTED"
    assert sess_res["is_flagged"] is True
    assert sess_res["flag_reason"] == "TAB_SWITCH_LIMIT_EXCEEDED"


def test_fullscreen_and_hardware_events_recording(client, proctoring_context):
    """Tests fullscreen, camera disconnect, and microphone disconnect event recording."""
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]

    # Fullscreen exit
    fs_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "FULLSCREEN_EXITED", "severity": "WARNING"},
        headers=ctx["h_st1"],
    )
    assert fs_res.status_code == 200
    assert fs_res.json()["event_type"] == "FULLSCREEN_EXITED"

    # Camera disconnected
    cam_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "CAMERA_DISCONNECTED", "severity": "HIGH"},
        headers=ctx["h_st1"],
    )
    assert cam_res.status_code == 200
    assert cam_res.json()["event_type"] == "CAMERA_DISCONNECTED"

    # Microphone disconnected
    mic_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "MICROPHONE_DISCONNECTED", "severity": "HIGH"},
        headers=ctx["h_st1"],
    )
    assert mic_res.status_code == 200
    assert mic_res.json()["event_type"] == "MICROPHONE_DISCONNECTED"


def test_non_tab_event_deduplication(client, proctoring_context):
    """Verifies that non-tab events undergo 30s deduplication while TAB_HIDDEN events always increment."""
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]

    # 1. Post FACE_NOT_DETECTED twice in rapid succession
    f1 = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "FACE_NOT_DETECTED"},
        headers=ctx["h_st1"],
    ).json()

    f2 = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "FACE_NOT_DETECTED"},
        headers=ctx["h_st1"],
    ).json()

    # Both returned responses have same event ID due to deduplication window
    assert f1["id"] == f2["id"]

    # 2. Post two TAB_HIDDEN events in rapid succession -> BOTH must increment count
    t1 = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "TAB_HIDDEN"},
        headers=ctx["h_st1"],
    ).json()

    t2 = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "TAB_HIDDEN"},
        headers=ctx["h_st1"],
    ).json()

    assert t1["tab_switch_count"] == 1
    assert t2["tab_switch_count"] == 2


def test_object_detection_events_recording(client, proctoring_context):
    """Tests Stage 9.2 object detection events (PHONE_DETECTED, LAPTOP_DETECTED, ADDITIONAL_PERSON_DETECTED)."""
    ctx = proctoring_context
    start_res = client.post(f"/api/student/exams/{ctx['exam1'].id}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]

    # Phone detected
    p_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "PHONE_DETECTED", "metadata_json": {"object": "cell phone", "confidence": 0.85}},
        headers=ctx["h_st1"],
    )
    assert p_res.status_code == 200
    assert p_res.json()["event_type"] == "PHONE_DETECTED"

    # Laptop detected
    l_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "LAPTOP_DETECTED", "metadata_json": {"object": "laptop", "confidence": 0.78}},
        headers=ctx["h_st1"],
    )
    assert l_res.status_code == 200
    assert l_res.json()["event_type"] == "LAPTOP_DETECTED"

    # Book detected
    b_res = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "BOOK_DETECTED", "metadata_json": {"object": "book", "confidence": 0.82}},
        headers=ctx["h_st1"],
    )
    assert b_res.status_code == 200
    assert b_res.json()["event_type"] == "BOOK_DETECTED"

    # Pre-exam check started & completed
    pre_start = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "PRE_EXAM_CHECK_STARTED"},
        headers=ctx["h_st1"],
    )
    assert pre_start.status_code == 200
    assert pre_start.json()["event_type"] == "PRE_EXAM_CHECK_STARTED"

    pre_comp = client.post(
        f"/api/student/sessions/{sess_id}/proctoring-events",
        json={"event_type": "PRE_EXAM_CHECK_COMPLETED"},
        headers=ctx["h_st1"],
    )
    assert pre_comp.status_code == 200
    assert pre_comp.json()["event_type"] == "PRE_EXAM_CHECK_COMPLETED"



