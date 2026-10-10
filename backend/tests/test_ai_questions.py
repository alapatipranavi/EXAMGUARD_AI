import json
import pytest
from unittest.mock import MagicMock, patch
from app.models.user import UserRole
from app.models.question import QuestionSource
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token
from app.core.config import settings


@pytest.fixture
def ai_users(db):
    ex = user_repository.create_user(db, "ai_ex@test.com", hash_password("Pass123!"), "Ai", "Ex", UserRole.EXAMINER)
    st = user_repository.create_user(db, "ai_st@test.com", hash_password("Pass123!"), "Ai", "St", UserRole.STUDENT)
    ad = user_repository.create_user(db, "ai_ad@test.com", hash_password("Pass123!"), "Ai", "Ad", UserRole.ADMIN)

    t_ex = create_access_token({"sub": str(ex.id), "role": "EXAMINER"})
    t_st = create_access_token({"sub": str(st.id), "role": "STUDENT"})
    t_ad = create_access_token({"sub": str(ad.id), "role": "ADMIN"})

    return {
        "h_ex": {"Authorization": f"Bearer {t_ex}"},
        "h_st": {"Authorization": f"Bearer {t_st}"},
        "h_ad": {"Authorization": f"Bearer {t_ad}"},
        "ex_user": ex,
    }


def test_ai_generate_returns_503_when_unconfigured(client, ai_users):
    payload = {
        "subject": "Computer Science",
        "topic": "Algorithms",
        "question_types": ["MCQ"],
        "difficulty": "MEDIUM",
        "count": 3,
        "marks": 2.0
    }
    with patch.object(settings, "GEMINI_API_KEY", None):
        res = client.post("/api/questions/generate", json=payload, headers=ai_users["h_ex"])
        assert res.status_code == 503
        assert "not configured" in res.json()["detail"].lower()


def test_ai_generate_forbidden_for_student_and_admin(client, ai_users):
    payload = {
        "subject": "Computer Science",
        "topic": "Algorithms",
        "question_types": ["MCQ"],
        "difficulty": "MEDIUM",
        "count": 3,
        "marks": 2.0
    }
    r_st = client.post("/api/questions/generate", json=payload, headers=ai_users["h_st"])
    assert r_st.status_code == 403

    r_ad = client.post("/api/questions/generate", json=payload, headers=ai_users["h_ad"])
    assert r_ad.status_code == 403


def test_ai_generate_malformed_response_rejected(client, ai_users):
    payload = {
        "subject": "Computer Science",
        "topic": "Algorithms",
        "question_types": ["MCQ"],
        "difficulty": "MEDIUM",
        "count": 2,
        "marks": 2.0
    }

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = "THIS IS NOT VALID JSON"
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "real_test_key_12345"):
        with patch("google.genai.Client", return_value=mock_client):
            res = client.post("/api/questions/generate", json=payload, headers=ai_users["h_ex"])
            assert res.status_code == 503
            assert "invalid question format" in res.json()["detail"].lower()


def test_ai_generate_drafts_not_persisted_automatically(client, db, ai_users):
    payload = {
        "subject": "Networking",
        "topic": "TCP",
        "question_types": ["MCQ"],
        "difficulty": "EASY",
        "count": 1,
        "marks": 2.0
    }

    mock_json = json.dumps([
        {
            "question_text": "What does TCP stand for?",
            "question_type": "MCQ",
            "difficulty": "EASY",
            "marks": 2.0,
            "negative_marks": 0.0,
            "model_answer": "Transmission Control Protocol",
            "explanation": "TCP is a core protocol.",
            "options": [
                {"option_text": "Transmission Control Protocol", "option_order": 1, "is_correct": True},
                {"option_text": "Transfer Control Protocol", "option_order": 2, "is_correct": False}
            ]
        }
    ])

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_json
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "real_test_key_12345"):
        with patch("google.genai.Client", return_value=mock_client):
            res = client.post("/api/questions/generate", json=payload, headers=ai_users["h_ex"])
            assert res.status_code == 200
            data = res.json()
            assert len(data["drafts"]) == 1
            assert data["drafts"][0]["question_text"] == "What does TCP stand for?"
            assert data["drafts"][0]["source"] == "AI_GENERATED"

            # Check database: No question with this text should exist yet
            list_res = client.get("/api/questions?search=TCP", headers=ai_users["h_ex"])
            assert list_res.status_code == 200
            assert list_res.json()["total"] == 0


def test_ai_accept_draft_saves_with_ai_generated_source(client, ai_users):
    create_payload = {
        "question_text": "AI generated test question statement",
        "subject": "Networking",
        "topic": "UDP",
        "question_type": "MCQ",
        "difficulty": "MEDIUM",
        "source": "AI_GENERATED",
        "marks": 2.0,
        "options": [
            {"option_text": "User Datagram Protocol", "option_order": 1, "is_correct": True},
            {"option_text": "Universal Data Protocol", "option_order": 2, "is_correct": False}
        ]
    }

    res = client.post("/api/questions", json=create_payload, headers=ai_users["h_ex"])
    assert res.status_code == 201
    q = res.json()
    assert q["source"] == "AI_GENERATED"
    assert q["created_by"] == str(ai_users["ex_user"].id)


def test_ai_assist_works_with_mocked_provider(client, ai_users):
    payload = {
        "action": "improve",
        "question_text": "Explain TCP congestion control",
        "question_type": "SHORT_ANSWER",
        "subject": "Networking",
        "topic": "TCP"
    }

    mock_json = json.dumps({
        "improved_question_text": "Describe the key mechanisms of TCP congestion control including Slow Start and Congestion Avoidance.",
        "suggested_explanation": "TCP congestion control prevents network saturation.",
        "suggested_model_answer": "Slow start, congestion avoidance, fast retransmit.",
        "suggested_options": None
    })

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_json
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "real_test_key_12345"):
        with patch("google.genai.Client", return_value=mock_client):
            res = client.post("/api/questions/assist", json=payload, headers=ai_users["h_ex"])
            assert res.status_code == 200
            data = res.json()
            assert "Slow Start" in data["improved_question_text"]


def test_api_key_never_appears_in_response(client, ai_users):
    secret_key = "super_secret_gemini_key_abc123"
    payload = {
        "subject": "Computer Science",
        "topic": "Algorithms",
        "question_types": ["MCQ"],
        "difficulty": "MEDIUM",
        "count": 1,
        "marks": 2.0
    }

    mock_json = json.dumps([
        {
            "question_text": "What is binary search time complexity?",
            "question_type": "MCQ",
            "difficulty": "MEDIUM",
            "marks": 2.0,
            "negative_marks": 0.0,
            "options": [
                {"option_text": "O(log n)", "option_order": 1, "is_correct": True},
                {"option_text": "O(n)", "option_order": 2, "is_correct": False}
            ]
        }
    ])

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_json
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", secret_key):
        with patch("google.genai.Client", return_value=mock_client):
            res = client.post("/api/questions/generate", json=payload, headers=ai_users["h_ex"])
            assert res.status_code == 200
            body_str = res.text
            assert secret_key not in body_str
            for header, value in res.headers.items():
                assert secret_key not in value


def test_mcq_and_multi_select_and_subjective_validation(client, ai_users):
    payload = {
        "subject": "Database Systems",
        "topic": "SQL",
        "question_types": ["MCQ", "MULTI_SELECT", "SHORT_ANSWER"],
        "difficulty": "MEDIUM",
        "count": 3,
        "marks": 2.0
    }

    mock_json = json.dumps([
        {
            "question_text": "Which SQL keyword filters rows?",
            "question_type": "MCQ",
            "difficulty": "MEDIUM",
            "marks": 2.0,
            "options": [
                {"option_text": "WHERE", "option_order": 1, "is_correct": True},
                {"option_text": "SELECT", "option_order": 2, "is_correct": False}
            ]
        },
        {
            "question_type": "MULTI_SELECT",
            "question_text": "Which of the following are DDL commands?",
            "difficulty": "MEDIUM",
            "marks": 2.0,
            "options": [
                {"option_text": "CREATE", "option_order": 1, "is_correct": True},
                {"option_text": "ALTER", "option_order": 2, "is_correct": True},
                {"option_text": "INSERT", "option_order": 3, "is_correct": False}
            ]
        },
        {
            "question_type": "SHORT_ANSWER",
            "question_text": "Define a database transaction.",
            "difficulty": "MEDIUM",
            "marks": 2.0,
            "options": [
                {"option_text": "should be ignored", "option_order": 1, "is_correct": False}
            ]
        }
    ])

    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.text = mock_json
    mock_client.models.generate_content.return_value = mock_response

    with patch.object(settings, "GEMINI_API_KEY", "real_test_key_12345"):
        with patch("google.genai.Client", return_value=mock_client):
            res = client.post("/api/questions/generate", json=payload, headers=ai_users["h_ex"])
            assert res.status_code == 200
            drafts = res.json()["drafts"]
            assert len(drafts) == 3

            # MCQ has exactly 1 correct
            mcq = drafts[0]
            assert mcq["question_type"] == "MCQ"
            assert sum(1 for o in mcq["options"] if o["is_correct"]) == 1

            # MULTI_SELECT has >= 2 correct
            ms = drafts[1]
            assert ms["question_type"] == "MULTI_SELECT"
            assert sum(1 for o in ms["options"] if o["is_correct"]) >= 2

            # SHORT_ANSWER options stripped to empty
            sa = drafts[2]
            assert sa["question_type"] == "SHORT_ANSWER"
            assert sa["options"] == []
