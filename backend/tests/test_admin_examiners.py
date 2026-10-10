import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.academic import College
from app.models.exam import Exam, ExamStatus, ExamTargetType
from app.repositories.user_repository import user_repository
from app.core.security import hash_password, create_access_token


def create_user(
    db,
    email: str,
    role: UserRole,
    first_name: str = "Test",
    last_name: str = "User",
    is_active: bool = True,
    college_id: uuid.UUID = None,
) -> User:
    return user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first_name,
        last_name=last_name,
        role=role,
        college_id=college_id,
    )


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


# ============================================================================
# 1. AUTHENTICATION & RBAC TESTS
# ============================================================================

def test_admin_examiners_auth_required(client):
    """Unauthenticated calls to /api/admin/examiners must return 401."""
    res = client.get("/api/admin/examiners")
    assert res.status_code == 401


def test_admin_examiners_rbac_forbidden(client, db):
    """STUDENT and EXAMINER callers must receive 403 Forbidden."""
    student = create_user(db, "student_ex_rbac@example.com", UserRole.STUDENT)
    examiner = create_user(db, "examiner_ex_rbac@example.com", UserRole.EXAMINER)

    # Student -> 403
    res_student = client.get("/api/admin/examiners", cookies=get_auth_cookies(student))
    assert res_student.status_code == 403

    # Examiner -> 403
    res_examiner = client.get("/api/admin/examiners", cookies=get_auth_cookies(examiner))
    assert res_examiner.status_code == 403


def test_admin_examiners_admin_access_success(client, db):
    """ADMIN role must successfully access /api/admin/examiners with 200."""
    admin = create_user(db, "admin_ex_access@example.com", UserRole.ADMIN)
    res = client.get("/api/admin/examiners", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "summary" in data


# ============================================================================
# 2. ROLE ISOLATION & FILTERING TESTS
# ============================================================================

def test_admin_examiners_only_examiners_returned(client, db):
    """Ensure the endpoint strictly returns only users with role=EXAMINER."""
    admin = create_user(db, "admin_ex_iso@example.com", UserRole.ADMIN)
    examiner1 = create_user(db, "ex_prof_alpha@university.edu", UserRole.EXAMINER, first_name="Alan", last_name="Turing")
    examiner2 = create_user(db, "ex_prof_beta@university.edu", UserRole.EXAMINER, first_name="Grace", last_name="Hopper")
    student1 = create_user(db, "student_not_examiner@university.edu", UserRole.STUDENT, first_name="Ada", last_name="Lovelace")

    res = client.get("/api/admin/examiners", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    returned_roles = [item["role"] for item in data["items"]]
    assert all(r == "EXAMINER" for r in returned_roles)
    returned_emails = [item["email"] for item in data["items"]]
    assert examiner1.email in returned_emails
    assert examiner2.email in returned_emails
    assert student1.email not in returned_emails
    assert admin.email not in returned_emails


def test_admin_examiners_search_by_name_and_email(client, db):
    """Case-insensitive search by examiner first name, last name, or email."""
    admin = create_user(db, "admin_ex_search@example.com", UserRole.ADMIN)
    e1 = create_user(db, "unique_stephen@university.edu", UserRole.EXAMINER, first_name="Stephen", last_name="Hawking")
    e2 = create_user(db, "richard_feynman@university.edu", UserRole.EXAMINER, first_name="Richard", last_name="Feynman")

    # Search by first name
    res = client.get("/api/admin/examiners?search=stephen", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    emails = [item["email"] for item in res.json()["items"]]
    assert e1.email in emails
    assert e2.email not in emails

    # Search by last name (case-insensitive)
    res = client.get("/api/admin/examiners?search=FEYNMAN", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    emails = [item["email"] for item in res.json()["items"]]
    assert e2.email in emails
    assert e1.email not in emails

    # Search by email fragment
    res = client.get("/api/admin/examiners?search=unique_stephen", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    emails = [item["email"] for item in res.json()["items"]]
    assert e1.email in emails
    assert e2.email not in emails


def test_admin_examiners_college_and_status_filters(client, db):
    """Filter examiners by college and account active status."""
    admin = create_user(db, "admin_ex_col_filter@example.com", UserRole.ADMIN)

    college = College(name="Oxford Science College", code=f"OSC_{uuid.uuid4().hex[:4]}", is_active=True)
    db.add(college)
    db.commit()
    db.refresh(college)

    assigned_ex = create_user(
        db,
        f"assigned_{uuid.uuid4().hex[:6]}@osc.edu",
        UserRole.EXAMINER,
        first_name="Marie",
        last_name="Curie",
        college_id=college.id,
    )

    unassigned_ex = create_user(
        db,
        f"unassigned_{uuid.uuid4().hex[:6]}@general.edu",
        UserRole.EXAMINER,
        first_name="Max",
        last_name="Planck",
    )

    inact_ex = create_user(
        db,
        f"inact_{uuid.uuid4().hex[:6]}@osc.edu",
        UserRole.EXAMINER,
        college_id=college.id,
    )
    inact_ex.is_active = False
    db.commit()

    # 1. Filter by college_id
    res_col = client.get(f"/api/admin/examiners?college_id={college.id}", cookies=get_auth_cookies(admin))
    assert res_col.status_code == 200
    col_items = res_col.json()["items"]
    assert any(item["id"] == str(assigned_ex.id) for item in col_items)
    assert not any(item["id"] == str(unassigned_ex.id) for item in col_items)

    # Verify resolved college details
    curie_item = next(item for item in col_items if item["id"] == str(assigned_ex.id))
    assert curie_item["college_name"] == college.name
    assert curie_item["college_code"] == college.code

    # 2. Filter by status: active only
    res_act = client.get(f"/api/admin/examiners?is_active=true", cookies=get_auth_cookies(admin))
    assert res_act.status_code == 200
    act_ids = [item["id"] for item in res_act.json()["items"]]
    assert str(assigned_ex.id) in act_ids
    assert str(inact_ex.id) not in act_ids

    # 3. Filter by status: inactive only
    res_inact = client.get(f"/api/admin/examiners?is_active=false", cookies=get_auth_cookies(admin))
    assert res_inact.status_code == 200
    inact_ids = [item["id"] for item in res_inact.json()["items"]]
    assert str(inact_ex.id) in inact_ids
    assert str(assigned_ex.id) not in inact_ids

    # 4. Combined: college + status
    res_comb = client.get(f"/api/admin/examiners?college_id={college.id}&is_active=false", cookies=get_auth_cookies(admin))
    assert res_comb.status_code == 200
    comb_ids = [item["id"] for item in res_comb.json()["items"]]
    assert str(inact_ex.id) in comb_ids
    assert str(assigned_ex.id) not in comb_ids


def test_admin_examiners_pagination(client, db):
    """Pagination parameters page and page_size work correctly."""
    admin = create_user(db, "admin_ex_paging@example.com", UserRole.ADMIN)
    res = client.get("/api/admin/examiners?page=1&page_size=2", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2
    assert "total_pages" in data


# ============================================================================
# 3. EXAMINER DETAIL & EXAM ACTIVITY TESTS
# ============================================================================

def test_admin_examiner_detail_success_with_exams(client, db):
    """Admin can retrieve full examiner details and accurate exam counts/recent exams."""
    admin = create_user(db, "admin_ex_det_user@example.com", UserRole.ADMIN)

    college = College(name="Cambridge Polytechnic", code=f"CP_{uuid.uuid4().hex[:4]}", is_active=True)
    db.add(college)
    db.commit()
    db.refresh(college)

    examiner = create_user(
        db,
        f"examiner_det_{uuid.uuid4().hex[:6]}@poly.edu",
        UserRole.EXAMINER,
        first_name="Niels",
        last_name="Bohr",
        college_id=college.id,
    )

    other_examiner = create_user(
        db,
        f"other_ex_{uuid.uuid4().hex[:6]}@poly.edu",
        UserRole.EXAMINER,
    )

    # Create exams for examiner
    exam_pub = Exam(
        title="Quantum Mechanics 101",
        subject="Physics",
        duration_minutes=90,
        total_marks=100.0,
        passing_marks=50.0,
        status=ExamStatus.PUBLISHED,
        created_by=examiner.id,
        target_type=ExamTargetType.COLLEGE,
    )
    exam_draft = Exam(
        title="Thermodynamics Draft",
        subject="Physics",
        duration_minutes=60,
        total_marks=50.0,
        passing_marks=25.0,
        status=ExamStatus.DRAFT,
        created_by=examiner.id,
    )
    # Unrelated exam from other examiner
    exam_unrelated = Exam(
        title="Unrelated Exam",
        subject="Chemistry",
        duration_minutes=60,
        status=ExamStatus.PUBLISHED,
        created_by=other_examiner.id,
    )
    db.add_all([exam_pub, exam_draft, exam_unrelated])
    db.commit()

    res = client.get(f"/api/admin/examiners/{examiner.id}", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(examiner.id)
    assert data["first_name"] == "Niels"
    assert data["last_name"] == "Bohr"
    assert data["role"] == "EXAMINER"
    assert data["college_name"] == "Cambridge Polytechnic"
    assert data["total_exams_created"] == 2
    assert data["published_exams_count"] == 1
    assert data["draft_exams_count"] == 1
    assert len(data["recent_exams"]) == 2
    titles = [e["title"] for e in data["recent_exams"]]
    assert "Quantum Mechanics 101" in titles
    assert "Thermodynamics Draft" in titles
    assert "Unrelated Exam" not in titles


def test_admin_examiner_detail_role_isolation(client, db):
    """Admin cannot view Student or Admin user records through /api/admin/examiners/{id}."""
    admin = create_user(db, "admin_ex_iso_tester@example.com", UserRole.ADMIN)
    student = create_user(db, "student_not_an_examiner@example.com", UserRole.STUDENT)
    other_admin = create_user(db, "other_admin_tester@example.com", UserRole.ADMIN)

    # Attempt to query Student ID via examiner detail endpoint -> 404
    res_st = client.get(f"/api/admin/examiners/{student.id}", cookies=get_auth_cookies(admin))
    assert res_st.status_code == 404
    assert "examiner not found" in res_st.json()["detail"].lower()

    # Attempt to query Admin ID via examiner detail endpoint -> 404
    res_ad = client.get(f"/api/admin/examiners/{other_admin.id}", cookies=get_auth_cookies(admin))
    assert res_ad.status_code == 404
    assert "examiner not found" in res_ad.json()["detail"].lower()

    # Non-existent UUID -> 404
    fake_id = uuid.uuid4()
    res_fake = client.get(f"/api/admin/examiners/{fake_id}", cookies=get_auth_cookies(admin))
    assert res_fake.status_code == 404


# ============================================================================
# 4. STATUS TOGGLE & SECURITY TESTS
# ============================================================================

def test_admin_examiner_status_toggle(client, db):
    """Admin can activate and deactivate an examiner via existing Admin User Management API."""
    admin = create_user(db, "admin_ex_status_act@example.com", UserRole.ADMIN)
    examiner = create_user(db, "examiner_toggle_act@example.com", UserRole.EXAMINER, is_active=True)

    # Deactivate
    res_deact = client.put(
        f"/api/admin/users/{examiner.id}/status",
        json={"is_active": False},
        cookies=get_auth_cookies(admin),
    )
    assert res_deact.status_code == 200
    assert res_deact.json()["is_active"] is False

    # Check via /api/admin/examiners/{id}
    res_check = client.get(f"/api/admin/examiners/{examiner.id}", cookies=get_auth_cookies(admin))
    assert res_check.status_code == 200
    assert res_check.json()["is_active"] is False

    # Reactivate
    res_react = client.put(
        f"/api/admin/users/{examiner.id}/status",
        json={"is_active": True},
        cookies=get_auth_cookies(admin),
    )
    assert res_react.status_code == 200
    assert res_react.json()["is_active"] is True


def test_admin_examiner_security_no_sensitive_fields(client, db):
    """Verify password_hash, face_embedding, biometric secrets are never present in responses."""
    admin = create_user(db, "admin_ex_sec_check@example.com", UserRole.ADMIN)
    examiner = create_user(db, "examiner_sec_check@example.com", UserRole.EXAMINER)

    # 1. In list response
    res_list = client.get("/api/admin/examiners", cookies=get_auth_cookies(admin))
    assert res_list.status_code == 200
    for item in res_list.json()["items"]:
        assert "password" not in item
        assert "password_hash" not in item
        assert "face_embedding" not in item
        assert "access_token" not in item
        assert "token" not in item

    # 2. In detail response
    res_detail = client.get(f"/api/admin/examiners/{examiner.id}", cookies=get_auth_cookies(admin))
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert "password" not in detail_data
    assert "password_hash" not in detail_data
    assert "face_embedding" not in detail_data
    assert "access_token" not in detail_data
    assert "token" not in detail_data
