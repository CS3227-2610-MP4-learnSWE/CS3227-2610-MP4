"""STU-01 reading: AC1, AC2, AC5, AC7 (record visibility), AC12 (content verbatim).

Black box over the contract in workflow/specs/STU-01/plan.md. Lessons are inserted by SQL.
"""
import re

import pytest
from auth_helpers import call, code_of, new_student
from stu01_helpers import sql
from stu01_helpers import (LESSON_NOT_FOUND, RANDOM_ID, STUDY, enrolled_student, enroll, get_course_lessons,
                           get_courses, get_lesson, make_course, make_draft, make_lesson, make_topic, uid,
                           withdraw)

COURSE_KEYS = {"id", "title", "lesson_count", "completed_count"}
DETAIL_KEYS = {"id", "course", "topic", "title", "content", "published_at", "completed", "completed_at"}


# ------------------------------------------------------------------ AC1 / AC5: courses
def test_stu01_ac1_student_sees_only_member_courses_ordered_case_insensitively():
    z, a, b, other = make_course("Zeta course"), make_course("alpha course"), make_course("Beta course"), make_course("Not mine")
    s = enrolled_student()
    for c in (z, a, b):
        enroll(s, c)
    make_lesson(other, title="Hidden")
    body = get_courses(s).json()
    assert set(body) == {"courses", "totals"}
    assert [c["title"] for c in body["courses"]] == ["alpha course", "Beta course", "Zeta course"]
    assert all(set(c) == COURSE_KEYS for c in body["courses"])
    assert other not in [c["id"] for c in body["courses"]]
    assert "Not mine" not in get_courses(s).text


def test_stu01_ac5_member_course_without_lessons_appears_with_zero_counts():
    cid = make_course("Empty course")
    s = enrolled_student(cid)
    body = get_courses(s).json()
    assert body["courses"] == [{"id": cid, "title": "Empty course", "lesson_count": 0, "completed_count": 0}]
    assert body["totals"] == {"lesson_count": 0, "completed_count": 0}


def test_stu01_ac5_student_with_no_courses_gets_empty_lists():
    body = get_courses(new_student()).json()
    assert body == {"courses": [], "totals": {"lesson_count": 0, "completed_count": 0}}


def test_stu01_ac5_course_ids_are_lowercase_hyphenated_strings():
    cid = make_course()
    s = enrolled_student(cid)
    got = get_courses(s).json()["courses"][0]["id"]
    assert got == cid and got == got.lower() and re.fullmatch(r"[0-9a-f-]{36}", got)


# ------------------------------------------------------------------ AC1 / AC5: course lessons
def test_stu01_ac1_only_published_not_withdrawn_lessons_are_listed_and_drafts_never():
    cid = make_course()
    s = enrolled_student(cid)
    live = make_lesson(cid, title="Live lesson")
    gone = make_lesson(cid, title="Withdrawn lesson", withdrawn=True)
    draft = make_draft(cid, title="Secret draft title", content="DRAFT-ONLY-CONTENT-7731")
    r = get_course_lessons(s, cid)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == {"course", "topics"}
    assert set(body["course"]) == {"id", "title"} and body["course"]["id"] == cid
    ids = [item["id"] for t in body["topics"] for item in t["lessons"]]
    assert ids == [live]
    for text in (gone, draft, "Withdrawn lesson", "Secret draft title", "DRAFT-ONLY-CONTENT-7731"):
        assert text not in r.text
    assert set(body["topics"][0]["lessons"][0]) == {"id", "title", "excerpt", "completed"}
    assert body["topics"][0]["lessons"][0]["completed"] is False


def test_stu01_ac5_topics_sorted_az_general_last_lessons_by_published_at():
    cid = make_course()
    s = enrolled_student(cid)
    t_b, t_a = make_topic(cid, "banana"), make_topic(cid, "Apple")
    make_topic(cid, "No lessons topic")
    late = make_lesson(cid, topic_id=t_a, title="late", published_at="2026-03-01T00:00:00Z")
    early = make_lesson(cid, topic_id=t_a, title="early", published_at="2026-01-01T00:00:00Z")
    general = make_lesson(cid, title="general", published_at="2025-01-01T00:00:00Z")
    in_b = make_lesson(cid, topic_id=t_b, title="b", published_at="2026-02-01T00:00:00Z")
    topics = get_course_lessons(s, cid).json()["topics"]
    assert [(t["id"], t["name"]) for t in topics] == [(t_a, "Apple"), (t_b, "banana"), (None, "General")]
    assert [i["id"] for i in topics[0]["lessons"]] == [early, late]
    assert [i["id"] for i in topics[1]["lessons"]] == [in_b]
    assert [i["id"] for i in topics[2]["lessons"]] == [general]


def test_stu01_ac5_topic_with_only_withdrawn_lessons_is_omitted():
    cid = make_course()
    s = enrolled_student(cid)
    t = make_topic(cid, "Gone topic")
    make_lesson(cid, topic_id=t, withdrawn=True)
    keep = make_lesson(cid, title="keep")
    topics = get_course_lessons(s, cid).json()["topics"]
    assert [x["name"] for x in topics] == ["General"]
    assert topics[0]["lessons"][0]["id"] == keep


def test_stu01_ac5_course_without_lessons_gives_empty_topics():
    cid = make_course("Quiet")
    s = enrolled_student(cid)
    body = get_course_lessons(s, cid).json()
    assert body["topics"] == [] and body["course"] == {"id": cid, "title": "Quiet"}


def test_stu01_ac5_excerpt_collapses_whitespace_and_stops_at_160_code_points():
    cid = make_course()
    s = enrolled_student(cid)
    content = "  First line\n\n\tsecond   line " + "x" * 300
    make_lesson(cid, content=content)
    expected = " ".join(content.split())[:160]
    item = get_course_lessons(s, cid).json()["topics"][0]["lessons"][0]
    assert item["excerpt"] == expected and len(item["excerpt"]) == 160
    assert "\n" not in item["excerpt"] and "…" not in item["excerpt"]


def test_stu01_ac5_excerpt_counts_code_points_not_bytes():
    cid = make_course()
    s = enrolled_student(cid)
    make_lesson(cid, content="\U0001F600" * 200)
    item = get_course_lessons(s, cid).json()["topics"][0]["lessons"][0]
    assert item["excerpt"] == "\U0001F600" * 160


def test_stu01_ac5_course_list_is_capped_at_500_lessons_in_publish_order():
    cid = make_course()
    s = enrolled_student(cid)
    sql("INSERT INTO published_lesson(id, course_id, title, content, published_by, published_at) "
        "SELECT gen_random_uuid(), %s, 'L' || i, 'body', 'demo-teacher', "
        "'2026-01-01T00:00:00Z'::timestamptz + (i || ' seconds')::interval FROM generate_series(1, 501) AS i",
        (cid,))
    topics = get_course_lessons(s, cid).json()["topics"]
    titles = [i["title"] for t in topics for i in t["lessons"]]
    assert len(titles) == 500
    assert titles[0] == "L1" and titles[-1] == "L500" and "L501" not in titles
    # the counts on the courses call are not capped by the list (they are the real totals)
    assert get_courses(s).json()["courses"][0]["lesson_count"] == 501


# ------------------------------------------------------------------ AC1: lesson detail
def test_stu01_ac1_lesson_detail_shape_and_general_topic():
    cid = make_course("Detail course")
    s = enrolled_student(cid)
    lid = make_lesson(cid, title="Title X", content="Content X")
    r = get_lesson(s, lid)
    assert r.status_code == 200
    body = r.json()
    assert set(body) == DETAIL_KEYS
    assert body["id"] == lid and body["course"] == {"id": cid, "title": "Detail course"}
    assert body["topic"] == {"id": None, "name": "General"}
    assert body["title"] == "Title X" and body["content"] == "Content X"
    assert body["completed"] is False and body["completed_at"] is None
    assert body["published_at"].endswith("Z")


def test_stu01_ac1_lesson_detail_returns_the_topic_of_the_lesson():
    cid = make_course()
    s = enrolled_student(cid)
    t = make_topic(cid, "Testing")
    lid = make_lesson(cid, topic_id=t)
    assert get_lesson(s, lid).json()["topic"] == {"id": t, "name": "Testing"}


def test_stu01_ac1_uuid_case_and_hyphen_forms_resolve_to_the_same_lesson():
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    for form in (lid.upper(), lid.replace("-", "")):
        r = get_lesson(s, form)
        assert r.status_code == 200 and r.json()["id"] == lid


def test_stu01_ac1_lesson_payload_has_no_answer_or_draft_fields():
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    for r in (get_lesson(s, lid), get_course_lessons(s, cid), get_courses(s)):
        low = r.text.lower()
        for word in ("correct_choice", "explanation", "answer", "source_draft", "withdrawn_at", "published_by"):
            assert word not in low, word


# ------------------------------------------------------------------ AC2 / AC7: invisible records look the same
def invisible_lessons():
    """Lesson ids a student must not read: draft, withdrawn, another course, random."""
    mine, other = make_course(), make_course()
    s = enrolled_student(mine)
    return s, {
        "draft": make_draft(mine),
        "withdrawn": make_lesson(mine, withdrawn=True),
        "other_course": make_lesson(other),
        "random": RANDOM_ID,
    }


def test_stu01_ac2_unreadable_lessons_return_one_identical_404_body_on_get():
    s, ids = invisible_lessons()
    bodies = {}
    for name, lid in ids.items():
        r = get_lesson(s, lid)
        assert r.status_code == 404, name
        bodies[name] = r.json()
    assert all(b == LESSON_NOT_FOUND for b in bodies.values()), bodies


def test_stu01_ac7_unreadable_lessons_return_the_same_404_body_on_put():
    s, ids = invisible_lessons()
    for name, lid in ids.items():
        r = call("PUT", f"{STUDY}/lessons/{lid}/completion", s, {"completed": True})
        assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND, name
    assert sql("SELECT count(*) FROM lesson_completion WHERE user_id = %s", (str(s),))[0][0] == 0


def test_stu01_ac2_draft_content_never_appears_in_any_study_response():
    s, ids = invisible_lessons()
    for r in (get_lesson(s, ids["draft"]), get_courses(s), get_course_lessons(s, sql(
            "SELECT course_id::text FROM course_membership WHERE user_id = %s", (str(s),))[0][0])):
        assert "DRAFT-ONLY-CONTENT-7731" not in r.text and "Draft title" not in r.text


def test_stu01_ac2_withdrawn_lesson_cannot_be_opened_even_after_it_was_readable():
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    assert get_lesson(s, lid).status_code == 200
    withdraw(lid)
    r = get_lesson(s, lid)
    assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND
    withdraw(lid, on=False)
    assert get_lesson(s, lid).status_code == 200


def test_stu01_ac7_lesson_becomes_unreadable_when_membership_is_removed():
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    assert get_lesson(s, lid).status_code == 200
    sql("DELETE FROM course_membership WHERE course_id = %s AND user_id = %s", (cid, str(s)))
    assert get_lesson(s, lid).json() == LESSON_NOT_FOUND
    assert get_courses(s).json()["courses"] == []


def test_stu01_ac7_non_member_course_and_missing_course_have_identical_404():
    mine, other = make_course(), make_course()
    s = enrolled_student(mine)
    make_lesson(other)
    a = get_course_lessons(s, other)
    b = get_course_lessons(s, RANDOM_ID)
    assert a.status_code == b.status_code == 404
    assert a.json() == b.json()
    assert code_of(a) == "not_found" and a.json()["detail"]["message"] == "Course not found."


def test_stu01_ac2_invalid_path_ids_are_422():
    s = new_student()
    for path in ("/lessons/not-a-uuid", "/lessons/1", "/courses/not-a-uuid/lessons", "/courses/abc/lessons"):
        assert call("GET", f"{STUDY}{path}", s).status_code == 422, path
    assert call("PUT", f"{STUDY}/lessons/not-a-uuid/completion", s, {"completed": True}).status_code == 422


def test_stu01_ac7_a_user_id_query_parameter_is_ignored():
    cid = make_course()
    a, b = enrolled_student(cid), enrolled_student(cid)
    lid = make_lesson(cid)
    assert call("PUT", f"{STUDY}/lessons/{lid}/completion", a, {"completed": True}).status_code == 200
    r = call("GET", f"{STUDY}/lessons/{lid}?user_id={a}", b)
    assert r.status_code == 200 and r.json()["completed"] is False
    r = call("GET", f"{STUDY}/courses?user_id={a}", b)
    assert r.json()["totals"]["completed_count"] == 0


def test_stu01_ac7_there_is_no_endpoint_to_list_all_lessons_or_delete():
    s = new_student()
    cid = make_course()
    enroll(s, cid)
    lid = make_lesson(cid)
    assert call("GET", f"{STUDY}/lessons", s).status_code in (404, 405)
    assert call("DELETE", f"{STUDY}/lessons/{lid}", s).status_code in (404, 405)
    assert call("DELETE", f"{STUDY}/lessons/{lid}/completion", s).status_code in (404, 405)
    assert call("POST", f"{STUDY}/lessons/{lid}/completion", s, {"completed": True}).status_code in (404, 405)


# ------------------------------------------------------------------ AC12: content returned byte for byte
def test_stu01_ac12_content_with_html_and_line_breaks_is_returned_verbatim():
    cid = make_course()
    s = enrolled_student(cid)
    title = "<b>Bold</b> & \"quoted\""
    content = "Line one\n<script>alert(1)</script>\r\n<img src=x onerror=alert(2)>\n\n  indented & <tag>"
    lid = make_lesson(cid, title=title, content=content)
    r = get_lesson(s, lid)
    assert r.json()["title"] == title and r.json()["content"] == content
    listed = get_course_lessons(s, cid).json()["topics"][0]["lessons"][0]
    assert listed["title"] == title
    assert r.headers["content-type"].startswith("application/json")


def test_stu01_ac12_content_limit_2000_characters_is_readable():
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid, content="é" * 2000)
    assert get_lesson(s, lid).json()["content"] == "é" * 2000


# ------------------------------------------------------------------ response headers
def test_stu01_ac7_study_responses_are_not_cacheable():
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid)
    for r in (get_courses(s), get_course_lessons(s, cid), get_lesson(s, lid),
              call("PUT", f"{STUDY}/lessons/{lid}/completion", s, {"completed": True})):
        assert r.status_code == 200
        assert "no-store" in r.headers.get("cache-control", ""), r.request.url


@pytest.mark.parametrize("name", ["lessons", "courses"])
def test_stu01_ac1_unknown_ids_never_500(name):
    s = new_student()
    path = f"{STUDY}/lessons/{uid()}" if name == "lessons" else f"{STUDY}/courses/{uid()}/lessons"
    assert call("GET", path, s).status_code == 404
