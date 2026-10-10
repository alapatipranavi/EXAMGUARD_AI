import pytest
from app.models.user import UserRole
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token


@pytest.fixture
def dash_users(db):
    st = user_repository.create_user(db, "dash_st@test.com", hash_password("Pass123!"), "Student", "User", UserRole.STUDENT)
    ex = user_repository.create_user(db, "dash_ex@test.com", hash_password("Pass123!"), "Examiner", "User", UserRole.EXAMINER)
    ad = user_repository.create_user(db, "dash_ad@test.com", hash_password("Pass123!"), "Admin", "User", UserRole.ADMIN)

    t_st = create_access_token({"sub": str(st.id), "role": "STUDENT"})
    t_ex = create_access_token({"sub": str(ex.id), "role": "EXAMINER"})
    t_ad = create_access_token({"sub": str(ad.id), "role": "ADMIN"})

    return {
        "h_st": {"Authorization": f"Bearer {t_st}"},
        "h_ex": {"Authorization": f"Bearer {t_ex}"},
        "h_ad": {"Authorization": f"Bearer {t_ad}"},
    }


def test_dashboard_summary_student(client, dash_users):
    res = client.get("/api/dashboard/summary", headers=dash_users["h_st"])
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "STUDENT"
    assert "stats" in data
    assert data["stats"]["upcoming_exams"] == 0


def test_dashboard_summary_examiner(client, dash_users):
    res = client.get("/api/dashboard/summary", headers=dash_users["h_ex"])
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "EXAMINER"
    assert "total_questions" in data["stats"]
    assert "active_questions" in data["stats"]


def test_dashboard_summary_admin(client, dash_users):
    res = client.get("/api/dashboard/summary", headers=dash_users["h_ad"])
    assert res.status_code == 200
    data = res.json()
    assert data["role"] == "ADMIN"
    assert "total_students" in data["stats"]
    assert "total_examiners" in data["stats"]


def test_dashboard_summary_unauthenticated(client):
    client.cookies.clear()
    res = client.get("/api/dashboard/summary")
    assert res.status_code == 401
