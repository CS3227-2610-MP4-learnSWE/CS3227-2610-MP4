"""STU-01 AC6: session, role, CSRF and Origin on every study endpoint, and the order of checks.

Order (plan): 401, 403 csrf_failed (PUT only), 403 forbidden, 422 path id, 404 record, 422 body, work.
"""
import pytest
from auth_helpers import call, code_of, new_student, seeded
from stu01_helpers import sql
from stu01_helpers import RANDOM_ID, STUDY, enrolled_student, make_course, make_lesson, world


def endpoints(cid, lid):
    return [
        ("GET", f"{STUDY}/courses", None),
        ("GET", f"{STUDY}/courses/{cid}/lessons", None),
        ("GET", f"{STUDY}/lessons/{lid}", None),
        ("PUT", f"{STUDY}/lessons/{lid}/completion", {"completed": True}),
    ]


def test_stu01_ac6_signed_out_is_401_on_every_endpoint():
    cid, _, (lid, _) = world()
    for method, path, body in endpoints(cid, lid):
        r = call(method, path, None, body)
        assert r.status_code == 401 and code_of(r) == "unauthenticated", (method, path)


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_stu01_ac6_teacher_and_admin_are_403_forbidden_on_every_endpoint(role):
    cid, student, (lid, _) = world()
    who = seeded(role)
    for method, path, body in endpoints(cid, lid):
        r = call(method, path, who, body)
        assert r.status_code == 403 and code_of(r) == "forbidden", (role, method, path, r.text)
    # the 403 must not have written anything
    assert sql("SELECT count(*) FROM lesson_completion WHERE lesson_id = %s", (lid,))[0][0] == 0


def test_stu01_ac6_teacher_who_is_a_course_member_still_gets_403():
    t = seeded("teacher")
    cid = make_course()
    lid = make_lesson(cid)
    sql("INSERT INTO course_membership(course_id, user_id) VALUES (%s, %s)", (cid, str(t)))
    try:
        for method, path, body in endpoints(cid, lid):
            assert call(method, path, t, body).status_code == 403, path
    finally:
        sql("DELETE FROM course_membership WHERE course_id = %s AND user_id = %s", (cid, str(t)))


def test_stu01_ac6_put_without_a_valid_csrf_token_is_403_csrf_failed_and_changes_nothing():
    _, s, (lid, _) = world()
    other = new_student()
    path = f"{STUDY}/lessons/{lid}/completion"
    for csrf in (False, "", "wrong-token", other.csrf, s.csrf + "x", s.csrf.swapcase()):
        r = call("PUT", path, s, {"completed": True}, csrf=csrf)
        assert r.status_code == 403 and code_of(r) == "csrf_failed", (csrf, r.text)
    assert sql("SELECT count(*) FROM lesson_completion WHERE user_id = %s", (str(s),))[0][0] == 0
    assert call("PUT", path, s, {"completed": True}).status_code == 200


def test_stu01_ac6_foreign_origin_is_rejected_even_with_a_valid_csrf_token():
    _, s, (lid, _) = world()
    path = f"{STUDY}/lessons/{lid}/completion"
    for origin in ("https://evil.example", "http://localhost:5174", "null", "http://localhost:5173.evil.example"):
        r = call("PUT", path, s, {"completed": True}, headers={"Origin": origin})
        assert r.status_code == 403 and code_of(r) == "csrf_failed", origin
    assert sql("SELECT count(*) FROM lesson_completion WHERE user_id = %s", (str(s),))[0][0] == 0
    assert call("PUT", path, s, {"completed": True}, headers={"Origin": "http://localhost:5173"}).status_code == 200


def test_stu01_ac6_get_endpoints_need_no_csrf_token():
    cid, s, (lid, _) = world()
    for method, path, body in endpoints(cid, lid)[:3]:
        assert call(method, path, s, csrf=False).status_code == 200, path


def test_stu01_ac6_identity_headers_are_ignored():
    cid, s, (lid, _) = world()
    spoof = {"X-Student-Id": "demo-student", "X-Demo-User-Id": "demo-teacher"}
    for method, path, body in endpoints(cid, lid):
        assert call(method, path, None, body, headers=spoof).status_code == 401, path
    # with a session the header cannot change who acts or what is stored
    r = call("PUT", f"{STUDY}/lessons/{lid}/completion", s, {"completed": True}, headers=spoof)
    assert r.status_code == 200
    assert sql("SELECT user_id FROM lesson_completion WHERE lesson_id = %s", (lid,)) == [(str(s),)]
    t = seeded("teacher")
    assert call("GET", f"{STUDY}/courses", t, headers={"X-Student-Id": str(s)}).status_code == 403


@pytest.mark.parametrize("bad", [{"completed": True, "user_id": "demo-student"}, {"user_id": "x"},
                                 {"completed": "true"}, {"completed": 1}, {"completed": 0},
                                 {"completed": None}, {"completed": [True]}, {}, {"completed": True, "x": 1}])
def test_stu01_ac6_invalid_bodies_are_422_validation_error_and_store_nothing(bad):
    _, s, (lid, _) = world()
    r = call("PUT", f"{STUDY}/lessons/{lid}/completion", s, bad)
    assert r.status_code == 422 and code_of(r) == "validation_error", (bad, r.text)
    fields = r.json()["detail"].get("fields")
    assert isinstance(fields, list)
    for value in ("demo-student", "true"):
        assert value not in r.text  # field names only, never submitted values
    assert sql("SELECT count(*) FROM lesson_completion WHERE user_id = %s", (str(s),))[0][0] == 0


def test_stu01_ac6_non_boolean_completed_names_the_field():
    _, s, (lid, _) = world()
    r = call("PUT", f"{STUDY}/lessons/{lid}/completion", s, {"completed": "yes"})
    assert "completed" in r.json()["detail"]["fields"]


def test_stu01_ac6_missing_or_malformed_json_body_is_422():
    _, s, (lid, _) = world()
    path = f"{STUDY}/lessons/{lid}/completion"
    assert call("PUT", path, s).status_code == 422
    r = call("PUT", path, s, content=b"{not json", headers={"Content-Type": "application/json"})
    assert r.status_code == 422
    r = call("PUT", path, s, content=b"[]", headers={"Content-Type": "application/json"})
    assert r.status_code == 422


def test_stu01_ac6_order_401_before_422_before_404():
    _, s, (lid, _) = world()
    bad_path = f"{STUDY}/lessons/not-a-uuid/completion"
    assert call("PUT", bad_path, None, {"completed": True}).status_code == 401
    assert call("GET", f"{STUDY}/lessons/not-a-uuid", None).status_code == 401
    assert call("GET", f"{STUDY}/courses/not-a-uuid/lessons", None).status_code == 401
    # path id (422) is checked before the record (404), and the record before the body (422)
    assert call("PUT", bad_path, s, {"completed": True}).status_code == 422
    r = call("PUT", f"{STUDY}/lessons/{RANDOM_ID}/completion", s, {"completed": "nonsense"})
    assert r.status_code == 404 and code_of(r) == "not_found"
    r = call("PUT", f"{STUDY}/lessons/{lid}/completion", s, {"completed": "nonsense"})
    assert r.status_code == 422


def test_stu01_ac6_order_csrf_before_forbidden_and_role_before_path_and_record():
    t = seeded("teacher")
    path = f"{STUDY}/lessons/{RANDOM_ID}/completion"
    r = call("PUT", path, t, {"completed": True}, csrf=False)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"
    r = call("PUT", path, t, {"completed": True})
    assert r.status_code == 403 and code_of(r) == "forbidden"
    r = call("PUT", f"{STUDY}/lessons/not-a-uuid/completion", t, {"completed": True})
    assert r.status_code == 403 and code_of(r) == "forbidden"
    r = call("GET", f"{STUDY}/lessons/not-a-uuid", t)
    assert r.status_code == 403 and code_of(r) == "forbidden"
    # a student without CSRF on a record that does not exist: csrf first
    s = new_student()
    r = call("PUT", path, s, {"completed": True}, csrf=False)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"


def test_stu01_ac6_role_change_takes_effect_on_the_next_request():
    cid, s, (lid, _) = world()
    assert call("GET", f"{STUDY}/lessons/{lid}", s).status_code == 200
    sql('UPDATE "user" SET role = %s WHERE id = %s', ("teacher", str(s)))
    try:
        r = call("GET", f"{STUDY}/lessons/{lid}", s)
        assert r.status_code == 403 and code_of(r) == "forbidden"
    finally:
        sql('UPDATE "user" SET role = %s WHERE id = %s', ("student", str(s)))


def test_stu01_ac6_deleted_user_session_gets_401():
    cid, s, _ = world()
    sql("DELETE FROM course_membership WHERE user_id = %s", (str(s),))
    sql('DELETE FROM "user" WHERE id = %s', (str(s),))
    r = call("GET", f"{STUDY}/courses", s)
    assert r.status_code == 401 and code_of(r) == "unauthenticated"


def test_stu01_ac6_error_bodies_leak_no_internals():
    cid, s, (lid, _) = world()
    probes = [call("GET", f"{STUDY}/lessons/{RANDOM_ID}", s),
              call("GET", f"{STUDY}/courses/{RANDOM_ID}/lessons", s),
              call("PUT", f"{STUDY}/lessons/{lid}/completion", s, {"completed": "x"}),
              call("GET", f"{STUDY}/lessons/{lid}", None)]
    for r in probes:
        for bad in ("Traceback", "sqlalchemy", "psycopg", "SELECT", ".py", "published_lesson"):
            assert bad not in r.text, (r.status_code, bad)


def test_stu01_ac6_database_failure_is_503_without_sample_data(monkeypatch):
    cid, s, (lid, _) = world()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none")
    for method, path, body in endpoints(cid, lid):
        r = call(method, path, s, body)
        assert r.status_code == 503 and code_of(r) == "service_unavailable", (path, r.status_code)
        assert "Traceback" not in r.text and "psycopg" not in r.text
