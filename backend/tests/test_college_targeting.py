import pytest
import uuid
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus, ExamTargetType
from app.models.question import Question, QuestionType, DifficultyLevel
from app.repositories.user_repository import user_repository
from app.repositories.academic_repository import academic_repository
from app.repositories.exam_repository import ExamRepository
from app.core.security import hash_password, create_access_token


def create_user(db, email: str, role: UserRole, first_name: str = "Test", last_name: str = "User") -> User:
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


def create_question(db, examiner: User) -> Question:
    q = Question(
        question_text="Sample Question text?",
        subject="Computer Science",
        question_type=QuestionType.MCQ,
        difficulty=DifficultyLevel.EASY,
        marks=5.0,
        created_by=examiner.id,
        is_active=True,
    )
    db.add(q)
    db.commit()
    db.refresh(q)
    return q


# ============================================================================
# 1. ACADEMIC STRUCTURE CRUD TESTS
# ============================================================================

def test_admin_create_college_and_departments(client, db):
    admin = create_user(db, "admin1@example.com", UserRole.ADMIN)
    cookies = get_auth_cookies(admin)

    # 1. Create College
    res = client.post("/api/admin/colleges", json={"name": "College of Engineering", "code": "COE"}, cookies=cookies)
    assert res.status_code == 201
    col_data = res.json()
    assert col_data["code"] == "COE"
    college_id = col_data["id"]

    # 2. Duplicate College Code Rejected
    res_dup = client.post("/api/admin/colleges", json={"name": "Duplicate College", "code": "coe"}, cookies=cookies)
    assert res_dup.status_code == 400

    # 3. Create Department
    res_dept = client.post("/api/admin/departments", json={"college_id": college_id, "name": "Computer Science", "code": "CSE"}, cookies=cookies)
    assert res_dept.status_code == 201
    dept_data = res_dept.json()
    assert dept_data["code"] == "CSE"
    dept_id = dept_data["id"]

    # 4. Create Section
    res_sec = client.post("/api/admin/sections", json={"department_id": dept_id, "year_of_study": 2, "name": "Section A", "code": "SEC-A"}, cookies=cookies)
    assert res_sec.status_code == 201
    sec_data = res_sec.json()
    assert sec_data["year_of_study"] == 2


def test_non_admin_academic_management_forbidden(client, db):
    examiner = create_user(db, "examiner1@example.com", UserRole.EXAMINER)
    cookies = get_auth_cookies(examiner)

    res = client.post("/api/admin/colleges", json={"name": "Forbidden Col", "code": "FORB"}, cookies=cookies)
    assert res.status_code == 403


# ============================================================================
# 2. USER ACADEMIC PROFILES & EXAMINER SCOPING
# ============================================================================

def test_assign_academic_profiles(client, db):
    admin = create_user(db, "admin2@example.com", UserRole.ADMIN)
    examiner = create_user(db, "ex2@example.com", UserRole.EXAMINER)
    student = create_user(db, "st2@example.com", UserRole.STUDENT)
    admin_cookies = get_auth_cookies(admin)

    college = academic_repository.create_college(db, "Science College", "SCI")
    dept = academic_repository.create_department(db, college.id, "Physics", "PHY")
    sec = academic_repository.create_section(db, dept.id, 3, "Physics Sec 1", "PHY-S1")

    # Assign Examiner College
    res_ex = client.put(f"/api/admin/users/{examiner.id}/college", json={"college_id": str(college.id)}, cookies=admin_cookies)
    assert res_ex.status_code == 200
    assert res_ex.json()["college_id"] == str(college.id)

    # Assign Student Profile
    res_st = client.put(
        f"/api/admin/students/{student.id}/academic-profile",
        json={
            "college_id": str(college.id),
            "department_id": str(dept.id),
            "year_of_study": 3,
            "section_id": str(sec.id),
        },
        cookies=admin_cookies,
    )
    assert res_st.status_code == 200
    st_data = res_st.json()
    assert st_data["college_id"] == str(college.id)
    assert st_data["department_id"] == str(dept.id)
    assert st_data["year_of_study"] == 3
    assert st_data["section_id"] == str(sec.id)


# ============================================================================
# 3. TARGETED EXAM ACCESS & AUTHORIZATION TESTS
# ============================================================================

def test_department_targeted_exam_access(client, db):
    admin = create_user(db, "admin3@example.com", UserRole.ADMIN)
    examiner = create_user(db, "ex3@example.com", UserRole.EXAMINER)
    student_cse = create_user(db, "student_cse@example.com", UserRole.STUDENT)
    student_ece = create_user(db, "student_ece@example.com", UserRole.STUDENT)

    college = academic_repository.create_college(db, "Engineering Tech", "ENG")
    dept_cse = academic_repository.create_department(db, college.id, "Comp Sci", "CS")
    dept_ece = academic_repository.create_department(db, college.id, "Electronics", "ECE")

    # Set student profiles
    academic_repository.update_student_academic_profile(db, student_cse, college.id, dept_cse.id, 2, None)
    academic_repository.update_student_academic_profile(db, student_ece, college.id, dept_ece.id, 2, None)
    academic_repository.update_user_college(db, examiner, college.id)

    q = create_question(db, examiner)
    ex_cookies = get_auth_cookies(examiner)

    # Create & publish CS Department targeted exam
    create_payload = {
        "title": "CS Data Structures Exam",
        "subject": "Computer Science",
        "duration_minutes": 60,
        "passing_marks": 2.0,
        "target_type": "DEPARTMENT",
        "target_department_id": str(dept_cse.id),
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res_create = client.post("/api/exams", json=create_payload, cookies=ex_cookies)
    assert res_create.status_code == 201
    exam_id = res_create.json()["id"]

    res_pub = client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)
    assert res_pub.status_code == 200

    # Test CS Student can see exam
    cse_cookies = get_auth_cookies(student_cse)
    res_cs_list = client.get("/api/student/exams", cookies=cse_cookies)
    assert res_cs_list.status_code == 200
    assert any(item["id"] == exam_id for item in res_cs_list.json()["items"])

    # Test ECE Student cannot see exam
    ece_cookies = get_auth_cookies(student_ece)
    res_ece_list = client.get("/api/student/exams", cookies=ece_cookies)
    assert res_ece_list.status_code == 200
    assert not any(item["id"] == exam_id for item in res_ece_list.json()["items"])

    # Test ECE Student start session receives 403 Forbidden
    res_start = client.post(f"/api/student/exams/{exam_id}/start", cookies=ece_cookies)
    assert res_start.status_code == 403
    assert "target audience" in res_start.json()["detail"].lower()


def test_specific_students_targeted_exam(client, db):
    examiner = create_user(db, "ex4@example.com", UserRole.EXAMINER)
    student1 = create_user(db, "target_st1@example.com", UserRole.STUDENT)
    student2 = create_user(db, "untargeted_st2@example.com", UserRole.STUDENT)

    q = create_question(db, examiner)
    ex_cookies = get_auth_cookies(examiner)

    create_payload = {
        "title": "Special Makeup Exam",
        "subject": "Computer Science",
        "duration_minutes": 45,
        "target_type": "SPECIFIC_STUDENTS",
        "target_student_ids": [str(student1.id)],
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res_create = client.post("/api/exams", json=create_payload, cookies=ex_cookies)
    assert res_create.status_code == 201
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    # Targeted student 1 can start
    st1_cookies = get_auth_cookies(student1)
    res_start1 = client.post(f"/api/student/exams/{exam_id}/start", cookies=st1_cookies)
    assert res_start1.status_code == 200

    # Untargeted student 2 gets 403
    st2_cookies = get_auth_cookies(student2)
    res_start2 = client.post(f"/api/student/exams/{exam_id}/start", cookies=st2_cookies)
    assert res_start2.status_code == 403
