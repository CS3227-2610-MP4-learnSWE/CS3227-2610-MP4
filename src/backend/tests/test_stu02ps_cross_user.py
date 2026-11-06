"""STU-02-published-sets AC8, AC10, AC12: cross-user and cross-course access (real DbSetProvider)."""
import uuid

import pytest

from auth_helpers import call, new_student, seeded
from published_sets import question_rows, world
from stu01_helpers import enroll, enrolled_student, unenroll

ATTEMPT_NOT_FOUND = {"detail": {"code": "attempt_not_found", "message": "Attempt not found."}}
SET_NOT_FOUND = {"detail": {"code": "set_not_found", "message": "Practice set not found."}}


def setup_submitted():
    cid, tid, sid = world()
    owner = enrolled_student(cid)
    aid = call("POST", f"/api/practice-sets/{sid}/attempts", owner).json()["attempt_id"]
    q = [r[0] for r in question_rows(sid)]
    call("PUT", f"/api/attempts/{aid}/answers", owner, {"answers": dict(zip(q, "abc"))})
    assert call("POST", f"/api/attempts/{aid}/submit", owner).status_code == 200
    open_aid = call("POST", f"/api/practice-sets/{sid}/attempts", owner).json()["attempt_id"]
    return cid, sid, owner, aid, open_aid, q


def touch_all(s, aid, q):
    return [
        call("GET", f"/api/attempts/{aid}", s),
        call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": {q[0]: "d"}}),
        call("POST", f"/api/attempts/{aid}/submit", s),
        call("GET", f"/api/attempts/{aid}/results", s),
    ]


@pytest.mark.parametrize("who", ["classmate", "other_course_student", "former_member"])
def test_stu02ps_cross_other_students_get_attempt_not_found_identical_to_an_unknown_id(who):
    cid, sid, owner, aid, open_aid, q = setup_submitted()
    if who == "classmate":
        other = enrolled_student(cid)
    elif who == "other_course_student":
        other = enrolled_student(world()[0])
    else:
        other = enrolled_student(cid)
        unenroll(other, cid)
    unknown = [r.json() for r in touch_all(other, f"t-{uuid.uuid4().hex[:20]}", q)]
    for target in (aid, open_aid):
        got = touch_all(other, target, q)
        assert [r.status_code for r in got] == [404] * 4
        assert [r.json() for r in got] == unknown == [ATTEMPT_NOT_FOUND] * 4
    # the owner's attempt is untouched
    assert call("GET", f"/api/attempts/{open_aid}", owner).json()["answers"] == {}
    assert call("GET", f"/api/attempts/{aid}/results", owner).status_code == 200


def test_stu02ps_cross_a_classmate_can_read_the_set_but_never_the_owners_score_in_the_picker():
    cid, sid, owner, aid, open_aid, q = setup_submitted()
    mate = enrolled_student(cid)
    assert call("GET", f"/api/practice-sets/{sid}", mate).status_code == 200
    mine = call("GET", "/api/practice-sets", owner).json()["courses"][0]["sets"][0]["best"]
    theirs = call("GET", "/api/practice-sets", mate).json()["courses"][0]["sets"][0]["best"]
    assert mine == {"correct": 3, "total": 3} and theirs is None
    assert call("GET", "/api/progress", mate).json()["practice"]["sets"] == []


def test_stu02ps_cross_a_student_outside_the_course_cannot_reach_the_set_and_gets_the_unknown_id_body():
    cid, sid, owner, aid, open_aid, q = setup_submitted()
    outsider = enrolled_student(world()[0])
    unknown = str(uuid.uuid4())
    for path, method in ((f"/api/practice-sets/{{}}", "GET"), ("/api/practice-sets/{}/attempts", "POST")):
        a = call(method, path.format(sid), outsider)
        b = call(method, path.format(unknown), outsider)
        assert a.status_code == b.status_code == 404
        assert a.json() == b.json() == SET_NOT_FOUND
        assert a.text == b.text
    assert call("GET", "/api/practice-sets", outsider).json()["courses"][0]["sets"][0]["id"] != sid


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_stu02ps_cross_teacher_and_admin_cannot_touch_a_students_attempts_or_sets(role):
    cid, sid, owner, aid, open_aid, q = setup_submitted()
    who = seeded(role)
    if role == "teacher":
        enroll(who, cid)  # even a member teacher of the set's course
    for r in touch_all(who, aid, q) + [call("GET", f"/api/practice-sets/{sid}", who),
                                       call("POST", f"/api/practice-sets/{sid}/attempts", who),
                                       call("GET", "/api/practice-sets", who)]:
        assert r.status_code == 403 and r.json()["detail"]["code"] == "forbidden"
    assert call("GET", f"/api/attempts/{aid}/results", owner).status_code == 200
    assert call("GET", f"/api/attempts/{open_aid}", owner).json()["answers"] == {}


def test_stu02ps_cross_a_forged_identity_header_does_not_open_the_owners_attempt():
    cid, sid, owner, aid, open_aid, q = setup_submitted()
    intruder = new_student()
    r = call("GET", f"/api/attempts/{aid}/results", intruder,
             headers={"X-Student-Id": str(owner), "X-Demo-User-Id": str(owner)})
    assert r.status_code == 404 and r.json() == ATTEMPT_NOT_FOUND
