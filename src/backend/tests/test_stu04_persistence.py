"""STU-04 AC8: practice attempts are stored in the practice_attempt table behind AttemptStore."""
import json
from datetime import datetime

import attempt_store
from auth_helpers import call, code_of, login, new_student, student_from_login
from stu04_helpers import (KEY, SET_ID, answers_with, attempt_rows, body_of, only_set, save, start, submit,
                           submitted)


def test_stu04_ac8_the_in_memory_store_is_gone():
    assert not hasattr(attempt_store, "InMemoryAttemptStore")
    assert hasattr(attempt_store, "store")


def test_stu04_ac8_starting_an_attempt_inserts_one_in_progress_row_owned_by_the_session_student():
    s = new_student()
    aid = start(s)
    rows = attempt_rows(s)
    assert len(rows) == 1
    row_id, status, answers, correct, total, key_version, correct_ids, submitted_at = rows[0]
    assert row_id == aid
    assert status == "in_progress"
    assert answers == {}
    assert (correct, total, key_version, submitted_at) == (None, None, None, None)
    assert correct_ids == []


def test_stu04_ac8_saved_answers_are_merged_into_the_stored_row():
    s = new_student()
    aid = start(s)
    save(aid, s, {"q1": "b"})
    save(aid, s, {"q2": "a"})
    save(aid, s, {"q1": "a"})
    assert attempt_rows(s)[0][2] == {"q1": "a", "q2": "a"}
    r = call("GET", f"/api/attempts/{aid}", s)
    assert r.json()["answers"] == {"q1": "a", "q2": "a"}


def test_stu04_ac8_submission_stores_score_key_version_correct_ids_and_timestamp():
    s = new_student()
    aid = start(s)
    save(aid, s, {"q1": "a", "q2": "a", "q3": "c"})  # q1 and q3 correct
    r = submit(aid, s)
    assert r.status_code == 200
    (row_id, status, answers, correct, total, key_version, correct_ids, submitted_at), = attempt_rows(s)
    assert (row_id, status) == (aid, "submitted")
    assert answers == {"q1": "a", "q2": "a", "q3": "c"}
    assert (correct, total) == (2, 3)
    assert key_version and isinstance(key_version, str)
    assert correct_ids == ["q1", "q3"]  # in set order
    assert isinstance(submitted_at, datetime)


def test_stu04_ac8_the_stored_row_never_contains_the_answer_key_or_explanations():
    s = new_student()
    submitted(s, 3)
    dump = json.dumps([[str(c) for c in row] for row in attempt_rows(s)])
    for needle in ("correct_choice", "explanation", "focused responsibility"):
        assert needle not in dump


def test_stu04_ac8_scores_survive_a_new_login_and_a_new_database_connection():
    s = new_student()
    submitted(s, 2)
    submitted(s, 3)
    first = body_of(s)
    fresh = student_from_login(login(s.email, s.password), s.email, s.password)
    assert body_of(fresh) == first
    assert only_set(first)["attempts_submitted"] == 2


def test_stu04_ac8_stu02_flow_keeps_its_bodies_and_codes():
    s = new_student()
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", s)
    assert r.status_code == 201
    aid = r.json()["attempt_id"]
    assert r.json() == {"attempt_id": aid, "set_id": SET_ID, "status": "in_progress", "answers": {}}
    assert save(aid, s, {"q1": "a"}).json() == {"attempt_id": aid, "status": "in_progress", "answers": {"q1": "a"}}
    assert save(aid, s, {"zz": "a"}).status_code == 422
    assert attempt_rows(s)[0][2] == {"q1": "a"}  # nothing from the rejected save is stored
    incomplete = submit(aid, s)
    assert incomplete.status_code == 422
    assert attempt_rows(s)[0][1] == "in_progress"  # nothing from the rejected submit is stored
    save(aid, s, {"q2": "b", "q3": "c"})
    ok = submit(aid, s)
    assert ok.status_code == 200
    assert ok.json()["score"] == {"correct": 3, "total": 3}
    again = submit(aid, s)
    assert again.status_code == 409 and code_of(again) == "already_submitted"
    late = save(aid, s, {"q1": "b"})
    assert late.status_code == 409
    row = attempt_rows(s)[0]
    assert row[2] == KEY and row[3] == 3  # the submitted row is not changed by the rejected calls


def test_stu04_ac8_unknown_attempt_id_is_404_with_the_same_body():
    s = new_student()
    r = call("GET", "/api/attempts/does-not-exist", s)
    assert r.status_code == 404
    assert r.json() == {"detail": {"code": "attempt_not_found", "message": "Attempt not found."}}


def test_stu04_ac8_attempt_ids_are_compared_exactly():
    s = new_student()
    aid = start(s)
    for variant in (aid.upper() if aid.upper() != aid else aid + "x", " " + aid, aid + " ", aid[:-1]):
        r = call("GET", f"/api/attempts/{variant}", s)
        assert r.status_code == 404, repr(variant)


def test_stu04_ac8_submitted_row_is_not_rewritten_by_a_second_submit_or_late_save():
    s = new_student()
    aid = submitted(s, 1)
    before = attempt_rows(s)
    assert submit(aid, s).status_code == 409
    assert save(aid, s, answers_with(3)).status_code == 409
    assert attempt_rows(s) == before


def test_stu04_ac8_a_database_failure_is_503_and_never_sample_data():
    from auth.db import get_session
    from main import app
    from sqlalchemy.exc import OperationalError

    def broken():
        raise OperationalError("select 1", {}, Exception("db is down"))
        yield  # pragma: no cover

    s = new_student()
    app.dependency_overrides[get_session] = broken
    try:
        r = call("GET", "/api/progress", s)
    finally:
        app.dependency_overrides.pop(get_session, None)
    assert r.status_code == 503
    assert r.json() == {"detail": {"code": "service_unavailable", "message": "The service is unavailable."}}
    assert "db is down" not in r.text
