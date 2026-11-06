"""STU-04 GET /api/progress through the real ASGI app (AC1, AC2, AC4, AC5, AC7, AC9, AC10, AC12)."""
import re

from auth_helpers import call, code_of, new_student, seeded
from stu01_helpers import (enroll, enrolled_student, make_course, make_lesson, put_completion, unenroll, withdraw,
                           world)
from stu04_helpers import (BASICS_TOPIC, EMPTY, EXPLANATIONS, FORBIDDEN_IN_BODY, QUESTION_TEXTS, SET_ID, SET_TITLE,
                           TOPIC_NAME, answers_with, body_of, insert_attempt, only_set, progress, save, start,
                           submit, submitted, topic_item)
import pytest as _pytest

pytestmark = _pytest.mark.usefixtures("fake_provider")

UUID = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")


# ------------------------------------------------------------------ AC5 access
def test_stu04_ac5_no_session_is_401_unauthenticated():
    r = progress(None)
    assert r.status_code == 401
    assert code_of(r) == "unauthenticated"
    assert r.json()["detail"].keys() == {"code", "message"}


def test_stu04_ac5_empty_or_unknown_cookie_is_401():
    for cookie in ("learnswe_session=", "learnswe_session=not-a-real-token"):
        r = progress(None, headers={"Cookie": cookie})
        assert r.status_code == 401, cookie
        assert code_of(r) == "unauthenticated"


def test_stu04_ac5_teacher_and_admin_get_403_forbidden():
    for role in ("teacher", "admin"):
        r = progress(seeded(role))
        assert r.status_code == 403, role
        assert code_of(r) == "forbidden"
        assert "lessons" not in r.text and "practice" not in r.text


def test_stu04_ac5_unauthenticated_is_checked_before_role():
    # 401 for a request with no session even with a teacher's id in every identity channel.
    r = progress(None, path="/api/progress?user_id=demo-teacher", headers={"X-Student-Id": "demo-teacher"})
    assert r.status_code == 401


def test_stu04_ac5_identity_headers_and_query_parameters_are_ignored():
    me, other = new_student(), new_student()
    submitted(other, 3)
    submitted(other, 3)
    assert body_of(me) == EMPTY
    for path, headers in [
        (f"/api/progress?user_id={other}", None),
        (f"/api/progress?student_id={other}", None),
        ("/api/progress?user_id=demo-student&student_id=demo-student", None),
        ("/api/progress", {"X-Student-Id": str(other)}),
        ("/api/progress", {"X-Demo-User-Id": str(other)}),
        (f"/api/progress?user_id={other}", {"X-Student-Id": str(other), "X-Demo-User-Id": str(other)}),
    ]:
        r = progress(me, path=path, headers=headers)
        assert r.status_code == 200, (path, headers)
        assert r.json() == EMPTY, (path, headers)


def test_stu04_ac5_a_teacher_cannot_borrow_a_student_through_query_or_header():
    student = new_student()
    submitted(student, 2)
    t = seeded("teacher")
    r = progress(t, path=f"/api/progress?user_id={student}", headers={"X-Student-Id": str(student)})
    assert r.status_code == 403
    assert code_of(r) == "forbidden"


def test_stu04_ac5_only_get_is_allowed():
    s = new_student()
    for method in ("POST", "PUT", "PATCH", "DELETE"):
        r = call(method, "/api/progress", s, {} if method != "DELETE" else None)
        assert r.status_code == 405, method


def test_stu04_ac5_response_is_not_cacheable():
    r = progress(new_student())
    assert "no-store" in r.headers.get("cache-control", "").lower()


# ------------------------------------------------------------------ AC2 / AC13 empty states
def test_stu04_ac2_a_new_student_gets_exactly_the_empty_body():
    r = progress(new_student())
    assert r.status_code == 200
    assert r.json() == EMPTY


def test_stu04_ac2_a_member_with_lessons_and_no_activity_gets_zero_completed_and_empty_sets():
    cid, s, lessons = world(2)
    body = body_of(s)
    assert body["lessons"]["totals"] == {"lesson_count": 2, "completed_count": 0}
    assert [(c["id"], c["lesson_count"], c["completed_count"]) for c in body["lessons"]["courses"]] == [(cid, 2, 0)]
    assert body["lessons"]["recent"] == []
    assert body["practice"] == {"sets": [], "average_latest_percent": None}
    assert body["topics"]["items"] == []
    assert body["topics"]["rule"] == {"min_answers": 3, "weak_below_percent": 60}


def test_stu04_ac2_a_member_course_without_lessons_is_listed_with_zero_and_zero():
    cid = make_course("Empty course")
    s = enrolled_student(cid)
    body = body_of(s)
    assert body["lessons"]["courses"] == [{"id": cid, "title": "Empty course", "lesson_count": 0,
                                           "completed_count": 0}]
    assert body["lessons"]["totals"] == {"lesson_count": 0, "completed_count": 0}


def test_stu04_ac2_an_in_progress_attempt_alone_gives_no_practice_and_no_topics():
    s = new_student()
    aid = start(s)
    save(aid, s, answers_with(3))
    body = body_of(s)
    assert body["practice"] == {"sets": [], "average_latest_percent": None}
    assert body["topics"]["items"] == []


# ------------------------------------------------------------------ AC7 lessons
def test_stu04_ac7_lesson_counts_follow_marking_complete_and_incomplete():
    cid, s, (l0, l1) = world(2)
    put_completion(s, l0, True)
    body = body_of(s)
    assert body["lessons"]["totals"] == {"lesson_count": 2, "completed_count": 1}
    assert body["lessons"]["courses"][0]["completed_count"] == 1
    assert [r["lesson_id"] for r in body["lessons"]["recent"]] == [l0]
    put_completion(s, l1, True)
    assert [r["lesson_id"] for r in body_of(s)["lessons"]["recent"]] == [l1, l0]  # newest first
    put_completion(s, l0, False)
    body = body_of(s)
    assert body["lessons"]["totals"]["completed_count"] == 1
    assert [r["lesson_id"] for r in body["lessons"]["recent"]] == [l1]


def test_stu04_ac7_recent_entries_have_the_contract_shape():
    cid, s, (l0, _) = world(2)
    put_completion(s, l0, True)
    entry = body_of(s)["lessons"]["recent"][0]
    assert set(entry) == {"lesson_id", "course_id", "title", "completed_at"}
    assert entry["lesson_id"] == l0 and entry["course_id"] == cid and entry["title"] == "Lesson 0"
    assert UUID.match(entry["lesson_id"]) and UUID.match(entry["course_id"])
    assert entry["completed_at"].endswith("Z")


def test_stu04_ac7_recent_is_limited_to_five_newest_while_the_counts_include_all():
    cid = make_course()
    s = enrolled_student(cid)
    ids = [make_lesson(cid, title=f"L{i}", published_at=f"2026-01-0{i + 1}T00:00:00Z") for i in range(7)]
    for lid in ids:
        assert put_completion(s, lid, True).status_code == 200
    body = body_of(s)
    assert body["lessons"]["totals"] == {"lesson_count": 7, "completed_count": 7}
    assert [r["lesson_id"] for r in body["lessons"]["recent"]] == list(reversed(ids))[:5]


def test_stu04_ac7_withdrawn_lessons_and_other_courses_are_not_counted():
    cid, s, (l0, l1) = world(2)
    other = make_course("Not mine")
    make_lesson(other, title="Hidden lesson")
    put_completion(s, l0, True)
    withdraw(l0)
    body = body_of(s)
    assert body["lessons"]["totals"] == {"lesson_count": 1, "completed_count": 0}
    assert [r["lesson_id"] for r in body["lessons"]["recent"]] == []
    assert other not in [c["id"] for c in body["lessons"]["courses"]]
    assert "Hidden lesson" not in str(body)


def test_stu04_ac7_leaving_a_course_removes_it_from_the_response():
    cid, s, (l0, _) = world(2)
    put_completion(s, l0, True)
    unenroll(s, cid)
    body = body_of(s)
    assert body["lessons"]["courses"] == []
    assert body["lessons"]["totals"] == {"lesson_count": 0, "completed_count": 0}
    assert body["lessons"]["recent"] == []
    enroll(s, cid)
    assert body_of(s)["lessons"]["totals"] == {"lesson_count": 2, "completed_count": 1}


def test_stu04_ac7_courses_are_ordered_by_title_ignoring_case_and_add_up_to_the_totals():
    s = new_student()
    made = {}
    for title, n in [("zebra course", 1), ("Alpha course", 3), ("beta course", 2)]:
        cid = make_course(title)
        enroll(s, cid)
        for i in range(n):
            make_lesson(cid, title=f"{title} {i}")
        made[title] = cid
    extra = make_lesson(made["Alpha course"], title="extra")
    assert put_completion(s, extra, True).status_code == 200
    body = body_of(s)
    assert [c["title"] for c in body["lessons"]["courses"]] == ["Alpha course", "beta course", "zebra course"]
    assert sum(c["lesson_count"] for c in body["lessons"]["courses"]) == body["lessons"]["totals"]["lesson_count"]
    assert sum(c["completed_count"] for c in body["lessons"]["courses"]) == body["lessons"]["totals"][
        "completed_count"] == 1


def test_stu04_ac7_lesson_figures_equal_the_study_endpoint_figures():
    cid, s, (l0, l1) = world(2)
    put_completion(s, l1, True)
    study = call("GET", "/api/study/courses", s).json()
    body = body_of(s)
    assert body["lessons"]["totals"] == study["totals"]
    assert body["lessons"]["courses"] == study["courses"]


# ------------------------------------------------------------------ AC1 / AC9 practice
def test_stu04_ac1_a_submitted_attempt_shows_its_score():
    s = new_student()
    submitted(s, 2)
    body = body_of(s)
    row = only_set(body)
    assert set(row) == {"set_id", "title", "attempts_submitted", "best", "latest"}
    assert row["set_id"] == SET_ID and row["title"] == SET_TITLE
    assert row["attempts_submitted"] == 1
    assert row["best"] == {"correct": 2, "total": 3}
    assert set(row["latest"]) == {"correct", "total", "submitted_at"}
    assert (row["latest"]["correct"], row["latest"]["total"]) == (2, 3)
    assert row["latest"]["submitted_at"].endswith("Z")
    assert body["practice"]["average_latest_percent"] == 66


def test_stu04_ac9_best_latest_and_count_over_several_attempts():
    s = new_student()
    for n in (1, 3, 2):
        submitted(s, n)
    row = only_set(body_of(s))
    assert row["attempts_submitted"] == 3
    assert row["best"] == {"correct": 3, "total": 3}
    assert (row["latest"]["correct"], row["latest"]["total"]) == (2, 3)


def test_stu04_ac9_latest_is_the_most_recently_submitted_not_the_most_recently_created():
    s = new_student()
    older = start(s)            # created first, submitted last
    newer = start(s)
    save(newer, s, answers_with(3))
    assert submit(newer, s).status_code == 200
    save(older, s, answers_with(1))
    assert submit(older, s).status_code == 200
    row = only_set(body_of(s))
    assert row["attempts_submitted"] == 2
    assert row["best"]["correct"] == 3
    assert row["latest"]["correct"] == 1


def test_stu04_ac9_best_ties_keep_the_same_score():
    s = new_student()
    submitted(s, 2)
    submitted(s, 2)
    row = only_set(body_of(s))
    assert row["attempts_submitted"] == 2
    assert row["best"] == {"correct": 2, "total": 3}


def test_stu04_ac9_an_in_progress_attempt_is_not_counted_anywhere():
    s = new_student()
    submitted(s, 1)
    before = body_of(s)
    aid = start(s)
    save(aid, s, answers_with(3))
    assert body_of(s) == before
    assert only_set(before)["attempts_submitted"] == 1


def test_stu04_ac9_a_set_with_only_in_progress_attempts_is_absent():
    s = new_student()
    for _ in range(2):
        aid = start(s)
        save(aid, s, answers_with(2))
    assert body_of(s)["practice"]["sets"] == []


def test_stu04_ac9_a_rejected_incomplete_submit_does_not_count():
    s = new_student()
    aid = start(s)
    save(aid, s, {"q1": "a"})
    r = submit(aid, s)
    assert r.status_code == 422
    assert body_of(s)["practice"]["sets"] == []


# ------------------------------------------------------------------ AC3 / AC4 / AC10 topics through the API
def topic_for(n_correct):
    s = new_student()
    submitted(s, n_correct)
    return topic_item(body_of(s))


def test_stu04_ac10_fixture_topic_boundaries_through_the_api():
    expect = {0: ("needs_practice", 0), 1: ("needs_practice", 33), 2: ("on_track", 66), 3: ("on_track", 100)}
    for n, (status, pct) in expect.items():
        item = topic_for(n)
        assert item["status"] == status, n
        assert item["accuracy_percent"] == pct, n
        assert (item["answered"], item["correct"]) == (3, n)
        assert item["topic"] == {"id": BASICS_TOPIC, "name": TOPIC_NAME}


def test_stu04_ac10_the_latest_attempt_replaces_the_earlier_one_for_topics():
    s = new_student()
    submitted(s, 0)
    assert topic_item(body_of(s))["status"] == "needs_practice"
    submitted(s, 3)
    item = topic_item(body_of(s))
    assert (item["answered"], item["correct"], item["status"]) == (3, 3, "on_track")  # not summed to 6
    submitted(s, 1)
    item = topic_item(body_of(s))
    assert (item["answered"], item["correct"], item["status"]) == (3, 1, "needs_practice")


def test_stu04_ac4_ac10_two_answers_is_insufficient_and_never_weak():
    s = new_student()
    insert_attempt(s, answers={"q1": "b", "q2": "a"}, correct_ids=[])
    item = topic_item(body_of(s))
    assert item["status"] == "insufficient"
    assert (item["answered"], item["correct"], item["accuracy_percent"]) == (2, 0, 0)


def test_stu04_ac10_topic_item_has_exactly_the_contract_keys():
    s = new_student()
    submitted(s, 1)
    item = topic_item(body_of(s))
    assert set(item) == {"topic", "answered", "correct", "accuracy_percent", "status"}
    assert set(item["topic"]) == {"id", "name"}


def test_stu04_ac11_the_response_carries_the_rule_numbers():
    s = new_student()
    assert body_of(s)["topics"]["rule"] == {"min_answers": 3, "weak_below_percent": 60}
    submitted(s, 1)
    assert body_of(s)["topics"]["rule"] == {"min_answers": 3, "weak_below_percent": 60}


# ------------------------------------------------------------------ AC12 no leak
def test_stu04_ac12_response_keys_are_exactly_the_contract():
    cid, s, (l0, _) = world(2)
    put_completion(s, l0, True)
    submitted(s, 2)
    body = body_of(s)
    assert set(body) == {"lessons", "practice", "topics"}
    assert set(body["lessons"]) == {"totals", "courses", "recent"}
    assert set(body["lessons"]["totals"]) == {"lesson_count", "completed_count"}
    assert set(body["lessons"]["courses"][0]) == {"id", "title", "lesson_count", "completed_count"}
    assert set(body["practice"]) == {"sets", "average_latest_percent"}
    assert set(body["topics"]) == {"rule", "items"}
    assert set(body["topics"]["rule"]) == {"min_answers", "weak_below_percent"}


def test_stu04_ac12_no_answer_key_question_text_choice_or_identity_in_the_body():
    cid, s, (l0, _) = world(2)
    put_completion(s, l0, True)
    for n in (0, 2, 3):
        submitted(s, n)
    start_id = start(s)
    save(start_id, s, answers_with(3))
    r = progress(s)
    text = r.text
    for needle in FORBIDDEN_IN_BODY + QUESTION_TEXTS + EXPLANATIONS + [str(s), start_id]:
        assert needle not in text, f"{needle!r} leaked: {text}"


def test_stu04_ac12_an_in_progress_attempt_changes_nothing_in_the_response():
    s = new_student()
    submitted(s, 1)
    before = progress(s).json()
    aid = start(s)
    for q, c in answers_with(3).items():
        save(aid, s, {q: c})
        assert progress(s).json() == before
    assert submit(aid, s).status_code == 200
    assert progress(s).json() != before  # only the submission changes it


def test_stu04_ac12_ids_in_the_body_are_lowercase_hyphenated_uuids():
    cid, s, (l0, _) = world(2)
    put_completion(s, l0, True)
    submitted(s, 1)
    body = body_of(s)
    for c in body["lessons"]["courses"]:
        assert UUID.match(c["id"])
    assert UUID.match(body["topics"]["items"][0]["topic"]["id"])


def test_stu04_ac8_a_database_row_for_an_unknown_set_is_skipped_without_error():
    s = new_student()
    submitted(s, 2)
    insert_attempt(s, answers={"q1": "a", "q2": "b", "q3": "c"}, correct_ids=["q1", "q2", "q3"], set_id="retired-set")
    r = progress(s)
    assert r.status_code == 200
    assert [x["set_id"] for x in r.json()["practice"]["sets"]] == [SET_ID]
