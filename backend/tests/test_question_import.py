import io
import pytest
from app.models.user import UserRole
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token


@pytest.fixture
def import_users(db):
    ex = user_repository.create_user(db, "imp_ex@test.com", hash_password("Pass123!"), "Imp", "Ex", UserRole.EXAMINER)
    st = user_repository.create_user(db, "imp_st@test.com", hash_password("Pass123!"), "Imp", "St", UserRole.STUDENT)
    ad = user_repository.create_user(db, "imp_ad@test.com", hash_password("Pass123!"), "Imp", "Ad", UserRole.ADMIN)

    t_ex = create_access_token({"sub": str(ex.id), "role": "EXAMINER"})
    t_st = create_access_token({"sub": str(st.id), "role": "STUDENT"})
    t_ad = create_access_token({"sub": str(ad.id), "role": "ADMIN"})

    return {
        "ex": ex,
        "h_ex": {"Authorization": f"Bearer {t_ex}"},
        "h_st": {"Authorization": f"Bearer {t_st}"},
        "h_ad": {"Authorization": f"Bearer {t_ad}"},
    }


def test_parse_csv_valid_and_invalid_rows(client, import_users):
    csv_content = (
        "question_text,subject,question_type,difficulty,marks,option_a,option_b,correct_options\n"
        "What is 2+2?,Math,MCQ,EASY,2.0,3,4,b\n"
        "Invalid MCQ?,Math,MCQ,EASY,2.0,3,4,none\n"
    )
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}
    res = client.post("/api/questions/import/csv/parse", files=files, headers=import_users["h_ex"])
    assert res.status_code == 200
    data = res.json()
    assert data["total_rows"] == 2
    assert data["valid_rows_count"] == 1
    assert data["invalid_rows_count"] == 1
    assert data["rows"][0]["is_valid"] is True
    assert data["rows"][1]["is_valid"] is False


def test_confirm_import_csv(client, import_users):
    payload = {
        "source": "CSV_IMPORT",
        "questions": [
            {
                "question_text": "CSV Imported Q1",
                "subject": "Physics",
                "question_type": "SHORT_ANSWER",
                "difficulty": "MEDIUM",
                "marks": 3.0
            }
        ]
    }
    res = client.post("/api/questions/import/confirm", json=payload, headers=import_users["h_ex"])
    assert res.status_code == 201
    items = res.json()
    assert len(items) == 1
    assert items[0]["question_text"] == "CSV Imported Q1"
    assert items[0]["source"] == "CSV_IMPORT"


def test_import_csv_forbidden_for_student_and_admin(client, import_users):
    csv_content = "question_text,subject,question_type,marks\nQ1,Math,SHORT_ANSWER,1.0\n"
    files = {"file": ("test.csv", io.BytesIO(csv_content.encode("utf-8")), "text/csv")}

    r_st = client.post("/api/questions/import/csv/parse", files=files, headers=import_users["h_st"])
    assert r_st.status_code == 403

    r_ad = client.post("/api/questions/import/csv/parse", files=files, headers=import_users["h_ad"])
    assert r_ad.status_code == 403
