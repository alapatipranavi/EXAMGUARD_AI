import pytest
import uuid
from datetime import datetime, timezone, timedelta
from app.models.user import UserRole, User
from app.models.academic import College, Department, Section
from app.models.exam import Exam, ExamStatus, ExamTargetType, ExamQuestion, ExamTargetStudent
from app.models.question import Question, QuestionType
from app.models.exam_session import ExamSession, SessionStatus
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
    u = user_repository.create_user(
        db=db,
        email=email,
        password_hash=hash_password("Password123!"),
        first_name=first_name,
        last_name=last_name,
        role=role,
        college_id=college_id,
    )
    if department_id or year_of_study or section_id:
        u.department_id = department_id
        u.year_of_study = year_of_study
        u.section_id = section_id
        db.commit()
        db.refresh(u)
    return u


def get_auth_cookies(user: User) -> dict:
    token = create_access_token({"sub": str(user.id), "role": user.role.value})
    return {"access_token": token}


# ============================================================================
# 1. AUTHENTICATION & RBAC TESTS
# ============================================================================

def test_admin_exams_auth_required(client):
    """Unauthenticated calls to /api/admin/exams must return 401."""
    res = client.get("/api/admin/exams")
    assert res.status_code == 401

    res_detail = client.get(f"/api/admin/exams/{uuid.uuid4()}")
    assert res_detail.status_code == 401


def test_admin_exams_rbac_forbidden(client, db):
    """STUDENT and EXAMINER callers must receive 403 Forbidden."""
    uid = uuid.uuid4().hex[:6]
    student = create_user(db, f"student_exams_rbac_{uid}@example.com", UserRole.STUDENT)
    examiner = create_user(db, f"examiner_exams_rbac_{uid}@example.com", UserRole.EXAMINER)

    # Student -> 403
    res_student = client.get("/api/admin/exams", cookies=get_auth_cookies(student))
    assert res_student.status_code == 403

    # Examiner -> 403
    res_examiner = client.get("/api/admin/exams", cookies=get_auth_cookies(examiner))
    assert res_examiner.status_code == 403


def test_admin_exams_admin_access_success(client, db):
    """ADMIN caller receives 200 with paginated exam response."""
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_exams_{uid}@example.com", UserRole.ADMIN)

    res = client.get("/api/admin/exams", cookies=get_auth_cookies(admin))
    assert res.status_code == 200
    data = res.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "summary" in data
    assert "total_exams" in data["summary"]
    assert "published_active_exams" in data["summary"]
    assert "completed_exams" in data["summary"]
    assert "draft_exams" in data["summary"]


# ============================================================================
# 2. SEARCH & FILTERING TESTS
# ============================================================================

def test_admin_exams_search_and_filters(client, db):
    """Test searching by title, subject, examiner name, and filtering by status and college."""
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_filter_{uid}@example.com", UserRole.ADMIN)

    # Create College
    college = College(name=f"College Admin Exams {uid}", code=f"CAE_{uid}", is_active=True)
    db.add(college)
    db.commit()
    db.refresh(college)

    examiner = create_user(
        db,
        f"examiner_filter_{uid}@example.com",
        UserRole.EXAMINER,
        first_name="ProfSearch",
        last_name="Exams",
        college_id=college.id,
    )

    # Create 2 exams
    exam1 = Exam(
        title=f"Advanced Mathematics {uid}",
        subject="Mathematics",
        duration_minutes=60,
        total_marks=100.0,
        passing_marks=40.0,
        status=ExamStatus.PUBLISHED,
        created_by=examiner.id,
    )
    exam2 = Exam(
        title=f"Physics Fundamentals {uid}",
        subject="Physics",
        duration_minutes=45,
        total_marks=50.0,
        passing_marks=20.0,
        status=ExamStatus.DRAFT,
        created_by=examiner.id,
    )
    db.add_all([exam1, exam2])
    db.commit()

    cookies = get_auth_cookies(admin)

    # Search by title
    res_search = client.get(f"/api/admin/exams?search=Advanced+Mathematics+{uid}", cookies=cookies)
    assert res_search.status_code == 200
    items = res_search.json()["items"]
    assert len(items) == 1
    assert items[0]["title"] == exam1.title

    # Search by examiner name
    res_prof = client.get(f"/api/admin/exams?search=ProfSearch", cookies=cookies)
    assert res_prof.status_code == 200
    assert any(i["id"] == str(exam1.id) for i in res_prof.json()["items"])

    # Filter by subject
    res_subject = client.get(f"/api/admin/exams?subject=Physics", cookies=cookies)
    assert res_subject.status_code == 200
    assert all("Physics" in i["subject"] for i in res_subject.json()["items"])

    # Filter by status
    res_status = client.get(f"/api/admin/exams?status=PUBLISHED", cookies=cookies)
    assert res_status.status_code == 200
    assert all(i["status"] == "PUBLISHED" for i in res_status.json()["items"])

    # Filter by college_id
    res_college = client.get(f"/api/admin/exams?college_id={college.id}", cookies=cookies)
    assert res_college.status_code == 200
    assert len(res_college.json()["items"]) == 2

    # Filter by examiner_id
    res_ex_id = client.get(f"/api/admin/exams?examiner_id={examiner.id}", cookies=cookies)
    assert res_ex_id.status_code == 200
    assert len(res_ex_id.json()["items"]) == 2


# ============================================================================
# 3. PAGINATION & BOUNDARIES
# ============================================================================

def test_admin_exams_pagination(client, db):
    """Test pagination controls on /api/admin/exams."""
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_pagi_{uid}@example.com", UserRole.ADMIN)
    examiner = create_user(db, f"examiner_pagi_{uid}@example.com", UserRole.EXAMINER)

    # Create 3 exams
    for i in range(3):
        e = Exam(
            title=f"Pagi Exam {uid} #{i}",
            subject="PagiSubject",
            duration_minutes=30,
            total_marks=30.0,
            passing_marks=10.0,
            status=ExamStatus.DRAFT,
            created_by=examiner.id,
        )
        db.add(e)
    db.commit()

    cookies = get_auth_cookies(admin)
    res = client.get(f"/api/admin/exams?search=Pagi+Exam+{uid}&page=1&page_size=2", cookies=cookies)
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == 2
    assert data["total"] == 3
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["total_pages"] == 2

    # Page 2
    res_p2 = client.get(f"/api/admin/exams?search=Pagi+Exam+{uid}&page=2&page_size=2", cookies=cookies)
    assert res_p2.status_code == 200
    assert len(res_p2.json()["items"]) == 1


# ============================================================================
# 4. EXAM DETAIL & METRICS TESTS
# ============================================================================

def test_admin_exam_detail_success(client, db):
    """Test full detail retrieval including questions breakdown and sessions."""
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_det_{uid}@example.com", UserRole.ADMIN)

    college = College(name=f"College Detail {uid}", code=f"CD_{uid}", is_active=True)
    db.add(college)
    db.commit()
    db.refresh(college)

    department = Department(college_id=college.id, name=f"CS {uid}", code=f"CS_{uid}", is_active=True)
    db.add(department)
    db.commit()
    db.refresh(department)

    examiner = create_user(
        db,
        f"examiner_det_{uid}@example.com",
        UserRole.EXAMINER,
        first_name="Alice",
        last_name="Prof",
        college_id=college.id,
    )

    student = create_user(
        db,
        f"student_det_{uid}@example.com",
        UserRole.STUDENT,
        first_name="Bob",
        last_name="Student",
        college_id=college.id,
        department_id=department.id,
        year_of_study=2,
    )

    exam = Exam(
        title=f"Data Structures {uid}",
        subject="Computer Science",
        description="Comprehensive exam on Trees and Graphs.",
        instructions="No external resources allowed.",
        duration_minutes=90,
        total_marks=100.0,
        passing_marks=50.0,
        status=ExamStatus.PUBLISHED,
        target_type=ExamTargetType.DEPARTMENT,
        target_department_id=department.id,
        created_by=examiner.id,
        proctoring_enabled=True,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    # Add questions
    q1 = Question(
        question_text="What is a Binary Tree?",
        question_type=QuestionType.MCQ,
        subject="Computer Science",
        marks=10.0,
        created_by=examiner.id,
    )
    q2 = Question(
        question_text="Implement Dijkstra in Python",
        question_type=QuestionType.SHORT_ANSWER,
        subject="Computer Science",
        marks=20.0,
        created_by=examiner.id,
    )
    db.add_all([q1, q2])
    db.commit()
    db.refresh(q1)
    db.refresh(q2)

    eq1 = ExamQuestion(exam_id=exam.id, question_id=q1.id, question_order=1)
    eq2 = ExamQuestion(exam_id=exam.id, question_id=q2.id, question_order=2)
    db.add_all([eq1, eq2])

    # Add a session
    sess = ExamSession(
        exam_id=exam.id,
        student_id=student.id,
        status=SessionStatus.SUBMITTED,
    )
    db.add(sess)
    db.commit()

    cookies = get_auth_cookies(admin)
    res = client.get(f"/api/admin/exams/{exam.id}", cookies=cookies)
    assert res.status_code == 200
    data = res.json()

    assert data["id"] == str(exam.id)
    assert data["title"] == exam.title
    assert data["subject"] == "Computer Science"
    assert data["examiner_name"] == "Alice Prof"
    assert data["examiner_college_name"] == college.name
    assert data["target_type"] == "DEPARTMENT"
    assert "Department:" in data["target_description"]
    assert data["target_department_name"] == department.name
    assert data["eligible_students_count"] == 1  # 1 matching student
    assert data["total_sessions_count"] == 1
    assert data["completed_sessions_count"] == 1
    assert data["question_count"] == 2
    assert data["mcq_count"] == 1
    assert data["short_answer_count"] == 1


def test_admin_exam_detail_not_found(client, db):
    """Non-existent exam returns 404."""
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_404_{uid}@example.com", UserRole.ADMIN)

    res = client.get(f"/api/admin/exams/{uuid.uuid4()}", cookies=get_auth_cookies(admin))
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()


def test_admin_exam_no_side_effects_on_examiner_ownership(client, db):
    """Admin viewing exam list or details must NOT alter created_by or exam properties."""
    uid = uuid.uuid4().hex[:6]
    admin = create_user(db, f"admin_safe_{uid}@example.com", UserRole.ADMIN)
    examiner = create_user(db, f"examiner_safe_{uid}@example.com", UserRole.EXAMINER)

    exam = Exam(
        title=f"Integrity Check Exam {uid}",
        subject="Integrity",
        duration_minutes=30,
        total_marks=30.0,
        passing_marks=10.0,
        status=ExamStatus.PUBLISHED,
        created_by=examiner.id,
    )
    db.add(exam)
    db.commit()
    db.refresh(exam)

    original_creator = exam.created_by
    original_status = exam.status

    cookies = get_auth_cookies(admin)
    client.get("/api/admin/exams", cookies=cookies)
    client.get(f"/api/admin/exams/{exam.id}", cookies=cookies)

    db.expire_all()
    refreshed_exam = db.query(Exam).filter(Exam.id == exam.id).first()
    assert refreshed_exam.created_by == original_creator
    assert refreshed_exam.status == original_status
