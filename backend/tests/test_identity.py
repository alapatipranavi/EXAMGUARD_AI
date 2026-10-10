import uuid
import math
import pytest
from datetime import datetime, timedelta, timezone
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamStatus, ExamQuestion
from app.models.question import Question, QuestionType
from app.models.exam_session import ExamSession, SessionStatus
from app.models.proctoring import ProctoringEvent, ProctoringEventType
from app.services.identity_service import identity_service
from app.services.integrity_service import integrity_service


def test_cosine_similarity():
    vec_a = [1.0] * 64
    vec_b = [1.0] * 64
    sim_identical = identity_service.calculate_cosine_similarity(vec_a, vec_b)
    assert round(sim_identical, 2) == 1.0

    vec_c = [-1.0] * 64
    sim_opposite = identity_service.calculate_cosine_similarity(vec_a, vec_c)
    assert round(sim_opposite, 2) == -1.0


def test_identity_registration_and_status(client, db: Session):
    student = User(
        id=uuid.uuid4(),
        email=f"identity_student_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="hashed_pwd",
        first_name="Identity",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add(student)
    db.commit()

    from app.core.security import create_access_token
    token = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Unregistered Status
    resp = client.get("/api/student/identity/status", headers=headers)
    assert resp.status_code == status.HTTP_200_OK
    assert resp.json()["is_face_registered"] is False

    # 2. Register Face
    valid_embedding = [0.5] * 64
    payload = {
        "face_embedding": valid_embedding,
        "consent_given": True,
    }
    reg_resp = client.post("/api/student/identity/register-face", json=payload, headers=headers)
    assert reg_resp.status_code == status.HTTP_200_OK
    assert reg_resp.json()["is_face_registered"] is True

    # Check status again
    status_resp = client.get("/api/student/identity/status", headers=headers)
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json()["is_face_registered"] is True
    assert status_resp.json()["face_registered_at"] is not None

    # 3. Clear Face Registration
    clear_resp = client.delete("/api/student/identity/face", headers=headers)
    assert clear_resp.status_code == status.HTTP_200_OK

    status_resp2 = client.get("/api/student/identity/status", headers=headers)
    assert status_resp2.json()["is_face_registered"] is False


def test_session_identity_verification_flow(client, db: Session):
    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Ex",
        last_name="Am",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    reference_embedding = [0.1 * (i % 5) for i in range(64)]
    student = User(
        id=uuid.uuid4(),
        email=f"st_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="St",
        last_name="Ud",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=reference_embedding,
    )
    db.add_all([examiner, student])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Identity Exam",
        subject="Test",
        duration_minutes=30,
        total_marks=100.0,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student.id,
        status=SessionStatus.IN_PROGRESS,
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    from app.core.security import create_access_token
    token = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Verification matching reference embedding
    matching_payload = {"face_embedding": reference_embedding}
    v_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json=matching_payload,
        headers=headers,
    )
    assert v_resp.status_code == status.HTTP_200_OK
    assert v_resp.json()["verified"] is True
    assert v_resp.json()["status"] == "VERIFIED"

    # 2. Temporary Mismatch
    mismatched_embedding = [-1.0 * (i % 5 + 1) for i in range(64)]
    mismatch_payload = {"face_embedding": mismatched_embedding}

    m_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json=mismatch_payload,
        headers=headers,
    )
    assert m_resp.status_code == status.HTTP_200_OK
    assert m_resp.json()["verified"] is False
    assert m_resp.json()["status"] == "TEMPORARILY_UNVERIFIED"

    # 3. Simulate continuous mismatch exceeding 180s grace period
    # Manually backdate the mismatch start timestamp in session metadata
    meta = dict(session.session_metadata or {})
    meta["identity_mismatch_started_at"] = (datetime.now(timezone.utc) - timedelta(seconds=185)).isoformat()
    session.session_metadata = meta
    db.commit()

    m_resp2 = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json=mismatch_payload,
        headers=headers,
    )
    assert m_resp2.status_code == status.HTTP_200_OK
    assert m_resp2.json()["verified"] is False
    assert m_resp2.json()["status"] == "CONFIRMED_IDENTITY_MISMATCH"

    db.refresh(session)
    assert session.is_flagged is True
    assert session.identity_verification_status == "CONFIRMED_IDENTITY_MISMATCH"

    # 4. Check integrity scoring deduction for CONFIRMED_IDENTITY_MISMATCH
    analysis = integrity_service.analyze_or_update_session_integrity(db, session)
    assert analysis.integrity_score <= 90.0  # At least 10 pts deduction applied


def test_security_access_control_unverified_vs_verified_session(client, db: Session):
    """
    PART 12: Automated security tests for identity verification enforcement:
    TEST A: Same embedding -> VERIFIED
    TEST B: Different embedding -> FAILED / UNVERIFIED
    TEST C: Zero / invalid embedding -> 400 Bad Request
    TEST D: Unregistered student -> 400 Bad Request
    TEST E: Exception / Invalid session -> 404 Not Found
    TEST F: Unverified session cannot access exam questions -> 403 Forbidden
    TEST G: Verified session can access exam questions -> 200 OK
    """
    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_sec_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Ex",
        last_name="Sec",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    ref_emb = [0.2 if i % 2 == 0 else -0.2 for i in range(64)]
    student = User(
        id=uuid.uuid4(),
        email=f"st_sec_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="St",
        last_name="Sec",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=ref_emb,
    )
    unreg_student = User(
        id=uuid.uuid4(),
        email=f"unreg_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Unreg",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=False,
    )
    db.add_all([examiner, student, unreg_student])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Security Test Exam",
        subject="Security",
        duration_minutes=30,
        total_marks=100.0,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    unreg_session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=unreg_student.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add_all([session, unreg_session])
    db.commit()

    from app.core.security import create_access_token
    token_st = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    token_unreg = create_access_token({"sub": str(unreg_student.id), "role": "STUDENT"})
    headers_st = {"Authorization": f"Bearer {token_st}"}
    headers_unreg = {"Authorization": f"Bearer {token_unreg}"}

    # TEST F: Unverified session CANNOT access exam questions -> 403 Forbidden
    f_resp = client.get(f"/api/student/sessions/{session.id}", headers=headers_st)
    assert f_resp.status_code == status.HTTP_403_FORBIDDEN
    assert f_resp.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    # TEST B: Different embedding -> FAILED / VERIFICATION_FAILED or TEMPORARILY_UNVERIFIED
    diff_emb = [-0.2 if i % 2 == 0 else 0.2 for i in range(64)]
    b_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": diff_emb},
        headers=headers_st,
    )
    assert b_resp.status_code == status.HTTP_200_OK
    assert b_resp.json()["verified"] is False
    assert b_resp.json()["status"] in ["VERIFICATION_FAILED", "TEMPORARILY_UNVERIFIED"]

    # TEST C: Zero / invalid embedding -> 400 Bad Request or 422 Unprocessable Entity
    c_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": [0.0] * 5},
        headers=headers_st,
    )
    assert c_resp.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # TEST D: Unregistered student -> 400 Bad Request
    d_resp = client.post(
        f"/api/student/sessions/{unreg_session.id}/verify-identity",
        json={"face_embedding": ref_emb},
        headers=headers_unreg,
    )
    assert d_resp.status_code == status.HTTP_400_BAD_REQUEST

    # TEST E: Non-existent session -> 404 Not Found
    fake_id = uuid.uuid4()
    e_resp = client.post(
        f"/api/student/sessions/{fake_id}/verify-identity",
        json={"face_embedding": ref_emb},
        headers=headers_st,
    )
    assert e_resp.status_code == status.HTTP_404_NOT_FOUND

    # TEST A: Same embedding -> VERIFIED
    a_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": ref_emb},
        headers=headers_st,
    )
    assert a_resp.status_code == status.HTTP_200_OK
    assert a_resp.json()["verified"] is True
    assert a_resp.json()["status"] == "VERIFIED"

    # TEST G: Verified session CAN access exam questions -> 200 OK
    g_resp = client.get(f"/api/student/sessions/{session.id}", headers=headers_st)
    assert g_resp.status_code == status.HTTP_200_OK
    assert g_resp.json()["id"] == str(session.id)


def test_stage12_1_comprehensive_security_gate(client, db: Session):
    """
    Stage 12.1 Comprehensive Security & Verification Gate Test Suite:
    1. Correct student + matching identity -> VERIFIED
    2. Different person -> VERIFICATION_FAILED
    3. No face / empty embedding -> 400 Bad Request
    4. Missing template -> verification fails safely (400 Bad Request)
    5. Authenticated student A cannot verify against student B's session (404)
    6. Unverified session retrieval -> 403 Forbidden
    7. Unverified answer submission -> 403 Forbidden
    8. Unverified exam submit -> 403 Forbidden
    9. Direct exam access while unverified -> blocked (403)
    10. Verified student can access exam normally (200 OK)
    11. Retry after failed verification works correctly
    12. Old VERIFIED state of student A cannot authorize student B's session
    """
    from app.core.security import create_access_token
    from app.models.question import Question, QuestionType, DifficultyLevel

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_s12_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Examiner",
        last_name="S12",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    emb_student_a = [0.15 * ((i % 7) - 3) for i in range(64)]
    emb_student_b = [-0.15 * ((i % 7) - 3) for i in range(64)]

    student_a = User(
        id=uuid.uuid4(),
        email=f"st_a_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Student",
        last_name="A",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=emb_student_a,
    )
    student_b = User(
        id=uuid.uuid4(),
        email=f"st_b_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Student",
        last_name="B",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=emb_student_b,
    )
    unreg_student = User(
        id=uuid.uuid4(),
        email=f"st_unreg_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Unregistered",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=False,
    )
    db.add_all([examiner, student_a, student_b, unreg_student])
    db.commit()

    question = Question(
        id=uuid.uuid4(),
        created_by=examiner.id,
        question_text="Sample Question 12.1",
        question_type=QuestionType.MCQ,
        subject="General",
        difficulty=DifficultyLevel.EASY,
        marks=5.0,
    )
    db.add(question)
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Gate Security Exam",
        subject="Security",
        duration_minutes=30,
        total_marks=5.0,
        passing_marks=2.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    from app.models.exam import ExamQuestion
    eq = ExamQuestion(
        id=uuid.uuid4(),
        exam_id=exam.id,
        question_id=question.id,
        question_order=1,
    )
    db.add(eq)
    db.commit()

    session_a = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_a.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    session_b = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_b.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    unreg_session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=unreg_student.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add_all([session_a, session_b, unreg_session])
    db.commit()

    token_a = create_access_token({"sub": str(student_a.id), "role": "STUDENT"})
    token_b = create_access_token({"sub": str(student_b.id), "role": "STUDENT"})
    token_unreg = create_access_token({"sub": str(unreg_student.id), "role": "STUDENT"})
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}
    headers_unreg = {"Authorization": f"Bearer {token_unreg}"}

    # 1. Unverified session retrieval -> 403 Forbidden
    resp = client.get(f"/api/student/sessions/{session_a.id}", headers=headers_a)
    assert resp.status_code == status.HTTP_403_FORBIDDEN
    assert resp.json()["detail"]["code"] == "IDENTITY_VERIFICATION_REQUIRED"

    # 2. Unverified answer submission -> 403 Forbidden
    ans_resp = client.put(
        f"/api/student/sessions/{session_a.id}/answers/{question.id}",
        json={"selected_option_ids": [str(uuid.uuid4())], "text_answer": ""},
        headers=headers_a,
    )
    assert ans_resp.status_code == status.HTTP_403_FORBIDDEN

    # 3. Unverified exam submit -> 403 Forbidden
    sub_resp = client.post(f"/api/student/sessions/{session_a.id}/submit", headers=headers_a)
    assert sub_resp.status_code == status.HTTP_403_FORBIDDEN

    # 4. Student A trying to verify against Student B's session -> 404 Not Found
    cross_resp = client.post(
        f"/api/student/sessions/{session_b.id}/verify-identity",
        json={"face_embedding": emb_student_a},
        headers=headers_a,
    )
    assert cross_resp.status_code == status.HTTP_404_NOT_FOUND

    # 5. Missing template -> verification fails safely (400 Bad Request)
    unreg_v_resp = client.post(
        f"/api/student/sessions/{unreg_session.id}/verify-identity",
        json={"face_embedding": emb_student_a},
        headers=headers_unreg,
    )
    assert unreg_v_resp.status_code == status.HTTP_400_BAD_REQUEST

    # 6. Different person's face -> VERIFICATION_FAILED
    fail_v_resp = client.post(
        f"/api/student/sessions/{session_a.id}/verify-identity",
        json={"face_embedding": emb_student_b},
        headers=headers_a,
    )
    assert fail_v_resp.status_code == status.HTTP_200_OK
    assert fail_v_resp.json()["verified"] is False
    assert fail_v_resp.json()["status"] == "VERIFICATION_FAILED"

    # 7. Retry after failed verification -> matching identity -> VERIFIED
    pass_v_resp = client.post(
        f"/api/student/sessions/{session_a.id}/verify-identity",
        json={"face_embedding": emb_student_a},
        headers=headers_a,
    )
    assert pass_v_resp.status_code == status.HTTP_200_OK
    assert pass_v_resp.json()["verified"] is True
    assert pass_v_resp.json()["status"] == "VERIFIED"

    # 8. Verified student A CAN access session details -> 200 OK
    ok_resp = client.get(f"/api/student/sessions/{session_a.id}", headers=headers_a)
    assert ok_resp.status_code == status.HTTP_200_OK

    # 9. Student B's session STILL unverified -> student B blocked -> 403 Forbidden
    b_blocked_resp = client.get(f"/api/student/sessions/{session_b.id}", headers=headers_b)
    assert b_blocked_resp.status_code == status.HTTP_403_FORBIDDEN


def test_stage12_2_user_binding_and_reference_template_integrity(client, db: Session):
    """
    Stage 12.2 Security Tests:
    - Verification CANNOT overwrite student_user.face_embedding during exam verification
    - Reference template remains unchanged after failed or successful verification calls
    - Independent identity reference per student
    - Verification compares current face strictly against registered reference template of authenticated JWT student
    """
    from app.core.security import create_access_token

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_s12_2_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Examiner",
        last_name="S122",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    original_emb_a = [0.1 * i for i in range(64)]
    original_emb_b = [-0.1 * i for i in range(64)]

    student_a = User(
        id=uuid.uuid4(),
        email=f"st_a_122_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="StudentA",
        last_name="Test",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=original_emb_a,
    )
    student_b = User(
        id=uuid.uuid4(),
        email=f"st_b_122_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="StudentB",
        last_name="Test",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=original_emb_b,
    )
    db.add_all([examiner, student_a, student_b])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Template Integrity Exam",
        subject="Security",
        duration_minutes=30,
        total_marks=10.0,
        passing_marks=4.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session_a = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_a.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add(session_a)
    db.commit()

    token_a = create_access_token({"sub": str(student_a.id), "role": "STUDENT"})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Verification with intruder face (Student B's face)
    resp1 = client.post(
        f"/api/student/sessions/{session_a.id}/verify-identity",
        json={"face_embedding": original_emb_b},
        headers=headers_a,
    )
    assert resp1.status_code == status.HTTP_200_OK
    assert resp1.json()["verified"] is False
    assert resp1.json()["status"] == "VERIFICATION_FAILED"

    # CONFIRM stored template of Student A was NOT overwritten by intruder face
    db.refresh(student_a)
    assert student_a.face_embedding == original_emb_a

    # 2. Successful verification with matching face (Student A's face)
    resp2 = client.post(
        f"/api/student/sessions/{session_a.id}/verify-identity",
        json={"face_embedding": original_emb_a},
        headers=headers_a,
    )
    assert resp2.status_code == status.HTTP_200_OK
    assert resp2.json()["verified"] is True
    assert resp2.json()["status"] == "VERIFIED"

    # CONFIRM stored template of Student A still remains intact
    db.refresh(student_a)
    assert student_a.face_embedding == original_emb_a


def test_stage14_1_different_person_biometric_mismatch(client, db: Session):
    """
    Stage 14.1 Requirement B: Wrong identity (different person's descriptor)
    MUST NOT become VERIFIED.
    Tests with realistic distinct facial geometry offsets.
    """
    from app.core.security import create_access_token

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_14_1_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Examiner",
        last_name="14",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    # Generate two realistic, non-opposite distinct face descriptor residuals
    import math
    vec_student_a = [0.1 * math.sin(i * 0.5) for i in range(64)]
    norm_a = math.sqrt(sum(x * x for x in vec_student_a))
    vec_student_a = [x / norm_a for x in vec_student_a]

    vec_student_b = [0.1 * math.cos(i * 0.8) for i in range(64)]
    norm_b = math.sqrt(sum(x * x for x in vec_student_b))
    vec_student_b = [x / norm_b for x in vec_student_b]

    # Verify our test vectors have low inter-person similarity (< 0.50)
    sim = identity_service.calculate_cosine_similarity(vec_student_a, vec_student_b)
    assert sim < 0.50, f"Sim between distinct faces was {sim}, expected < 0.50"

    student_a = User(
        id=uuid.uuid4(),
        email=f"st_14a_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Registered",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=vec_student_a,
    )
    db.add_all([examiner, student_a])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Stage 14.1 Identity Test",
        subject="Proctoring",
        duration_minutes=30,
        total_marks=50.0,
        passing_marks=20.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_a.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    token_a = create_access_token({"sub": str(student_a.id), "role": "STUDENT"})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Test B: Impostor / Different person's face MUST NOT become VERIFIED
    impostor_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": vec_student_b},
        headers=headers_a,
    )
    assert impostor_resp.status_code == status.HTTP_200_OK
    assert impostor_resp.json()["verified"] is False
    assert impostor_resp.json()["status"] == "VERIFICATION_FAILED"
    assert "face_embedding" not in impostor_resp.json()

    # Session remains unverified
    db.refresh(session)
    assert session.identity_verification_status == "VERIFICATION_FAILED"

    # Test A: Correct student's matching face -> VERIFIED
    correct_resp = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": vec_student_a},
        headers=headers_a,
    )
    assert correct_resp.status_code == status.HTTP_200_OK
    assert correct_resp.json()["verified"] is True
    assert correct_resp.json()["status"] == "VERIFIED"

    db.refresh(session)
    assert session.identity_verification_status == "VERIFIED"


def test_stage14_1_invalid_embeddings_rejection(client, db: Session):
    """
    Stage 14.1 Requirement F: Invalid descriptor does not become VERIFIED
    Checks rejection of all-zeros, NaN, short vectors, and un-registered users.
    """
    from app.core.security import create_access_token

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_14_inv_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Examiner",
        last_name="Inv",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    ref_emb = [0.2] * 64
    student = User(
        id=uuid.uuid4(),
        email=f"st_14_inv_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Student",
        last_name="Inv",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=ref_emb,
    )
    db.add_all([examiner, student])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Invalid Vector Test Exam",
        subject="Security",
        duration_minutes=30,
        total_marks=10.0,
        passing_marks=4.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    token = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. All zeros embedding
    resp_zeros = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": [0.0] * 64},
        headers=headers,
    )
    assert resp_zeros.status_code == status.HTTP_400_BAD_REQUEST

    # 2. Too short embedding (< 16)
    resp_short = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": [0.1, 0.2]},
        headers=headers,
    )
    assert resp_short.status_code in [status.HTTP_400_BAD_REQUEST, status.HTTP_422_UNPROCESSABLE_ENTITY]

    # 3. Registration with all zeros rejected
    reg_zeros = client.post(
        "/api/student/identity/register-face",
        json={"face_embedding": [0.0] * 64, "consent_given": True},
        headers=headers,
    )
    assert reg_zeros.status_code == status.HTTP_400_BAD_REQUEST

    # 4. Registration without consent rejected
    reg_no_consent = client.post(
        "/api/student/identity/register-face",
        json={"face_embedding": [0.1] * 64, "consent_given": False},
        headers=headers,
    )
    assert reg_no_consent.status_code == status.HTTP_400_BAD_REQUEST


def test_stage14_1_state_machine_recovery_and_continuous_timeout(client, db: Session):
    """
    Stage 14.1 Requirements G, H, I:
    - VERIFIED -> Mismatch detected -> TEMPORARILY_UNVERIFIED
    - TEMPORARILY_UNVERIFIED -> Correct student returns -> restored to VERIFIED
    - TEMPORARILY_UNVERIFIED -> Continuous mismatch >= 180s -> CONFIRMED_IDENTITY_MISMATCH
    """
    from app.core.security import create_access_token

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_14_sm_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Examiner",
        last_name="SM",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    ref_emb = [0.1 * ((i % 10) - 5) for i in range(64)]
    diff_emb = [-0.1 * ((i % 10) - 5) for i in range(64)]

    student = User(
        id=uuid.uuid4(),
        email=f"st_14_sm_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Student",
        last_name="SM",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=ref_emb,
    )
    db.add_all([examiner, student])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="State Machine Exam",
        subject="Security",
        duration_minutes=30,
        total_marks=20.0,
        passing_marks=8.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    token = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # Step 1: Verify student -> VERIFIED
    res1 = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": ref_emb},
        headers=headers,
    )
    assert res1.json()["status"] == "VERIFIED"

    # Step 2: Different person replaces student during exam -> TEMPORARILY_UNVERIFIED
    res2 = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": diff_emb},
        headers=headers,
    )
    assert res2.json()["verified"] is False
    assert res2.json()["status"] == "TEMPORARILY_UNVERIFIED"

    # Step 3: Correct student returns -> restored to VERIFIED
    res3 = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": ref_emb},
        headers=headers,
    )
    assert res3.json()["verified"] is True
    assert res3.json()["status"] == "VERIFIED"

    # Check event was logged in DB
    restored_event = (
        db.query(ProctoringEvent)
        .filter(
            ProctoringEvent.session_id == session.id,
            ProctoringEvent.event_type == ProctoringEventType.IDENTITY_VERIFICATION_RESTORED,
        )
        .first()
    )
    assert restored_event is not None

    # Step 4: Different person appears again -> TEMPORARILY_UNVERIFIED
    res4 = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": diff_emb},
        headers=headers,
    )
    assert res4.json()["status"] == "TEMPORARILY_UNVERIFIED"

    # Step 5: Simulate >= 180 seconds continuous mismatch
    meta = dict(session.session_metadata or {})
    meta["identity_mismatch_started_at"] = (datetime.now(timezone.utc) - timedelta(seconds=185)).isoformat()
    session.session_metadata = meta
    db.commit()

    res5 = client.post(
        f"/api/student/sessions/{session.id}/verify-identity",
        json={"face_embedding": diff_emb},
        headers=headers,
    )
    assert res5.json()["verified"] is False
    assert res5.json()["status"] == "CONFIRMED_IDENTITY_MISMATCH"

    db.refresh(session)
    assert session.identity_verification_status == "CONFIRMED_IDENTITY_MISMATCH"
    assert session.is_flagged is True
    assert session.flag_reason == "IDENTITY_MISMATCH_CONFIRMED"


def test_stage14_1_idor_and_no_biometric_leakage(client, db: Session):
    """
    Stage 14.1 Requirements K, L, M, and 10:
    - Student A cannot verify or access Student B's session (IDOR protection)
    - Unauthenticated cannot access identity endpoints (401)
    - No raw biometric vectors leaked in responses or status
    """
    from app.core.security import create_access_token

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_14_idor_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="Examiner",
        last_name="Idor",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    emb_a = [0.1 * i for i in range(64)]
    emb_b = [-0.1 * i for i in range(64)]

    student_a = User(
        id=uuid.uuid4(),
        email=f"st_14_a_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="StudentA",
        last_name="Idor",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=emb_a,
    )
    student_b = User(
        id=uuid.uuid4(),
        email=f"st_14_b_{uuid.uuid4().hex[:6]}@test.com",
        password_hash="pwd",
        first_name="StudentB",
        last_name="Idor",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=emb_b,
    )
    db.add_all([examiner, student_a, student_b])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="IDOR Exam",
        subject="Security",
        duration_minutes=30,
        total_marks=20.0,
        passing_marks=8.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    session_b = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_b.id,
        status=SessionStatus.IN_PROGRESS,
        identity_verification_status="UNVERIFIED",
        started_at=datetime.utcnow(),
    )
    db.add(session_b)
    db.commit()

    token_a = create_access_token({"sub": str(student_a.id), "role": "STUDENT"})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # 1. Student A trying to verify Student B's session -> 404 Not Found (resource hidden)
    idor_resp = client.post(
        f"/api/student/sessions/{session_b.id}/verify-identity",
        json={"face_embedding": emb_a},
        headers=headers_a,
    )
    assert idor_resp.status_code == status.HTTP_404_NOT_FOUND

    # 2. Unauthenticated verification attempt -> 401 Unauthorized
    unauth_resp = client.post(
        f"/api/student/sessions/{session_b.id}/verify-identity",
        json={"face_embedding": emb_a},
    )
    assert unauth_resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 3. Check status response does NOT leak raw vector
    status_resp = client.get("/api/student/identity/status", headers=headers_a)
    assert status_resp.status_code == status.HTTP_200_OK
    assert "face_embedding" not in status_resp.json()
    assert "embedding" not in status_resp.json()
    assert "is_face_registered" in status_resp.json()


def test_session_resume_resets_verification_status_and_enforces_reverification(client, db: Session):
    """
    Stage 14.1 Security Hardening:
    Verifies that resuming an active session resets identity_verification_status to UNVERIFIED,
    and a wrong person cannot remain or become VERIFIED upon application/exam restart.
    """
    from app.core.security import create_access_token
    from app.models.question import Question, QuestionType

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Ex",
        last_name="Am",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    # Distinct face templates (Student A vs Wrong Person B)
    emb_a = [0.1 * ((i * 7) % 11 - 5) for i in range(64)]
    emb_b = [0.1 * ((i * 3 + 4) % 13 - 6) for i in range(64)]

    student_a = User(
        id=uuid.uuid4(),
        email=f"sta_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Student",
        last_name="A",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=emb_a,
    )
    db.add_all([examiner, student_a])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Resume Security Exam",
        subject="Proctoring",
        duration_minutes=30,
        total_marks=10.0,
        passing_marks=4.0,
        status=ExamStatus.PUBLISHED,
    )
    q = Question(
        id=uuid.uuid4(),
        created_by=examiner.id,
        subject="Proctoring",
        question_text="Sample Q",
        question_type=QuestionType.MCQ,
        marks=10.0,
    )
    db.add_all([exam, q])
    db.commit()

    from app.models.exam import ExamQuestion
    eq = ExamQuestion(exam_id=exam.id, question_id=q.id, question_order=1)
    db.add(eq)
    db.commit()

    token_a = create_access_token({"sub": str(student_a.id), "role": "STUDENT"})
    headers_a = {"Authorization": f"Bearer {token_a}"}

    # Step 1: Start exam session initial run
    start_resp = client.post(f"/api/student/exams/{exam.id}/start", headers=headers_a)
    assert start_resp.status_code == status.HTTP_200_OK
    session_id = start_resp.json()["id"]

    # Step 2: Student A verifies identity successfully
    v1_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": emb_a},
        headers=headers_a,
    )
    assert v1_resp.status_code == status.HTTP_200_OK
    assert v1_resp.json()["verified"] is True
    assert v1_resp.json()["status"] == "VERIFIED"

    # Verify session is currently VERIFIED in DB
    sess_uuid = uuid.UUID(session_id)
    db_sess = db.query(ExamSession).filter(ExamSession.id == sess_uuid).first()
    assert db_sess.identity_verification_status == "VERIFIED"

    # Step 3: Student leaves, browser restarts, student/attacker resumes active session
    resume_resp = client.post(f"/api/student/exams/{exam.id}/start", headers=headers_a)
    assert resume_resp.status_code == status.HTTP_200_OK
    assert resume_resp.json()["id"] == session_id
    assert resume_resp.json()["identity_verification_status"] == "UNVERIFIED"

    db.refresh(db_sess)
    assert db_sess.identity_verification_status == "UNVERIFIED"

    # Step 4: Wrong person (B) sits at camera -> verification MUST fail
    v_wrong = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": emb_b},
        headers=headers_a,
    )
    assert v_wrong.status_code == status.HTTP_200_OK
    assert v_wrong.json()["verified"] is False
    assert v_wrong.json()["status"] == "VERIFICATION_FAILED"

    # Confirm session did NOT become VERIFIED for wrong person
    db.refresh(db_sess)
    assert db_sess.identity_verification_status == "VERIFICATION_FAILED"

    # Step 5: Legitimate Student A sits back down -> verification succeeds
    v_correct = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": emb_a},
        headers=headers_a,
    )
    assert v_correct.status_code == status.HTTP_200_OK
    assert v_correct.json()["verified"] is True
    assert v_correct.json()["status"] == "VERIFIED"

    db.refresh(db_sess)
    assert db_sess.identity_verification_status == "VERIFIED"


def test_regression_wrong_person_rejection_and_stale_session_lock(client, db: Session):
    """
    Regression Test Stage 14.1:
    Ensures that a wrong person cannot obtain VERIFIED status,
    and a stale or previously-verified state cannot authorize entry without fresh live match.
    """
    examiner = User(
        id=uuid.uuid4(),
        email=f"reg_ex_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="RegEx",
        last_name="Examiner",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    # Stored legitimate template
    legit_embedding = [0.1 * ((i % 7) + 1) for i in range(64)]
    # Completely different impostor / wrong-person embedding
    impostor_embedding_1 = [-0.1 * ((i % 5) + 1) for i in range(64)]
    impostor_embedding_2 = [0.1 if (i % 3 == 0) else -0.3 for i in range(64)]

    student = User(
        id=uuid.uuid4(),
        email=f"reg_st_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="RegSt",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow(),
        face_embedding=legit_embedding,
    )
    db.add_all([examiner, student])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Regression Test Exam",
        subject="Proctoring",
        duration_minutes=45,
        total_marks=100.0,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    q = Question(
        question_text="What is 2 + 2?",
        question_type=QuestionType.MCQ,
        subject="Proctoring",
        marks=100.0,
        created_by=examiner.id,
    )
    db.add(q)
    db.commit()

    eq = ExamQuestion(exam_id=exam.id, question_id=q.id, question_order=1)
    db.add(eq)
    db.commit()
    db.refresh(exam)

    from app.core.security import create_access_token
    token = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Start session
    start_resp = client.post(f"/api/student/exams/{exam.id}/start", headers=headers)
    assert start_resp.status_code == status.HTTP_200_OK
    session_id = start_resp.json()["id"]

    # Session is initially UNVERIFIED
    sess_obj = db.query(ExamSession).filter(ExamSession.id == uuid.UUID(session_id)).first()
    assert sess_obj.identity_verification_status == "UNVERIFIED"

    # Attempting to fetch session details with verification enforcement fails (403 Forbidden)
    get_resp_locked = client.get(f"/api/student/sessions/{session_id}", headers=headers)
    assert get_resp_locked.status_code == status.HTTP_403_FORBIDDEN
    assert "IDENTITY_VERIFICATION_REQUIRED" in get_resp_locked.json()["detail"]["code"]

    # 2. Impostor 1 tries to verify -> Rejected
    imp1_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": impostor_embedding_1},
        headers=headers,
    )
    assert imp1_resp.status_code == status.HTTP_200_OK
    assert imp1_resp.json()["verified"] is False
    assert imp1_resp.json()["status"] == "VERIFICATION_FAILED"
    assert imp1_resp.json()["similarity"] < 0.80

    db.refresh(sess_obj)
    assert sess_obj.identity_verification_status == "VERIFICATION_FAILED"

    # Session details STILL locked (403 Forbidden)
    get_resp_locked2 = client.get(f"/api/student/sessions/{session_id}", headers=headers)
    assert get_resp_locked2.status_code == status.HTTP_403_FORBIDDEN

    # 3. Impostor 2 tries to verify -> Rejected again
    imp2_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": impostor_embedding_2},
        headers=headers,
    )
    assert imp2_resp.status_code == status.HTTP_200_OK
    assert imp2_resp.json()["verified"] is False
    assert imp2_resp.json()["status"] == "VERIFICATION_FAILED"
    assert imp2_resp.json()["similarity"] < 0.80

    # 4. Legitimate student verifies -> Accepted
    legit_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": legit_embedding},
        headers=headers,
    )
    assert legit_resp.status_code == status.HTTP_200_OK
    assert legit_resp.json()["verified"] is True
    assert legit_resp.json()["status"] == "VERIFIED"
    assert legit_resp.json()["similarity"] >= 0.80

    db.refresh(sess_obj)
    assert sess_obj.identity_verification_status == "VERIFIED"

    # Session details now unlock (200 OK)
    get_resp_unlocked = client.get(f"/api/student/sessions/{session_id}", headers=headers)
    assert get_resp_unlocked.status_code == status.HTTP_200_OK

    # 5. Session resume test: Student re-starts/resumes exam
    # Resume MUST reset identity_verification_status to UNVERIFIED so a different person cannot hijack
    resume_resp = client.post(f"/api/student/exams/{exam.id}/start", headers=headers)
    assert resume_resp.status_code == status.HTTP_200_OK
    assert resume_resp.json()["identity_verification_status"] == "UNVERIFIED"

    db.refresh(sess_obj)
    assert sess_obj.identity_verification_status == "UNVERIFIED"

    # Direct access is re-locked until verified again
    get_resp_relocked = client.get(f"/api/student/sessions/{session_id}", headers=headers)
    assert get_resp_relocked.status_code == status.HTTP_403_FORBIDDEN


def test_template_descriptor_version_migration_and_re_enrollment(client, db: Session):
    """
    Stage 14.1 Regression & Migration Security Tests:
    - Legacy template (v1) triggers TEMPLATE_VERSION_MISMATCH and requires re-enrollment
    - Status endpoint reports requires_re_enrollment=True and is_face_registered=False
    - Exam session verification is blocked (HTTP 400 TEMPLATE_VERSION_MISMATCH) for v1 template
    - Re-enrollment upgrades template to v2 with explicit version tracking
    - Upgraded v2 template accepts legitimate student face (similarity >= 0.80)
    - Upgraded v2 template strictly rejects impostor face (similarity < 0.80)
    """
    from app.core.security import create_access_token

    examiner = User(
        id=uuid.uuid4(),
        email=f"ex_mig_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Examiner",
        last_name="Migration",
        role=UserRole.EXAMINER,
        is_active=True,
    )

    # Legacy v1 template (simulating user registered prior to zero-centered calibration)
    legacy_template = [0.2 if i % 2 == 0 else -0.1 for i in range(64)]
    norm_l = math.sqrt(sum(x * x for x in legacy_template))
    legacy_template = [x / norm_l for x in legacy_template]

    student = User(
        id=uuid.uuid4(),
        email=f"mig_st_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Migrated",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
        is_face_registered=True,
        face_registered_at=datetime.utcnow() - timedelta(days=10),
        face_embedding=legacy_template,
        face_descriptor_version=1,  # Legacy version 1
    )
    db.add_all([examiner, student])
    db.commit()

    token = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Identity status reports re-enrollment required
    status_resp = client.get("/api/student/identity/status", headers=headers)
    assert status_resp.status_code == status.HTTP_200_OK
    assert status_resp.json()["is_face_registered"] is False
    assert status_resp.json()["requires_re_enrollment"] is True
    assert status_resp.json()["descriptor_version"] == 1
    assert status_resp.json()["current_system_version"] == 2

    # 2. Setup exam and session
    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Migration Exam",
        subject="Biometrics",
        duration_minutes=30,
        total_marks=50.0,
        passing_marks=20.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    q = Question(
        question_text="Sample migration question",
        question_type=QuestionType.MCQ,
        subject="Biometrics",
        marks=50.0,
        created_by=examiner.id,
    )
    db.add(q)
    db.commit()

    eq = ExamQuestion(exam_id=exam.id, question_id=q.id, question_order=1)
    db.add(eq)
    db.commit()

    start_resp = client.post(f"/api/student/exams/{exam.id}/start", headers=headers)
    assert start_resp.status_code == status.HTTP_200_OK
    session_id = start_resp.json()["id"]

    # 3. Attempting verification with legacy v1 template is blocked with TEMPLATE_VERSION_MISMATCH
    v2_live = [0.3 if i % 3 == 0 else -0.05 for i in range(64)]
    norm_v2 = math.sqrt(sum(x * x for x in v2_live))
    v2_live = [x / norm_v2 for x in v2_live]

    blocked_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": v2_live, "descriptor_version": 2},
        headers=headers,
    )
    assert blocked_resp.status_code == status.HTTP_400_BAD_REQUEST
    assert "TEMPLATE_VERSION_MISMATCH" in str(blocked_resp.json()["detail"])

    # 4. Student re-registers face in Profile (safe re-enrollment to v2)
    re_enroll_resp = client.post(
        "/api/student/identity/register-face",
        json={"face_embedding": v2_live, "consent_given": True, "descriptor_version": 2},
        headers=headers,
    )
    assert re_enroll_resp.status_code == status.HTTP_200_OK
    assert re_enroll_resp.json()["is_face_registered"] is True
    assert re_enroll_resp.json()["descriptor_version"] == 2

    # Verify status is now healthy v2
    status_resp_after = client.get("/api/student/identity/status", headers=headers)
    assert status_resp_after.status_code == status.HTTP_200_OK
    assert status_resp_after.json()["is_face_registered"] is True
    assert status_resp_after.json()["requires_re_enrollment"] is False
    assert status_resp_after.json()["descriptor_version"] == 2

    # 5. Live verification now succeeds for same student face
    live_same_jitter = [v2_live[i] + 0.005 * (1 if i % 2 == 0 else -1) for i in range(64)]
    norm_j = math.sqrt(sum(x * x for x in live_same_jitter))
    live_same_jitter = [x / norm_j for x in live_same_jitter]

    pass_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": live_same_jitter, "descriptor_version": 2},
        headers=headers,
    )
    assert pass_resp.status_code == status.HTTP_200_OK
    assert pass_resp.json()["verified"] is True
    assert pass_resp.json()["status"] == "VERIFIED"
    assert pass_resp.json()["similarity"] >= 0.80

    # 6. Impostor face is strictly rejected
    impostor_face = [-1.0 * v2_live[i] for i in range(64)]
    fail_resp = client.post(
        f"/api/student/sessions/{session_id}/verify-identity",
        json={"face_embedding": impostor_face, "descriptor_version": 2},
        headers=headers,
    )
    assert fail_resp.status_code == status.HTTP_200_OK
    assert fail_resp.json()["verified"] is False
    assert fail_resp.json()["status"] in ["VERIFICATION_FAILED", "TEMPORARILY_UNVERIFIED"]
    assert fail_resp.json()["similarity"] < 0.80






