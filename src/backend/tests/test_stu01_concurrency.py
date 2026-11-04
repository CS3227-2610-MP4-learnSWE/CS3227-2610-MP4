"""STU-01 AC9: simultaneous completion requests (task 9).

Threads each drive the ASGI app; the plan's single INSERT ... ON CONFLICT statement must leave one
row per (student, lesson), never raise a 500, and keep different students independent.
"""
import threading
from concurrent.futures import ThreadPoolExecutor

from stu01_helpers import sql
from stu01_helpers import (completion_rows, course_entry, enrolled_student, get_lesson, make_course, make_lesson,
                           put_completion, world)


def fire(requests, workers=None):
    """Run callables at (nearly) the same moment; return their results in order."""
    workers = workers or len(requests)
    barrier = threading.Barrier(workers)

    def run(fn):
        barrier.wait(timeout=60)
        return fn()

    with ThreadPoolExecutor(max_workers=workers) as pool:
        return list(pool.map(run, requests))


def test_stu01_ac9_simultaneous_mixed_puts_leave_one_row_and_one_consistent_state():
    cid, s, (lid, _) = world()
    wanted = [True, False] * 8
    results = fire([lambda w=w: put_completion(s, lid, w) for w in wanted])
    assert all(r.status_code == 200 for r in results), [r.status_code for r in results]
    rows = completion_rows(s, lid)
    assert len(rows) == 1
    _, done, at = rows[0]
    assert done in (True, False) and (at is not None) == done  # the CHECK invariant holds
    # the final state is one that a request asked for, and every reader sees the stored row
    detail = get_lesson(s, lid).json()
    assert detail["completed"] is done
    assert course_entry(s, cid)["completed_count"] == (1 if done else 0)
    # each response was self-consistent
    for r in results:
        body = r.json()
        assert (body["completed_at"] is not None) == body["completed"]
        assert body["course"]["completed_count"] in (0, 1)


def test_stu01_ac9_simultaneous_identical_puts_all_succeed_with_one_completed_at():
    _, s, (lid, _) = world()
    results = fire([lambda: put_completion(s, lid, True) for _ in range(12)])
    assert all(r.status_code == 200 and r.json()["completed"] is True for r in results)
    assert len({r.json()["completed_at"] for r in results}) == 1
    assert len(completion_rows(s, lid)) == 1


def test_stu01_ac9_first_ever_write_race_does_not_raise_a_unique_violation():
    # No row exists yet: every request takes the INSERT path at once.
    for _ in range(3):
        cid, s, (lid, _) = world(1)
        results = fire([lambda: put_completion(s, lid, True) for _ in range(10)])
        assert {r.status_code for r in results} == {200}, [r.text for r in results if r.status_code != 200]
        assert len(completion_rows(s, lid)) == 1


def test_stu01_ac9_final_state_matches_the_last_committed_request_when_run_in_sequence_after_a_race():
    _, s, (lid, _) = world()
    fire([lambda w=w: put_completion(s, lid, w) for w in [True, False, True, False]])
    assert put_completion(s, lid, True).json()["completed"] is True
    assert put_completion(s, lid, False).json()["completed"] is False
    assert len(completion_rows(s, lid)) == 1


def test_stu01_ac9_two_students_racing_on_one_lesson_get_independent_rows():
    cid = make_course()
    a, b = enrolled_student(cid), enrolled_student(cid)
    lid = make_lesson(cid)
    reqs = [lambda: put_completion(a, lid, True) for _ in range(6)] + [lambda: put_completion(b, lid, False) for _ in range(6)]
    results = fire(reqs)
    assert all(r.status_code == 200 for r in results)
    assert [r.json()["completed"] for r in results[:6]] == [True] * 6
    assert [r.json()["completed"] for r in results[6:]] == [False] * 6
    assert len(completion_rows(a, lid)) == 1 and len(completion_rows(b, lid)) == 1
    assert get_lesson(a, lid).json()["completed"] is True
    assert get_lesson(b, lid).json()["completed"] is False
    assert sql("SELECT count(*) FROM lesson_completion WHERE lesson_id = %s", (lid,))[0][0] == 2


def test_stu01_ac9_many_students_each_complete_the_same_lesson_at_once():
    cid = make_course()
    lid = make_lesson(cid)
    students = [enrolled_student(cid) for _ in range(8)]
    results = fire([lambda s=s: put_completion(s, lid, True) for s in students])
    assert all(r.status_code == 200 and r.json()["course"]["completed_count"] == 1 for r in results)
    assert sql("SELECT count(*) FROM lesson_completion WHERE lesson_id = %s AND completed", (lid,))[0][0] == 8


def test_stu01_ac9_concurrent_writes_to_different_lessons_by_one_student_do_not_interfere():
    cid, s, lessons = world(5)
    results = fire([lambda l=l: put_completion(s, l, True) for l in lessons])
    assert all(r.status_code == 200 for r in results)
    assert course_entry(s, cid)["completed_count"] == 5
    assert len(completion_rows(s)) == 5


def test_stu01_ac9_put_racing_with_withdrawal_never_returns_500():
    cid, s, (lid, _) = world()
    from stu01_helpers import withdraw

    reqs = [lambda: put_completion(s, lid, True) for _ in range(8)] + [lambda: withdraw(lid)]
    results = fire(reqs)
    codes = {r.status_code for r in results if hasattr(r, "status_code")}
    assert codes <= {200, 404}, codes
    assert len(completion_rows(s, lid)) <= 1
    assert get_lesson(s, lid).status_code == 404


def test_stu01_ac9_concurrent_reads_and_writes_see_only_valid_states():
    cid, s, (lid, _) = world()
    reqs = []
    for i in range(10):
        reqs.append(lambda i=i: put_completion(s, lid, i % 2 == 0))
        reqs.append(lambda: get_lesson(s, lid))
    results = fire(reqs)
    assert {r.status_code for r in results} == {200}
    for r in results:
        body = r.json()
        if "completed_at" in body:
            assert (body["completed_at"] is not None) == body["completed"]
