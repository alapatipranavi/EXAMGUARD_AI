import uuid
from datetime import datetime, timezone, timedelta
import pytest
from app.models.user import User, UserRole
from app.models.exam import ExamStatus
from app.models.exam_session import SessionStatus
from app.models.question import QuestionType, DifficultyLevel
from app.repositories.question_repository import question_repository


@pytest.fixture
def student_exam_context(client, db):
    """Sets up Users (Student 1, Student 2, Examiner, Admin), Questions, and Exams."""
    from app.core.security import hash_password, create_access_token
    from app.models.user import User

    # Create users
    u_st1 = User(email="student1@examguard.ai", password_hash=hash_password("Student123!"), first_name="Alice", last_name="Student", role=UserRole.STUDENT)
    u_st2 = User(email="student2@examguard.ai", password_hash=hash_password("Student123!"), first_name="Bob", last_name="Student", role=UserRole.STUDENT)
    u_ex = User(email="examiner1@examguard.ai", password_hash=hash_password("Examiner123!"), first_name="John", last_name="Examiner", role=UserRole.EXAMINER)
    u_ad = User(email="admin1@examguard.ai", password_hash=hash_password("Admin123!"), first_name="Admin", last_name="User", role=UserRole.ADMIN)

    db.add_all([u_st1, u_st2, u_ex, u_ad])
    db.commit()

    # Headers
    h_st1 = {"Authorization": f"Bearer {create_access_token(data={'sub': str(u_st1.id)})}"}
    h_st2 = {"Authorization": f"Bearer {create_access_token(data={'sub': str(u_st2.id)})}"}
    h_ex = {"Authorization": f"Bearer {create_access_token(data={'sub': str(u_ex.id)})}"}
    h_ad = {"Authorization": f"Bearer {create_access_token(data={'sub': str(u_ad.id)})}"}

    from app.schemas.question import QuestionCreate, QuestionOptionCreate, QuestionSource

    # Create questions for examiner
    q_mcq = question_repository.create_question(db, QuestionCreate(
        question_text="Capital of France?", subject="Geography", question_type=QuestionType.MCQ,
        difficulty=DifficultyLevel.EASY, source=QuestionSource.MANUAL, marks=2.0, options=[
            QuestionOptionCreate(option_text="Paris", is_correct=True, option_order=1),
            QuestionOptionCreate(option_text="London", is_correct=False, option_order=2),
        ]
    ), creator_id=u_ex.id)

    q_multi = question_repository.create_question(db, QuestionCreate(
        question_text="Prime numbers?", subject="Math", question_type=QuestionType.MULTI_SELECT,
        difficulty=DifficultyLevel.MEDIUM, source=QuestionSource.MANUAL, marks=3.0, options=[
            QuestionOptionCreate(option_text="2", is_correct=True, option_order=1),
            QuestionOptionCreate(option_text="3", is_correct=True, option_order=2),
            QuestionOptionCreate(option_text="4", is_correct=False, option_order=3),
        ]
    ), creator_id=u_ex.id)

    q_short = question_repository.create_question(db, QuestionCreate(
        question_text="Define HTTP.", subject="CS", question_type=QuestionType.SHORT_ANSWER,
        difficulty=DifficultyLevel.EASY, source=QuestionSource.MANUAL, marks=5.0
    ), creator_id=u_ex.id)

    q_long = question_repository.create_question(db, QuestionCreate(
        question_text="Explain TCP 3-way handshake.", subject="CS", question_type=QuestionType.LONG_ANSWER,
        difficulty=DifficultyLevel.HARD, source=QuestionSource.MANUAL, marks=10.0
    ), creator_id=u_ex.id)

    q_outside = question_repository.create_question(db, QuestionCreate(
        question_text="Unrelated question.", subject="Other", question_type=QuestionType.SHORT_ANSWER,
        difficulty=DifficultyLevel.EASY, source=QuestionSource.MANUAL, marks=1.0
    ), creator_id=u_ex.id)

    # Create Draft Exam
    r_draft = client.post("/api/exams", json={
        "title": "Draft Exam Test", "subject": "CS", "duration_minutes": 30,
        "questions": [{"question_id": str(q_mcq.id), "question_order": 1}]
    }, headers=h_ex)
    draft_exam_id = r_draft.json()["id"]

    # Create Published Exam
    r_pub = client.post("/api/exams", json={
        "title": "Published CS Exam", "subject": "CS", "duration_minutes": 60, "passing_marks": 5.0,
        "questions": [
            {"question_id": str(q_mcq.id), "question_order": 1},
            {"question_id": str(q_multi.id), "question_order": 2},
            {"question_id": str(q_short.id), "question_order": 3},
            {"question_id": str(q_long.id), "question_order": 4},
        ]
    }, headers=h_ex)
    pub_exam_id = r_pub.json()["id"]
    client.post(f"/api/exams/{pub_exam_id}/publish", headers=h_ex)

    # Create Archived Exam
    r_arc = client.post("/api/exams", json={
        "title": "Archived Exam Test", "subject": "CS", "duration_minutes": 45,
        "questions": [{"question_id": str(q_mcq.id), "question_order": 1}]
    }, headers=h_ex)
    arc_exam_id = r_arc.json()["id"]
    client.post(f"/api/exams/{arc_exam_id}/publish", headers=h_ex)
    client.post(f"/api/exams/{arc_exam_id}/archive", headers=h_ex)

    return {
        "st1": u_st1, "st2": u_st2, "ex": u_ex, "ad": u_ad,
        "h_st1": h_st1, "h_st2": h_st2, "h_ex": h_ex, "h_ad": h_ad,
        "q_mcq": q_mcq, "q_multi": q_multi, "q_short": q_short, "q_long": q_long, "q_outside": q_outside,
        "draft_exam_id": draft_exam_id, "pub_exam_id": pub_exam_id, "arc_exam_id": arc_exam_id,
    }


def test_student_list_published_exams_excludes_draft_and_archived(client, student_exam_context):
    ctx = student_exam_context

    # 1. Student can list published exams
    res = client.get("/api/student/exams", headers=ctx["h_st1"])
    assert res.status_code == 200
    data = res.json()
    listed_ids = [item["id"] for item in data["items"]]

    # 2 & 3. Published appears; DRAFT and ARCHIVED are strictly hidden
    assert ctx["pub_exam_id"] in listed_ids
    assert ctx["draft_exam_id"] not in listed_ids
    assert ctx["arc_exam_id"] not in listed_ids


def test_student_view_eligible_exam_details(client, student_exam_context):
    ctx = student_exam_context

    # 4. Student can view eligible exam details
    res = client.get(f"/api/student/exams/{ctx['pub_exam_id']}", headers=ctx["h_st1"])
    assert res.status_code == 200
    data = res.json()
    assert data["title"] == "Published CS Exam"
    assert data["duration_minutes"] == 60
    assert data["question_count"] == 4
    assert "created_by" not in data


def test_student_start_exam_and_duplicate_prevention(client, student_exam_context):
    ctx = student_exam_context

    # 5. Student can start a published exam
    res1 = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    assert res1.status_code == 200
    sess1 = res1.json()
    assert sess1["status"] == "IN_PROGRESS"
    assert len(sess1["questions"]) == 4

    # 6. Duplicate active session is NOT created (returns same active session)
    res2 = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    assert res2.status_code == 200
    sess2 = res2.json()
    assert sess2["id"] == sess1["id"]


def _mark_verified(db, sess_id):
    from app.models.exam_session import ExamSession
    s_id = uuid.UUID(sess_id) if isinstance(sess_id, str) else sess_id
    db.query(ExamSession).filter(ExamSession.id == s_id).update({"identity_verification_status": "VERIFIED"})
    db.commit()


def test_student_save_mcq_answer(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)
    paris_opt_id = str(ctx["q_mcq"].options[0].id)

    # 7. Student can save MCQ answer
    save_res = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_mcq'].id}",
        json={"selected_option_ids": [paris_opt_id]},
        headers=ctx["h_st1"]
    )
    assert save_res.status_code == 200
    assert save_res.json()["selected_option_ids"] == [paris_opt_id]


def test_student_save_multi_select_answer(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)
    opt_ids = [str(ctx["q_multi"].options[0].id), str(ctx["q_multi"].options[1].id)]

    # 8. Student can save MULTI_SELECT answer
    save_res = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_multi'].id}",
        json={"selected_option_ids": opt_ids},
        headers=ctx["h_st1"]
    )
    assert save_res.status_code == 200
    assert set(save_res.json()["selected_option_ids"]) == set(opt_ids)


def test_student_save_short_answer(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    # 9. Student can save SHORT_ANSWER answer
    save_res = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_short'].id}",
        json={"text_answer": "Hypertext Transfer Protocol"},
        headers=ctx["h_st1"]
    )
    assert save_res.status_code == 200
    assert save_res.json()["text_answer"] == "Hypertext Transfer Protocol"


def test_student_save_long_answer(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    # 10. Student can save LONG_ANSWER answer
    long_text = "SYN -> SYN-ACK -> ACK. Establish connection between client and server."
    save_res = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_long'].id}",
        json={"text_answer": long_text},
        headers=ctx["h_st1"]
    )
    assert save_res.status_code == 200
    assert save_res.json()["text_answer"] == long_text


def test_student_session_isolation_and_cross_access(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    # 11. Student 2 cannot access Student 1's session -> 403
    st2_get = client.get(f"/api/exam-sessions/{sess_id}", headers=ctx["h_st2"])
    assert st2_get.status_code == 403

    # 12. Student 1 cannot answer a question outside the session exam -> 400
    outside_ans = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_outside'].id}",
        json={"text_answer": "Should fail"},
        headers=ctx["h_st1"]
    )
    assert outside_ans.status_code == 400


def test_student_submit_exam_session_and_modification_locking(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    # Save an answer first
    client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_short'].id}",
        json={"text_answer": "Initial Answer"},
        headers=ctx["h_st1"]
    )

    # 15. Student 2 cannot submit Student 1's session -> 403
    st2_sub = client.post(f"/api/exam-sessions/{sess_id}/submit", headers=ctx["h_st2"])
    assert st2_sub.status_code == 403

    # 14. Student 1 can submit active session -> SUBMITTED
    sub_res = client.post(f"/api/exam-sessions/{sess_id}/submit", headers=ctx["h_st1"])
    assert sub_res.status_code == 200
    assert sub_res.json()["status"] == "SUBMITTED"

    # 13 & 19. Completed/submitted session cannot be modified -> 400
    mod_res = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_short'].id}",
        json={"text_answer": "Modified Answer After Submit"},
        headers=ctx["h_st1"]
    )
    assert mod_res.status_code == 400
    assert "submitted" in mod_res.json()["detail"].lower() or "completed" in mod_res.json()["detail"].lower()


def test_rbac_examiner_and_admin_cannot_use_student_session_apis(client, student_exam_context):
    ctx = student_exam_context

    # 16. Examiner cannot use Student exam-session APIs -> 403
    ex_res = client.get("/api/student/exams", headers=ctx["h_ex"])
    assert ex_res.status_code == 403

    ex_start = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_ex"])
    assert ex_start.status_code == 403

    # 17. Admin cannot use Student exam-session APIs -> 403
    ad_res = client.get("/api/student/exams", headers=ctx["h_ad"])
    assert ad_res.status_code == 403

    ad_start = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_ad"])
    assert ad_start.status_code == 403


def test_server_side_session_expiry_enforcement(client, student_exam_context, db):
    from app.models.exam_session import ExamSession
    ctx = student_exam_context

    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = uuid.UUID(start_res.json()["id"])
    _mark_verified(db, sess_id)

    # Manually expire the session in DB
    session_db = db.query(ExamSession).filter(ExamSession.id == sess_id).first()
    session_db.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()

    # 18. Timer/session expiry is enforced server-side upon get or save answer
    get_res = client.get(f"/api/exam-sessions/{sess_id}", headers=ctx["h_st1"])
    assert get_res.status_code == 200
    assert get_res.json()["status"] == "EXPIRED"

    save_res = client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_short'].id}",
        json={"text_answer": "Too late"},
        headers=ctx["h_st1"]
    )
    assert save_res.status_code == 400
    assert "expired" in save_res.json()["detail"].lower()


def test_questions_remain_unchanged_after_answering(client, student_exam_context, db):
    ctx = student_exam_context

    # Get question initial state
    q_before = question_repository.get_by_id(db, ctx["q_mcq"].id)
    initial_text = q_before.question_text
    initial_marks = q_before.marks

    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    client.put(
        f"/api/exam-sessions/{sess_id}/answers/{ctx['q_mcq'].id}",
        json={"selected_option_ids": [str(ctx["q_mcq"].options[0].id)]},
        headers=ctx["h_st1"]
    )

    client.post(f"/api/exam-sessions/{sess_id}/submit", headers=ctx["h_st1"])

    # 20. Questions in Question Bank remain completely unchanged
    q_after = question_repository.get_by_id(db, ctx["q_mcq"].id)
    assert q_after.question_text == initial_text
    assert q_after.marks == initial_marks


def test_student_toggle_mark_for_review_and_persistence(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    q1_id = str(ctx["q_mcq"].id)
    q2_id = str(ctx["q_short"].id)

    # Initially, marked_for_review_question_ids is empty
    assert start_res.json()["marked_for_review_question_ids"] == []

    # Mark Q1 for review
    rev1 = client.put(
        f"/api/student/sessions/{sess_id}/questions/{q1_id}/review",
        json={"marked": True},
        headers=ctx["h_st1"],
    )
    assert rev1.status_code == 200
    assert q1_id in rev1.json()["marked_for_review_question_ids"]

    # Mark Q2 for review
    rev2 = client.put(
        f"/api/student/sessions/{sess_id}/questions/{q2_id}/review",
        json={"marked": True},
        headers=ctx["h_st1"],
    )
    assert rev2.status_code == 200
    assert q1_id in rev2.json()["marked_for_review_question_ids"]
    assert q2_id in rev2.json()["marked_for_review_question_ids"]

    # Unmark Q1 for review
    unrev1 = client.put(
        f"/api/student/sessions/{sess_id}/questions/{q1_id}/review",
        json={"marked": False},
        headers=ctx["h_st1"],
    )
    assert unrev1.status_code == 200
    assert q1_id not in unrev1.json()["marked_for_review_question_ids"]
    assert q2_id in unrev1.json()["marked_for_review_question_ids"]

    # Session refresh preserves review marks
    get_res = client.get(f"/api/student/sessions/{sess_id}", headers=ctx["h_st1"])
    assert get_res.status_code == 200
    assert q2_id in get_res.json()["marked_for_review_question_ids"]


def test_student_cannot_toggle_review_after_submit_or_expiry(client, student_exam_context, db):
    from app.models.exam_session import ExamSession
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)
    q1_id = str(ctx["q_mcq"].id)

    # Student 2 cannot modify Student 1's review state -> 403
    st2_rev = client.put(
        f"/api/student/sessions/{sess_id}/questions/{q1_id}/review",
        json={"marked": True},
        headers=ctx["h_st2"],
    )
    assert st2_rev.status_code == 403

    # Submit session
    client.post(f"/api/student/sessions/{sess_id}/submit", headers=ctx["h_st1"])

    # Cannot toggle review state after submission -> 400
    sub_rev = client.put(
        f"/api/student/sessions/{sess_id}/questions/{q1_id}/review",
        json={"marked": True},
        headers=ctx["h_st1"],
    )
    assert sub_rev.status_code == 400

    # Start session with student 2 and expire it
    start_res2 = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st2"])
    sess_id2 = uuid.UUID(start_res2.json()["id"])
    _mark_verified(db, sess_id2)

    session_db = db.query(ExamSession).filter(ExamSession.id == sess_id2).first()
    session_db.expires_at = datetime.now(timezone.utc) - timedelta(minutes=5)
    db.commit()

    # Cannot toggle review state after session expiry -> 400
    exp_rev = client.put(
        f"/api/student/sessions/{sess_id2}/questions/{q1_id}/review",
        json={"marked": True},
        headers=ctx["h_st2"],
    )
    assert exp_rev.status_code == 400


def test_student_clear_answers_preserves_review_mark(client, student_exam_context, db):
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    sess_id = start_res.json()["id"]
    _mark_verified(db, sess_id)

    q_mcq_id = str(ctx["q_mcq"].id)
    opt_id = str(ctx["q_mcq"].options[0].id)
    q_short_id = str(ctx["q_short"].id)

    # 1. Answer MCQ and Mark for Review
    client.put(
        f"/api/student/sessions/{sess_id}/answers/{q_mcq_id}",
        json={"selected_option_ids": [opt_id]},
        headers=ctx["h_st1"],
    )
    client.put(
        f"/api/student/sessions/{sess_id}/questions/{q_mcq_id}/review",
        json={"marked": True},
        headers=ctx["h_st1"],
    )

    # 2. Answer Short question
    client.put(
        f"/api/student/sessions/{sess_id}/answers/{q_short_id}",
        json={"text_answer": "Temporary Short Text"},
        headers=ctx["h_st1"],
    )

    # Verify initial session state
    sess_before = client.get(f"/api/student/sessions/{sess_id}", headers=ctx["h_st1"]).json()
    assert q_mcq_id in sess_before["marked_for_review_question_ids"]
    mcq_ans_before = next(a for a in sess_before["answers"] if a["question_id"] == q_mcq_id)
    assert mcq_ans_before["selected_option_ids"] == [opt_id]

    # 3. Clear MCQ answer
    clear_mcq = client.put(
        f"/api/student/sessions/{sess_id}/answers/{q_mcq_id}",
        json={"selected_option_ids": [], "text_answer": ""},
        headers=ctx["h_st1"],
    )
    assert clear_mcq.status_code == 200
    assert clear_mcq.json()["selected_option_ids"] == []

    # 4. Clear Short answer
    clear_short = client.put(
        f"/api/student/sessions/{sess_id}/answers/{q_short_id}",
        json={"selected_option_ids": [], "text_answer": ""},
        headers=ctx["h_st1"],
    )
    assert clear_short.status_code == 200
    assert clear_short.json()["text_answer"] in ["", None]

    # 5. Verify marked_for_review_question_ids STILL contains MCQ question ID
    sess_after = client.get(f"/api/student/sessions/{sess_id}", headers=ctx["h_st1"]).json()
    assert q_mcq_id in sess_after["marked_for_review_question_ids"]


def test_unverified_identity_blocks_exam_session_access(client, student_exam_context, db):
    """Verifies that an unverified exam session blocks direct session access, saving answers, review toggling, and submission."""
    ctx = student_exam_context
    start_res = client.post(f"/api/student/exams/{ctx['pub_exam_id']}/start", headers=ctx["h_st1"])
    assert start_res.status_code == 200
    sess_id = start_res.json()["id"]
    q_mcq_id = str(ctx["q_mcq"].id)

    # 1. GET session details is blocked with 403 IDENTITY_VERIFICATION_REQUIRED
    get_res = client.get(f"/api/student/sessions/{sess_id}", headers=ctx["h_st1"])
    assert get_res.status_code == 403
    assert get_res.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    # 2. Save answer is blocked
    save_res = client.put(
        f"/api/student/sessions/{sess_id}/answers/{q_mcq_id}",
        json={"selected_option_ids": [str(ctx["q_mcq"].options[0].id)]},
        headers=ctx["h_st1"],
    )
    assert save_res.status_code == 403
    assert save_res.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    # 3. Toggle review is blocked
    rev_res = client.put(
        f"/api/student/sessions/{sess_id}/questions/{q_mcq_id}/review",
        json={"marked": True},
        headers=ctx["h_st1"],
    )
    assert rev_res.status_code == 403
    assert rev_res.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    # 4. Submit session is blocked
    sub_res = client.post(f"/api/student/sessions/{sess_id}/submit", headers=ctx["h_st1"])
    assert sub_res.status_code == 403
    assert sub_res.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    # 5. Verify identity
    _mark_verified(db, sess_id)

    # 6. Now GET session details succeeds
    get_res_after = client.get(f"/api/student/sessions/{sess_id}", headers=ctx["h_st1"])
    assert get_res_after.status_code == 200
    assert get_res_after.json()["identity_verification_status"] == "VERIFIED"
    assert len(get_res_after.json()["questions"]) == 4


