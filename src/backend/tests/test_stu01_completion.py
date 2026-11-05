"""STU-01 completion: AC3, AC4, AC8 (persistence), AC10 (totals)."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

from auth_helpers import call, code_of, login, student_from_login
from stu01_helpers import sql
from stu01_helpers import (STUDY, completion_rows, course_entry, enroll, enrolled_student, get_course_lessons,
                           get_courses, get_lesson, make_course, make_lesson, put_completion, unenroll, withdraw,
                           world)

BACKEND = Path(__file__).resolve().parents[1]
PUT_KEYS = {"lesson_id", "completed", "completed_at", "course"}


# ------------------------------------------------------------------ AC3
def test_stu01_ac3_complete_then_incomplete_then_complete_again():
    cid, s, (lid, _) = world()
    r = put_completion(s, lid, True)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == PUT_KEYS
    assert body["lesson_id"] == lid and body["completed"] is True
    assert body["completed_at"] and body["completed_at"].endswith("Z")
    assert set(body["course"]) == {"id", "lesson_count", "completed_count"}
    assert body["course"] == {"id": cid, "lesson_count": 2, "completed_count": 1}
    ((_, done, at),) = completion_rows(s, lid)
    assert done is True and at is not None

    r = put_completion(s, lid, False)
    assert r.status_code == 200
    assert r.json()["completed"] is False and r.json()["completed_at"] is None
    assert r.json()["course"]["completed_count"] == 0
    ((_, done, at),) = completion_rows(s, lid)  # the row is kept, not deleted
    assert done is False and at is None

    r = put_completion(s, lid, True)
    assert r.json()["completed"] is True and r.json()["completed_at"] is not None
    assert len(completion_rows(s, lid)) == 1


def test_stu01_ac3_lesson_detail_shows_the_stored_state():
    _, s, (lid, other) = world()
    assert get_lesson(s, lid).json()["completed"] is False
    put_completion(s, lid, True)
    detail = get_lesson(s, lid).json()
    assert detail["completed"] is True and detail["completed_at"].endswith("Z")
    assert get_lesson(s, other).json()["completed"] is False  # only the marked lesson changed
    put_completion(s, lid, False)
    detail = get_lesson(s, lid).json()
    assert detail["completed"] is False and detail["completed_at"] is None


def test_stu01_ac3_course_lesson_list_carries_the_completed_flag():
    cid, s, (a, b) = world()
    put_completion(s, b, True)
    flags = {i["id"]: i["completed"] for t in get_course_lessons(s, cid).json()["topics"] for i in t["lessons"]}
    assert flags == {a: False, b: True}


def test_stu01_ac3_marking_incomplete_before_ever_completing_is_allowed():
    _, s, (lid, _) = world()
    r = put_completion(s, lid, False)
    assert r.status_code == 200 and r.json()["completed"] is False and r.json()["completed_at"] is None
    assert get_lesson(s, lid).json()["completed"] is False


def test_stu01_ac9_repeating_the_same_request_is_idempotent_and_keeps_first_completed_at():
    _, s, (lid, _) = world()
    first = put_completion(s, lid, True).json()
    time.sleep(0.05)
    second = put_completion(s, lid, True).json()
    assert first["completed_at"] == second["completed_at"] and second["completed"] is True
    assert first["course"] == second["course"]
    assert len(completion_rows(s, lid)) == 1
    assert put_completion(s, lid, False).json() == put_completion(s, lid, False).json()


def test_stu01_ac9_a_retry_never_flips_the_state_back():
    _, s, (lid, _) = world()
    for _ in range(3):
        assert put_completion(s, lid, True).json()["completed"] is True
    assert get_lesson(s, lid).json()["completed"] is True


# ------------------------------------------------------------------ AC4 / AC8: persistence
def test_stu01_ac4_state_survives_logout_and_login():
    _, s, (lid, other) = world()
    put_completion(s, lid, True)
    assert call("POST", "/api/auth/logout", s).status_code == 200
    assert call("GET", f"{STUDY}/lessons/{lid}", s).status_code == 401
    s2 = student_from_login(login(s.email, s.password), s.email, s.password)
    assert get_lesson(s2, lid).json()["completed"] is True
    assert get_lesson(s2, other).json()["completed"] is False
    put_completion(s2, lid, False)
    s3 = student_from_login(login(s.email, s.password), s.email, s.password)
    assert get_lesson(s3, lid).json()["completed"] is False


def test_stu01_ac8_state_is_read_from_the_database_not_server_memory():
    cid, s, (lid, _) = world()
    put_completion(s, lid, True)
    sql("UPDATE lesson_completion SET completed = false, completed_at = NULL WHERE user_id = %s AND lesson_id = %s",
        (str(s), lid))
    assert get_lesson(s, lid).json()["completed"] is False
    assert course_entry(s, cid)["completed_count"] == 0
    sql("UPDATE lesson_completion SET completed = true, completed_at = now() WHERE user_id = %s AND lesson_id = %s",
        (str(s), lid))
    assert get_lesson(s, lid).json()["completed"] is True
    assert course_entry(s, cid)["completed_count"] == 1


def test_stu01_ac8_a_new_server_process_returns_the_same_status():
    _, s, (lid, other) = world()
    put_completion(s, lid, True)
    script = (
        "import asyncio, json, sys, httpx\n"
        "from main import app\n"
        "async def go():\n"
        "    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as c:\n"
        "        out = {}\n"
        "        for key, lid in (('done', sys.argv[2]), ('open', sys.argv[3])):\n"
        "            r = await c.get('/api/study/lessons/' + lid, headers={'Cookie': sys.argv[1], "
        "'X-Forwarded-For': '10.9.9.9'})\n"
        "            out[key] = [r.status_code, r.json().get('completed')]\n"
        "        print(json.dumps(out))\n"
        "asyncio.run(go())\n"
    )
    run = subprocess.run([sys.executable, "-c", script, s.cookie, lid, other], cwd=BACKEND, env=os.environ.copy(),
                         capture_output=True, text=True, timeout=120)
    assert run.returncode == 0, run.stderr[-800:]
    assert json.loads(run.stdout.strip().splitlines()[-1]) == {"done": [200, True], "open": [200, False]}


def test_stu01_ac8_completion_is_stored_in_the_lesson_completion_table():
    _, s, (lid, _) = world()
    put_completion(s, lid, True)
    rows = sql("SELECT user_id, lesson_id::text, course_id::text, completed, completed_at IS NOT NULL, "
               "updated_at IS NOT NULL FROM lesson_completion WHERE user_id = %s", (str(s),))
    assert len(rows) == 1
    assert rows[0][0] == str(s) and rows[0][1] == lid and rows[0][3] is True and rows[0][4] and rows[0][5]


def test_stu01_ac8_course_id_stored_with_the_row_is_the_lessons_course():
    cid, s, (lid, _) = world()
    put_completion(s, lid, True)
    assert sql("SELECT course_id::text FROM lesson_completion WHERE lesson_id = %s", (lid,)) == [(cid,)]


# ------------------------------------------------------------------ AC10: totals
def test_stu01_ac10_counts_follow_complete_incomplete_and_return_to_earlier_values():
    cid, s, (a, b) = world()
    other_course = make_course()
    enroll(s, other_course)
    make_lesson(other_course)
    before = get_courses(s).json()
    assert before["totals"] == {"lesson_count": 3, "completed_count": 0}
    put_completion(s, a, True)
    after = get_courses(s).json()
    assert course_entry(s, cid) == {"id": cid, "title": course_entry(s, cid)["title"], "lesson_count": 2,
                                    "completed_count": 1}
    assert after["totals"] == {"lesson_count": 3, "completed_count": 1}
    assert after["totals"] == {k: sum(c[k] for c in after["courses"]) for k in ("lesson_count", "completed_count")}
    put_completion(s, a, False)
    assert get_courses(s).json() == before


def test_stu01_ac10_put_response_counts_match_the_course_list():
    cid, s, (a, b) = world()
    r1 = put_completion(s, a, True).json()["course"]
    r2 = put_completion(s, b, True).json()["course"]
    assert r1 == {"id": cid, "lesson_count": 2, "completed_count": 1}
    assert r2 == {"id": cid, "lesson_count": 2, "completed_count": 2}
    entry = course_entry(s, cid)
    assert (entry["lesson_count"], entry["completed_count"]) == (2, 2)


def test_stu01_ac10_lessons_of_a_course_the_student_is_not_in_are_not_counted():
    cid, s, _ = world()
    outsider_course = make_course()
    make_lesson(outsider_course)
    assert get_courses(s).json()["totals"]["lesson_count"] == 2


def test_stu01_ac10_withdrawing_a_completed_lesson_stops_counting_but_keeps_the_record():
    cid, s, (a, b) = world()
    put_completion(s, a, True)
    put_completion(s, b, True)
    assert course_entry(s, cid)["completed_count"] == 2
    withdraw(a)
    entry = course_entry(s, cid)
    assert (entry["lesson_count"], entry["completed_count"]) == (1, 1)
    assert get_courses(s).json()["totals"] == {"lesson_count": 1, "completed_count": 1}
    assert len(completion_rows(s, a)) == 1  # record kept
    assert put_completion(s, a, False).status_code == 404  # cannot be changed while withdrawn
    assert completion_rows(s, a)[0][1] is True
    withdraw(a, on=False)
    assert course_entry(s, cid)["completed_count"] == 2  # reinstated: counts again


def test_stu01_ac10_completed_lessons_of_a_left_course_stop_counting():
    cid, s, (a, _) = world()
    put_completion(s, a, True)
    unenroll(s, cid)
    assert get_courses(s).json() == {"courses": [], "totals": {"lesson_count": 0, "completed_count": 0}}
    enroll(s, cid)
    assert course_entry(s, cid)["completed_count"] == 1


def test_stu01_ac10_totals_with_no_courses_are_zero():
    s = enrolled_student()
    assert get_courses(s).json()["totals"] == {"lesson_count": 0, "completed_count": 0}


def test_stu01_ac10_error_code_of_withdrawn_put_is_not_found():
    cid, s, (a, _) = world()
    withdraw(a)
    r = put_completion(s, a, True)
    assert r.status_code == 404 and code_of(r) == "not_found"
