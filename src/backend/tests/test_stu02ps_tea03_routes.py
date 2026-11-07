"""STU-02-published-sets AC27: the TEA-03 student routes keep their contract and agree with the practice routes.

Real DbSetProvider through the HTTP API. The two TEA-03 guard tests in test_tea03_publications.py stay
as they were; these tests add the cross-route agreement.
"""
import re
from pathlib import Path

import pytest

from auth_helpers import call, code_of, new_student, seeded
from published_sets import QUESTIONS, insert_published_set, question_rows, question_set, world
from stu01_helpers import enroll, enrolled_student, make_course, make_topic, unenroll

META_KEYS = {"id", "kind", "course_id", "topic_id", "topic_name", "title", "published_at", "question_count"}


def listing(s, cid):
    return call("GET", f"/api/study/courses/{cid}/practice-sets", s)


def detail(s, sid):
    return call("GET", f"/api/study/practice-sets/{sid}", s)


def test_stu02ps_tea03_routes_list_body_order_keys_and_headers():
    cid = make_course("TEA03 course")
    tid = make_topic(cid, "Listed topic")
    s = enrolled_student(cid)
    old = insert_published_set(cid, tid, "Old", published_at="2026-01-01T00:00:00Z")
    new = insert_published_set(cid, tid, "New", published_at="2026-03-01T00:00:00Z")
    r = listing(s, cid)
    assert r.status_code == 200 and r.headers.get("cache-control") == "no-store"
    body = r.json()
    assert isinstance(body, list) and [x["id"] for x in body] == [new, old]
    for item in body:
        assert set(item) == META_KEYS
        assert item["kind"] == "practice_set" and item["course_id"] == cid and item["topic_id"] == tid
        assert item["topic_name"] == "Listed topic" and item["question_count"] == 3
        assert item["published_at"].endswith("Z")
    assert body[0]["title"] == "New"
    blob = r.text
    for forbidden in ("explanation", "correct", "choices", "source_draft", "published_by"):
        assert forbidden not in blob


def test_stu02ps_tea03_routes_detail_body_equals_the_practice_set_body():
    qs = question_set((0, 1, 2), tag="TEA03-")
    cid, tid, sid = world(questions=qs)
    s = enrolled_student(cid)
    r = detail(s, sid)
    assert r.status_code == 200 and r.headers.get("cache-control") == "no-store"
    body = r.json()
    assert set(body) == {"id", "title", "questions"}
    assert [q["id"] for q in body["questions"]] == [row[0] for row in question_rows(sid)]
    for q, (text, choices, _, _) in zip(body["questions"], qs):
        assert set(q) == {"id", "text", "code", "choices"} and q["code"] is None and q["text"] == text
        assert [c["id"] for c in q["choices"]] == list("abcd") and [c["text"] for c in q["choices"]] == choices
    assert "Explanation" not in r.text
    assert body == call("GET", f"/api/practice-sets/{sid}", s).json()


def test_stu02ps_tea03_routes_error_codes_and_messages_are_unchanged():
    cid, tid, sid = world()
    stranger = new_student()
    r = listing(stranger, cid)
    assert r.status_code == 404 and r.json() == {"detail": {"code": "not_found", "message": "Course not found."}}
    assert r.headers.get("cache-control") == "no-store"
    r = detail(stranger, sid)
    assert r.status_code == 404 and r.json() == {"detail": {"code": "not_found", "message": "Publication not found."}}
    r = detail(stranger, "intro-se-1")
    assert r.status_code == 422 and r.json() == {"detail": {"code": "validation_error", "message": "A valid UUID is required."}}
    r = listing(stranger, "intro-se-1")
    assert r.status_code == 422 and code_of(r) == "validation_error"
    assert call("GET", f"/api/study/practice-sets/{sid}").status_code == 401
    t = seeded("teacher")
    assert detail(t, sid).status_code == 403 and listing(t, cid).status_code == 403


@pytest.mark.parametrize("state", ["member", "non_member", "former_member", "restored_member"])
def test_stu02ps_tea03_routes_all_routes_agree_on_membership(state):
    cid, tid, sid = world()
    s = new_student()
    if state != "non_member":
        enroll(s, cid)
    if state in ("former_member", "restored_member"):
        unenroll(s, cid)
    if state == "restored_member":
        enroll(s, cid)
    expected = state in ("member", "restored_member")
    picker = call("GET", "/api/practice-sets", s).json()["courses"]
    in_picker = any(x["id"] == sid for c in picker for x in c["sets"])
    in_list = listing(s, cid).status_code == 200 and any(x["id"] == sid for x in listing(s, cid).json())
    seen = {
        "tea03_list": in_list,
        "tea03_detail": detail(s, sid).status_code == 200,
        "picker": in_picker,
        "practice_read": call("GET", f"/api/practice-sets/{sid}", s).status_code == 200,
        "practice_start": call("POST", f"/api/practice-sets/{sid}/attempts", s).status_code == 201,
    }
    assert seen == {k: expected for k in seen}, seen


def test_stu02ps_tea03_routes_a_membership_change_is_seen_by_every_route_at_once():
    cid, tid, sid = world()
    s = enrolled_student(cid)
    assert detail(s, sid).status_code == 200 and call("GET", f"/api/practice-sets/{sid}", s).status_code == 200
    unenroll(s, cid)
    assert detail(s, sid).status_code == 404
    assert call("GET", f"/api/practice-sets/{sid}", s).status_code == 404
    assert listing(s, cid).status_code == 404
    assert call("GET", "/api/practice-sets", s).json() == {"courses": []}


def test_stu02ps_tea03_routes_picker_and_both_tea03_routes_call_the_provider(monkeypatch):
    import set_provider

    seen = []
    for name in ("get_for_student", "get_many_for_student", "catalog_for_student", "accessible_sets"):
        real = getattr(set_provider.DbSetProvider, name)

        def wrapper(self, *a, __real=real, __name=name, **k):
            seen.append(__name)
            return __real(self, *a, **k)

        monkeypatch.setattr(set_provider.DbSetProvider, name, wrapper)
    cid, tid, sid = world()
    s = enrolled_student(cid)
    for label, fire, expected in [
        ("picker", lambda: call("GET", "/api/practice-sets", s), {"catalog_for_student"}),
        ("tea03 list", lambda: listing(s, cid), {"catalog_for_student"}),
        ("tea03 detail", lambda: detail(s, sid), {"get_for_student"}),
        ("practice read", lambda: call("GET", f"/api/practice-sets/{sid}", s), {"get_for_student"}),
    ]:
        seen.clear()
        assert fire().status_code == 200, label
        assert expected <= set(seen), (label, seen)


def test_stu02ps_tea03_routes_only_the_provider_reads_published_sets_for_students():
    """No second copy of the membership query: outside the provider, the teacher packages and the
    migrations, no backend module touches the published practice tables."""
    root = Path(__file__).resolve().parents[1]
    offenders = []
    for path in root.rglob("*.py"):
        rel = path.relative_to(root).as_posix()
        if rel.startswith(("tests/", ".venv/", "alembic", "migrations/", "teacher_")) or rel == "set_provider.py":
            continue
        text = path.read_text(encoding="utf-8")
        if re.search(r"published_practice_(set|question)|PublishedPractice(Set|Question)", text):
            offenders.append(rel)
    assert offenders == []
