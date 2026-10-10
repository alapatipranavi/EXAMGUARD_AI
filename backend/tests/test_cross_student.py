import uuid
import pytest
from datetime import datetime, timezone
from fastapi import status
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.exam import Exam, ExamQuestion, ExamStatus
from app.models.question import Question, QuestionType, QuestionOption
from app.models.exam_session import ExamSession, SessionStatus
from app.models.answer import StudentAnswer, AnswerSelectedOption
from app.models.integrity import CrossStudentAnalysis
from app.services.cross_student_service import cross_student_service


def test_text_normalization_and_jaccard_similarity():
    # Test 8: Text normalization works
    t1 = "  The quick BROWN fox... jumps over lazy DOG!! "
    t2 = "the quick brown fox jumps over lazy dog"
    assert cross_student_service.normalize_text(t1) == "the quick brown fox jumps over lazy dog"
    assert cross_student_service.calculate_text_jaccard_similarity(t1, t2) == 1.0

    t3 = "A completely different answer about computer science"
    sim_diff = cross_student_service.calculate_text_jaccard_similarity(t1, t3)
    assert sim_diff < 0.20

    # Test 9: Empty text does not create fake similarity
    assert cross_student_service.calculate_text_jaccard_similarity("", t1) == 0.0


def test_cross_student_analysis_flow(client, db: Session):
    # Setup Examiner, Exam, Questions
    examiner1 = User(
        id=uuid.uuid4(),
        email=f"ex1_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Examiner",
        last_name="One",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    examiner2 = User(
        id=uuid.uuid4(),
        email=f"ex2_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Examiner",
        last_name="Two",
        role=UserRole.EXAMINER,
        is_active=True,
    )
    student_a = User(
        id=uuid.uuid4(),
        email=f"stud_a_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Student",
        last_name="A",
        role=UserRole.STUDENT,
        is_active=True,
    )
    student_b = User(
        id=uuid.uuid4(),
        email=f"stud_b_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Student",
        last_name="B",
        role=UserRole.STUDENT,
        is_active=True,
    )
    student_c = User(
        id=uuid.uuid4(),
        email=f"stud_c_{uuid.uuid4().hex[:6]}@examguard.test",
        password_hash="pwd",
        first_name="Student",
        last_name="C",
        role=UserRole.STUDENT,
        is_active=True,
    )
    db.add_all([examiner1, examiner2, student_a, student_b, student_c])
    db.commit()

    exam = Exam(
        id=uuid.uuid4(),
        created_by=examiner1.id,
        title="Cross Student Test Exam",
        subject="Computer Science",
        duration_minutes=60,
        total_marks=100.0,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
    )
    db.add(exam)
    db.commit()

    # Question 1: MCQ with Option 1 (Correct), Option 2 (Incorrect)
    q1 = Question(
        id=uuid.uuid4(),
        created_by=examiner1.id,
        question_text="What is 2+2?",
        subject="CS",
        question_type=QuestionType.MCQ,
        marks=10.0,
    )
    opt1_correct = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="4", is_correct=True, option_order=1)
    opt1_wrong = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="5", is_correct=False, option_order=2)
    q1.options = [opt1_correct, opt1_wrong]

    # Question 2: MCQ where Student A & B choose SAME INCORRECT option
    q2 = Question(
        id=uuid.uuid4(),
        created_by=examiner1.id,
        question_text="What is speed of light?",
        subject="CS",
        question_type=QuestionType.MCQ,
        marks=10.0,
    )
    opt2_correct = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="3x10^8 m/s", is_correct=True, option_order=1)
    opt2_wrong = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="150 m/s", is_correct=False, option_order=2)
    q2.options = [opt2_correct, opt2_wrong]

    db.add_all([q1, q2])
    db.commit()

    eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, question_order=1, marks_override=10.0)
    eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, question_order=2, marks_override=10.0)
    db.add_all([eq1, eq2])
    db.commit()

    # Create Session A (Submitted)
    sess_a = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_a.id,
        status=SessionStatus.SUBMITTED,
        started_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
        session_metadata={
            "question_durations": {str(q1.id): 30.0, str(q2.id): 45.0},
            "answer_changes": {str(q1.id): ["opt1_wrong", "opt1_correct"]},
            "navigation_order": [str(q1.id), str(q2.id)],
        }
    )
    # Create Session B (Submitted - High Similarity to A: same wrong answer on Q2)
    sess_b = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_b.id,
        status=SessionStatus.SUBMITTED,
        started_at=datetime.now(timezone.utc),
        submitted_at=datetime.now(timezone.utc),
        session_metadata={
            "question_durations": {str(q1.id): 32.0, str(q2.id): 44.0},
            "answer_changes": {str(q1.id): ["opt1_wrong", "opt1_correct"]},
            "navigation_order": [str(q1.id), str(q2.id)],
        }
    )
    # Create Session C (Ineligible active IN_PROGRESS session)
    sess_c = ExamSession(
        id=uuid.uuid4(),
        exam_id=exam.id,
        student_id=student_c.id,
        status=SessionStatus.IN_PROGRESS,
        started_at=datetime.now(timezone.utc),
    )
    db.add_all([sess_a, sess_b, sess_c])
    db.commit()

    # Session A Answers: Q1 -> Correct, Q2 -> Wrong
    ans_a1 = StudentAnswer(session_id=sess_a.id, question_id=q1.id)
    ans_a1.selected_options = [AnswerSelectedOption(option_id=opt1_correct.id)]

    ans_a2 = StudentAnswer(session_id=sess_a.id, question_id=q2.id)
    ans_a2.selected_options = [AnswerSelectedOption(option_id=opt2_wrong.id)]

    # Session B Answers: Q1 -> Correct, Q2 -> Same Wrong as A!
    ans_b1 = StudentAnswer(session_id=sess_b.id, question_id=q1.id)
    ans_b1.selected_options = [AnswerSelectedOption(option_id=opt1_correct.id)]

    ans_b2 = StudentAnswer(session_id=sess_b.id, question_id=q2.id)
    ans_b2.selected_options = [AnswerSelectedOption(option_id=opt2_wrong.id)]

    db.add_all([ans_a1, ans_a2, ans_b1, ans_b2])
    db.commit()

    from app.core.security import create_access_token
    token_ex1 = create_access_token({"sub": str(examiner1.id), "role": "EXAMINER"})
    token_ex2 = create_access_token({"sub": str(examiner2.id), "role": "EXAMINER"})
    token_st = create_access_token({"sub": str(student_a.id), "role": "STUDENT"})

    headers_ex1 = {"Authorization": f"Bearer {token_ex1}"}
    headers_ex2 = {"Authorization": f"Bearer {token_ex2}"}
    headers_st = {"Authorization": f"Bearer {token_st}"}

    # Test 3: Student gets 403 Forbidden
    st_resp = client.get(f"/api/exams/{exam.id}/cross-student-analysis", headers=headers_st)
    assert st_resp.status_code == status.HTTP_403_FORBIDDEN

    # Test 2: Examiner cannot access another Examiner's exam
    ex2_resp = client.get(f"/api/exams/{exam.id}/cross-student-analysis", headers=headers_ex2)
    assert ex2_resp.status_code == status.HTTP_403_FORBIDDEN

    # Test 1 & 14 & 16: Examiner runs analysis (Idempotent execution & pair order normalization)
    run_resp = client.post(f"/api/exams/{exam.id}/cross-student-analysis/run", headers=headers_ex1)
    assert run_resp.status_code == status.HTTP_200_OK
    assert run_resp.json()["total_pairs_count"] == 1
    assert run_resp.json()["analyzed_students_count"] == 2  # Session C excluded (ineligible IN_PROGRESS)

    # Re-run analysis to verify idempotency (Test 16)
    run_resp2 = client.post(f"/api/exams/{exam.id}/cross-student-analysis/run", headers=headers_ex1)
    assert run_resp2.status_code == status.HTTP_200_OK
    assert run_resp2.json()["total_pairs_count"] == 1

    # Fetch summary (Test 1 & 5 & 6 & 10 & 11 & 12 & 13)
    sum_resp = client.get(f"/api/exams/{exam.id}/cross-student-analysis", headers=headers_ex1)
    assert sum_resp.status_code == status.HTTP_200_OK
    summary_data = sum_resp.json()

    assert summary_data["analyzed_students_count"] == 2
    assert summary_data["total_pairs_count"] == 1
    assert len(summary_data["items"]) == 1

    pair_item = summary_data["items"][0]
    assert pair_item["similarity_score"] >= 70.0  # High similarity due to identical answers, timing & sequence
    assert pair_item["same_correct_answers_count"] == 1
    assert pair_item["same_incorrect_answers_count"] == 1  # Test 6: Same wrong answer detected
    assert pair_item["category"] == "HIGH_SIMILARITY"

    # Test 18: No self-comparison occurs
    assert pair_item["source_session_id"] != pair_item["target_session_id"]

    # Test Pair Detail Endpoint
    detail_resp = client.get(
        f"/api/exams/{exam.id}/cross-student-analysis/{pair_item['id']}",
        headers=headers_ex1
    )
    assert detail_resp.status_code == status.HTTP_200_OK
    detail_data = detail_resp.json()
    assert len(detail_data["common_wrong_answers"]) == 1
    assert detail_data["common_wrong_answers"][0]["student_a_option"] == "150 m/s"
    assert len(detail_data["evidence_items"]) > 0

    # Test 20: No raw biometric/media data returned
    assert "face_embedding" not in str(detail_data)
    assert "webcam" not in str(detail_data)

    # Test 4: Fewer than 2 eligible sessions returns clean empty state
    # Delete session B
    db.delete(sess_b)
    db.commit()

    run_empty_resp = client.post(f"/api/exams/{exam.id}/cross-student-analysis/run", headers=headers_ex1)
    assert run_empty_resp.status_code == status.HTTP_200_OK
    assert run_empty_resp.json()["message"] == "Not enough student attempts for cross-student analysis."
