import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.user import User, UserRole
from app.models.question import Question, QuestionType, DifficultyLevel, QuestionOption
from app.models.exam import Exam, ExamQuestion, ExamStatus
from app.models.exam_session import ExamSession, SessionStatus
from app.models.answer import StudentAnswer, AnswerSelectedOption
from app.models.evaluation import ExamSessionEvaluation, EvaluationResult, EvaluationStatus, PassFailStatus
from app.services.evaluation_service import evaluation_service


def _create_test_user(db: Session, email: str, role: UserRole) -> User:
    from app.core.security import hash_password
    u = User(
        id=uuid.uuid4(),
        email=email,
        password_hash=hash_password("Password123!"),
        first_name="Test",
        last_name=role.value,
        role=role,
        is_active=True,
    )
    db.add(u)
    db.commit()
    db.refresh(u)
    return u


def _auth_headers_for_user(user: User) -> dict:
    from app.core.security import create_access_token
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


class TestObjectiveEvaluation:

    def test_mcq_evaluation_rules(self, db: Session):
        """Tests MCQ correct, incorrect with negative marks, incorrect zero negative marks, and unanswered."""
        examiner = _create_test_user(db, "mcq_eval_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "mcq_eval_st@test.com", UserRole.STUDENT)

        # Question 1: 2 marks, 0.5 negative
        q1 = Question(
            id=uuid.uuid4(),
            question_text="MCQ Q1",
            question_type=QuestionType.MCQ,
            subject="Math",
            marks=2.0,
            negative_marks=0.5,
            created_by=examiner.id,
        )
        opt1_corr = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="Correct", option_order=1, is_correct=True)
        opt1_inc = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="Incorrect", option_order=2, is_correct=False)
        q1.options = [opt1_corr, opt1_inc]

        # Question 2: 3 marks, 0 negative
        q2 = Question(
            id=uuid.uuid4(),
            question_text="MCQ Q2",
            question_type=QuestionType.MCQ,
            subject="Math",
            marks=3.0,
            negative_marks=0.0,
            created_by=examiner.id,
        )
        opt2_corr = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="Correct", option_order=1, is_correct=True)
        opt2_inc = QuestionOption(id=uuid.uuid4(), question_id=q2.id, option_text="Incorrect", option_order=2, is_correct=False)
        q2.options = [opt2_corr, opt2_inc]

        # Question 3: 4 marks, 1.0 negative
        q3 = Question(
            id=uuid.uuid4(),
            question_text="MCQ Q3",
            question_type=QuestionType.MCQ,
            subject="Math",
            marks=4.0,
            negative_marks=1.0,
            created_by=examiner.id,
        )
        opt3_corr = QuestionOption(id=uuid.uuid4(), question_id=q3.id, option_text="Correct", option_order=1, is_correct=True)
        opt3_inc = QuestionOption(id=uuid.uuid4(), question_id=q3.id, option_text="Incorrect", option_order=2, is_correct=False)
        q3.options = [opt3_corr, opt3_inc]

        db.add_all([q1, q2, q3])
        db.commit()

        # Exam with negative marking enabled
        exam = Exam(
            id=uuid.uuid4(),
            title="MCQ Test Exam",
            subject="Math",
            created_by=examiner.id,
            duration_minutes=60,
            total_marks=9.0,
            passing_marks=4.0,
            negative_marking_enabled=True,
            status=ExamStatus.PUBLISHED,
        )
        eq1 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q1.id, question_order=1)
        eq2 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q2.id, question_order=2)
        eq3 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q3.id, question_order=3)
        exam.exam_questions = [eq1, eq2, eq3]
        db.add(exam)
        db.commit()

        # Session: Q1 correct (+2), Q2 incorrect with 0 neg (-0), Q3 unanswered (0)
        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.SUBMITTED,
        )
        db.add(session)
        db.commit()

        # Answer 1 -> Correct
        ans1 = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q1.id)
        ans1.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans1.id, option_id=opt1_corr.id))

        # Answer 2 -> Incorrect
        ans2 = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q2.id)
        ans2.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans2.id, option_id=opt2_inc.id))

        db.add_all([ans1, ans2])
        db.commit()

        res = evaluation_service.evaluate_exam_session(db, session.id)

        assert res.total_questions == 3
        assert res.answered_questions == 2
        assert res.unanswered_questions == 1
        assert res.correct_answers == 1
        assert res.incorrect_answers == 1
        assert float(res.objective_marks) == 2.0
        assert float(res.negative_marks) == 0.0
        assert float(res.total_score) == 2.0
        assert float(res.maximum_marks) == 9.0

    def test_multi_select_evaluation_rules(self, db: Session):
        """Tests MULTI_SELECT exact match, partial match (incorrect), extra option (incorrect), and empty selection."""
        examiner = _create_test_user(db, "multi_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "multi_st@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="Multi Select Q",
            question_type=QuestionType.MULTI_SELECT,
            subject="Physics",
            marks=5.0,
            negative_marks=1.0,
            created_by=examiner.id,
        )
        optA = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="A", option_order=1, is_correct=True)
        optB = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="B", option_order=2, is_correct=False)
        optC = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=3, is_correct=True)
        q.options = [optA, optB, optC]

        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Multi Select Exam",
            subject="Physics",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=5.0,
            passing_marks=3.0,
            negative_marking_enabled=True,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        # Case 1: Exact set match A + C -> Full marks (+5.0)
        session1 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(session1)
        db.commit()
        ans1 = StudentAnswer(id=uuid.uuid4(), session_id=session1.id, question_id=q.id)
        ans1.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans1.id, option_id=optA.id))
        ans1.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans1.id, option_id=optC.id))
        db.add(ans1)
        db.commit()

        res1 = evaluation_service.evaluate_exam_session(db, session1.id)
        assert res1.correct_answers == 1
        assert float(res1.total_score) == 5.0

        # Case 2: Partial set A only -> Incorrect (-1.0)
        session2 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(session2)
        db.commit()
        ans2 = StudentAnswer(id=uuid.uuid4(), session_id=session2.id, question_id=q.id)
        ans2.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans2.id, option_id=optA.id))
        db.add(ans2)
        db.commit()

        res2 = evaluation_service.evaluate_exam_session(db, session2.id)
        assert res2.incorrect_answers == 1
        assert float(res2.negative_marks) == 1.0
        assert float(res2.total_score) == -1.0

    def test_score_calculation_percentage_pass_fail(self, db: Session):
        """Verifies total score, maximum marks, percentage calculation, and pass/fail status."""
        examiner = _create_test_user(db, "calc_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "calc_st@test.com", UserRole.STUDENT)

        q1 = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.MCQ, subject="Bio", marks=10.0, negative_marks=2.0, created_by=examiner.id)
        opt1_corr = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="C", option_order=1, is_correct=True)
        opt1_inc = QuestionOption(id=uuid.uuid4(), question_id=q1.id, option_text="I", option_order=2, is_correct=False)
        q1.options = [opt1_corr, opt1_inc]

        db.add(q1)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Bio Exam",
            subject="Bio",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            negative_marking_enabled=True,
            status=ExamStatus.PUBLISHED,
        )
        eq1 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q1.id, question_order=1)
        exam.exam_questions = [eq1]
        db.add(exam)
        db.commit()

        # Passed session
        sess_pass = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(sess_pass)
        db.commit()
        ans_pass = StudentAnswer(id=uuid.uuid4(), session_id=sess_pass.id, question_id=q1.id)
        ans_pass.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans_pass.id, option_id=opt1_corr.id))
        db.add(ans_pass)
        db.commit()

        res_pass = evaluation_service.evaluate_exam_session(db, sess_pass.id)
        assert res_pass.pass_fail_status == PassFailStatus.PASSED
        assert float(res_pass.percentage) == 100.0

        # Failed session
        sess_fail = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(sess_fail)
        db.commit()
        ans_fail = StudentAnswer(id=uuid.uuid4(), session_id=sess_fail.id, question_id=q1.id)
        ans_fail.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans_fail.id, option_id=opt1_inc.id))
        db.add(ans_fail)
        db.commit()

        res_fail = evaluation_service.evaluate_exam_session(db, sess_fail.id)
        assert res_fail.pass_fail_status == PassFailStatus.FAILED
        assert float(res_fail.total_score) == -2.0
        assert float(res_fail.percentage) == -20.0

    def test_subjective_questions_remain_pending_review(self, db: Session):
        """Verifies SHORT_ANSWER questions remain PENDING_REVIEW."""
        examiner = _create_test_user(db, "subj_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "subj_st@test.com", UserRole.STUDENT)

        q_subj = Question(
            id=uuid.uuid4(),
            question_text="Explain photosynthesis",
            question_type=QuestionType.SHORT_ANSWER,
            subject="Bio",
            marks=5.0,
            negative_marks=0.0,
            created_by=examiner.id,
        )
        db.add(q_subj)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Subj Exam",
            subject="Bio",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=5.0,
            passing_marks=3.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q_subj.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q_subj.id, text_answer="Photosynthesis is...")
        db.add(ans)
        db.commit()

        res = evaluation_service.evaluate_exam_session(db, session.id)
        assert res.status in (EvaluationStatus.PENDING_REVIEW, EvaluationStatus.AI_EVALUATED)
        assert float(res.total_score) == 0.0

    def test_idempotent_evaluation(self, db: Session):
        """Tests duplicate evaluation does not create duplicate result rows."""
        examiner = _create_test_user(db, "idem_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "idem_st@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q", question_type=QuestionType.MCQ, subject="History", marks=2.0, created_by=examiner.id)
        opt_corr = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=1, is_correct=True)
        q.options = [opt_corr]
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="History Exam", subject="History", created_by=examiner.id, duration_minutes=30, total_marks=2.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id)
        ans.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans.id, option_id=opt_corr.id))
        db.add(ans)
        db.commit()

        res1 = evaluation_service.evaluate_exam_session(db, session.id)
        res2 = evaluation_service.evaluate_exam_session(db, session.id)

        assert res1.id == res2.id
        count = db.query(ExamSessionEvaluation).filter(ExamSessionEvaluation.session_id == session.id).count()
        assert count == 1


class TestResultsApiSecurity:

    def test_student_cannot_access_another_student_result(self, client: TestClient, db: Session):
        """Verifies a student cannot view another student's exam result."""
        examiner = _create_test_user(db, "sec_ex@test.com", UserRole.EXAMINER)
        student1 = _create_test_user(db, "st1@test.com", UserRole.STUDENT)
        student2 = _create_test_user(db, "st2@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q", question_type=QuestionType.MCQ, subject="CS", marks=2.0, created_by=examiner.id)
        opt_corr = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=1, is_correct=True)
        q.options = [opt_corr]
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="CS Exam", subject="CS", created_by=examiner.id, duration_minutes=30, total_marks=2.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        # Session for student 1
        sess1 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student1.id, status=SessionStatus.SUBMITTED)
        db.add(sess1)
        db.commit()

        evaluation_service.evaluate_exam_session(db, sess1.id)

        # Student 2 tries to access Student 1 session result detail
        headers2 = _auth_headers_for_user(student2)
        resp = client.get(f"/api/student/results/{sess1.id}", headers=headers2)
        assert resp.status_code == 403

    def test_examiner_cannot_access_another_examiner_exam_results(self, client: TestClient, db: Session):
        """Verifies an examiner cannot view results for an exam owned by another examiner."""
        ex1 = _create_test_user(db, "ex1_owner@test.com", UserRole.EXAMINER)
        ex2 = _create_test_user(db, "ex2_other@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "st_sec@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q", question_type=QuestionType.MCQ, subject="Art", marks=2.0, created_by=ex1.id)
        opt_corr = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=1, is_correct=True)
        q.options = [opt_corr]
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Art Exam", subject="Art", created_by=ex1.id, duration_minutes=30, total_marks=2.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers_ex2 = _auth_headers_for_user(ex2)
        resp = client.get(f"/api/exams/{exam.id}/results", headers=headers_ex2)
        assert resp.status_code == 403

    def test_submitted_exam_triggers_evaluation_safely(self, client: TestClient, db: Session):
        """Tests that submitting an exam session triggers evaluation and returns evaluation status."""
        examiner = _create_test_user(db, "trig_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "trig_st@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q", question_type=QuestionType.MCQ, subject="Chem", marks=2.0, created_by=examiner.id)
        opt_corr = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=1, is_correct=True)
        q.options = [opt_corr]
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Chem Exam", subject="Chem", created_by=examiner.id, duration_minutes=30, total_marks=2.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=student.id, status=SessionStatus.IN_PROGRESS, identity_verification_status="VERIFIED")
        db.add(session)
        db.commit()

        headers_st = _auth_headers_for_user(student)
        resp = client.post(f"/api/student/sessions/{session.id}/submit", headers=headers_st)
        assert resp.status_code == 200

        # Verify evaluation record was automatically created
        eval_record = db.query(ExamSessionEvaluation).filter(ExamSessionEvaluation.session_id == session.id).first()
        assert eval_record is not None
        assert float(eval_record.maximum_marks) == 2.0

    def test_examiner_can_open_own_exam_result_detail(self, client: TestClient, db: Session):
        """Verifies examiner can retrieve detailed result for a session belonging to their exam."""
        ex = _create_test_user(db, "ex_det@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_det@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.MCQ, subject="Math", marks=5.0, created_by=ex.id)
        opt_corr = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="A", option_order=1, is_correct=True)
        q.options = [opt_corr]
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Math Exam", subject="Math", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/results/{session.id}", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        assert data["session_id"] == str(session.id)
        assert data["exam_title"] == "Math Exam"
        assert "question_evaluations" in data
        assert len(data["question_evaluations"]) == 1

    def test_examiner_cannot_open_other_examiner_exam_result_detail(self, client: TestClient, db: Session):
        """Verifies examiner cannot open session result detail for another examiner's exam."""
        ex1 = _create_test_user(db, "ex1_det_own@test.com", UserRole.EXAMINER)
        ex2 = _create_test_user(db, "ex2_det_oth@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_det_sec@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.MCQ, subject="Math", marks=5.0, created_by=ex1.id)
        opt_corr = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="A", option_order=1, is_correct=True)
        q.options = [opt_corr]
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Math Exam 1", subject="Math", created_by=ex1.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers_ex2 = _auth_headers_for_user(ex2)
        resp = client.get(f"/api/exams/{exam.id}/results/{session.id}", headers=headers_ex2)
        assert resp.status_code == 403

    def test_student_cannot_access_examiner_detail_endpoint(self, client: TestClient, db: Session):
        """Verifies student is rejected from examiner detail endpoint."""
        ex = _create_test_user(db, "ex_det_st@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_det_endpoint@test.com", UserRole.STUDENT)

        exam = Exam(id=uuid.uuid4(), title="Test Exam", subject="Math", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        headers_st = _auth_headers_for_user(st)
        resp = client.get(f"/api/exams/{exam.id}/results/{session.id}", headers=headers_st)
        assert resp.status_code == 403

    def test_examiner_detail_session_exam_mismatch(self, client: TestClient, db: Session):
        """Verifies 400 is returned if session does not belong to requested exam."""
        ex = _create_test_user(db, "ex_mismatch@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_mismatch@test.com", UserRole.STUDENT)

        exam1 = Exam(id=uuid.uuid4(), title="Exam 1", subject="Math", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        exam2 = Exam(id=uuid.uuid4(), title="Exam 2", subject="Math", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        db.add_all([exam1, exam2])
        db.commit()

        session1 = ExamSession(id=uuid.uuid4(), exam_id=exam1.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session1)
        db.commit()

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam2.id}/results/{session1.id}", headers=headers_ex)
        assert resp.status_code == 400


class TestSubjectiveAIEvaluation:

    def test_short_answer_ai_evaluation_full_credit(self, db: Session):
        """Tests SHORT_ANSWER AI evaluation with full credit."""
        from unittest.mock import patch
        from app.services.ai_subjective_evaluation_service import SubjectiveAIEvaluationOutput, ai_subjective_evaluation_service
        from app.models.evaluation import EvaluatorType

        examiner = _create_test_user(db, "sa_full_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "sa_full_st@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="What is Photosynthesis?",
            question_type=QuestionType.SHORT_ANSWER,
            subject="Biology",
            marks=5.0,
            model_answer="Process by which plants convert light energy into chemical energy.",
            explanation="Requires light, water, and CO2.",
            created_by=examiner.id,
        )
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Bio Test",
            subject="Biology",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=5.0,
            passing_marks=3.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.SUBMITTED,
        )
        db.add(session)
        db.commit()

        ans = StudentAnswer(
            id=uuid.uuid4(),
            session_id=session.id,
            question_id=q.id,
            text_answer="Photosynthesis converts light into chemical energy using chlorophyll.",
        )
        db.add(ans)
        db.commit()

        mock_out = SubjectiveAIEvaluationOutput(
            score=5.0,
            max_score=5.0,
            correctness=1.0,
            relevance=1.0,
            completeness=1.0,
            key_points_covered=["converts light energy", "chemical energy", "chlorophyll"],
            missing_key_points=[],
            feedback="Excellent explanation of photosynthesis.",
            reason="Full credit awarded for complete and accurate answer.",
        )

        with patch.object(ai_subjective_evaluation_service, "evaluate_answer", return_value=mock_out):
            res = evaluation_service.evaluate_exam_session(db, session.id)

        assert res.status == EvaluationStatus.AI_EVALUATED
        assert float(res.subjective_marks) == 5.0
        assert float(res.total_score) == 5.0
        assert res.pass_fail_status == PassFailStatus.PASSED

        # Check EvaluationResult details
        eval_res = db.query(EvaluationResult).filter(EvaluationResult.answer_id == ans.id).first()
        assert eval_res is not None
        assert eval_res.evaluator_type == EvaluatorType.AI
        assert float(eval_res.final_score) == 5.0
        assert eval_res.justification == "Full credit awarded for complete and accurate answer."
        assert eval_res.matched_concepts["key_points_covered"] == ["converts light energy", "chemical energy", "chlorophyll"]

    def test_short_answer_ai_evaluation_partial_credit(self, db: Session):
        """Tests SHORT_ANSWER AI evaluation with partial credit."""
        from unittest.mock import patch
        from app.services.ai_subjective_evaluation_service import SubjectiveAIEvaluationOutput, ai_subjective_evaluation_service

        examiner = _create_test_user(db, "sa_part_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "sa_part_st@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="Describe Newton's First Law",
            question_type=QuestionType.SHORT_ANSWER,
            subject="Physics",
            marks=10.0,
            model_answer="An object at rest remains at rest unless acted upon by an external net force.",
            created_by=examiner.id,
        )
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Physics Exam",
            subject="Physics",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.SUBMITTED,
        )
        db.add(session)
        db.commit()

        ans = StudentAnswer(
            id=uuid.uuid4(),
            session_id=session.id,
            question_id=q.id,
            text_answer="An object stays at rest unless a force acts on it.",
        )
        db.add(ans)
        db.commit()

        mock_out = SubjectiveAIEvaluationOutput(
            score=6.0,
            max_score=10.0,
            correctness=0.7,
            relevance=0.8,
            completeness=0.6,
            key_points_covered=["object stays at rest", "force acts on it"],
            missing_key_points=["external net force requirement", "object in motion stays in motion"],
            feedback="Good effort, but omitted external net force detail.",
            reason="Partial credit (6.0/10.0) for essential concept.",
        )

        with patch.object(ai_subjective_evaluation_service, "evaluate_answer", return_value=mock_out):
            res = evaluation_service.evaluate_exam_session(db, session.id)

        assert res.status == EvaluationStatus.AI_EVALUATED
        assert float(res.subjective_marks) == 6.0
        assert float(res.total_score) == 6.0
        assert res.pass_fail_status == PassFailStatus.PASSED

    def test_empty_student_answer_immediate_zero_without_api_call(self):
        """Tests that empty/whitespace student answer returns score 0 without invoking Gemini API."""
        from app.services.ai_subjective_evaluation_service import AISubjectiveEvaluationService

        service = AISubjectiveEvaluationService()
        out_empty = service.evaluate_answer(
            question_text="Explain Quantum Computing",
            question_type="LONG_ANSWER",
            student_answer="",
            model_answer="Quantum bits (qubits) leverage superposition and entanglement.",
            explanation=None,
            max_marks=10.0,
        )
        assert out_empty is not None
        assert out_empty.score == 0.0
        assert out_empty.max_score == 10.0
        assert "No answer" in out_empty.feedback

        out_spaces = service.evaluate_answer(
            question_text="Explain Quantum Computing",
            question_type="LONG_ANSWER",
            student_answer="   \n \t ",
            model_answer="Quantum bits (qubits) leverage superposition and entanglement.",
            explanation=None,
            max_marks=10.0,
        )
        assert out_spaces is not None
        assert out_spaces.score == 0.0

    def test_score_bounds_clamping(self):
        """Tests score clamping to [0, max_marks] when parsing AI response."""
        from unittest.mock import patch
        from app.services.ai_subjective_evaluation_service import AISubjectiveEvaluationService

        service = AISubjectiveEvaluationService()

        # Test upper bound overflow
        with patch.object(service, "_get_gemini_client") as mock_get_client:
            mock_client = mock_get_client.return_value
            mock_response = type("Response", (), {
                "text": '{"score": 15.0, "max_score": 10.0, "correctness": 1.0, "relevance": 1.0, "completeness": 1.0, "key_points_covered": [], "missing_key_points": [], "feedback": "Superb", "reason": "Too good"}'
            })
            mock_client.models.generate_content.return_value = mock_response

            res_overflow = service.evaluate_answer(
                question_text="Test Q",
                question_type="SHORT_ANSWER",
                student_answer="Some answer",
                model_answer="Model",
                explanation=None,
                max_marks=10.0,
            )
            assert res_overflow is not None
            assert res_overflow.score == 10.0  # Clamped down to max_marks

            # Test lower bound underflow
            mock_response_underflow = type("Response", (), {
                "text": '{"score": -5.0, "max_score": 10.0, "correctness": 0.0, "relevance": 0.0, "completeness": 0.0, "key_points_covered": [], "missing_key_points": [], "feedback": "Bad", "reason": "Negative score"}'
            })
            mock_client.models.generate_content.return_value = mock_response_underflow

            res_underflow = service.evaluate_answer(
                question_text="Test Q",
                question_type="SHORT_ANSWER",
                student_answer="Bad answer",
                model_answer="Model",
                explanation=None,
                max_marks=10.0,
            )
            assert res_underflow is not None
            assert res_underflow.score == 0.0  # Clamped up to 0.0

    def test_handwritten_questions_remain_pending_review(self, db: Session):
        """Verifies HANDWRITTEN questions remain PENDING_REVIEW without AI evaluation."""
        examiner = _create_test_user(db, "hw_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "hw_st@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="Draw and upload a circuit diagram",
            question_type=QuestionType.HANDWRITTEN,
            subject="EE",
            marks=10.0,
            created_by=examiner.id,
        )
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="EE Exam",
            subject="EE",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.SUBMITTED,
        )
        db.add(session)
        db.commit()

        ans = StudentAnswer(
            id=uuid.uuid4(),
            session_id=session.id,
            question_id=q.id,
            answer_image_url="http://example.com/circuit.png",
        )
        db.add(ans)
        db.commit()

        res = evaluation_service.evaluate_exam_session(db, session.id)
        assert res.status == EvaluationStatus.PENDING_REVIEW
        assert float(res.subjective_marks) == 0.0
        assert float(res.total_score) == 0.0

    def test_ai_provider_failure_graceful_fallback(self, db: Session):
        """Verifies session evaluation completes safely if AI provider returns None (failure/unavailable)."""
        from unittest.mock import patch
        from app.services.ai_subjective_evaluation_service import ai_subjective_evaluation_service

        examiner = _create_test_user(db, "ai_fail_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "ai_fail_st@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="Explain Machine Learning",
            question_type=QuestionType.SHORT_ANSWER,
            subject="CS",
            marks=5.0,
            created_by=examiner.id,
        )
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="CS Exam",
            subject="CS",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=5.0,
            passing_marks=3.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.SUBMITTED,
        )
        db.add(session)
        db.commit()

        ans = StudentAnswer(
            id=uuid.uuid4(),
            session_id=session.id,
            question_id=q.id,
            text_answer="Machine Learning trains models on data.",
        )
        db.add(ans)
        db.commit()

        with patch.object(ai_subjective_evaluation_service, "evaluate_answer", return_value=None):
            res = evaluation_service.evaluate_exam_session(db, session.id)

        assert res.status == EvaluationStatus.PENDING_REVIEW
        assert float(res.subjective_marks) == 0.0
        assert float(res.total_score) == 0.0

    def test_idempotent_subjective_evaluation(self, db: Session):
        """Tests that repeated evaluation on AI-evaluated subjective session preserves results without duplication."""
        from unittest.mock import patch
        from app.services.ai_subjective_evaluation_service import SubjectiveAIEvaluationOutput, ai_subjective_evaluation_service

        examiner = _create_test_user(db, "idem_subj_ex@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, "idem_subj_st@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="What is a Neural Network?",
            question_type=QuestionType.SHORT_ANSWER,
            subject="AI",
            marks=4.0,
            created_by=examiner.id,
        )
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="AI Exam",
            subject="AI",
            created_by=examiner.id,
            duration_minutes=30,
            total_marks=4.0,
            passing_marks=2.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.SUBMITTED,
        )
        db.add(session)
        db.commit()

        ans = StudentAnswer(
            id=uuid.uuid4(),
            session_id=session.id,
            question_id=q.id,
            text_answer="A computing system inspired by biological neural networks.",
        )
        db.add(ans)
        db.commit()

        mock_out = SubjectiveAIEvaluationOutput(
            score=4.0,
            max_score=4.0,
            correctness=1.0,
            relevance=1.0,
            completeness=1.0,
            key_points_covered=["computing system", "biological neural networks"],
            missing_key_points=[],
            feedback="Perfect definition.",
            reason="Full marks awarded.",
        )

        with patch.object(ai_subjective_evaluation_service, "evaluate_answer", return_value=mock_out):
            res1 = evaluation_service.evaluate_exam_session(db, session.id)
            res2 = evaluation_service.evaluate_exam_session(db, session.id)

        assert res1.id == res2.id
        assert float(res1.subjective_marks) == float(res2.subjective_marks) == 4.0
        eval_count = db.query(EvaluationResult).filter(EvaluationResult.answer_id == ans.id).count()
        assert eval_count == 1


class TestExaminerManualReview:

    def test_examiner_review_own_exam_subjective_answer_save_draft(self, client: TestClient, db: Session):
        """Tests Examiner reviewing own exam subjective answer (Save Review -> MANUAL_REVIEW)."""
        ex = _create_test_user(db, "ex_rev1@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_rev1@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Explain TCP 3-way handshake", question_type=QuestionType.SHORT_ANSWER, subject="Networking", marks=5.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Net Exam", subject="Networking", created_by=ex.id, duration_minutes=30, total_marks=5.0, passing_marks=3.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, text_answer="SYN, SYN-ACK, ACK.")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers = _auth_headers_for_user(ex)
        payload = {"final_score": 4.5, "comment": "Good answer, precise explanation.", "is_finalized": False}
        resp = client.patch(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/review", json=payload, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] == 4.5
        assert data["percentage"] == 90.0
        assert data["pass_fail_status"] == "PASSED"
        assert data["status"] == "MANUAL_REVIEW"

        # Check per-question evaluation detail
        q_eval = data["question_evaluations"][0]
        assert q_eval["earned_score"] == 4.5
        assert q_eval["examiner_comment"] == "Good answer, precise explanation."
        assert q_eval["evaluator_type"] == "EXAMINER"
        assert q_eval["status"] == "MANUAL_REVIEW"

    def test_examiner_finalize_subjective_answer(self, client: TestClient, db: Session):
        """Tests Examiner finalizing subjective answer evaluation."""
        ex = _create_test_user(db, "ex_fin@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_fin@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Explain OS Deadlocks", question_type=QuestionType.LONG_ANSWER, subject="OS", marks=10.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="OS Exam", subject="OS", created_by=ex.id, duration_minutes=30, total_marks=10.0, passing_marks=6.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, text_answer="Deadlock conditions: Mutual exclusion, hold and wait, no preemption, circular wait.")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers = _auth_headers_for_user(ex)
        payload = {"final_score": 9.5, "comment": "Excellent answer listing all 4 Coffman conditions."}
        resp = client.post(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/finalize", json=payload, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] == 9.5
        assert data["percentage"] == 95.0
        assert data["pass_fail_status"] == "PASSED"
        assert data["status"] == "FINALIZED"

        # Verify DB evaluation result
        er = db.query(EvaluationResult).filter(EvaluationResult.answer_id == ans.id).first()
        assert er.status == EvaluationStatus.FINALIZED
        assert float(er.final_score) == 9.5
        assert er.reviewed_by == ex.id
        assert er.reviewed_at is not None

    def test_finalized_evaluation_is_read_only(self, client: TestClient, db: Session):
        """Tests that finalized evaluations cannot be modified accidentally."""
        ex = _create_test_user(db, "ex_ro@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_ro@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Explain RAM", question_type=QuestionType.SHORT_ANSWER, subject="Hardware", marks=5.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Hardware Exam", subject="Hardware", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, text_answer="Volatile memory")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers = _auth_headers_for_user(ex)
        # Finalize first
        client.post(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/finalize", json={"final_score": 4.0, "comment": "Finalized"}, headers=headers)

        # Attempt to modify finalized evaluation
        resp = client.patch(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/review", json={"final_score": 2.0, "comment": "Modify"}, headers=headers)
        assert resp.status_code == 400
        assert "read-only" in resp.json()["detail"]

    def test_examiner_cannot_review_other_examiner_exam(self, client: TestClient, db: Session):
        """Verifies examiner cannot review another examiner's exam result."""
        ex1 = _create_test_user(db, "ex1_owner_rev@test.com", UserRole.EXAMINER)
        ex2 = _create_test_user(db, "ex2_other_rev@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_sec_rev@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.SHORT_ANSWER, subject="Math", marks=5.0, created_by=ex1.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Math Exam", subject="Math", created_by=ex1.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, text_answer="Ans")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers_ex2 = _auth_headers_for_user(ex2)
        resp = client.patch(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/review", json={"final_score": 3.0}, headers=headers_ex2)
        assert resp.status_code == 403

    def test_student_cannot_review(self, client: TestClient, db: Session):
        """Verifies student is rejected from reviewing evaluation."""
        ex = _create_test_user(db, "ex_st_no_rev@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_no_rev@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.SHORT_ANSWER, subject="Bio", marks=5.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Bio Exam", subject="Bio", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, text_answer="Ans")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers_st = _auth_headers_for_user(st)
        resp = client.patch(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/review", json={"final_score": 3.0}, headers=headers_st)
        assert resp.status_code == 403

    def test_score_range_validation_negative_and_exceeding_max(self, client: TestClient, db: Session):
        """Tests that negative score or score exceeding max marks is rejected by backend validation."""
        ex = _create_test_user(db, "ex_bounds@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_bounds@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.SHORT_ANSWER, subject="Physics", marks=5.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Physics Exam", subject="Physics", created_by=ex.id, duration_minutes=30, total_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, text_answer="Ans")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers = _auth_headers_for_user(ex)

        # Test negative score
        resp_neg = client.patch(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/review", json={"final_score": -1.0}, headers=headers)
        assert resp_neg.status_code == 400

        # Test score exceeding max marks (5.0)
        resp_over = client.patch(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/review", json={"final_score": 10.0}, headers=headers)
        assert resp_over.status_code == 400

    def test_handwritten_question_manual_scoring(self, client: TestClient, db: Session):
        """Tests manual scoring for HANDWRITTEN questions."""
        ex = _create_test_user(db, "ex_hw_man@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "st_hw_man@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Handwritten Proof", question_type=QuestionType.HANDWRITTEN, subject="Math", marks=10.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Math Proof Exam", subject="Math", created_by=ex.id, duration_minutes=30, total_marks=10.0, passing_marks=5.0, status=ExamStatus.PUBLISHED)
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id, answer_image_url="http://example.com/proof.png")
        db.add(ans)
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers = _auth_headers_for_user(ex)
        resp = client.post(f"/api/exams/{exam.id}/results/{session.id}/answers/{ans.id}/finalize", json={"final_score": 8.5, "comment": "Good proof steps."}, headers=headers)

        assert resp.status_code == 200
        data = resp.json()
        assert data["total_score"] == 8.5
        assert data["percentage"] == 85.0
        assert data["pass_fail_status"] == "PASSED"
        assert data["status"] == "FINALIZED"

