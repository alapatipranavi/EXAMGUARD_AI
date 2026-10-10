import pytest
from app.models.user import UserRole, User
from app.repositories.user_repository import user_repository
from app.repositories.academic_repository import academic_repository
from app.core.security import hash_password, create_access_token


def create_user(
    db,
    email: str,
    role: UserRole,
    first_name: str = "Test",
    last_name: str = "User",
    password: str = "Password123!",
    is_active: bool = True,
) -> User:
    u = user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password(password),
        first_name=first_name,
        last_name=last_name,
        role=role,
    )
    if not is_active:
        u.is_active = False
        db.commit()
        db.refresh(u)
    return u


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


def test_unauthenticated_requests(client):
    """Endpoints require authentication and reject unauthenticated requests."""
    assert client.get("/api/users/me/profile").status_code == 401
    assert client.put("/api/users/me/profile", json={"first_name": "New"}).status_code == 401
    assert client.put("/api/users/me/password", json={"current_password": "a", "new_password": "b"}).status_code == 401
    assert client.get("/api/users/me/settings").status_code == 401
    assert client.put("/api/users/me/settings", json={}).status_code == 401


def test_get_profile_student(db, client):
    """Student profile returns resolved academic hierarchy information."""
    col = academic_repository.create_college(db, "Apex Engineering College", "AEC")
    dept = academic_repository.create_department(db, col.id, "Computer Science", "CSE")
    sec = academic_repository.create_section(db, dept.id, 2, "Section A", "SEC-A")

    student = create_user(db, "student1@test.com", UserRole.STUDENT, first_name="John", last_name="Doe")
    academic_repository.update_student_academic_profile(db, student, col.id, dept.id, 2, sec.id)

    cookies = get_auth_cookies(student)
    response = client.get("/api/users/me/profile", cookies=cookies)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "student1@test.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Doe"
    assert data["role"] == "STUDENT"
    assert data["is_active"] is True
    assert data["college_name"] == "Apex Engineering College"
    assert data["college_code"] == "AEC"
    assert data["department_name"] == "Computer Science"
    assert data["department_code"] == "CSE"
    assert data["year_of_study"] == 2
    assert data["section_name"] == "Section A"
    assert data["section_code"] == "SEC-A"


def test_get_profile_examiner(db, client):
    """Examiner profile returns assigned college details without student academic fields."""
    col = academic_repository.create_college(db, "National Tech Institute", "NTI")
    examiner = create_user(db, "prof1@test.com", UserRole.EXAMINER, first_name="Dr. Alan", last_name="Turing")
    academic_repository.update_user_college(db, examiner, col.id)

    cookies = get_auth_cookies(examiner)
    response = client.get("/api/users/me/profile", cookies=cookies)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "prof1@test.com"
    assert data["first_name"] == "Dr. Alan"
    assert data["last_name"] == "Turing"
    assert data["role"] == "EXAMINER"
    assert data["college_name"] == "National Tech Institute"
    assert data["college_code"] == "NTI"
    assert data["department_name"] is None
    assert data["year_of_study"] is None
    assert data["section_name"] is None


def test_get_profile_admin(db, client):
    """Admin profile returns administrative account info."""
    admin = create_user(db, "admin1@test.com", UserRole.ADMIN, first_name="Chief", last_name="Admin")
    cookies = get_auth_cookies(admin)
    response = client.get("/api/users/me/profile", cookies=cookies)

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "admin1@test.com"
    assert data["role"] == "ADMIN"
    assert data["college_id"] is None
    assert data["college_name"] is None


def test_update_profile_success(db, client):
    """Updating first_name and last_name succeeds and trims whitespace."""
    user = create_user(db, "user_update@test.com", UserRole.STUDENT, first_name="Old", last_name="Name")
    cookies = get_auth_cookies(user)

    payload = {
        "first_name": "  UpdatedFirst  ",
        "last_name": "  UpdatedLast  ",
    }
    response = client.put("/api/users/me/profile", json=payload, cookies=cookies)
    assert response.status_code == 200
    data = response.json()
    assert data["first_name"] == "UpdatedFirst"
    assert data["last_name"] == "UpdatedLast"

    # Verify persisted in database
    db.refresh(user)
    assert user.first_name == "UpdatedFirst"
    assert user.last_name == "UpdatedLast"


def test_update_profile_validation_rejects_empty_name(db, client):
    """Updating first_name to empty or all whitespace is rejected."""
    user = create_user(db, "user_empty@test.com", UserRole.STUDENT)
    cookies = get_auth_cookies(user)

    response = client.put("/api/users/me/profile", json={"first_name": "   ", "last_name": "Valid"}, cookies=cookies)
    assert response.status_code == 422


def test_update_profile_rejects_forbidden_fields(db, client):
    """Privileged fields like role, email, is_active, college_id cannot be altered through profile update."""
    user = create_user(db, "user_forbidden@test.com", UserRole.STUDENT)
    cookies = get_auth_cookies(user)

    # Attempt to escalate role to ADMIN
    payload = {
        "first_name": "Hacker",
        "last_name": "Attempt",
        "role": "ADMIN",
    }
    response = client.put("/api/users/me/profile", json=payload, cookies=cookies)
    assert response.status_code == 422

    # Attempt to change email
    payload = {
        "first_name": "Hacker",
        "email": "hacked@example.com",
    }
    response = client.put("/api/users/me/profile", json=payload, cookies=cookies)
    assert response.status_code == 422


def test_change_password_success(db, client):
    """Valid password change succeeds and updates credentials for authentication."""
    user = create_user(db, "pwd_test@test.com", UserRole.STUDENT, password="OldPassword123!")
    cookies = get_auth_cookies(user)

    payload = {
        "current_password": "OldPassword123!",
        "new_password": "NewSecurePassword456!",
    }
    response = client.put("/api/users/me/password", json=payload, cookies=cookies)
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed successfully."

    # Test login with old password fails
    login_old = client.post("/api/auth/login", json={"email": "pwd_test@test.com", "password": "OldPassword123!"})
    assert login_old.status_code == 401

    # Test login with new password succeeds
    login_new = client.post("/api/auth/login", json={"email": "pwd_test@test.com", "password": "NewSecurePassword456!"})
    assert login_new.status_code == 200


def test_change_password_incorrect_current_password(db, client):
    """Providing wrong current password is rejected with 400 Bad Request."""
    user = create_user(db, "pwd_fail@test.com", UserRole.STUDENT, password="CorrectPassword123!")
    cookies = get_auth_cookies(user)

    payload = {
        "current_password": "WrongPassword123!",
        "new_password": "BrandNewPassword789!",
    }
    response = client.put("/api/users/me/password", json=payload, cookies=cookies)
    assert response.status_code == 400
    assert "Current password is incorrect" in response.json()["detail"]


def test_change_password_too_short(db, client):
    """Short new password (< 8 chars) is rejected."""
    user = create_user(db, "pwd_short@test.com", UserRole.STUDENT, password="CorrectPassword123!")
    cookies = get_auth_cookies(user)

    payload = {
        "current_password": "CorrectPassword123!",
        "new_password": "short",
    }
    response = client.put("/api/users/me/password", json=payload, cookies=cookies)
    assert response.status_code == 422


def test_notification_settings_flow(db, client):
    """Notification settings can be retrieved and updated per user."""
    user = create_user(db, "settings_user@test.com", UserRole.STUDENT)
    cookies = get_auth_cookies(user)

    # 1. Fetch default settings
    res = client.get("/api/users/me/settings", cookies=cookies)
    assert res.status_code == 200
    defaults = res.json()
    assert defaults["exam_reminders"] is True
    assert defaults["result_notifications"] is True
    assert defaults["integrity_alerts"] is True
    assert defaults["system_updates"] is True

    # 2. Update settings
    update_payload = {
        "exam_reminders": False,
        "result_notifications": True,
        "integrity_alerts": False,
        "system_updates": True,
    }
    res_update = client.put("/api/users/me/settings", json=update_payload, cookies=cookies)
    assert res_update.status_code == 200
    assert res_update.json()["exam_reminders"] is False
    assert res_update.json()["integrity_alerts"] is False

    # 3. Retrieve updated settings again
    res_again = client.get("/api/users/me/settings", cookies=cookies)
    assert res_again.status_code == 200
    assert res_again.json()["exam_reminders"] is False
    assert res_again.json()["integrity_alerts"] is False
