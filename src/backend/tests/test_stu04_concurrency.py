"""STU-04 AC17: simultaneous requests on one attempt, on progress reads, and from different students.

Threads each drive the ASGI app (pattern of test_stu01_concurrency). The row lock inside
AttemptStore.lock must give exactly one successful submit and merge simultaneous answer saves.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

from auth_helpers import call, code_of, new_student
from stu04_helpers import (KEY, answers_with, attempt_rows, body_of, only_set, progress, save, start, submit,
                           topic_item)


def fire(requests, workers=None):
    """Run callables at (nearly) the same moment; return their results in order."""
    workers = workers or len(requests)
    barrier = threading.Barrier(workers)

    def run(fn):
        barrier.wait(timeout=60)
        return fn()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, requests))


def ready_attempt(student, n_correct=2):
    aid = start(student)
    assert save(aid, student, answers_with(n_correct)).status_code == 200
    return aid


def test_stu04_ac17_simultaneous_submits_of_one_attempt_give_one_200_and_the_rest_409():
    for _ in range(3):
        s = new_student()
        aid = ready_attempt(s)
        results = fire([lambda: submit(aid, s) for _ in range(10)])
        codes = sorted(r.status_code for r in results)
        assert codes == [200] + [409] * 9, codes
        for r in results:
            if r.status_code == 409:
                assert code_of(r) == "already_submitted"
            else:
                assert r.json()["score"] == {"correct": 2, "total": 3}
        rows = attempt_rows(s)
        assert len(rows) == 1 and rows[0][1] == "submitted"
        assert only_set(body_of(s))["attempts_submitted"] == 1


def test_stu04_ac17_the_stored_score_is_the_one_returned_by_the_winning_submit():
    s = new_student()
    aid = ready_attempt(s, 1)
    results = fire([lambda: submit(aid, s) for _ in range(6)])
    winner = [r for r in results if r.status_code == 200]
    assert len(winner) == 1
    (row,) = attempt_rows(s)
    assert (row[3], row[4]) == (winner[0].json()["score"]["correct"], winner[0].json()["score"]["total"])
    assert row[6] == ["q1"]


def test_stu04_ac17_simultaneous_saves_of_different_questions_keep_every_answer_and_never_500():
    for _ in range(3):
        s = new_student()
        aid = start(s)
        results = fire([lambda q=q, c=c: save(aid, s, {q: c}) for q, c in KEY.items()])
        assert [r.status_code for r in results] == [200, 200, 200], [r.text for r in results]
        assert attempt_rows(s)[0][2] == KEY
        assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == KEY


def test_stu04_ac17_many_simultaneous_saves_of_the_same_question_end_with_one_requested_value():
    s = new_student()
    aid = start(s)
    values = ["a", "b", "c"] * 4
    results = fire([lambda v=v: save(aid, s, {"q1": v}) for v in values])
    assert {r.status_code for r in results} == {200}
    assert attempt_rows(s)[0][2]["q1"] in {"a", "b", "c"}


def test_stu04_ac17_saves_racing_a_submit_never_500_and_the_stored_row_is_consistent():
    for _ in range(3):
        s = new_student()
        aid = ready_attempt(s, 3)
        jobs = [lambda: submit(aid, s)] + [lambda: save(aid, s, {"q1": "b"}) for _ in range(4)]
        results = fire(jobs)
        assert all(r.status_code in (200, 409) for r in results), [r.status_code for r in results]
        assert results[0].status_code in (200, 409)
        (row,) = attempt_rows(s)
        assert row[1] == "submitted"
        # score and answers in the row agree (a save that lost the race did not change a submitted row)
        correct_ids = [q for q in ("q1", "q2", "q3") if row[2].get(q) == KEY[q]]
        assert row[3] == len(correct_ids) == len(row[6])
        assert row[6] == correct_ids


def test_stu04_ac17_simultaneous_progress_reads_during_a_submit_see_a_consistent_view():
    s = new_student()
    aid = ready_attempt(s, 2)
    jobs = [lambda: submit(aid, s)] + [lambda: progress(s) for _ in range(12)]
    results = fire(jobs)
    assert results[0].status_code == 200
    for r in results[1:]:
        assert r.status_code == 200, r.text
        body = r.json()
        sets = body["practice"]["sets"]
        if not sets:  # read before the commit: nothing at all of the attempt
            assert body["topics"]["items"] == []
            assert body["practice"]["average_latest_percent"] is None
        else:  # read after the commit: the whole attempt
            assert sets[0]["attempts_submitted"] == 1
            assert sets[0]["best"] == {"correct": 2, "total": 3}
            assert body["practice"]["average_latest_percent"] == 66
            assert topic_item(body)["answered"] == 3


def test_stu04_ac17_simultaneous_progress_reads_all_return_the_same_body():
    s = new_student()
    aid = ready_attempt(s, 2)
    assert submit(aid, s).status_code == 200
    results = fire([lambda: progress(s) for _ in range(12)])
    assert {r.status_code for r in results} == {200}
    first = results[0].json()
    assert all(r.json() == first for r in results)


def test_stu04_ac17_simultaneous_attempt_creation_gives_distinct_rows():
    s = new_student()
    results = fire([lambda: call("POST", "/api/practice-sets/intro-se-1/attempts", s) for _ in range(8)])
    assert {r.status_code for r in results} == {201}
    ids = [r.json()["attempt_id"] for r in results]
    assert len(set(ids)) == 8
    assert len(attempt_rows(s)) == 8
    assert body_of(s)["practice"]["sets"] == []  # none submitted


def test_stu04_ac17_different_students_do_not_affect_each_other():
    students = [new_student(f"s{i}") for i in range(6)]
    plan = {str(s): i % 4 for i, s in enumerate(students)}
    attempts = {str(s): ready_attempt(s, plan[str(s)]) for s in students}
    results = fire([lambda s=s: submit(attempts[str(s)], s) for s in students])
    assert all(r.status_code == 200 for r in results), [r.text for r in results]
    for s in students:
        row = only_set(body_of(s))
        assert row["attempts_submitted"] == 1
        assert row["latest"]["correct"] == plan[str(s)]
        assert len(attempt_rows(s)) == 1


def test_stu04_ac17_two_students_submitting_while_a_third_reads_stay_independent():
    a, b, c = new_student("a"), new_student("b"), new_student("c")
    aa, ab = ready_attempt(a, 3), ready_attempt(b, 0)
    results = fire([lambda: submit(aa, a), lambda: submit(ab, b)] + [lambda: progress(c) for _ in range(6)])
    assert results[0].status_code == 200 and results[1].status_code == 200
    for r in results[2:]:
        assert r.status_code == 200 and r.json()["practice"]["sets"] == []
    assert only_set(body_of(a))["latest"]["correct"] == 3
    assert only_set(body_of(b))["latest"]["correct"] == 0
