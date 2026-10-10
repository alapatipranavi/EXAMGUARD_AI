import uuid
import pytest
from datetime import datetime, timedelta
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamStatus
from app.models.exam_session import ExamSession, SessionStatus
from app.models.proctoring import ProctoringEvent, ProctoringEventType, EventSeverity
from app.models.integrity import IntegrityAnalysis, AnalysisStatus
from app.services.integrity_service import integrity_service, BASELINE_INTEGRITY_SCORE


@pytest.fixture
def test_setup(db: Session):
    """Fixture creating Examiner, Student, Exam, and ExamSession for integrity tests."""
    examiner = User(
        id=uuid.uuid4(),
        email=f"examiner_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="hashed_pwd",
        first_name="Integrity",
        last_name="Examiner",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    other_examiner = User(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="hashed_pwd",
        first_name="Other",
        last_name="Examiner",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    student = User(
        id=uuid.uuid4(),
        email=f"student_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="hashed_pwd",
        first_name="Alice",
        last_name="Student",
        role=UserRole.STUDENT,
        is_active=True,
    )
    admin = User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="hashed_pwd",
        first_name="Admin",
        last_name="User",
        role=UserRole.ADMIN,
        is_active=True,
    )
    db.add_all([examiner, other_examiner, student, admin])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner.id,
        title="Integrity Test Exam",
        subject="Computer Science",
        duration_minutes=60,
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
        status=SessionStatus.SUBMITTED,
        started_at=datetime.utcnow() - timedelta(minutes=45),
        submitted_at=datetime.utcnow(),
    )
    db.add(session)
    db.commit()

    return {
        "examiner": examiner,
        "other_examiner": other_examiner,
        "student": student,
        "admin": admin,
        "exam": exam,
        "session": session,
    }


class TestIntegrityService:
    def test_no_events_neutral_integrity(self, db: Session, test_setup: dict):
        """Scenario 1: No events -> 100 score, LOW risk, default observation."""
        session = test_setup["session"]
        analysis = integrity_service.analyze_or_update_session_integrity(db, session)

        assert analysis.integrity_score == 100.0
        sig = analysis.contributing_signals
        assert sig["risk_level"] == "LOW"
        assert "Normal session activity" in sig["recommendation"]
        assert len(sig["evidence"]) == 1
        assert sig["evidence"][0]["signal_type"] == "NO_SIGNALS"

    def test_small_number_tab_switches(self, db: Session, test_setup: dict):
        """Scenario 2: Small number of tab switches (1 event) -> minor deduction."""
        session = test_setup["session"]
        ev = ProctoringEvent(
            id=uuid.uuid4(),
            session_id=session.id,
            event_type=ProctoringEventType.TAB_HIDDEN,
            severity=EventSeverity.MEDIUM,
            occurred_at=datetime.utcnow() - timedelta(minutes=30),
        )
        db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        assert analysis.integrity_score == 95.0  # 100 - 5.0
        assert analysis.contributing_signals["risk_level"] == "LOW"

    def test_repeated_tab_switches(self, db: Session, test_setup: dict):
        """Scenario 3: Repeated tab switches (5 events) -> capped deduction (-30.0)."""
        session = test_setup["session"]
        for i in range(5):
            ev = ProctoringEvent(
                id=uuid.uuid4(),
                session_id=session.id,
                event_type=ProctoringEventType.TAB_HIDDEN,
                severity=EventSeverity.WARNING,
                occurred_at=datetime.utcnow() - timedelta(minutes=40 - i * 5),
            )
            db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        assert analysis.integrity_score == 75.0  # 100 - 25.0 (5 * 5)
        assert analysis.contributing_signals["risk_level"] == "MODERATE"

    def test_face_not_detected_events(self, db: Session, test_setup: dict):
        """Scenario 4: Face-not-detected events -> score deduction."""
        session = test_setup["session"]
        for i in range(2):
            ev = ProctoringEvent(
                id=uuid.uuid4(),
                session_id=session.id,
                event_type=ProctoringEventType.FACE_NOT_DETECTED,
                severity=EventSeverity.HIGH,
                occurred_at=datetime.utcnow() - timedelta(minutes=20 - i),
            )
            db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        assert analysis.integrity_score == 88.0  # 100 - 12.0 (2 * 6)
        assert analysis.contributing_signals["risk_level"] == "LOW"

    def test_multiple_faces_events(self, db: Session, test_setup: dict):
        """Scenario 5: Multiple-face events -> significant score deduction."""
        session = test_setup["session"]
        ev = ProctoringEvent(
            id=uuid.uuid4(),
            session_id=session.id,
            event_type=ProctoringEventType.MULTIPLE_FACES_DETECTED,
            severity=EventSeverity.HIGH,
            occurred_at=datetime.utcnow() - timedelta(minutes=15),
        )
        db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        assert analysis.integrity_score == 90.0  # 100 - 10.0
        assert len(analysis.contributing_signals["evidence"]) == 1

    def test_fullscreen_events(self, db: Session, test_setup: dict):
        """Scenario 6: Fullscreen exit events -> deduction."""
        session = test_setup["session"]
        ev = ProctoringEvent(
            id=uuid.uuid4(),
            session_id=session.id,
            event_type=ProctoringEventType.FULLSCREEN_EXITED,
            severity=EventSeverity.WARNING,
            occurred_at=datetime.utcnow() - timedelta(minutes=25),
        )
        db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        assert analysis.integrity_score == 93.0  # 100 - 7.0

    def test_combined_signals_and_score_bounds(self, db: Session, test_setup: dict):
        """Scenario 7 & 8: Combined heavy signals -> HIGH risk, score lower bound 0.0."""
        session = test_setup["session"]
        events = [
            ProctoringEventType.TAB_HIDDEN,
            ProctoringEventType.TAB_HIDDEN,
            ProctoringEventType.TAB_HIDDEN,
            ProctoringEventType.FULLSCREEN_EXITED,
            ProctoringEventType.FACE_NOT_DETECTED,
            ProctoringEventType.MULTIPLE_FACES_DETECTED,
            ProctoringEventType.CAMERA_DISCONNECTED,
            ProctoringEventType.TAB_SWITCH_LIMIT_EXCEEDED,
        ]
        for idx, etype in enumerate(events):
            ev = ProctoringEvent(
                id=uuid.uuid4(),
                session_id=session.id,
                event_type=etype,
                severity=EventSeverity.HIGH,
                occurred_at=datetime.utcnow() - timedelta(minutes=35 - idx),
            )
            db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        # Expected deductions: 15 (tab) + 7 (fullscreen) + 6 (face) + 10 (multi) + 12 (cam) + 20 (limit) = 70. Score = 30.0
        assert analysis.integrity_score == 30.0
        assert analysis.contributing_signals["risk_level"] == "HIGH"
        assert "Examiner review recommended" in analysis.contributing_signals["recommendation"]

    def test_risk_level_thresholds(self, db: Session):
        """Scenario 9: Centralized risk level thresholds logic."""
        assert integrity_service.determine_risk_level(95.0) == "LOW"
        assert integrity_service.determine_risk_level(85.0) == "LOW"
        assert integrity_service.determine_risk_level(84.9) == "MODERATE"
        assert integrity_service.determine_risk_level(65.0) == "MODERATE"
        assert integrity_service.determine_risk_level(64.9) == "HIGH"
        assert integrity_service.determine_risk_level(0.0) == "HIGH"

    def test_evidence_generation(self, db: Session, test_setup: dict):
        """Scenario 10: Structured evidence list with observations and deductions."""
        session = test_setup["session"]
        ev = ProctoringEvent(
            id=uuid.uuid4(),
            session_id=session.id,
            event_type=ProctoringEventType.TAB_HIDDEN,
            severity=EventSeverity.WARNING,
            occurred_at=datetime.utcnow() - timedelta(minutes=10),
        )
        db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        ev_list = analysis.contributing_signals["evidence"]
        assert len(ev_list) == 1
        assert ev_list[0]["signal_type"] == "TAB_SWITCH"
        assert ev_list[0]["count"] == 1
        assert ev_list[0]["score_deduction"] == 5.0

    def test_timeline_ordering(self, db: Session, test_setup: dict):
        """Scenario 11: Chronological event ordering in timeline."""
        session = test_setup["session"]
        t1 = datetime.utcnow() - timedelta(minutes=30)
        t2 = datetime.utcnow() - timedelta(minutes=15)

        ev1 = ProctoringEvent(
            id=uuid.uuid4(),
            session_id=session.id,
            event_type=ProctoringEventType.FULLSCREEN_EXITED,
            occurred_at=t2,
        )
        ev2 = ProctoringEvent(
            id=uuid.uuid4(),
            session_id=session.id,
            event_type=ProctoringEventType.TAB_HIDDEN,
            occurred_at=t1,
        )
        db.add_all([ev1, ev2])
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        timeline = analysis.contributing_signals["timeline"]
        # timeline items should be in chronological order
        timestamps = [item["timestamp"] for item in timeline if item["timestamp"]]
        assert timestamps == sorted(timestamps)

    def test_idempotent_recalculation(self, db: Session, test_setup: dict):
        """Scenario 12: Calling analysis multiple times updates existing record without duplicate."""
        session = test_setup["session"]
        a1 = integrity_service.analyze_or_update_session_integrity(db, session)
        a2 = integrity_service.analyze_or_update_session_integrity(db, session)

        assert a1.id == a2.id
        count = db.query(IntegrityAnalysis).filter(IntegrityAnalysis.session_id == session.id).count()
        assert count == 1

    def test_behavioural_fingerprint_rapid_answer_changes(self, db: Session, test_setup: dict):
        """Stage 9.3: Rapid answer changes detection & fingerprint generation."""
        session = test_setup["session"]
        q_id = str(uuid.uuid4())
        now = datetime.utcnow()

        # Add 3 answer change events within 2 seconds
        for i in range(3):
            ev = ProctoringEvent(
                id=uuid.uuid4(),
                session_id=session.id,
                event_type=ProctoringEventType.ANSWER_CHANGED,
                severity=EventSeverity.LOW,
                occurred_at=now + timedelta(seconds=i),
                event_metadata={"question_id": q_id},
            )
            db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        sig = analysis.contributing_signals
        bs = sig.get("behavioural_summary")
        assert bs is not None
        assert bs["answer_change_count"] == 3
        assert bs["rapid_change_count"] >= 1

        ev_types = [e["signal_type"] for e in sig["evidence"]]
        assert "RAPID_ANSWER_CHANGES" in ev_types

    def test_behavioural_navigation_and_unusual_timing(self, db: Session, test_setup: dict):
        """Stage 9.3: Navigation anomaly & unusual timing detection."""
        session = test_setup["session"]
        q1, q2 = str(uuid.uuid4()), str(uuid.uuid4())
        now = datetime.utcnow()

        # Add 4 rapid question navigations (< 3s apart) with backtracking
        for i in range(5):
            ev = ProctoringEvent(
                id=uuid.uuid4(),
                session_id=session.id,
                event_type=ProctoringEventType.QUESTION_NAVIGATION,
                severity=EventSeverity.LOW,
                occurred_at=now + timedelta(seconds=i * 2),
                event_metadata={"from_question_id": q1 if i % 2 == 0 else q2, "to_question_id": q2 if i % 2 == 0 else q1},
            )
            db.add(ev)
        db.commit()

        analysis = integrity_service.analyze_or_update_session_integrity(db, session)
        sig = analysis.contributing_signals
        bs = sig.get("behavioural_summary")
        assert bs is not None
        assert bs["navigation_count"] == 5
        assert bs["backtrack_count"] >= 2


class TestIntegrityAPIEndpoints:
    def test_examiner_access_own_exam_integrity_summary(self, client, test_setup: dict):
        """Scenario 13a: Examiner can access own exam integrity summary."""
        examiner = test_setup["examiner"]
        exam = test_setup["exam"]

        from app.core.security import create_access_token
        token = create_access_token(data={"sub": str(examiner.id), "email": examiner.email, "role": examiner.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/exams/{exam.id}/integrity", headers=headers)
        assert resp.status_code == status.HTTP_200_OK
        data = resp.json()
        assert data["exam_id"] == str(exam.id)
        assert data["total_sessions"] == 1
        assert len(data["items"]) == 1

    def test_examiner_cannot_access_other_examiner_integrity(self, client, test_setup: dict):
        """Scenario 13b: Examiner cannot access another examiner's exam integrity (403)."""
        other_examiner = test_setup["other_examiner"]
        exam = test_setup["exam"]

        from app.core.security import create_access_token
        token = create_access_token(data={"sub": str(other_examiner.id), "email": other_examiner.email, "role": other_examiner.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        resp = client.get(f"/api/exams/{exam.id}/integrity", headers=headers)
        assert resp.status_code == status.HTTP_403_FORBIDDEN

    def test_student_cannot_access_integrity(self, client, test_setup: dict):
        """Scenario 14: Student is forbidden from integrity APIs (403)."""
        student = test_setup["student"]
        exam = test_setup["exam"]
        session = test_setup["session"]

        from app.core.security import create_access_token
        token = create_access_token(data={"sub": str(student.id), "email": student.email, "role": student.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        resp1 = client.get(f"/api/exams/{exam.id}/integrity", headers=headers)
        assert resp1.status_code == status.HTTP_403_FORBIDDEN

        resp2 = client.get(f"/api/exams/{exam.id}/sessions/{session.id}/integrity", headers=headers)
        assert resp2.status_code == status.HTTP_403_FORBIDDEN

    def test_admin_can_access_integrity(self, client, test_setup: dict):
        """Scenario 15: Admin can access integrity APIs across exams."""
        admin = test_setup["admin"]
        exam = test_setup["exam"]
        session = test_setup["session"]

        from app.core.security import create_access_token
        token = create_access_token(data={"sub": str(admin.id), "email": admin.email, "role": admin.role.value})
        headers = {"Authorization": f"Bearer {token}"}

        resp1 = client.get(f"/api/exams/{exam.id}/integrity", headers=headers)
        assert resp1.status_code == status.HTTP_200_OK

        resp2 = client.get(f"/api/exams/{exam.id}/sessions/{session.id}/integrity", headers=headers)
        assert resp2.status_code == status.HTTP_200_OK
        detail = resp2.json()
        assert detail["session_id"] == str(session.id)
        assert "evidence" in detail
        assert "timeline" in detail
