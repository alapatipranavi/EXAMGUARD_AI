from datetime import datetime, timedelta, timezone
import pytest
from app.models.user import UserRole
from app.models.exam import ExamStatus
from app.repositories.user_repository import user_repository
from app.repositories.question_repository import question_repository
from app.schemas.question import QuestionCreate
from app.core.security import hash_password, create_access_token


@pytest.fixture
def exam_test_context(db):
    ex1 = user_repository.create_user(db, "ex1@test.com", hash_password("Pass123!"), "Ex1", "User", UserRole.EXAMINER)
    ex2 = user_repository.create_user(db, "ex2@test.com", hash_password("Pass123!"), "Ex2", "User", UserRole.EXAMINER)
    st = user_repository.create_user(db, "st1@test.com", hash_password("Pass123!"), "St1", "User", UserRole.STUDENT)
    ad = user_repository.create_user(db, "ad1@test.com", hash_password("Pass123!"), "Ad1", "User", UserRole.ADMIN)

    t_ex1 = create_access_token({"sub": str(ex1.id), "role": "EXAMINER"})
    t_ex2 = create_access_token({"sub": str(ex2.id), "role": "EXAMINER"})
    t_st = create_access_token({"sub": str(st.id), "role": "STUDENT"})
    t_ad = create_access_token({"sub": str(ad.id), "role": "ADMIN"})

    # Create questions for ex1
    q1 = question_repository.create_question(
        db,
        QuestionCreate(
            question_text="Q1 text for EX1",
            subject="Computer Science",
            topic="Algorithms",
            question_type="MCQ",
            difficulty="EASY",
            marks=2.0,
            options=[{"option_text": "A", "option_order": 1, "is_correct": True}, {"option_text": "B", "option_order": 2, "is_correct": False}]
        ),
        ex1.id
    )
    q2 = question_repository.create_question(
        db,
        QuestionCreate(
            question_text="Q2 text for EX1",
            subject="Computer Science",
            topic="Algorithms",
            question_type="SHORT_ANSWER",
            difficulty="MEDIUM",
            marks=3.0
        ),
        ex1.id
    )

    # Inactive question for ex1
    q_inactive = question_repository.create_question(
        db,
        QuestionCreate(
            question_text="Inactive question text",
            subject="Computer Science",
            question_type="SHORT_ANSWER",
            marks=5.0
        ),
        ex1.id
    )
    question_repository.archive_question(db, q_inactive)

    # Question for ex2
    q_ex2 = question_repository.create_question(
        db,
        QuestionCreate(
            question_text="Q text for EX2",
            subject="Computer Science",
            question_type="SHORT_ANSWER",
            marks=4.0
        ),
        ex2.id
    )

    return {
        "ex1": ex1,
        "ex2": ex2,
        "st": st,
        "ad": ad,
        "h_ex1": {"Authorization": f"Bearer {t_ex1}"},
        "h_ex2": {"Authorization": f"Bearer {t_ex2}"},
        "h_st": {"Authorization": f"Bearer {t_st}"},
        "h_ad": {"Authorization": f"Bearer {t_ad}"},
        "q1": q1,
        "q2": q2,
        "q_inactive": q_inactive,
        "q_ex2": q_ex2,
    }


def test_examiner_create_draft_exam_success(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Midterm Exam 2026",
        "subject": "Computer Science",
        "description": "Algorithms midterm exam",
        "instructions": "No calculators allowed.",
        "duration_minutes": 60,
        "passing_marks": 2.5,
        "questions": [
            {"question_id": str(ctx["q1"].id), "question_order": 1},
            {"question_id": str(ctx["q2"].id), "question_order": 2, "marks_override": 4.0}
        ]
    }

    res = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    assert res.status_code == 201
    data = res.json()
    assert data["title"] == "Midterm Exam 2026"
    assert data["status"] == "DRAFT"
    assert data["created_by"] == str(ctx["ex1"].id)
    assert data["total_marks"] == 6.0  # 2.0 (q1) + 4.0 (q2 override)
    assert len(data["questions"]) == 2


def test_student_and_admin_cannot_create_exam_forbidden(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Unauthorized Exam",
        "subject": "Computer Science",
        "duration_minutes": 60
    }

    res_st = client.post("/api/exams", json=payload, headers=ctx["h_st"])
    assert res_st.status_code == 403

    res_ad = client.post("/api/exams", json=payload, headers=ctx["h_ad"])
    assert res_ad.status_code == 403


def test_examiner_can_only_see_own_exams(client, exam_test_context):
    ctx = exam_test_context
    # Create exam for ex1
    r1 = client.post("/api/exams", json={"title": "EX1 Exam", "subject": "CS", "duration_minutes": 30}, headers=ctx["h_ex1"])
    exam1_id = r1.json()["id"]

    # Create exam for ex2
    r2 = client.post("/api/exams", json={"title": "EX2 Exam", "subject": "CS", "duration_minutes": 45}, headers=ctx["h_ex2"])

    # ex1 lists exams
    list_ex1 = client.get("/api/exams", headers=ctx["h_ex1"])
    assert list_ex1.status_code == 200
    items1 = list_ex1.json()["items"]
    assert len(items1) == 1
    assert items1[0]["id"] == exam1_id

    # ex2 cannot access ex1's exam details
    get_cross = client.get(f"/api/exams/{exam1_id}", headers=ctx["h_ex2"])
    assert get_cross.status_code == 404


def test_examiner_cannot_edit_other_examiner_exam(client, exam_test_context):
    ctx = exam_test_context
    r1 = client.post("/api/exams", json={"title": "EX1 Original Exam", "subject": "CS", "duration_minutes": 30}, headers=ctx["h_ex1"])
    exam1_id = r1.json()["id"]

    # ex2 attempts to update ex1's exam
    res = client.patch(f"/api/exams/{exam1_id}", json={"title": "Hacked Title"}, headers=ctx["h_ex2"])
    assert res.status_code == 404


def test_examiner_cannot_select_other_examiner_question(client, exam_test_context):
    ctx = exam_test_context
    # ex1 attempts to include ex2's question
    payload = {
        "title": "Cross Question Exam",
        "subject": "CS",
        "duration_minutes": 30,
        "questions": [{"question_id": str(ctx["q_ex2"].id), "question_order": 1}]
    }

    res = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    assert res.status_code == 400
    assert "owned by another examiner" in res.json()["detail"].lower() or "invalid" in res.json()["detail"].lower()


def test_inactive_question_cannot_be_selected(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Inactive Question Exam",
        "subject": "CS",
        "duration_minutes": 30,
        "questions": [{"question_id": str(ctx["q_inactive"].id), "question_order": 1}]
    }

    res = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    assert res.status_code == 400


def test_at_least_one_question_required_before_publish(client, exam_test_context):
    ctx = exam_test_context
    # Create empty DRAFT exam
    r1 = client.post("/api/exams", json={"title": "Empty Exam", "subject": "CS", "duration_minutes": 30}, headers=ctx["h_ex1"])
    exam_id = r1.json()["id"]

    # Attempt to publish empty exam
    pub_res = client.post(f"/api/exams/{exam_id}/publish", headers=ctx["h_ex1"])
    assert pub_res.status_code == 400
    assert "at least one active question" in pub_res.json()["detail"].lower()


def test_invalid_marks_and_passing_marks_rejected(client, exam_test_context):
    ctx = exam_test_context

    # Passing marks > total marks
    payload = {
        "title": "Passing Marks Too High",
        "subject": "CS",
        "duration_minutes": 30,
        "passing_marks": 100.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]  # total marks = 2.0
    }
    res = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    assert res.status_code == 400
    assert "cannot exceed total marks" in res.json()["detail"].lower()


def test_invalid_schedule_rejected(client, exam_test_context):
    ctx = exam_test_context
    now = datetime.now(timezone.utc)
    payload = {
        "title": "Invalid Schedule Exam",
        "subject": "CS",
        "duration_minutes": 30,
        "start_at": (now + timedelta(hours=2)).isoformat(),
        "end_at": (now + timedelta(hours=1)).isoformat()  # end before start
    }
    res = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    assert res.status_code == 400
    assert "end time must be after start time" in res.json()["detail"].lower()


def test_valid_draft_can_be_published(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Valid Final Exam",
        "subject": "CS",
        "duration_minutes": 60,
        "passing_marks": 1.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]
    }

    r1 = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    exam_id = r1.json()["id"]

    pub_res = client.post(f"/api/exams/{exam_id}/publish", headers=ctx["h_ex1"])
    assert pub_res.status_code == 200
    assert pub_res.json()["status"] == "PUBLISHED"


def test_published_exam_cannot_be_edited(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Published Exam to Edit",
        "subject": "CS",
        "duration_minutes": 60,
        "passing_marks": 1.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]
    }

    r1 = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    exam_id = r1.json()["id"]

    # Publish it
    client.post(f"/api/exams/{exam_id}/publish", headers=ctx["h_ex1"])

    # Attempt patch on published exam
    patch_res = client.patch(f"/api/exams/{exam_id}", json={"title": "New Title"}, headers=ctx["h_ex1"])
    assert patch_res.status_code == 400
    assert "cannot be edited" in patch_res.json()["detail"].lower()


def test_published_exam_can_be_archived(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Published Exam to Archive",
        "subject": "CS",
        "duration_minutes": 60,
        "passing_marks": 1.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]
    }

    r1 = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    exam_id = r1.json()["id"]

    client.post(f"/api/exams/{exam_id}/publish", headers=ctx["h_ex1"])

    arc_res = client.post(f"/api/exams/{exam_id}/archive", headers=ctx["h_ex1"])
    assert arc_res.status_code == 200
    assert arc_res.json()["status"] == "ARCHIVED"


def test_exam_ownership_derived_from_jwt(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "JWT Ownership Test",
        "subject": "CS",
        "duration_minutes": 45
    }

    res = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    assert res.status_code == 201
    assert res.json()["created_by"] == str(ctx["ex1"].id)


def test_unarchive_exam_lifecycle_and_security(client, exam_test_context):
    ctx = exam_test_context
    payload = {
        "title": "Archived Exam to Unarchive",
        "subject": "CS",
        "duration_minutes": 60,
        "passing_marks": 1.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]
    }

    # 1. Create & Archive exam
    r1 = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    exam_id = r1.json()["id"]
    client.post(f"/api/exams/{exam_id}/archive", headers=ctx["h_ex1"])

    # 4. Student cannot unarchive -> 403
    st_res = client.post(f"/api/exams/{exam_id}/unarchive", headers=ctx["h_st"])
    assert st_res.status_code == 403

    # 5. Admin cannot unarchive -> 403
    ad_res = client.post(f"/api/exams/{exam_id}/unarchive", headers=ctx["h_ad"])
    assert ad_res.status_code == 403

    # 6. Examiner cannot unarchive another Examiner's exam -> 404
    ex2_res = client.post(f"/api/exams/{exam_id}/unarchive", headers=ctx["h_ex2"])
    assert ex2_res.status_code == 404

    # 1 & 2. Owner Examiner can unarchive ARCHIVED exam -> status becomes DRAFT
    unarc_res = client.post(f"/api/exams/{exam_id}/unarchive", headers=ctx["h_ex1"])
    assert unarc_res.status_code == 200
    assert unarc_res.json()["status"] == "DRAFT"

    # 3. Unarchived exam becomes editable again
    edit_res = client.patch(
        f"/api/exams/{exam_id}",
        json={"title": "Updated Title After Unarchive"},
        headers=ctx["h_ex1"]
    )
    assert edit_res.status_code == 200
    assert edit_res.json()["title"] == "Updated Title After Unarchive"

    # 7. DRAFT cannot be unarchived -> 400
    draft_unarc_res = client.post(f"/api/exams/{exam_id}/unarchive", headers=ctx["h_ex1"])
    assert draft_unarc_res.status_code == 400
    assert "DRAFT" in draft_unarc_res.json()["detail"]

    # 8 & 9. PUBLISHED cannot be unarchived & remains unchanged if unarchive fails
    client.post(f"/api/exams/{exam_id}/publish", headers=ctx["h_ex1"])
    pub_unarc_res = client.post(f"/api/exams/{exam_id}/unarchive", headers=ctx["h_ex1"])
    assert pub_unarc_res.status_code == 400
    assert "PUBLISHED" in pub_unarc_res.json()["detail"]

    # Verify status remains PUBLISHED
    get_res = client.get(f"/api/exams/{exam_id}", headers=ctx["h_ex1"])
    assert get_res.json()["status"] == "PUBLISHED"


def test_delete_draft_exam_lifecycle_and_security(client, exam_test_context, db):
    import uuid
    ctx = exam_test_context
    payload = {
        "title": "Draft Exam to Delete",
        "subject": "CS",
        "duration_minutes": 30,
        "passing_marks": 1.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]
    }

    # Create draft exam
    r1 = client.post("/api/exams", json=payload, headers=ctx["h_ex1"])
    exam_id = r1.json()["id"]

    # Create an unrelated exam to verify deletion does not affect unrelated data
    r_unrelated = client.post("/api/exams", json={"title": "Unrelated Exam", "subject": "CS", "duration_minutes": 45}, headers=ctx["h_ex1"])
    unrelated_id = r_unrelated.json()["id"]

    # 7. Student cannot delete -> 403
    st_res = client.delete(f"/api/exams/{exam_id}", headers=ctx["h_st"])
    assert st_res.status_code == 403

    # 8. Admin cannot delete -> 403
    ad_res = client.delete(f"/api/exams/{exam_id}", headers=ctx["h_ad"])
    assert ad_res.status_code == 403

    # 9. Examiner cannot delete another Examiner's exam -> 404
    ex2_res = client.delete(f"/api/exams/{exam_id}", headers=ctx["h_ex2"])
    assert ex2_res.status_code == 404

    # 5. Published exam cannot be deleted -> 400
    pub_payload = {
        "title": "Published Exam to Delete Test",
        "subject": "CS",
        "duration_minutes": 60,
        "passing_marks": 1.0,
        "questions": [{"question_id": str(ctx["q1"].id), "question_order": 1}]
    }
    r_pub = client.post("/api/exams", json=pub_payload, headers=ctx["h_ex1"])
    pub_id = r_pub.json()["id"]
    client.post(f"/api/exams/{pub_id}/publish", headers=ctx["h_ex1"])

    pub_del_res = client.delete(f"/api/exams/{pub_id}", headers=ctx["h_ex1"])
    assert pub_del_res.status_code == 400
    assert "Published exams cannot be deleted" in pub_del_res.json()["detail"]

    # 6. Archived exam cannot be deleted -> 400
    r_arc = client.post("/api/exams", json={"title": "Archived Exam Delete Test", "subject": "CS", "duration_minutes": 30}, headers=ctx["h_ex1"])
    arc_id = r_arc.json()["id"]
    client.post(f"/api/exams/{arc_id}/archive", headers=ctx["h_ex1"])

    arc_del_res = client.delete(f"/api/exams/{arc_id}", headers=ctx["h_ex1"])
    assert arc_del_res.status_code == 400
    assert "Archived exams cannot be deleted" in arc_del_res.json()["detail"]

    # 1. Owner Examiner can delete DRAFT -> 204 No Content with empty body
    del_res = client.delete(f"/api/exams/{exam_id}", headers=ctx["h_ex1"])
    assert del_res.status_code == 204
    assert del_res.content == b""

    # 2. Deleted exam no longer appears in exam list
    get_res = client.get(f"/api/exams/{exam_id}", headers=ctx["h_ex1"])
    assert get_res.status_code == 404

    list_res = client.get("/api/exams", headers=ctx["h_ex1"])
    listed_ids = [e["id"] for e in list_res.json()["items"]]
    assert exam_id not in listed_ids

    # 3. Associated exam_questions are removed from database
    from app.models.exam import ExamQuestion
    eq_count = db.query(ExamQuestion).filter(ExamQuestion.exam_id == uuid.UUID(exam_id)).count()
    assert eq_count == 0

    # 4. Original Question Bank questions still exist!
    q1_db = question_repository.get_by_id(db, ctx["q1"].id)
    assert q1_db is not None
    assert q1_db.id == ctx["q1"].id

    # 10. Unrelated exam and questions are completely unaffected
    unrelated_get = client.get(f"/api/exams/{unrelated_id}", headers=ctx["h_ex1"])
    assert unrelated_get.status_code == 200
