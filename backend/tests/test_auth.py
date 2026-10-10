import pytest
from datetime import timedelta
from fastapi import FastAPI, Depends
from fastapi.testclient import TestClient

from app.models.user import UserRole
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token
from app.core.dependencies import (
    get_current_user,
    require_student,
    require_examiner,
    require_admin,
)
from app.db.session import get_db

# ==========================================
# 1. REGISTRATION TESTS
# ==========================================

def test_register_student_success(client):
    payload = {
        "email": "student1@example.com",
        "password": "SecurePassword123!",
        "first_name": "John",
        "last_name": "Student",
        "role": "STUDENT"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["email"] == "student1@example.com"
    assert data["first_name"] == "John"
    assert data["last_name"] == "Student"
    assert data["role"] == "STUDENT"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email_rejected(client):
    payload = {
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
        "first_name": "Alice",
        "last_name": "Smith",
        "role": "STUDENT"
    }
    res1 = client.post("/api/auth/register", json=payload)
    assert res1.status_code == 201

    res2 = client.post("/api/auth/register", json=payload)
    assert res2.status_code == 400
    assert "already registered" in res2.json()["detail"].lower()


def test_register_weak_password_rejected(client):
    payload = {
        "email": "weak@example.com",
        "password": "short",
        "first_name": "Weak",
        "last_name": "Pass",
        "role": "STUDENT"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 422


def test_register_public_admin_rejected(client):
    payload = {
        "email": "hacker@example.com",
        "password": "SecurePassword123!",
        "first_name": "Bad",
        "last_name": "Actor",
        "role": "ADMIN"
    }
    response = client.post("/api/auth/register", json=payload)
    assert response.status_code == 400
    assert any(term in response.json()["detail"].lower() for term in ["student", "admin", "registration"])


def test_password_is_hashed_in_database(client, db):
    payload = {
        "email": "hashed@example.com",
        "password": "MySecretPassword123!",
        "first_name": "Hashed",
        "last_name": "User",
        "role": "STUDENT"
    }
    client.post("/api/auth/register", json=payload)
    user = user_repository.get_by_email(db, "hashed@example.com")
    assert user is not None
    assert user.password_hash != "MySecretPassword123!"
    assert user.password_hash.startswith("$argon2")


# ==========================================
# 2. LOGIN & COOKIE TESTS (SECURITY SPEC)
# ==========================================

def test_login_success_sets_httponly_cookie_and_excludes_raw_jwt(client):
    # Register user
    reg_payload = {
        "email": "login_sec@example.com",
        "password": "SecurePassword123!",
        "first_name": "Jane",
        "last_name": "Doe",
        "role": "STUDENT"
    }
    client.post("/api/auth/register", json=reg_payload)

    # Perform login
    login_payload = {
        "email": "login_sec@example.com",
        "password": "SecurePassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 200
    data = response.json()

    # 1. Verify safe user profile is returned
    assert "user" in data
    assert data["user"]["email"] == "login_sec@example.com"
    assert data["user"]["role"] == "STUDENT"
    assert "password" not in data["user"]
    assert "password_hash" not in data["user"]

    # 2. Verify raw access token is NOT exposed in JSON response
    assert "access_token" not in data
    assert "jwt" not in data
    assert "token" not in data

    # 3. Verify HttpOnly access_token cookie is set in response header
    set_cookie_header = response.headers.get("set-cookie", "")
    assert "access_token=" in set_cookie_header
    assert "httponly" in set_cookie_header.lower()


def test_login_wrong_password_fails(client):
    reg_payload = {
        "email": "wrongpwd@example.com",
        "password": "CorrectPassword123!",
        "first_name": "Bob",
        "last_name": "Test",
        "role": "STUDENT"
    }
    client.post("/api/auth/register", json=reg_payload)

    login_payload = {
        "email": "wrongpwd@example.com",
        "password": "WrongPassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_login_non_existent_user_fails(client):
    login_payload = {
        "email": "nobody@example.com",
        "password": "SomePassword123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401
    assert "incorrect email or password" in response.json()["detail"].lower()


def test_login_inactive_user_fails(client, db):
    user = user_repository.create_user(
        db=db,
        email="inactive@example.com",
        password_hash=hash_password("Password123!"),
        first_name="Inactive",
        last_name="User",
        role=UserRole.STUDENT
    )
    user.is_active = False
    db.commit()

    login_payload = {
        "email": "inactive@example.com",
        "password": "Password123!"
    }
    response = client.post("/api/auth/login", json=login_payload)
    assert response.status_code == 401


# ==========================================
# 3. GET /api/auth/me & JWT VALIDATION
# ==========================================

def test_get_me_with_valid_cookie(client):
    reg_payload = {
        "email": "me_cookie@example.com",
        "password": "SecurePassword123!",
        "first_name": "Cookie",
        "last_name": "User",
        "role": "STUDENT"
    }
    client.post("/api/auth/register", json=reg_payload)

    # Login automatically stores set-cookie in TestClient session
    client.post("/api/auth/login", json={"email": "me_cookie@example.com", "password": "SecurePassword123!"})

    res = client.get("/api/auth/me")
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "me_cookie@example.com"
    assert data["first_name"] == "Cookie"
    assert "password_hash" not in data


def test_get_me_with_valid_bearer_header(client, db):
    user = user_repository.create_user(
        db=db,
        email="me_bearer@example.com",
        password_hash=hash_password("SecurePassword123!"),
        first_name="Bearer",
        last_name="User",
        role=UserRole.EXAMINER
    )
    token = create_access_token({"sub": str(user.id), "role": "EXAMINER"})

    # Request /api/auth/me with Authorization Bearer header
    client.cookies.clear()
    headers = {"Authorization": f"Bearer {token}"}
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 200
    assert res.json()["email"] == "me_bearer@example.com"


def test_get_me_unauthenticated_fails(client):
    client.cookies.clear()
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_get_me_expired_token_fails(client, db):
    user = user_repository.create_user(
        db=db,
        email="expired@example.com",
        password_hash=hash_password("Password123!"),
        first_name="Expired",
        last_name="Token",
        role=UserRole.STUDENT
    )
    expired_token = create_access_token({"sub": str(user.id)}, expires_delta=timedelta(seconds=-10))

    client.cookies.clear()
    headers = {"Authorization": f"Bearer {expired_token}"}
    res = client.get("/api/auth/me", headers=headers)
    assert res.status_code == 401


# ==========================================
# 4. LOGOUT TEST
# ==========================================

def test_logout_clears_cookie(client):
    client.cookies.set("access_token", "fake_token_value")
    res = client.post("/api/auth/logout")
    assert res.status_code == 200
    assert "Logged out successfully" in res.json()["message"]


# ==========================================
# 5. RBAC PERMISSION TESTS
# ==========================================

def test_rbac_permissions(db):
    """Tests RBAC dependencies via isolated test app instance."""
    test_app = FastAPI()

    @test_app.get("/student-route")
    def student_endpoint(user=Depends(require_student)):
        return {"msg": "student access granted"}

    @test_app.get("/examiner-route")
    def examiner_endpoint(user=Depends(require_examiner)):
        return {"msg": "examiner access granted"}

    @test_app.get("/admin-route")
    def admin_endpoint(user=Depends(require_admin)):
        return {"msg": "admin access granted"}

    def override_get_db():
        yield db

    test_app.dependency_overrides[get_db] = override_get_db
    test_client = TestClient(test_app)

    # Create users
    student = user_repository.create_user(db, "rbac_student@ex.com", hash_password("P@ss123!"), "S", "User", UserRole.STUDENT)
    examiner = user_repository.create_user(db, "rbac_examiner@ex.com", hash_password("P@ss123!"), "E", "User", UserRole.EXAMINER)
    admin = user_repository.create_user(db, "rbac_admin@ex.com", hash_password("P@ss123!"), "A", "User", UserRole.ADMIN)

    t_student = create_access_token({"sub": str(student.id), "role": "STUDENT"})
    t_examiner = create_access_token({"sub": str(examiner.id), "role": "EXAMINER"})
    t_admin = create_access_token({"sub": str(admin.id), "role": "ADMIN"})

    # Student checks
    r1 = test_client.get("/student-route", headers={"Authorization": f"Bearer {t_student}"})
    assert r1.status_code == 200

    r2 = test_client.get("/examiner-route", headers={"Authorization": f"Bearer {t_student}"})
    assert r2.status_code == 403

    r3 = test_client.get("/admin-route", headers={"Authorization": f"Bearer {t_student}"})
    assert r3.status_code == 403

    # Examiner checks
    r4 = test_client.get("/examiner-route", headers={"Authorization": f"Bearer {t_examiner}"})
    assert r4.status_code == 200

    r5 = test_client.get("/admin-route", headers={"Authorization": f"Bearer {t_examiner}"})
    assert r5.status_code == 403

    # Admin checks
    r6 = test_client.get("/admin-route", headers={"Authorization": f"Bearer {t_admin}"})
    assert r6.status_code == 200
