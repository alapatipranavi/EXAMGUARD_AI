import pytest
from app.models.user import UserRole, User
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token


def create_test_user(db, email: str, role: UserRole, is_active: bool = True, first_name: str = "Test", last_name: str = "User") -> User:
    return user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first_name,
        last_name=last_name,
        role=role,
    )


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


# ============================================================================
# 1. PUBLIC SELF-REGISTRATION TESTS
# ============================================================================

def test_public_registration_student_success(client):
    payload = {
        "email": "public_student@example.com",
        "password": "Password123!",
        "first_name": "Public",
        "last_name": "Student",
        "role": "STUDENT"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["role"] == "STUDENT"
    assert data["email"] == "public_student@example.com"


def test_public_registration_examiner_rejected(client):
    payload = {
        "email": "public_examiner@example.com",
        "password": "Password123!",
        "first_name": "Public",
        "last_name": "Examiner",
        "role": "EXAMINER"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "only student self-registration" in res.json()["detail"].lower()


def test_public_registration_admin_rejected(client):
    payload = {
        "email": "public_admin@example.com",
        "password": "Password123!",
        "first_name": "Public",
        "last_name": "Admin",
        "role": "ADMIN"
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400


# ============================================================================
# 2. ADMIN USER LISTING & FILTERING TESTS
# ============================================================================

def test_admin_get_users_unauthenticated(client):
    res = client.get("/api/admin/users")
    assert res.status_code == 401


def test_admin_get_users_non_admin_forbidden(client, db):
    student = create_test_user(db, "student_list@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(student)
    res = client.get("/api/admin/users", cookies=cookies)
    assert res.status_code == 403


def test_admin_get_users_success(client, db):
    admin = create_test_user(db, "admin_list@example.com", UserRole.ADMIN)
    create_test_user(db, "u1@example.com", UserRole.STUDENT, first_name="Alice")
    create_test_user(db, "u2@example.com", UserRole.EXAMINER, first_name="Bob")

    cookies = get_auth_cookies(admin)
    res = client.get("/api/admin/users", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert data["total"] >= 3


def test_admin_get_users_filter_role(client, db):
    admin = create_test_user(db, "admin_rf@example.com", UserRole.ADMIN)
    create_test_user(db, "student_rf@example.com", UserRole.STUDENT)
    create_test_user(db, "examiner_rf@example.com", UserRole.EXAMINER)

    cookies = get_auth_cookies(admin)
    res = client.get("/api/admin/users?role=EXAMINER", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert all(item["role"] == "EXAMINER" for item in data["items"])


def test_admin_get_users_filter_status(client, db):
    admin = create_test_user(db, "admin_sf@example.com", UserRole.ADMIN)
    u_active = create_test_user(db, "active_user@example.com", UserRole.STUDENT)
    u_inactive = create_test_user(db, "inactive_user@example.com", UserRole.STUDENT)
    u_inactive.is_active = False
    db.commit()
    db.refresh(u_inactive)

    cookies = get_auth_cookies(admin)
    res_active = client.get("/api/admin/users?is_active=true", cookies=cookies)
    assert res_active.status_code == 200
    assert all(item["is_active"] is True for item in res_active.json()["items"])

    res_inactive = client.get("/api/admin/users?is_active=false", cookies=cookies)
    assert res_inactive.status_code == 200
    assert all(item["is_active"] is False for item in res_inactive.json()["items"])


def test_admin_get_users_search(client, db):
    admin = create_test_user(db, "admin_srch@example.com", UserRole.ADMIN)
    create_test_user(db, "unique_john@example.com", UserRole.STUDENT, first_name="Johnathon")
    create_test_user(db, "other@example.com", UserRole.STUDENT, first_name="Sam")

    cookies = get_auth_cookies(admin)
    res = client.get("/api/admin/users?search=Johnathon", cookies=cookies)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["first_name"] == "Johnathon"


def test_admin_get_users_pagination(client, db):
    admin = create_test_user(db, "admin_page@example.com", UserRole.ADMIN)
    for i in range(5):
        create_test_user(db, f"p_user_{i}@example.com", UserRole.STUDENT)

    cookies = get_auth_cookies(admin)
    res = client.get("/api/admin/users?page=1&page_size=2", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total"] >= 6


# ============================================================================
# 3. ADMIN PROVISION USER TESTS
# ============================================================================

def test_admin_create_examiner_success(client, db):
    admin = create_test_user(db, "admin_cre_ex@example.com", UserRole.ADMIN)
    cookies = get_auth_cookies(admin)

    payload = {
        "email": "prov_examiner@example.com",
        "password": "Password123!",
        "first_name": "Prov",
        "last_name": "Examiner",
        "role": "EXAMINER"
    }
    res = client.post("/api/admin/users", json=payload, cookies=cookies)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "prov_examiner@example.com"
    assert data["role"] == "EXAMINER"


def test_admin_create_student_success(client, db):
    admin = create_test_user(db, "admin_cre_st@example.com", UserRole.ADMIN)
    cookies = get_auth_cookies(admin)

    payload = {
        "email": "prov_student@example.com",
        "password": "Password123!",
        "first_name": "Prov",
        "last_name": "Student",
        "role": "STUDENT"
    }
    res = client.post("/api/admin/users", json=payload, cookies=cookies)
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "prov_student@example.com"
    assert data["role"] == "STUDENT"


def test_admin_create_admin_rejected(client, db):
    admin = create_test_user(db, "admin_cre_adm@example.com", UserRole.ADMIN)
    cookies = get_auth_cookies(admin)

    payload = {
        "email": "prov_admin@example.com",
        "password": "Password123!",
        "first_name": "Prov",
        "last_name": "Admin",
        "role": "ADMIN"
    }
    res = client.post("/api/admin/users", json=payload, cookies=cookies)
    assert res.status_code == 400


def test_non_admin_create_user_forbidden(client, db):
    examiner = create_test_user(db, "examiner_cre_forbid@example.com", UserRole.EXAMINER)
    cookies = get_auth_cookies(examiner)

    payload = {
        "email": "forbidden_prov@example.com",
        "password": "Password123!",
        "first_name": "Forbidden",
        "last_name": "User",
        "role": "STUDENT"
    }
    res = client.post("/api/admin/users", json=payload, cookies=cookies)
    assert res.status_code == 403


# ============================================================================
# 4. USER STATUS TOGGLE & INACTIVE DEACTIVATION ENFORCEMENT
# ============================================================================

def test_admin_update_user_status_deactivate_and_activate(client, db):
    admin = create_test_user(db, "admin_stat@example.com", UserRole.ADMIN)
    target = create_test_user(db, "target_stat@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(admin)

    # Deactivate
    res1 = client.put(f"/api/admin/users/{target.id}/status", json={"is_active": False}, cookies=cookies)
    assert res1.status_code == 200
    assert res1.json()["is_active"] is False

    # Reactivate
    res2 = client.put(f"/api/admin/users/{target.id}/status", json={"is_active": True}, cookies=cookies)
    assert res2.status_code == 200
    assert res2.json()["is_active"] is True


def test_deactivated_user_cannot_login(client, db):
    user = create_test_user(db, "deact_login@example.com", UserRole.STUDENT)
    user.is_active = False
    db.commit()
    db.refresh(user)

    res = client.post("/api/auth/login", json={"email": "deact_login@example.com", "password": "Password123!"})
    assert res.status_code == 401
    assert "incorrect email or password" in res.json()["detail"].lower()


def test_deactivated_user_jwt_rejected(client, db):
    user = create_test_user(db, "deact_jwt@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(user)

    # Deactivate user after issuing token
    user.is_active = False
    db.commit()
    db.refresh(user)

    # Call endpoint requiring authentication
    res = client.get("/api/auth/me", cookies=cookies)
    assert res.status_code == 401
    assert "inactive" in res.json()["detail"].lower()


# ============================================================================
# 5. USER ROLE UPDATE TESTS
# ============================================================================

def test_admin_update_user_role_success(client, db):
    admin = create_test_user(db, "admin_role_upd@example.com", UserRole.ADMIN)
    target = create_test_user(db, "target_role_upd@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(admin)

    res = client.put(f"/api/admin/users/{target.id}/role", json={"role": "EXAMINER"}, cookies=cookies)
    assert res.status_code == 200
    assert res.json()["role"] == "EXAMINER"

    res_back = client.put(f"/api/admin/users/{target.id}/role", json={"role": "STUDENT"}, cookies=cookies)
    assert res_back.status_code == 200
    assert res_back.json()["role"] == "STUDENT"


def test_admin_update_admin_role_rejected(client, db):
    admin1 = create_test_user(db, "admin1_role@example.com", UserRole.ADMIN)
    admin2 = create_test_user(db, "admin2_role@example.com", UserRole.ADMIN)
    cookies = get_auth_cookies(admin1)

    # Cannot edit an admin's role
    res = client.put(f"/api/admin/users/{admin2.id}/role", json={"role": "STUDENT"}, cookies=cookies)
    assert res.status_code == 400


def test_non_admin_update_status_or_role_forbidden(client, db):
    student = create_test_user(db, "student_non_adm@example.com", UserRole.STUDENT)
    target = create_test_user(db, "target_non_adm@example.com", UserRole.STUDENT)
    cookies = get_auth_cookies(student)

    res1 = client.put(f"/api/admin/users/{target.id}/status", json={"is_active": False}, cookies=cookies)
    assert res1.status_code == 403

    res2 = client.put(f"/api/admin/users/{target.id}/role", json={"role": "EXAMINER"}, cookies=cookies)
    assert res2.status_code == 403
