"""STU-01 adversarial cross-user and cross-course tests (AC7, task 10; threat model: IDOR, draft probing)."""
from auth_helpers import call, code_of, new_student, seeded
from stu01_helpers import sql
from stu01_helpers import (LESSON_NOT_FOUND, RANDOM_ID, STUDY, completion_rows, course_entry, enroll,
                           enrolled_student, get_course_lessons, get_courses, get_lesson, make_course, make_draft,
                           make_lesson, put_completion, withdraw, world)


def test_stu01_ac7_a_second_student_in_the_same_course_sees_only_their_own_completion():
    cid, a, (l1, l2) = world()
    b = enrolled_student(cid)
    put_completion(a, l1, True)
    assert get_lesson(a, l1).json()["completed"] is True
    assert get_lesson(b, l1).json()["completed"] is False
    assert get_lesson(b, l1).json()["completed_at"] is None
    assert course_entry(b, cid)["completed_count"] == 0
    assert course_entry(a, cid)["completed_count"] == 1
    flags = {i["id"]: i["completed"] for t in get_course_lessons(b, cid).json()["topics"] for i in t["lessons"]}
    assert flags == {l1: False, l2: False}


def test_stu01_ac7_changing_my_completion_never_touches_the_other_students_row():
    cid, a, (l1, _) = world()
    b = enrolled_student(cid)
    put_completion(a, l1, True)
    put_completion(b, l1, True)
    put_completion(b, l1, False)
    assert get_lesson(a, l1).json()["completed"] is True
    assert completion_rows(a, l1)[0][1] is True
    assert completion_rows(b, l1)[0][1] is False


def test_stu01_ac7_a_student_in_another_course_cannot_read_or_change_completion():
    cid, a, (l1, _) = world()
    other_course = make_course()
    outsider = enrolled_student(other_course)
    put_completion(a, l1, True)
    assert get_lesson(outsider, l1).json() == LESSON_NOT_FOUND
    r = put_completion(outsider, l1, True)
    assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND
    assert completion_rows(outsider) == []
    assert get_course_lessons(outsider, cid).status_code == 404
    assert get_courses(outsider).json()["courses"][0]["completed_count"] == 0


def test_stu01_ac7_the_not_found_answer_does_not_reveal_whether_the_lesson_exists():
    cid, a, (l1, _) = world()
    outsider = new_student()
    real = call("GET", f"{STUDY}/lessons/{l1}", outsider)
    fake = call("GET", f"{STUDY}/lessons/{RANDOM_ID}", outsider)
    assert real.status_code == fake.status_code == 404 and real.json() == fake.json()
    real = call("PUT", f"{STUDY}/lessons/{l1}/completion", outsider, {"completed": True})
    fake = call("PUT", f"{STUDY}/lessons/{RANDOM_ID}/completion", outsider, {"completed": True})
    assert real.status_code == fake.status_code == 404 and real.json() == fake.json()
    real = call("GET", f"{STUDY}/courses/{cid}/lessons", outsider)
    fake = call("GET", f"{STUDY}/courses/{RANDOM_ID}/lessons", outsider)
    assert real.status_code == fake.status_code == 404 and real.json() == fake.json()


def test_stu01_ac7_no_body_or_query_field_can_choose_another_user():
    cid, a, (l1, _) = world()
    b = enrolled_student(cid)
    put_completion(a, l1, True)
    for body in ({"completed": True, "user_id": str(a)}, {"completed": False, "user_id": str(a)}):
        assert call("PUT", f"{STUDY}/lessons/{l1}/completion", b, body).status_code == 422
    r = call("PUT", f"{STUDY}/lessons/{l1}/completion?user_id={a}", b, {"completed": False})
    assert r.status_code == 200
    assert completion_rows(a, l1)[0][1] is True  # a unchanged
    assert completion_rows(b, l1)[0][1] is False  # the write went to b's own row


def test_stu01_ac7_header_spoofing_does_not_read_or_write_another_students_row():
    cid, a, (l1, _) = world()
    b = enrolled_student(cid)
    put_completion(a, l1, True)
    spoof = {"X-Student-Id": str(a), "X-Demo-User-Id": str(a)}
    r = call("GET", f"{STUDY}/lessons/{l1}", b, headers=spoof)
    assert r.json()["completed"] is False
    call("PUT", f"{STUDY}/lessons/{l1}/completion", b, {"completed": False}, headers=spoof)
    assert completion_rows(a, l1)[0][1] is True


def test_stu01_ac7_session_of_one_student_cannot_be_used_with_the_csrf_token_of_another():
    cid, a, (l1, _) = world()
    b = enrolled_student(cid)
    r = call("PUT", f"{STUDY}/lessons/{l1}/completion", a, {"completed": True}, csrf=b.csrf)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"
    assert completion_rows(a, l1) == []


def test_stu01_ac7_teacher_and_admin_cannot_read_or_change_a_students_completion():
    cid, a, (l1, _) = world()
    put_completion(a, l1, True)
    for role in ("teacher", "admin"):
        who = seeded(role)
        assert call("GET", f"{STUDY}/lessons/{l1}", who).status_code == 403
        assert call("GET", f"{STUDY}/courses", who).status_code == 403
        assert call("GET", f"{STUDY}/courses/{cid}/lessons", who).status_code == 403
        assert call("PUT", f"{STUDY}/lessons/{l1}/completion", who, {"completed": False}).status_code == 403
    assert completion_rows(a, l1)[0][1] is True


def test_stu01_ac7_completion_data_is_never_present_in_another_students_responses():
    cid, a, (l1, l2) = world()
    b = enrolled_student(cid)
    put_completion(a, l1, True)
    at = get_lesson(a, l1).json()["completed_at"]
    for r in (get_lesson(b, l1), get_courses(b), get_course_lessons(b, cid), put_completion(b, l2, True)):
        assert at not in r.text
        assert str(a) not in r.text


def test_stu01_ac2_draft_ids_withdrawn_and_foreign_lessons_cannot_be_completed():
    cid, a, _ = world()
    other = make_course()
    cases = {"draft": make_draft(cid), "withdrawn": make_lesson(cid, withdrawn=True),
             "foreign": make_lesson(other), "random": RANDOM_ID}
    for name, lid in cases.items():
        for completed in (True, False):
            r = call("PUT", f"{STUDY}/lessons/{lid}/completion", a, {"completed": completed})
            assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND, (name, completed)
    assert completion_rows(a) == []


def test_stu01_ac2_a_draft_id_cannot_be_probed_through_the_course_lists_either():
    cid, a, _ = world()
    draft = make_draft(cid, title="PRIVATE-DRAFT-TITLE", content="PRIVATE-DRAFT-BODY")
    for r in (get_course_lessons(a, cid), get_courses(a), get_lesson(a, draft)):
        assert draft not in r.text.replace(cid, "")
        assert "PRIVATE-DRAFT" not in r.text


def test_stu01_ac7_withdrawing_a_lesson_hides_it_from_every_student_but_keeps_everyones_records():
    cid, a, (l1, l2) = world()
    b = enrolled_student(cid)
    put_completion(a, l1, True)
    put_completion(b, l1, True)
    withdraw(l1)
    for s in (a, b):
        assert get_lesson(s, l1).json() == LESSON_NOT_FOUND
        ids = [i["id"] for t in get_course_lessons(s, cid).json()["topics"] for i in t["lessons"]]
        assert ids == [l2]
    assert sql("SELECT count(*) FROM lesson_completion WHERE lesson_id = %s", (l1,))[0][0] == 2


def test_stu01_ac7_a_student_removed_from_a_course_keeps_the_record_but_loses_access():
    cid, a, (l1, _) = world()
    put_completion(a, l1, True)
    sql("DELETE FROM course_membership WHERE course_id = %s AND user_id = %s", (cid, str(a)))
    assert get_lesson(a, l1).status_code == 404
    assert put_completion(a, l1, False).status_code == 404
    assert completion_rows(a, l1)[0][1] is True
    enroll(a, cid)
    assert get_lesson(a, l1).json()["completed"] is True
