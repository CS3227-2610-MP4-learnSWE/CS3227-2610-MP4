"""STU-02-published-sets AC22: simultaneous requests on published sets (real DbSetProvider).

Threads each drive the ASGI app (pattern of test_stu04_concurrency).
"""
import threading
from concurrent.futures import ThreadPoolExecutor

from auth_helpers import call, code_of
from published_sets import question_rows, world
from stu01_helpers import enrolled_student, sql, unenroll

NOT_FOUND = {"detail": {"code": "set_not_found", "message": "Practice set not found."}}


def fire(requests):
    barrier = threading.Barrier(len(requests))

    def run(fn):
        barrier.wait(timeout=60)
        return fn()

    with ThreadPoolExecutor(max_workers=len(requests)) as pool:
        return list(pool.map(run, requests))


def start(s, sid):
    r = call("POST", f"/api/practice-sets/{sid}/attempts", s)
    assert r.status_code == 201, r.text
    return r.json()["attempt_id"]


def qids(sid):
    return [r[0] for r in question_rows(sid)]


def put(aid, s, answers):
    return call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": answers})


def test_stu02ps_conc_two_submits_of_one_attempt_give_one_200_and_one_409():
    for _ in range(3):
        cid, tid, sid = world()
        s = enrolled_student(cid)
        aid = start(s, sid)
        assert put(aid, s, dict(zip(qids(sid), "abc"))).status_code == 200
        results = fire([lambda: call("POST", f"/api/attempts/{aid}/submit", s) for _ in range(2)])
        assert sorted(r.status_code for r in results) == [200, 409]
        loser = next(r for r in results if r.status_code == 409)
        assert code_of(loser) == "already_submitted"
        winner = next(r for r in results if r.status_code == 200)
        assert winner.json()["score"] == {"correct": 3, "total": 3}
        row = sql("SELECT status, score_correct, score_total FROM practice_attempt WHERE id = %s", (aid,))
        assert row == [("submitted", 3, 3)]


def test_stu02ps_conc_simultaneous_saves_on_different_questions_lose_nothing():
    cid, tid, sid = world()
    s = enrolled_student(cid)
    aid = start(s, sid)
    q = qids(sid)
    results = fire([lambda i=i: put(aid, s, {q[i]: "abc"[i]}) for i in range(3)])
    assert all(r.status_code == 200 for r in results)
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == dict(zip(q, "abc"))


def test_stu02ps_conc_eight_simultaneous_starts_make_eight_independent_attempts():
    cid, tid, sid = world()
    s = enrolled_student(cid)
    results = fire([lambda: call("POST", f"/api/practice-sets/{sid}/attempts", s) for _ in range(8)])
    assert all(r.status_code == 201 for r in results)
    ids = {r.json()["attempt_id"] for r in results}
    assert len(ids) == 8
    rows = sql("SELECT count(*) FROM practice_attempt WHERE student_id = %s AND set_id = %s", (str(s), sid))
    assert rows == [(8,)]
    for r in results:
        assert r.json()["answers"] == {} and r.json()["status"] == "in_progress" and r.json()["set_id"] == sid


def test_stu02ps_conc_two_students_submitting_the_same_set_at_once_do_not_interfere():
    cid, tid, sid = world()
    a, b = enrolled_student(cid), enrolled_student(cid)
    aa, ab = start(a, sid), start(b, sid)
    q = qids(sid)
    put(aa, a, dict(zip(q, "abc")))
    put(ab, b, dict(zip(q, "ddd")))
    ra, rb = fire([lambda: call("POST", f"/api/attempts/{aa}/submit", a), lambda: call("POST", f"/api/attempts/{ab}/submit", b)])
    assert ra.status_code == rb.status_code == 200
    assert ra.json()["score"] == {"correct": 3, "total": 3}
    assert rb.json()["score"] == {"correct": 0, "total": 3}


def test_stu02ps_conc_a_membership_revoke_racing_a_save_gives_only_200_or_404_and_a_consistent_attempt():
    for _ in range(5):
        cid, tid, sid = world()
        s = enrolled_student(cid)
        aid = start(s, sid)
        q = qids(sid)
        answers = dict(zip(q, "abc"))
        save_r, _ = fire([lambda: put(aid, s, answers), lambda: unenroll(s, cid)])
        assert save_r.status_code in (200, 404), save_r.text
        if save_r.status_code == 404:
            assert save_r.json() == NOT_FOUND
        stored = sql("SELECT answers::text FROM practice_attempt WHERE id = %s", (aid,))[0][0]
        import json
        assert json.loads(stored) in ({}, answers)
        # every request that starts after the removal committed is a 404
        assert put(aid, s, answers).status_code == 404


def test_stu02ps_conc_a_revoke_racing_a_submit_gives_only_200_or_404_never_500():
    for _ in range(5):
        cid, tid, sid = world()
        s = enrolled_student(cid)
        aid = start(s, sid)
        put(aid, s, dict(zip(qids(sid), "abc")))
        sub, _ = fire([lambda: call("POST", f"/api/attempts/{aid}/submit", s), lambda: unenroll(s, cid)])
        assert sub.status_code in (200, 404)
        status = sql("SELECT status FROM practice_attempt WHERE id = %s", (aid,))[0][0]
        assert status == ("submitted" if sub.status_code == 200 else "in_progress")
