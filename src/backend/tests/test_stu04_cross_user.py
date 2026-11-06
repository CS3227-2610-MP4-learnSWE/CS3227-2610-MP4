"""STU-04 AC6 (SHR-05): one student never sees or changes another student's progress or attempts."""
from auth_helpers import call, code_of, new_student, seeded
from stu01_helpers import enroll, enrolled_student, make_course, make_lesson, put_completion
from stu04_helpers import (EMPTY, answers_with, attempt_rows, body_of, only_set, progress, save, start, submit,
                           submitted, topic_item)

NOT_FOUND = {"detail": {"code": "attempt_not_found", "message": "Attempt not found."}}


def test_stu04_ac6_two_students_on_the_same_set_and_course_see_only_their_own_scores():
    cid = make_course()
    a, b = enrolled_student(cid, "alice"), enrolled_student(cid, "bob")
    lid = make_lesson(cid, title="Shared lesson")
    put_completion(a, lid, True)
    for n in (3, 3):
        submitted(a, n)
    for n in (0, 1, 0):
        submitted(b, n)
    sa, sb = only_set(body_of(a)), only_set(body_of(b))
    assert (sa["attempts_submitted"], sa["best"]["correct"], sa["latest"]["correct"]) == (2, 3, 3)
    assert (sb["attempts_submitted"], sb["best"]["correct"], sb["latest"]["correct"]) == (3, 1, 0)
    assert topic_item(body_of(a))["status"] == "on_track"
    assert topic_item(body_of(b))["status"] == "needs_practice"
    assert body_of(a)["lessons"]["totals"]["completed_count"] == 1
    assert body_of(b)["lessons"]["totals"]["completed_count"] == 0
    assert body_of(b)["lessons"]["recent"] == []


def test_stu04_ac6_another_students_attempts_do_not_change_my_figures():
    a, b = new_student("alice"), new_student("bob")
    submitted(a, 2)
    before = progress(a).json()
    for n in (0, 3, 1):
        submitted(b, n)
        aid = start(b)
        save(aid, b, answers_with(3))
        assert progress(a).json() == before
    assert progress(a).json() == before


def test_stu04_ac6_a_student_with_no_activity_sees_nothing_of_a_busy_classmate():
    cid = make_course()
    busy, idle = enrolled_student(cid, "busy"), enrolled_student(cid, "idle")
    submitted(busy, 3)
    put_completion(busy, make_lesson(cid), True)
    body = body_of(idle)
    assert body["practice"] == EMPTY["practice"]
    assert body["topics"]["items"] == []
    assert body["lessons"]["totals"]["completed_count"] == 0


def test_stu04_ac6_a_student_in_another_course_sees_none_of_the_first_courses_lessons():
    cid = make_course("Private course")
    a = enrolled_student(cid, "alice")
    make_lesson(cid, title="Private lesson")
    outsider = new_student("outsider")
    assert body_of(outsider)["lessons"] == EMPTY["lessons"]
    assert "Private" not in progress(outsider).text
    assert "Private lesson" not in progress(a).text  # titles of lessons are not part of the counts body


def test_stu04_ac6_attempt_ids_of_another_student_give_the_same_404_on_every_stu02_endpoint():
    a, b = new_student("alice"), new_student("bob")
    aid = start(a)
    save(aid, a, {"q1": "a"})
    unknown = call("GET", "/api/attempts/does-not-exist", b)
    assert unknown.status_code == 404 and unknown.json() == NOT_FOUND
    for method, path, body in [
        ("GET", f"/api/attempts/{aid}", None),
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q2": "b"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
    ]:
        r = call(method, path, b, body)
        assert r.status_code == 404, (method, path, r.text)
        assert r.json() == NOT_FOUND, (method, path)
        assert code_of(r) == "attempt_not_found"
    # A's attempt is untouched and still its owner's
    rows = attempt_rows(a)
    assert len(rows) == 1 and rows[0][1] == "in_progress" and rows[0][2] == {"q1": "a"}
    assert attempt_rows(b) == []


def test_stu04_ac6_a_failed_cross_user_submit_does_not_submit_the_victims_attempt():
    a, b = new_student("alice"), new_student("bob")
    aid = start(a)
    save(aid, a, answers_with(3))
    assert call("POST", f"/api/attempts/{aid}/submit", b).status_code == 404
    assert body_of(a)["practice"]["sets"] == []
    assert submit(aid, a).status_code == 200
    assert only_set(body_of(a))["attempts_submitted"] == 1
    assert body_of(b)["practice"]["sets"] == []


def test_stu04_ac6_teacher_and_admin_cannot_read_or_change_a_students_attempt_or_progress():
    s = new_student()
    aid = submitted(s, 3)
    before = body_of(s)
    for role in ("teacher", "admin"):
        u = seeded(role)
        assert progress(u).status_code == 403
        for method, path, body in [
            ("GET", f"/api/attempts/{aid}", None),
            ("GET", f"/api/attempts/{aid}/results", None),
            ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "b"}}),
            ("POST", f"/api/attempts/{aid}/submit", None),
        ]:
            r = call(method, path, u, body)
            assert r.status_code in (403, 404), (role, method, path, r.status_code)
            for needle in ("explanation", "correct_choice", "score"):
                assert needle not in r.text, (role, path, needle)
    assert body_of(s) == before
    rows = attempt_rows(s)
    assert len(rows) == 1 and rows[0][1] == "submitted" and rows[0][3] == 3


def test_stu04_ac6_a_new_login_of_the_same_student_sees_the_same_figures_and_another_login_does_not():
    from auth_helpers import login, student_from_login

    a = new_student("alice")
    submitted(a, 2)
    again = student_from_login(login(a.email, a.password), a.email, a.password)
    assert again.token != a.token
    assert body_of(again) == body_of(a)
    other = new_student("bob")
    assert body_of(other)["practice"]["sets"] == []


def test_stu04_ac6_membership_changes_for_one_student_do_not_affect_another():
    cid = make_course("Shared course")
    a, b = new_student("alice"), new_student("bob")
    enroll(a, cid)
    lid = make_lesson(cid)
    put_completion(a, lid, True)
    assert body_of(a)["lessons"]["totals"] == {"lesson_count": 1, "completed_count": 1}
    assert body_of(b)["lessons"]["totals"] == {"lesson_count": 0, "completed_count": 0}
    enroll(b, cid)
    assert body_of(b)["lessons"]["totals"] == {"lesson_count": 1, "completed_count": 0}
    assert body_of(a)["lessons"]["totals"] == {"lesson_count": 1, "completed_count": 1}
