import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.academic import College, Department, Section
from app.models.exam import Exam, ExamStatus
from app.models.exam_session import ExamSession, SessionStatus
from app.models.evaluation import ExamSessionEvaluation, EvaluationStatus, PassFailStatus
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
    department_id: uuid.UUID = None,
    year_of_study: int = None,
    section_id: uuid.UUID = None,
) -> User:
    return user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first_name,
        last_name=last_name,
        role=role,
        college_id=college_id,
        department_id=department_id,
        year_of_study=year_of_study,
        section_id=section_id,
    )


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


# ============================================================================
# 1. AUTHENTICATION & RBAC TESTS
# ============================================================================

def test_admin_students_auth_required(client):
    """Unauthenticated calls to /api/admin/students must return 401."""
    res = client.get("/api/admin/students")
    assert res.status_code == 401


def test_admin_students_rbac_forbidden(client, db):
    """STUDENT and EXAMINER callers must receive 403 Forbidden."""
    student = create_user(db, "student_rbac@example.com", UserRole.STUDENT)
    examiner = create_user(db, "examiner_rbac@example.com", UserRole.EXAMINER)

    # Student -> 403
    res_student = client.get("/api/admin/students", cookies=get_auth_cookies(student))
    assert res_student.status_code == 403

    # Examiner -> 403
    res_examiner = client.get("/api/admin/students", cookies=get_auth_cookies(examiner))
    assert res_examiner.status_code == 403


def test_admin_students_admin_access_success(client, db):
    """ADMIN role must successfully access /api/admin/students with 200."""
    admin = create_user(db, "admin_access@example.com", UserRole.ADMIN)
    res = client.get("/api/admin/students", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "summary" in data


# ============================================================================
# 2. FILTERING & SEARCH TESTS
# ============================================================================

def test_admin_students_only_students_returned(client, db):
    """Ensure the endpoint strictly returns only users with role=STUDENT."""
    admin = create_user(db, "admin_filter_check@example.com", UserRole.ADMIN)
    student1 = create_user(db, "student_filter1@example.com", UserRole.STUDENT, first_name="Alice", last_name="Smith")
    student2 = create_user(db, "student_filter2@example.com", UserRole.STUDENT, first_name="Bob", last_name="Jones")
    examiner1 = create_user(db, "examiner_filter1@example.com", UserRole.EXAMINER, first_name="Charlie", last_name="Prof")

    res = client.get("/api/admin/students", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    returned_roles = [item["role"] for item in data["items"]]
    assert all(r == "STUDENT" for r in returned_roles)
    returned_emails = [item["email"] for item in data["items"]]
    assert student1.email in returned_emails
    assert student2.email in returned_emails
    assert examiner1.email not in returned_emails
    assert admin.email not in returned_emails


def test_admin_students_search_by_name_and_email(client, db):
    """Case-insensitive search by student first name, last name, or email."""
    admin = create_user(db, "admin_search@example.com", UserRole.ADMIN)
    s1 = create_user(db, "unique_zara@university.edu", UserRole.STUDENT, first_name="Zara", last_name="Ahmed")
    s2 = create_user(db, "david_miller@university.edu", UserRole.STUDENT, first_name="David", last_name="Miller")

    # Search by first name
    res = client.get("/api/admin/students?search=zara", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    emails = [item["email"] for item in data["items"]]
    assert s1.email in emails
    assert s2.email not in emails

    # Search by last name (case-insensitive)
    res = client.get("/api/admin/students?search=MILLER", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    emails = [item["email"] for item in data["items"]]
    assert s2.email in emails
    assert s1.email not in emails

    # Search by email fragment
    res = client.get("/api/admin/students?search=unique_zara", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    emails = [item["email"] for item in res.json()["items"]]
    assert s1.email in emails
    assert s2.email not in emails


def test_admin_students_academic_hierarchy_filters(client, db):
    """Filter students by college, department, year, and section with resolved names."""
    admin = create_user(db, "admin_acad_filter@example.com", UserRole.ADMIN)

    # Create academic structure
    college = College(name="Engineering Institute of Tech", code=f"EIT_{uuid.uuid4().hex[:4]}", is_active=True)
    db.add(college)
    db.commit()
    db.refresh(college)

    dept = Department(college_id=college.id, name="Computer Science", code="CS", is_active=True)
    db.add(dept)
    db.commit()
    db.refresh(dept)

    sec = Section(department_id=dept.id, year_of_study=3, name="Section Alpha", code="SEC-A", is_active=True)
    db.add(sec)
    db.commit()
    db.refresh(sec)

    # Student in this section
    assigned_student = create_user(
        db,
        f"assigned_{uuid.uuid4().hex[:6]}@eit.edu",
        UserRole.STUDENT,
        first_name="Priya",
        last_name="Sharma",
        college_id=college.id,
        department_id=dept.id,
        year_of_study=3,
        section_id=sec.id,
    )

    # Student not in this college
    unassigned_student = create_user(
        db,
        f"unassigned_{uuid.uuid4().hex[:6]}@other.edu",
        UserRole.STUDENT,
        first_name="Rahul",
        last_name="Verma",
    )

    # 1. Filter by college_id
    res = client.get(f"/api/admin/students?college_id={college.id}", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    items = res.json()["items"]
    assert any(item["id"] == str(assigned_student.id) for item in items)
    assert not any(item["id"] == str(unassigned_student.id) for item in items)

    # Verify resolved names
    matching_item = next(item for item in items if item["id"] == str(assigned_student.id))
    assert matching_item["college_name"] == college.name
    assert matching_item["college_code"] == college.code
    assert matching_item["department_name"] == dept.name
    assert matching_item["department_code"] == dept.code
    assert matching_item["section_name"] == sec.name
    assert matching_item["section_code"] == sec.code
    assert matching_item["year_of_study"] == 3

    # 2. Filter by department_id
    res_dept = client.get(f"/api/admin/students?department_id={dept.id}", cookies=get_auth_cookies(admin))
    assert res_dept.status_code == 200
    assert any(item["id"] == str(assigned_student.id) for item in res_dept.json()["items"])

    # 3. Filter by year_of_study
    res_year = client.get(f"/api/admin/students?year_of_study=3", cookies=get_auth_cookies(admin))
    assert res_year.status_code == 200
    assert any(item["id"] == str(assigned_student.id) for item in res_year.json()["items"])

    # 4. Filter by section_id
    res_sec = client.get(f"/api/admin/students?section_id={sec.id}", cookies=get_auth_cookies(admin))
    assert res_sec.status_code == 200
    assert any(item["id"] == str(assigned_student.id) for item in res_sec.json()["items"])


def test_admin_students_status_filter(client, db):
    """Filter students by is_active=True and is_active=False."""
    admin = create_user(db, "admin_status_filter@example.com", UserRole.ADMIN)
    act_student = create_user(db, f"active_{uuid.uuid4().hex[:6]}@test.com", UserRole.STUDENT, is_active=True)
    inact_student = create_user(db, f"inactive_{uuid.uuid4().hex[:6]}@test.com", UserRole.STUDENT, is_active=True)
    inact_student.is_active = False
    db.commit()

    # Active filter
    res_act = client.get(f"/api/admin/students?is_active=true", cookies=get_auth_cookies(admin))
    assert res_act.status_code == 200
    active_ids = [item["id"] for item in res_act.json()["items"]]
    assert str(act_student.id) in active_ids
    assert str(inact_student.id) not in active_ids

    # Inactive filter
    res_inact = client.get(f"/api/admin/students?is_active=false", cookies=get_auth_cookies(admin))
    assert res_inact.status_code == 200
    inactive_ids = [item["id"] for item in res_inact.json()["items"]]
    assert str(inact_student.id) in inactive_ids
    assert str(act_student.id) not in inactive_ids


def test_admin_students_pagination(client, db):
    """Pagination parameters page and page_size work correctly."""
    admin = create_user(db, "admin_paging@example.com", UserRole.ADMIN)
    res = client.get("/api/admin/students?page=1&page_size=2", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert len(data["items"]) <= 2
    assert "total_pages" in data


# ============================================================================
# 3. STUDENT DETAIL TESTS
# ============================================================================

def test_admin_student_detail_success(client, db):
    """Admin can retrieve full student details including academic scope and session summary."""
    admin = create_user(db, "admin_detail@example.com", UserRole.ADMIN)
    examiner = create_user(db, f"examiner_det_{uuid.uuid4().hex[:4]}@exam.edu", UserRole.EXAMINER)

    college = College(name="Tech Academy", code=f"TAC_{uuid.uuid4().hex[:4]}", is_active=True)
    db.add(college)
    db.commit()
    db.refresh(college)

    student = create_user(
        db,
        f"student_det_{uuid.uuid4().hex[:6]}@test.com",
        UserRole.STUDENT,
        first_name="Deepak",
        last_name="Kumar",
        college_id=college.id,
        year_of_study=2,
    )

    # Create exam and session for student
    exam = Exam(
        title="Algorithms 101",
        subject="Computer Science",
        duration_minutes=45,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
        created_by=examiner.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    session = ExamSession(
        exam_id=exam.id,
        student_id=student.id,
        status=SessionStatus.SUBMITTED,
        started_at=datetime.now(timezone.utc) - timedelta(minutes=40),
        submitted_at=datetime.now(timezone.utc),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    # Evaluation
    eval_res = ExamSessionEvaluation(
        session_id=session.id,
        exam_id=exam.id,
        student_id=student.id,
        percentage=85.0,
        pass_fail_status=PassFailStatus.PASSED,
        status=EvaluationStatus.COMPLETED,
    )
    db.add(eval_res)
    db.commit()

    res = client.get(f"/api/admin/students/{student.id}", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert data["id"] == str(student.id)
    assert data["first_name"] == "Deepak"
    assert data["last_name"] == "Kumar"
    assert data["role"] == "STUDENT"
    assert data["college_name"] == "Tech Academy"
    assert data["year_of_study"] == 2
    assert data["exams_attempted_count"] >= 1
    assert data["exams_completed_count"] >= 1
    assert len(data["recent_sessions"]) >= 1
    sess_item = data["recent_sessions"][0]
    assert sess_item["exam_title"] == "Algorithms 101"
    assert sess_item["percentage"] == 85.0
    assert sess_item["pass_fail_status"] == "PASSED"


def test_admin_student_detail_role_isolation(client, db):
    """Admin cannot view Examiner or Admin user records through /api/admin/students/{id}."""
    admin = create_user(db, "admin_iso_test@example.com", UserRole.ADMIN)
    examiner = create_user(db, "examiner_iso_test@example.com", UserRole.EXAMINER)
    other_admin = create_user(db, "other_admin_iso@example.com", UserRole.ADMIN)

    # Attempt to query Examiner ID via student detail endpoint -> 404
    res_ex = client.get(f"/api/admin/students/{examiner.id}", cookies=get_auth_cookies(admin))
    assert res_ex.status_code == 404
    assert "student not found" in res_ex.json()["detail"].lower()

    # Attempt to query Admin ID via student detail endpoint -> 404
    res_ad = client.get(f"/api/admin/students/{other_admin.id}", cookies=get_auth_cookies(admin))
    assert res_ad.status_code == 404
    assert "student not found" in res_ad.json()["detail"].lower()

    # Non-existent UUID -> 404
    fake_id = uuid.uuid4()
    res_fake = client.get(f"/api/admin/students/{fake_id}", cookies=get_auth_cookies(admin))
    assert res_fake.status_code == 404


# ============================================================================
# 4. STATUS TOGGLE & SECURITY TESTS
# ============================================================================

def test_admin_student_status_toggle(client, db):
    """Admin can activate and deactivate a student via existing Admin User Management API."""
    admin = create_user(db, "admin_status_act@example.com", UserRole.ADMIN)
    student = create_user(db, "student_toggle_act@example.com", UserRole.STUDENT, is_active=True)

    # Deactivate
    res_deact = client.put(
        f"/api/admin/users/{student.id}/status",
        json={"is_active": False},
        cookies=get_auth_cookies(admin),
    )
    assert res_deact.status_code == 200
    assert res_deact.json()["is_active"] is False

    # Check via /api/admin/students/{id}
    res_check = client.get(f"/api/admin/students/{student.id}", cookies=get_auth_cookies(admin))
    assert res_check.status_code == 200
    assert res_check.json()["is_active"] is False

    # Reactivate
    res_react = client.put(
        f"/api/admin/users/{student.id}/status",
        json={"is_active": True},
        cookies=get_auth_cookies(admin),
    )
    assert res_react.status_code == 200
    assert res_react.json()["is_active"] is True


def test_admin_student_security_no_sensitive_fields(client, db):
    """Verify password_hash, face_embedding, biometric secrets are never present in responses."""
    admin = create_user(db, "admin_sec_check@example.com", UserRole.ADMIN)
    student = create_user(db, "student_sec_check@example.com", UserRole.STUDENT)

    # 1. In list response
    res_list = client.get("/api/admin/students", cookies=get_auth_cookies(admin))
    assert res_list.status_code == 200
    for item in res_list.json()["items"]:
        assert "password" not in item
        assert "password_hash" not in item
        assert "face_embedding" not in item
        assert "access_token" not in item
        assert "token" not in item

    # 2. In detail response
    res_detail = client.get(f"/api/admin/students/{student.id}", cookies=get_auth_cookies(admin))
    assert res_detail.status_code == 200
    detail_data = res_detail.json()
    assert "password" not in detail_data
    assert "password_hash" not in detail_data
    assert "face_embedding" not in detail_data
    assert "access_token" not in detail_data
    assert "token" not in detail_data
