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


class TestExamAnalytics:

    def test_examiner_can_access_own_exam_analytics(self, client: TestClient, db: Session):
        """Verifies Examiner can view analytics for an exam they created."""
        ex = _create_test_user(db, "an_ex_own@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "an_st_own@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="Q1",
            question_type=QuestionType.MCQ,
            subject="Physics",
            marks=10.0,
            topic="Kinematics",
            difficulty=DifficultyLevel.EASY,
            created_by=ex.id,
        )
        opt_c = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=1, is_correct=True)
        q.options = [opt_c]
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Physics Exam",
            subject="Physics",
            created_by=ex.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q.id)
        ans.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans.id, option_id=opt_c.id))
        db.add(ans)
        db.commit()

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        assert data["exam_info"]["title"] == "Physics Exam"
        assert data["summary"]["total_sessions"] == 1
        assert data["summary"]["pass_count"] == 1

    def test_examiner_cannot_access_another_examiner_exam_analytics(self, client: TestClient, db: Session):
        """Verifies Examiner is rejected with 403 when trying to access analytics of another Examiner's exam."""
        ex1 = _create_test_user(db, "an_ex1@test.com", UserRole.EXAMINER)
        ex2 = _create_test_user(db, "an_ex2@test.com", UserRole.EXAMINER)

        exam = Exam(
            id=uuid.uuid4(),
            title="Ex1 Exam",
            subject="Chem",
            created_by=ex1.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        db.add(exam)
        db.commit()

        headers_ex2 = _auth_headers_for_user(ex2)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex2)
        assert resp.status_code == 403

    def test_student_receives_403(self, client: TestClient, db: Session):
        """Verifies Student role receives 403 for analytics endpoint."""
        ex = _create_test_user(db, "an_ex_st@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "an_st_forbidden@test.com", UserRole.STUDENT)

        exam = Exam(
            id=uuid.uuid4(),
            title="Bio Exam",
            subject="Bio",
            created_by=ex.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        db.add(exam)
        db.commit()

        headers_st = _auth_headers_for_user(st)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_st)
        assert resp.status_code == 403

    def test_empty_exam_analytics_returns_zero_metrics(self, client: TestClient, db: Session):
        """Verifies an exam with 0 sessions returns clean 0 metrics without NaN/errors."""
        ex = _create_test_user(db, "an_ex_empty@test.com", UserRole.EXAMINER)

        exam = Exam(
            id=uuid.uuid4(),
            title="Empty Exam",
            subject="Math",
            created_by=ex.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=5.0,
            status=ExamStatus.PUBLISHED,
        )
        db.add(exam)
        db.commit()

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_sessions"] == 0
        assert data["summary"]["average_score"] == 0.0
        assert data["summary"]["pass_rate"] == 0.0
        assert data["score_performance"]["median_percentage"] == 0.0

    def test_summary_and_pass_fail_counts(self, client: TestClient, db: Session):
        """Verifies correct summary, pass/fail counts, and average percentage across multiple sessions."""
        ex = _create_test_user(db, "an_ex_counts@test.com", UserRole.EXAMINER)
        st1 = _create_test_user(db, "an_st_pass@test.com", UserRole.STUDENT)
        st2 = _create_test_user(db, "an_st_fail@test.com", UserRole.STUDENT)

        q = Question(
            id=uuid.uuid4(),
            question_text="Q1",
            question_type=QuestionType.MCQ,
            subject="Math",
            marks=10.0,
            created_by=ex.id,
        )
        opt_c = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="C", option_order=1, is_correct=True)
        opt_i = QuestionOption(id=uuid.uuid4(), question_id=q.id, option_text="I", option_order=2, is_correct=False)
        q.options = [opt_c, opt_i]
        db.add(q)
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="Math Exam",
            subject="Math",
            created_by=ex.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        eq = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q.id, question_order=1)
        exam.exam_questions = [eq]
        db.add(exam)
        db.commit()

        # Passed session (10.0 / 10.0 -> 100%)
        sess1 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st1.id, status=SessionStatus.SUBMITTED)
        db.add(sess1)
        db.commit()
        ans1 = StudentAnswer(id=uuid.uuid4(), session_id=sess1.id, question_id=q.id)
        ans1.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans1.id, option_id=opt_c.id))
        db.add(ans1)
        db.commit()
        evaluation_service.evaluate_exam_session(db, sess1.id)

        # Failed session (0.0 / 10.0 -> 0%)
        sess2 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st2.id, status=SessionStatus.SUBMITTED)
        db.add(sess2)
        db.commit()
        ans2 = StudentAnswer(id=uuid.uuid4(), session_id=sess2.id, question_id=q.id)
        ans2.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans2.id, option_id=opt_i.id))
        db.add(ans2)
        db.commit()
        evaluation_service.evaluate_exam_session(db, sess2.id)

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        assert data["summary"]["total_sessions"] == 2
        assert data["summary"]["pass_count"] == 1
        assert data["summary"]["fail_count"] == 1
        assert data["summary"]["pass_rate"] == 50.0
        assert data["summary"]["average_percentage"] == 50.0

    def test_score_distribution_buckets(self, client: TestClient, db: Session):
        """Verifies score distribution buckets placement."""
        ex = _create_test_user(db, "an_ex_dist@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "an_st_dist@test.com", UserRole.STUDENT)

        exam = Exam(
            id=uuid.uuid4(),
            title="Dist Exam",
            subject="CS",
            created_by=ex.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=5.0,
            status=ExamStatus.PUBLISHED,
        )
        db.add(exam)
        db.commit()

        # Add a session with 90% score directly in DB
        sess = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(sess)
        db.commit()

        eval_rec = ExamSessionEvaluation(
            id=uuid.uuid4(),
            session_id=sess.id,
            exam_id=exam.id,
            student_id=st.id,
            total_questions=1,
            answered_questions=1,
            correct_answers=1,
            incorrect_answers=0,
            objective_marks=9.0,
            total_score=9.0,
            maximum_marks=10.0,
            percentage=90.0,
            passing_marks=5.0,
            pass_fail_status=PassFailStatus.PASSED,
            status=EvaluationStatus.COMPLETED,
        )
        db.add(eval_rec)
        db.commit()

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        assert data["score_distribution"]["bucket_81_100"] == 1
        assert data["score_distribution"]["bucket_0_20"] == 0

    def test_question_level_objective_and_subjective_statistics(self, client: TestClient, db: Session):
        """Verifies question level objective accuracy and subjective pending review tracking."""
        ex = _create_test_user(db, "an_ex_qstats@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "an_st_qstats@test.com", UserRole.STUDENT)

        q_obj = Question(
            id=uuid.uuid4(),
            question_text="Obj Q",
            question_type=QuestionType.MCQ,
            subject="History",
            marks=5.0,
            topic="Ancient",
            difficulty=DifficultyLevel.EASY,
            created_by=ex.id,
        )
        opt_c = QuestionOption(id=uuid.uuid4(), question_id=q_obj.id, option_text="C", option_order=1, is_correct=True)
        q_obj.options = [opt_c]

        q_subj = Question(
            id=uuid.uuid4(),
            question_text="Subj Q",
            question_type=QuestionType.SHORT_ANSWER,
            subject="History",
            marks=5.0,
            topic="Modern",
            difficulty=DifficultyLevel.HARD,
            created_by=ex.id,
        )
        db.add_all([q_obj, q_subj])
        db.commit()

        exam = Exam(
            id=uuid.uuid4(),
            title="History Exam",
            subject="History",
            created_by=ex.id,
            duration_minutes=30,
            total_marks=10.0,
            passing_marks=6.0,
            status=ExamStatus.PUBLISHED,
        )
        eq1 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q_obj.id, question_order=1)
        eq2 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q_subj.id, question_order=2)
        exam.exam_questions = [eq1, eq2]
        db.add(exam)
        db.commit()

        session = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st.id, status=SessionStatus.SUBMITTED)
        db.add(session)
        db.commit()

        ans1 = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q_obj.id)
        ans1.selected_options.append(AnswerSelectedOption(id=uuid.uuid4(), answer_id=ans1.id, option_id=opt_c.id))
        ans2 = StudentAnswer(id=uuid.uuid4(), session_id=session.id, question_id=q_subj.id, text_answer="Modern history notes")
        db.add_all([ans1, ans2])
        db.commit()

        evaluation_service.evaluate_exam_session(db, session.id)

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()

        q_perf = data["question_performance"]
        assert len(q_perf) == 2
        assert q_perf[0]["question_type"] == "MCQ"
        assert q_perf[0]["correct_count"] == 1
        assert q_perf[0]["accuracy_percentage"] == 100.0

        assert q_perf[1]["question_type"] == "SHORT_ANSWER"
        assert q_perf[1]["pending_review_count"] == 1

        # Check pending reviews list
        assert len(data["pending_reviews"]) == 1
        assert data["pending_reviews"][0]["student_email"] == st.email

    def test_finalized_evaluation_statistics(self, client: TestClient, db: Session):
        """Verifies statistics for finalized evaluations."""
        ex = _create_test_user(db, "an_ex_fin@test.com", UserRole.EXAMINER)
        st = _create_test_user(db, "an_st_fin@test.com", UserRole.STUDENT)

        q = Question(id=uuid.uuid4(), question_text="Q1", question_type=QuestionType.SHORT_ANSWER, subject="Bio", marks=5.0, created_by=ex.id)
        db.add(q)
        db.commit()

        exam = Exam(id=uuid.uuid4(), title="Bio Exam", subject="Bio", created_by=ex.id, duration_minutes=30, total_marks=5.0, passing_marks=3.0, status=ExamStatus.PUBLISHED)
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

        # Finalize subjective review
        evaluation_service.review_subjective_answer(
            db=db,
            exam_id=exam.id,
            session_id=session.id,
            answer_id=ans.id,
            current_user=ex,
            final_score=5.0,
            comment="Finalized full score",
            is_finalized=True,
        )

        headers_ex = _auth_headers_for_user(ex)
        resp = client.get(f"/api/exams/{exam.id}/analytics", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        fin_perf = data["finalized_performance"]
        assert fin_perf["finalized_sessions"] == 1
        assert fin_perf["average_finalized_score"] == 5.0
        assert fin_perf["finalized_pass_rate"] == 100.0

    def test_search_and_filter_student_performance(self, client: TestClient, db: Session):
        """Verifies search, pass/fail filter, and status filter on student performance table."""
        ex = _create_test_user(db, "an_ex_flt@test.com", UserRole.EXAMINER)
        st1 = _create_test_user(db, "alice@test.com", UserRole.STUDENT)
        st2 = _create_test_user(db, "bob@test.com", UserRole.STUDENT)

        exam = Exam(id=uuid.uuid4(), title="Filter Exam", subject="CS", created_by=ex.id, duration_minutes=30, total_marks=10.0, status=ExamStatus.PUBLISHED)
        db.add(exam)
        db.commit()

        sess1 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st1.id, status=SessionStatus.SUBMITTED)
        sess2 = ExamSession(id=uuid.uuid4(), exam_id=exam.id, student_id=st2.id, status=SessionStatus.SUBMITTED)
        db.add_all([sess1, sess2])
        db.commit()

        eval1 = ExamSessionEvaluation(id=uuid.uuid4(), session_id=sess1.id, exam_id=exam.id, student_id=st1.id, total_score=10.0, maximum_marks=10.0, percentage=100.0, passing_marks=5.0, pass_fail_status=PassFailStatus.PASSED, status=EvaluationStatus.FINALIZED)
        eval2 = ExamSessionEvaluation(id=uuid.uuid4(), session_id=sess2.id, exam_id=exam.id, student_id=st2.id, total_score=2.0, maximum_marks=10.0, percentage=20.0, passing_marks=5.0, pass_fail_status=PassFailStatus.FAILED, status=EvaluationStatus.COMPLETED)
        db.add_all([eval1, eval2])
        db.commit()

        headers_ex = _auth_headers_for_user(ex)

        # Search by student name
        resp = client.get(f"/api/exams/{exam.id}/analytics?search=alice", headers=headers_ex)
        assert resp.status_code == 200
        data = resp.json()
        assert data["student_performance"]["total"] == 1
        assert data["student_performance"]["items"][0]["student_email"] == "alice@test.com"

        # Filter by PASSED
        resp_pf = client.get(f"/api/exams/{exam.id}/analytics?pass_fail=PASSED", headers=headers_ex)
        assert resp_pf.status_code == 200
        assert resp_pf.json()["student_performance"]["total"] == 1

        # Filter by status FINALIZED
        resp_st = client.get(f"/api/exams/{exam.id}/analytics?session_status=FINALIZED", headers=headers_ex)
        assert resp_st.status_code == 200
        assert resp_st.json()["student_performance"]["total"] == 1
