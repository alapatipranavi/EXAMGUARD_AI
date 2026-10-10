import pytest
import uuid
from app.models.user import UserRole, User
from app.models.exam import Exam, ExamStatus, ExamTargetType
from app.models.question import Question, QuestionType, DifficultyLevel
from app.repositories.user_repository import user_repository
from app.repositories.academic_repository import academic_repository
from app.core.security import hash_password, create_access_token


def create_test_user(db, email: str, role: UserRole, first_name: str = "Test", last_name: str = "User") -> User:
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
        question_text="Targeting Test Question?",
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


# Helper to setup a full academic structure (2 colleges, depts, sections)
def setup_academic_environment(db):
    col_a = academic_repository.create_college(db, "Alpha College of Engineering", "ACE")
    dept_a1 = academic_repository.create_department(db, col_a.id, "Computer Science & Engineering", "CSE")
    dept_a2 = academic_repository.create_department(db, col_a.id, "Electrical Engineering", "EEE")
    sec_a1_y2_secA = academic_repository.create_section(db, dept_a1.id, 2, "Section A", "CSE-2A")
    sec_a1_y2_secB = academic_repository.create_section(db, dept_a1.id, 2, "Section B", "CSE-2B")

    col_b = academic_repository.create_college(db, "Beta Institute of Tech", "BIT")
    dept_b1 = academic_repository.create_department(db, col_b.id, "Information Technology", "IT")
    sec_b1_y2_secA = academic_repository.create_section(db, dept_b1.id, 2, "Section A", "IT-2A")

    return {
        "col_a": col_a,
        "dept_a1": dept_a1,
        "dept_a2": dept_a2,
        "sec_a1_y2_secA": sec_a1_y2_secA,
        "sec_a1_y2_secB": sec_a1_y2_secB,
        "col_b": col_b,
        "dept_b1": dept_b1,
        "sec_b1_y2_secA": sec_b1_y2_secA,
    }


# ============================================================================
# 1. STUDENT REGISTRATION & ACADEMIC VALIDATIONS (Scenarios 1 - 6)
# ============================================================================

def test_1_student_registration_with_valid_academic_details(client, db):
    env = setup_academic_environment(db)
    payload = {
        "email": "reg_student_valid@example.com",
        "password": "Password123!",
        "first_name": "Valid",
        "last_name": "Student",
        "role": "STUDENT",
        "college_id": str(env["col_a"].id),
        "department_id": str(env["dept_a1"].id),
        "year_of_study": 2,
        "section_id": str(env["sec_a1_y2_secA"].id),
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 201
    data = res.json()
    assert data["college_id"] == str(env["col_a"].id)
    assert data["department_id"] == str(env["dept_a1"].id)
    assert data["year_of_study"] == 2
    assert data["section_id"] == str(env["sec_a1_y2_secA"].id)


def test_2_registration_invalid_college(client, db):
    fake_college_id = str(uuid.uuid4())
    payload = {
        "email": "reg_invalid_col@example.com",
        "password": "Password123!",
        "first_name": "Invalid",
        "last_name": "College",
        "role": "STUDENT",
        "college_id": fake_college_id,
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "college" in res.json()["detail"].lower()


def test_3_registration_department_from_another_college(client, db):
    env = setup_academic_environment(db)
    # College A with Department from College B
    payload = {
        "email": "reg_mismatched_dept@example.com",
        "password": "Password123!",
        "first_name": "Mismatch",
        "last_name": "Dept",
        "role": "STUDENT",
        "college_id": str(env["col_a"].id),
        "department_id": str(env["dept_b1"].id),
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "belong to selected college" in res.json()["detail"].lower()


def test_4_registration_invalid_section(client, db):
    env = setup_academic_environment(db)
    # Section from Year 2 attached with year_of_study 3
    payload = {
        "email": "reg_mismatched_sec@example.com",
        "password": "Password123!",
        "first_name": "Mismatch",
        "last_name": "Section",
        "role": "STUDENT",
        "college_id": str(env["col_a"].id),
        "department_id": str(env["dept_a1"].id),
        "year_of_study": 3,
        "section_id": str(env["sec_a1_y2_secA"].id),  # sec_a1_y2_secA is Year 2
    }
    res = client.post("/api/auth/register", json=payload)
    assert res.status_code == 400
    assert "section" in res.json()["detail"].lower()


def test_5_student_academic_details_saved_automatically(client, db):
    env = setup_academic_environment(db)
    payload = {
        "email": "auto_saved_student@example.com",
        "password": "Password123!",
        "first_name": "Auto",
        "last_name": "Saved",
        "role": "STUDENT",
        "college_id": str(env["col_a"].id),
        "department_id": str(env["dept_a1"].id),
        "year_of_study": 2,
        "section_id": str(env["sec_a1_y2_secA"].id),
    }
    client.post("/api/auth/register", json=payload)

    # Login and GET /api/auth/me
    login_res = client.post("/api/auth/login", json={"email": payload["email"], "password": payload["password"]})
    assert login_res.status_code == 200
    me_res = client.get("/api/auth/me", cookies=login_res.cookies)
    assert me_res.status_code == 200
    user_me = me_res.json()
    assert user_me["college_id"] == str(env["col_a"].id)
    assert user_me["department_id"] == str(env["dept_a1"].id)
    assert user_me["year_of_study"] == 2
    assert user_me["section_id"] == str(env["sec_a1_y2_secA"].id)


def test_6_admin_can_correct_student_academic_details(client, db):
    env = setup_academic_environment(db)
    student = create_test_user(db, "st_to_correct@example.com", UserRole.STUDENT)
    admin = create_test_user(db, "admin_corrector@example.com", UserRole.ADMIN)

    admin_cookies = get_auth_cookies(admin)
    update_payload = {
        "college_id": str(env["col_a"].id),
        "department_id": str(env["dept_a1"].id),
        "year_of_study": 2,
        "section_id": str(env["sec_a1_y2_secA"].id),
    }
    res = client.put(f"/api/admin/students/{student.id}/academic-profile", json=update_payload, cookies=admin_cookies)
    assert res.status_code == 200
    updated_st = res.json()
    assert updated_st["college_id"] == str(env["col_a"].id)
    assert updated_st["department_id"] == str(env["dept_a1"].id)
    assert updated_st["year_of_study"] == 2
    assert updated_st["section_id"] == str(env["sec_a1_y2_secA"].id)


# ============================================================================
# 2. EXAMINER SCOPING VALIDATIONS (Scenarios 7 - 8)
# ============================================================================

def test_7_examiner_can_only_target_their_college(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_col_a@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    cookies = get_auth_cookies(examiner)
    payload = {
        "title": "College A Exam",
        "subject": "Computer Science",
        "duration_minutes": 60,
        "target_type": "COLLEGE",
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res = client.post("/api/exams", json=payload, cookies=cookies)
    assert res.status_code == 201


def test_8_examiner_cannot_target_another_college(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_col_a_strict@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    cookies = get_auth_cookies(examiner)
    # Attempt to target department in College B
    payload = {
        "title": "Cross College Exam Attack",
        "subject": "Computer Science",
        "duration_minutes": 60,
        "target_type": "DEPARTMENT",
        "target_department_id": str(env["dept_b1"].id),  # Belongs to College B
        "questions": [{"question_id": str(q.id), "question_order": 1}],
    }
    res = client.post("/api/exams", json=payload, cookies=cookies)
    assert res.status_code in (400, 403)
    assert "college" in res.json()["detail"].lower()


# ============================================================================
# 3. COMPLETE COLLEGE-BASED TARGETING & VISIBILITY (Scenarios 9 - 18)
# ============================================================================

def test_9_college_level_exam_visibility(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_col_a_vis@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    student_col_a = create_test_user(db, "st_col_a@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, student_col_a, env["col_a"].id, env["dept_a1"].id, 2, env["sec_a1_y2_secA"].id)

    student_col_b = create_test_user(db, "st_col_b@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, student_col_b, env["col_b"].id, env["dept_b1"].id, 2, env["sec_b1_y2_secA"].id)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Alpha College Wide Exam",
            "subject": "General Engineering",
            "duration_minutes": 60,
            "target_type": "COLLEGE",
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    # Student from College A sees it
    res_st_a = client.get("/api/student/exams", cookies=get_auth_cookies(student_col_a))
    assert any(ex["id"] == exam_id for ex in res_st_a.json()["items"])

    # Student from College B does NOT see it
    res_st_b = client.get("/api/student/exams", cookies=get_auth_cookies(student_col_b))
    assert not any(ex["id"] == exam_id for ex in res_st_b.json()["items"])


def test_10_department_level_targeting(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_dept_target@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_dept_a1 = create_test_user(db, "st_dept_a1@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_dept_a1, env["col_a"].id, env["dept_a1"].id, 2, None)

    st_dept_a2 = create_test_user(db, "st_dept_a2@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_dept_a2, env["col_a"].id, env["dept_a2"].id, 2, None)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "CSE Department Exam",
            "subject": "CS Specialization",
            "duration_minutes": 60,
            "target_type": "DEPARTMENT",
            "target_department_id": str(env["dept_a1"].id),
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    assert any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_dept_a1)).json()["items"])
    assert not any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_dept_a2)).json()["items"])


def test_11_year_level_targeting(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_year_target@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_y2 = create_test_user(db, "st_y2@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_y2, env["col_a"].id, env["dept_a1"].id, 2, None)

    st_y3 = create_test_user(db, "st_y3@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_y3, env["col_a"].id, env["dept_a1"].id, 3, None)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "CSE 2nd Year Exam",
            "subject": "Data Structures",
            "duration_minutes": 60,
            "target_type": "YEAR",
            "target_department_id": str(env["dept_a1"].id),
            "target_year_of_study": 2,
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    assert any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_y2)).json()["items"])
    assert not any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_y3)).json()["items"])


def test_12_section_level_targeting(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_sec_target@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_sec_a = create_test_user(db, "st_sec_a@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_sec_a, env["col_a"].id, env["dept_a1"].id, 2, env["sec_a1_y2_secA"].id)

    st_sec_b = create_test_user(db, "st_sec_b@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_sec_b, env["col_a"].id, env["dept_a1"].id, 2, env["sec_a1_y2_secB"].id)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "CSE 2nd Year Section A Quiz",
            "subject": "Algorithms",
            "duration_minutes": 30,
            "target_type": "SECTION",
            "target_department_id": str(env["dept_a1"].id),
            "target_year_of_study": 2,
            "target_section_id": str(env["sec_a1_y2_secA"].id),
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    assert any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_sec_a)).json()["items"])
    assert not any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_sec_b)).json()["items"])


def test_13_specific_student_targeting(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_spec_target@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_chosen = create_test_user(db, "st_chosen@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_chosen, env["col_a"].id, env["dept_a1"].id, 2, env["sec_a1_y2_secA"].id)

    st_other = create_test_user(db, "st_other@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_other, env["col_a"].id, env["dept_a1"].id, 2, env["sec_a1_y2_secA"].id)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Remedial Exam for Chosen Student",
            "subject": "Mathematics",
            "duration_minutes": 45,
            "target_type": "SPECIFIC_STUDENTS",
            "target_student_ids": [str(st_chosen.id)],
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    assert any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_chosen)).json()["items"])
    assert not any(ex["id"] == exam_id for ex in client.get("/api/student/exams", cookies=get_auth_cookies(st_other)).json()["items"])


def test_14_wrong_college_student_blocked(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_col_block@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_col_b = create_test_user(db, "st_col_b_blocked@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_col_b, env["col_b"].id, env["dept_b1"].id, 2, env["sec_b1_y2_secA"].id)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "College A Strict Exam",
            "subject": "Physics",
            "duration_minutes": 60,
            "target_type": "COLLEGE",
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    # Attempt start
    res_start = client.post(f"/api/student/exams/{exam_id}/start", cookies=get_auth_cookies(st_col_b))
    assert res_start.status_code == 403


def test_15_wrong_department_student_blocked(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_dept_block@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_dept_a2 = create_test_user(db, "st_dept_a2_blocked@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_dept_a2, env["col_a"].id, env["dept_a2"].id, 2, None)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "CSE Only Exam",
            "subject": "Software Engineering",
            "duration_minutes": 60,
            "target_type": "DEPARTMENT",
            "target_department_id": str(env["dept_a1"].id),
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    res_start = client.post(f"/api/student/exams/{exam_id}/start", cookies=get_auth_cookies(st_dept_a2))
    assert res_start.status_code == 403


def test_16_wrong_year_student_blocked(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_year_block@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_y1 = create_test_user(db, "st_y1_blocked@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_y1, env["col_a"].id, env["dept_a1"].id, 1, None)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Year 2 Only Exam",
            "subject": "Operating Systems",
            "duration_minutes": 60,
            "target_type": "YEAR",
            "target_department_id": str(env["dept_a1"].id),
            "target_year_of_study": 2,
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    res_start = client.post(f"/api/student/exams/{exam_id}/start", cookies=get_auth_cookies(st_y1))
    assert res_start.status_code == 403


def test_17_wrong_section_student_blocked(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_sec_block@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    st_sec_b = create_test_user(db, "st_sec_b_blocked@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, st_sec_b, env["col_a"].id, env["dept_a1"].id, 2, env["sec_a1_y2_secB"].id)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Sec A Only Exam",
            "subject": "Networks",
            "duration_minutes": 60,
            "target_type": "SECTION",
            "target_department_id": str(env["dept_a1"].id),
            "target_year_of_study": 2,
            "target_section_id": str(env["sec_a1_y2_secA"].id),
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    res_start = client.post(f"/api/student/exams/{exam_id}/start", cookies=get_auth_cookies(st_sec_b))
    assert res_start.status_code == 403


def test_18_direct_url_api_access_blocked(client, db):
    env = setup_academic_environment(db)
    examiner = create_test_user(db, "ex_direct_block@example.com", UserRole.EXAMINER)
    academic_repository.update_user_college(db, examiner, env["col_a"].id)
    q = create_question(db, examiner)

    unauthorized_student = create_test_user(db, "unauth_student@example.com", UserRole.STUDENT)
    academic_repository.update_student_academic_profile(db, unauthorized_student, env["col_b"].id, env["dept_b1"].id, 2, env["sec_b1_y2_secA"].id)

    ex_cookies = get_auth_cookies(examiner)
    res_create = client.post(
        "/api/exams",
        json={
            "title": "Secret Exam",
            "subject": "Cybersecurity",
            "duration_minutes": 60,
            "target_type": "COLLEGE",
            "questions": [{"question_id": str(q.id), "question_order": 1}],
        },
        cookies=ex_cookies,
    )
    exam_id = res_create.json()["id"]
    client.post(f"/api/exams/{exam_id}/publish", cookies=ex_cookies)

    unauth_cookies = get_auth_cookies(unauthorized_student)

    # Direct GET /api/student/exams/{exam_id} returns 403
    res_get = client.get(f"/api/student/exams/{exam_id}", cookies=unauth_cookies)
    assert res_get.status_code == 403

    # Direct POST /api/student/exams/{exam_id}/start returns 403
    res_start = client.post(f"/api/student/exams/{exam_id}/start", cookies=unauth_cookies)
    assert res_start.status_code == 403
