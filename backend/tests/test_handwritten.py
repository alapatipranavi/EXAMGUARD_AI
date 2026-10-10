import uuid
import base64
import pytest
from unittest.mock import patch, MagicMock
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.models.user import User, UserRole
from app.models.question import Question, QuestionType, DifficultyLevel
from app.models.exam import Exam, ExamQuestion, ExamStatus
from app.models.exam_session import ExamSession, SessionStatus
from app.models.answer import StudentAnswer
from app.models.evaluation import EvaluationResult, EvaluatorType, EvaluationStatus
from app.services.handwritten_ocr_service import handwritten_ocr_service, OCRResult, OCRStatus
from app.services.ai_subjective_evaluation_service import SubjectiveAIEvaluationOutput




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


# Sample 100x100 white image PNG base64 for testing capture payload
TEST_IMAGE_BASE64 = (
    "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAGQAAABkCAYAAABw4pVUAAAABmJLR0QA/wD/AP+gvaeTAAAACXBIWXMA"
    "AAsTAAALEwEAmpwYAAAAB3RJTUUH5gIDFQcK9O7zYQAAACVJREFUeNrtwTEBAAAACIK1/7VmuIEAAAAAAAAAAAAAAA"
    "AAAAAA5gYKpAABX7s+YAAAAABJRU5ErkJggg=="
)


class TestHandwrittenAnswerWorkflow:

    def _setup_handwritten_exam(self, db: Session):
        examiner = _create_test_user(db, f"ex_hw_{uuid.uuid4().hex[:6]}@test.com", UserRole.EXAMINER)
        student = _create_test_user(db, f"st_hw_{uuid.uuid4().hex[:6]}@test.com", UserRole.STUDENT)
        other_student = _create_test_user(db, f"st_other_{uuid.uuid4().hex[:6]}@test.com", UserRole.STUDENT)

        q_hw = Question(
            id=uuid.uuid4(),
            question_text="Derive Newton's Second Law of Motion on paper.",
            question_type=QuestionType.HANDWRITTEN,
            subject="Physics",
            difficulty=DifficultyLevel.MEDIUM,
            marks=10.0,
            model_answer="F = ma, Force is rate of change of momentum.",
            explanation="F = d(mv)/dt = ma",
            created_by=examiner.id,
        )
        db.add(q_hw)

        q_mcq = Question(
            id=uuid.uuid4(),
            question_text="What is unit of force?",
            question_type=QuestionType.MCQ,
            subject="Physics",
            marks=2.0,
            created_by=examiner.id,
        )
        db.add(q_mcq)

        exam = Exam(
            id=uuid.uuid4(),
            title="Physics Handwritten Exam",
            subject="Physics",
            duration_minutes=60,
            total_marks=12.0,
            passing_marks=5.0,
            status=ExamStatus.PUBLISHED,
            created_by=examiner.id,
        )
        db.add(exam)
        db.flush()

        eq1 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q_hw.id, question_order=1)
        eq2 = ExamQuestion(id=uuid.uuid4(), exam_id=exam.id, question_id=q_mcq.id, question_order=2)
        db.add_all([eq1, eq2])

        session = ExamSession(
            id=uuid.uuid4(),
            exam_id=exam.id,
            student_id=student.id,
            status=SessionStatus.IN_PROGRESS,
            identity_verification_status="VERIFIED",
        )
        db.add(session)
        db.commit()

        return {
            "examiner": examiner,
            "student": student,
            "other_student": other_student,
            "exam": exam,
            "q_hw": q_hw,
            "q_mcq": q_mcq,
            "session": session,
        }

    def test_handwritten_answer_submission_ocr_success(self, client, db: Session):
        """Tests successful handwritten answer upload, OCR extraction, and AI evaluation integration."""
        data = self._setup_handwritten_exam(db)
        headers = _auth_headers_for_user(data["student"])

        mock_ocr = OCRResult(
            extracted_text="F = ma. Force equals mass times acceleration.",
            confidence=0.88,
            status=OCRStatus.OCR_SUCCESS,
        )

        mock_ai = SubjectiveAIEvaluationOutput(
            score=9.0,
            max_score=10.0,
            reason="Good derivation of F = ma.",
            correctness=0.9,
            relevance=0.9,
            completeness=0.9,
            key_points_covered=["F = ma"],
            missing_key_points=[],
        )

        with patch("app.services.student_exam_service.handwritten_ocr_service.extract_text", return_value=mock_ocr), \
             patch("app.services.student_exam_service.ai_subjective_evaluation_service.evaluate_answer", return_value=mock_ai):
            res = client.post(
                f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
                json={"image_data": TEST_IMAGE_BASE64},
                headers=headers,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["ocr_status"] == "OCR_SUCCESS"
        assert body["ocr_confidence"] == 0.88
        assert "F = ma" in body["extracted_text"]
        assert body["evaluation_status"] == "AI_EVALUATED"
        assert "/uploads/handwritten/" in body["answer_image_url"]

        # Verify DB record
        ans = db.query(StudentAnswer).filter(StudentAnswer.session_id == data["session"].id, StudentAnswer.question_id == data["q_hw"].id).first()
        assert ans is not None
        assert ans.answer_image_url is not None
        assert ans.ocr_status == "OCR_SUCCESS"
        assert ans.evaluation_result is not None
        assert float(ans.evaluation_result.final_score) == 9.0

    def test_student_ownership_rbac(self, client, db: Session):
        """Tests that another student cannot submit handwritten answer for a session they do not own."""
        data = self._setup_handwritten_exam(db)
        headers_other = _auth_headers_for_user(data["other_student"])

        res = client.post(
            f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
            json={"image_data": TEST_IMAGE_BASE64},
            headers=headers_other,
        )
        assert res.status_code == 403
        assert "do not own" in res.json()["detail"].lower()

    def test_invalid_question_type(self, client, db: Session):
        """Tests submitting a handwritten answer for an MCQ question returns 400 Bad Request."""
        data = self._setup_handwritten_exam(db)
        headers = _auth_headers_for_user(data["student"])

        res = client.post(
            f"/api/student/sessions/{data['session'].id}/answers/{data['q_mcq'].id}/handwritten",
            json={"image_data": TEST_IMAGE_BASE64},
            headers=headers,
        )
        assert res.status_code == 400
        assert "not handwritten" in res.json()["detail"].lower()

    def test_invalid_session_state(self, client, db: Session):
        """Tests submitting handwritten answer for a completed/submitted session returns 400."""
        data = self._setup_handwritten_exam(db)
        headers = _auth_headers_for_user(data["student"])

        # Mark session as SUBMITTED
        data["session"].status = SessionStatus.SUBMITTED
        db.commit()

        res = client.post(
            f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
            json={"image_data": TEST_IMAGE_BASE64},
            headers=headers,
        )
        assert res.status_code == 400

    def test_ocr_failure_fallback_pending_review(self, client, db: Session):
        """Tests OCR failure safely sets evaluation status to PENDING_REVIEW without awarding fake marks."""
        data = self._setup_handwritten_exam(db)
        headers = _auth_headers_for_user(data["student"])

        mock_ocr = OCRResult(
            extracted_text="",
            confidence=0.0,
            status=OCRStatus.OCR_FAILED,
            error_message="Image unreadable",
        )

        with patch("app.services.student_exam_service.handwritten_ocr_service.extract_text", return_value=mock_ocr):
            res = client.post(
                f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
                json={"image_data": TEST_IMAGE_BASE64},
                headers=headers,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["ocr_status"] == "OCR_FAILED"
        assert body["evaluation_status"] == "PENDING_REVIEW"

        # Verify score remains 0 and status is PENDING_REVIEW
        ans = db.query(StudentAnswer).filter(StudentAnswer.session_id == data["session"].id).first()
        assert ans.evaluation_result.status == EvaluationStatus.PENDING_REVIEW
        assert float(ans.evaluation_result.final_score) == 0.0

    def test_ocr_low_confidence_fallback_pending_review(self, client, db: Session):
        """Tests low confidence OCR safely queues answer for manual examiner review."""
        data = self._setup_handwritten_exam(db)
        headers = _auth_headers_for_user(data["student"])

        mock_ocr = OCRResult(
            extracted_text="blurry text",
            confidence=0.20,
            status=OCRStatus.OCR_LOW_CONFIDENCE,
        )

        with patch("app.services.student_exam_service.handwritten_ocr_service.extract_text", return_value=mock_ocr):
            res = client.post(
                f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
                json={"image_data": TEST_IMAGE_BASE64},
                headers=headers,
            )

        assert res.status_code == 200
        body = res.json()
        assert body["ocr_status"] == "OCR_LOW_CONFIDENCE"
        assert body["evaluation_status"] == "PENDING_REVIEW"

    def test_examiner_manual_review_and_finalization(self, client, db: Session):
        """Tests Examiner reviewing and finalizing a handwritten answer evaluation."""
        data = self._setup_handwritten_exam(db)
        headers_student = _auth_headers_for_user(data["student"])
        headers_examiner = _auth_headers_for_user(data["examiner"])

        mock_ocr = OCRResult(
            extracted_text="Handwritten physics equation",
            confidence=0.85,
            status=OCRStatus.OCR_SUCCESS,
        )

        with patch("app.services.student_exam_service.handwritten_ocr_service.extract_text", return_value=mock_ocr):
            client.post(
                f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
                json={"image_data": TEST_IMAGE_BASE64},
                headers=headers_student,
            )

        ans = db.query(StudentAnswer).filter(StudentAnswer.session_id == data["session"].id).first()

        # 1. Save draft review
        res_review = client.patch(
            f"/api/exams/{data['exam'].id}/results/{data['session'].id}/answers/{ans.id}/review",
            json={"final_score": 8.5, "comment": "Clear steps shown", "is_finalized": False},
            headers=headers_examiner,
        )
        assert res_review.status_code == 200

        # 2. Finalize evaluation
        res_finalize = client.post(
            f"/api/exams/{data['exam'].id}/results/{data['session'].id}/answers/{ans.id}/finalize",
            json={"final_score": 9.5, "comment": "Excellent handwriting and accuracy"},
            headers=headers_examiner,
        )
        assert res_finalize.status_code == 200

        # Verify finalized state in DB
        db.refresh(ans.evaluation_result)
        assert ans.evaluation_result.status == EvaluationStatus.FINALIZED
        assert float(ans.evaluation_result.final_score) == 9.5

        # 3. Attempting to modify finalized evaluation returns 400 Bad Request
        res_locked = client.patch(
            f"/api/exams/{data['exam'].id}/results/{data['session'].id}/answers/{ans.id}/review",
            json={"final_score": 5.0, "comment": "Trying to overwrite"},
            headers=headers_examiner,
        )
        assert res_locked.status_code == 400
        assert "read-only" in res_locked.json()["detail"].lower()

    def test_no_duplicate_handwritten_answers(self, client, db: Session):
        """Tests that submitting handwritten answer multiple times updates existing answer row instead of duplicating."""
        data = self._setup_handwritten_exam(db)
        headers = _auth_headers_for_user(data["student"])

        mock_ocr = OCRResult(extracted_text="Version 1", confidence=0.8, status=OCRStatus.OCR_SUCCESS)
        with patch("app.services.student_exam_service.handwritten_ocr_service.extract_text", return_value=mock_ocr):
            client.post(
                f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
                json={"image_data": TEST_IMAGE_BASE64},
                headers=headers,
            )

        mock_ocr_2 = OCRResult(extracted_text="Version 2", confidence=0.9, status=OCRStatus.OCR_SUCCESS)
        with patch("app.services.student_exam_service.handwritten_ocr_service.extract_text", return_value=mock_ocr_2):
            client.post(
                f"/api/student/sessions/{data['session'].id}/answers/{data['q_hw'].id}/handwritten",
                json={"image_data": TEST_IMAGE_BASE64},
                headers=headers,
            )

        answers_count = db.query(StudentAnswer).filter(
            StudentAnswer.session_id == data["session"].id, StudentAnswer.question_id == data["q_hw"].id
        ).count()
        assert answers_count == 1

    def test_ocr_validation_rejects_meaningless_symbol_noise(self):
        """Tests that OCR text validation strictly rejects symbol/dash noise ('--', '..', '- -') and marks OCR_FAILED."""
        # Test Case A: '--' or '- -' dash noise
        status_dash, conf_dash, text_dash = handwritten_ocr_service._validate_ocr_text_and_confidence("--", [75.0, 80.0])
        assert status_dash == OCRStatus.OCR_FAILED
        assert text_dash == ""
        assert conf_dash == 0.0

        # Test Case B: '.. ' dot noise
        status_dot, conf_dot, text_dot = handwritten_ocr_service._validate_ocr_text_and_confidence(".. ", [60.0])
        assert status_dot == OCRStatus.OCR_FAILED
        assert text_dot == ""

        # Test Case C: '| | ~ ~' symbol noise
        status_sym, conf_sym, text_sym = handwritten_ocr_service._validate_ocr_text_and_confidence("| | ~ ~", [85.0, 90.0])
        assert status_sym == OCRStatus.OCR_FAILED
        assert text_sym == ""

    def test_ocr_validation_accepts_valid_alphanumeric_text(self):
        """Tests that OCR text validation accepts clear handwritten alphanumeric derivation text."""
        status, conf, text = handwritten_ocr_service._validate_ocr_text_and_confidence(
            "F = ma. Force equals mass times acceleration.", [88.0, 92.0, 85.0]
        )
        assert status == OCRStatus.OCR_SUCCESS
        assert conf >= 0.35
        assert "F = ma" in text

    def test_ocr_validation_low_confidence_classification(self):
        """Tests that OCR text with low confidence score is classified as OCR_LOW_CONFIDENCE."""
        status, conf, text = handwritten_ocr_service._validate_ocr_text_and_confidence(
            "F = ma derivation step 1", [20.0, 25.0]
        )
        assert status == OCRStatus.OCR_LOW_CONFIDENCE
        assert conf < 0.35
        assert text == "F = ma derivation step 1"

