import pytest
from app.models.user import UserRole
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token


@pytest.fixture
def test_users(db):
    """Fixture providing examiner1, examiner2, student, admin with JWT headers."""
    ex1 = user_repository.create_user(db, "examiner1@test.com", hash_password("Pass123!"), "Ex1", "Teacher", UserRole.EXAMINER)
    ex2 = user_repository.create_user(db, "examiner2@test.com", hash_password("Pass123!"), "Ex2", "Teacher", UserRole.EXAMINER)
    st = user_repository.create_user(db, "student@test.com", hash_password("Pass123!"), "Stu", "Dent", UserRole.STUDENT)
    ad = user_repository.create_user(db, "admin@test.com", hash_password("Pass123!"), "Ad", "Min", UserRole.ADMIN)

    t_ex1 = create_access_token({"sub": str(ex1.id), "role": "EXAMINER"})
    t_ex2 = create_access_token({"sub": str(ex2.id), "role": "EXAMINER"})
    t_st = create_access_token({"sub": str(st.id), "role": "STUDENT"})
    t_ad = create_access_token({"sub": str(ad.id), "role": "ADMIN"})

    return {
        "ex1": ex1,
        "ex2": ex2,
        "st": st,
        "ad": ad,
        "h_ex1": {"Authorization": f"Bearer {t_ex1}"},
        "h_ex2": {"Authorization": f"Bearer {t_ex2}"},
        "h_st": {"Authorization": f"Bearer {t_st}"},
        "h_ad": {"Authorization": f"Bearer {t_ad}"},
    }


# ==========================================
# 1. CREATION TESTS (EXAMINER)
# ==========================================

def test_examiner_create_mcq_success(client, test_users):
    payload = {
        "question_text": "What is the capital of France?",
        "subject": "Geography",
        "topic": "Capitals",
        "question_type": "MCQ",
        "difficulty": "EASY",
        "marks": 2.0,
        "negative_marks": 0.5,
        "explanation": "Paris is the capital of France.",
        "options": [
            {"option_text": "Paris", "option_order": 1, "is_correct": True},
            {"option_text": "London", "option_order": 2, "is_correct": False},
            {"option_text": "Berlin", "option_order": 3, "is_correct": False},
        ]
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 201
    data = res.json()
    assert data["question_text"] == "What is the capital of France?"
    assert data["question_type"] == "MCQ"
    assert data["created_by"] == str(test_users["ex1"].id)
    assert len(data["options"]) == 3
    correct = [o for o in data["options"] if o["is_correct"]]
    assert len(correct) == 1
    assert correct[0]["option_text"] == "Paris"


def test_examiner_create_multi_select_success(client, test_users):
    payload = {
        "question_text": "Select all prime numbers below 10.",
        "subject": "Mathematics",
        "topic": "Number Theory",
        "question_type": "MULTI_SELECT",
        "difficulty": "MEDIUM",
        "marks": 4.0,
        "options": [
            {"option_text": "2", "option_order": 1, "is_correct": True},
            {"option_text": "3", "option_order": 2, "is_correct": True},
            {"option_text": "4", "option_order": 3, "is_correct": False},
            {"option_text": "5", "option_order": 4, "is_correct": True},
        ]
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 201
    data = res.json()
    assert data["question_type"] == "MULTI_SELECT"
    assert len([o for o in data["options"] if o["is_correct"]]) == 3


def test_examiner_create_short_answer_success(client, test_users):
    payload = {
        "question_text": "Define photosynthesis in one sentence.",
        "subject": "Biology",
        "topic": "Botany",
        "question_type": "SHORT_ANSWER",
        "difficulty": "EASY",
        "marks": 3.0,
        "model_answer": "Process by which green plants convert sunlight into chemical energy."
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 201
    data = res.json()
    assert data["question_type"] == "SHORT_ANSWER"
    assert data["model_answer"] is not None
    assert len(data["options"]) == 0


def test_examiner_create_long_answer_success(client, test_users):
    payload = {
        "question_text": "Explain the architectural layers of ExamGuard AI in detail.",
        "subject": "Software Engineering",
        "question_type": "LONG_ANSWER",
        "difficulty": "HARD",
        "marks": 10.0,
        "model_answer": "Detailed breakdown of Frontend, Backend FastAPI, PostgreSQL, and AI proctoring services."
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 201
    assert res.json()["question_type"] == "LONG_ANSWER"


def test_examiner_create_handwritten_success(client, test_users):
    payload = {
        "question_text": "Derive Schrödinger's wave equation on paper.",
        "subject": "Physics",
        "question_type": "HANDWRITTEN",
        "difficulty": "HARD",
        "marks": 15.0
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 201
    data = res.json()
    assert data["question_type"] == "HANDWRITTEN"
    assert len(data["options"]) == 0


# ==========================================
# 2. VALIDATION FAILURE TESTS
# ==========================================

def test_create_mcq_fails_if_no_correct_option(client, test_users):
    payload = {
        "question_text": "Invalid MCQ?",
        "subject": "Test",
        "question_type": "MCQ",
        "marks": 1.0,
        "options": [
            {"option_text": "A", "option_order": 1, "is_correct": False},
            {"option_text": "B", "option_order": 2, "is_correct": False},
        ]
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 422


def test_create_mcq_fails_if_multiple_correct_options(client, test_users):
    payload = {
        "question_text": "Invalid MCQ?",
        "subject": "Test",
        "question_type": "MCQ",
        "marks": 1.0,
        "options": [
            {"option_text": "A", "option_order": 1, "is_correct": True},
            {"option_text": "B", "option_order": 2, "is_correct": True},
        ]
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 422


def test_create_mcq_fails_if_fewer_than_2_options(client, test_users):
    payload = {
        "question_text": "Invalid MCQ?",
        "subject": "Test",
        "question_type": "MCQ",
        "marks": 1.0,
        "options": [
            {"option_text": "A", "option_order": 1, "is_correct": True},
        ]
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 422


def test_create_multi_select_fails_if_less_than_2_correct(client, test_users):
    payload = {
        "question_text": "Invalid Multi-Select?",
        "subject": "Test",
        "question_type": "MULTI_SELECT",
        "marks": 1.0,
        "options": [
            {"option_text": "A", "option_order": 1, "is_correct": True},
            {"option_text": "B", "option_order": 2, "is_correct": False},
            {"option_text": "C", "option_order": 3, "is_correct": False},
        ]
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ex1"])
    assert res.status_code == 422


# ==========================================
# 3. ROLE-BASED ACCESS CONTROL (RBAC) TESTS
# ==========================================

def test_admin_create_question_forbidden(client, test_users):
    payload = {
        "question_text": "Admin creation test",
        "subject": "General",
        "question_type": "SHORT_ANSWER",
        "marks": 1.0
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_ad"])
    assert res.status_code == 403
    assert "restricted to examiners" in res.json()["detail"].lower()


def test_student_create_question_forbidden(client, test_users):
    payload = {
        "question_text": "Student creation test",
        "subject": "General",
        "question_type": "SHORT_ANSWER",
        "marks": 1.0
    }
    res = client.post("/api/questions", json=payload, headers=test_users["h_st"])
    assert res.status_code == 403
    assert "restricted to examiners" in res.json()["detail"].lower()


def test_unauthenticated_create_question_unauthorized(client):
    payload = {
        "question_text": "Anon creation test",
        "subject": "General",
        "question_type": "SHORT_ANSWER",
        "marks": 1.0
    }
    client.cookies.clear()
    res = client.post("/api/questions", json=payload)
    assert res.status_code == 401


def test_admin_student_list_questions_forbidden(client, test_users):
    res_ad = client.get("/api/questions", headers=test_users["h_ad"])
    assert res_ad.status_code == 403

    res_st = client.get("/api/questions", headers=test_users["h_st"])
    assert res_st.status_code == 403


# ==========================================
# 4. OWNERSHIP & ISOLATION TESTS
# ==========================================

def test_examiner_list_own_questions(client, test_users):
    # Create question for Ex1
    client.post("/api/questions", json={"question_text": "Ex1 Q1", "subject": "Math", "question_type": "SHORT_ANSWER", "marks": 1.0}, headers=test_users["h_ex1"])
    # Create question for Ex2
    client.post("/api/questions", json={"question_text": "Ex2 Q1", "subject": "Math", "question_type": "SHORT_ANSWER", "marks": 1.0}, headers=test_users["h_ex2"])

    res1 = client.get("/api/questions", headers=test_users["h_ex1"])
    assert res1.status_code == 200
    items1 = res1.json()["items"]
    assert all(q["created_by"] == str(test_users["ex1"].id) for q in items1)
    assert any(q["question_text"] == "Ex1 Q1" for q in items1)
    assert not any(q["question_text"] == "Ex2 Q1" for q in items1)


def test_examiner_cannot_view_other_examiner_question(client, test_users):
    res_create = client.post("/api/questions", json={"question_text": "Ex2 Private Q", "subject": "Math", "question_type": "SHORT_ANSWER", "marks": 1.0}, headers=test_users["h_ex2"])
    q_id = res_create.json()["id"]

    res_get = client.get(f"/api/questions/{q_id}", headers=test_users["h_ex1"])
    assert res_get.status_code == 403
    assert "do not own this question" in res_get.json()["detail"].lower()


def test_examiner_cannot_update_other_examiner_question(client, test_users):
    res_create = client.post("/api/questions", json={"question_text": "Ex2 Private Q", "subject": "Math", "question_type": "SHORT_ANSWER", "marks": 1.0}, headers=test_users["h_ex2"])
    q_id = res_create.json()["id"]

    res_patch = client.patch(f"/api/questions/{q_id}", json={"question_text": "Hacked Q"}, headers=test_users["h_ex1"])
    assert res_patch.status_code == 403


def test_examiner_cannot_archive_other_examiner_question(client, test_users):
    res_create = client.post("/api/questions", json={"question_text": "Ex2 Private Q", "subject": "Math", "question_type": "SHORT_ANSWER", "marks": 1.0}, headers=test_users["h_ex2"])
    q_id = res_create.json()["id"]

    res_del = client.delete(f"/api/questions/{q_id}", headers=test_users["h_ex1"])
    assert res_del.status_code == 403


# ==========================================
# 5. UPDATE, SOFT DELETE & PAGINATION TESTS
# ==========================================

def test_examiner_update_question_options(client, test_users):
    res_create = client.post("/api/questions", json={
        "question_text": "Original MCQ?",
        "subject": "Science",
        "question_type": "MCQ",
        "marks": 2.0,
        "options": [
            {"option_text": "Opt 1", "option_order": 1, "is_correct": True},
            {"option_text": "Opt 2", "option_order": 2, "is_correct": False},
        ]
    }, headers=test_users["h_ex1"])
    q_id = res_create.json()["id"]

    update_payload = {
        "question_text": "Updated MCQ?",
        "options": [
            {"option_text": "Opt 1", "option_order": 1, "is_correct": False},
            {"option_text": "Opt 2 Correct", "option_order": 2, "is_correct": True},
        ]
    }
    res_update = client.patch(f"/api/questions/{q_id}", json=update_payload, headers=test_users["h_ex1"])
    assert res_update.status_code == 200
    data = res_update.json()
    assert data["question_text"] == "Updated MCQ?"
    correct = [o for o in data["options"] if o["is_correct"]]
    assert len(correct) == 1
    assert correct[0]["option_text"] == "Opt 2 Correct"


def test_examiner_archive_question_soft_delete(client, test_users):
    res_create = client.post("/api/questions", json={
        "question_text": "To be archived",
        "subject": "History",
        "question_type": "SHORT_ANSWER",
        "marks": 1.0
    }, headers=test_users["h_ex1"])
    q_id = res_create.json()["id"]

    res_del = client.delete(f"/api/questions/{q_id}", headers=test_users["h_ex1"])
    assert res_del.status_code == 200
    assert res_del.json()["is_active"] is False


def test_question_pagination(client, test_users):
    for i in range(15):
        client.post("/api/questions", json={
            "question_text": f"Paginated Q{i}",
            "subject": "Math",
            "question_type": "SHORT_ANSWER",
            "marks": 1.0
        }, headers=test_users["h_ex1"])

    res = client.get("/api/questions?page=1&page_size=10", headers=test_users["h_ex1"])
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 10
    assert data["page"] == 1
    assert data["page_size"] == 10
    assert data["total"] >= 15
    assert data["total_pages"] >= 2


def test_question_search_filter(client, test_users):
    client.post("/api/questions", json={"question_text": "Quantum Physics concept", "subject": "Physics", "topic": "Quantum", "question_type": "SHORT_ANSWER", "marks": 5.0}, headers=test_users["h_ex1"])
    client.post("/api/questions", json={"question_text": "Organic Chemistry synthesis", "subject": "Chemistry", "topic": "Organic", "question_type": "SHORT_ANSWER", "marks": 5.0}, headers=test_users["h_ex1"])

    res_search = client.get("/api/questions?search=Quantum", headers=test_users["h_ex1"])
    assert res_search.status_code == 200
    data = res_search.json()
    assert len(data["items"]) == 1
    assert "Quantum Physics" in data["items"][0]["question_text"]
