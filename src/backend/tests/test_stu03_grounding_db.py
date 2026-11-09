"""STU-03-grounding against the real lesson provider and the real published_lesson / course_membership rules.

Rows are inserted by SQL (stu01_helpers); the LLM is a fake or a mock-transport client, so there is no
live call and no key. These tests skip when TEA01_TEST_DATABASE_URL is not set. They cover the records
tasks of tasks.md: AC6 (uniform 404, recheck after the call), AC11 and cross-user access (task 7), AC13
(visibility of related lessons), AC19 (no connection held), and concurrency (task 6).
Contract: workflow/specs/STU-03-grounding/{spec,plan}.md.
"""
import threading
import uuid

import httpx
import llm_client
import pytest
from auth_helpers import call, seeded
from companion_helpers import (
    BENIGN,
    SET_ID,
    URL,
    ask,
    assert_no_key_in,
    body_of,
    code_of,
    new_student,
)
from grounding_helpers import LESSON_NOT_FOUND_BODY, lesson_ask, other_ask
from llm_client import Limits, Settings, SoclaasClient
from main import app
from stu01_helpers import (
    enroll,
    enrolled_student,
    make_course,
    make_draft,
    make_lesson,
    sql,
    unenroll,
    withdraw,
)

pytestmark = pytest.mark.usefixtures("fake_provider")

TITLE = "Closures and scope"
BODY = "A closure remembers variables from the scope where it was created."
W1, W2, W3 = "alphaword", "betaword", "gammaword"


def world():
    """A course, an enrolled student and one published lesson."""
    cid = make_course()
    s = enrolled_student(cid)
    return cid, s, make_lesson(cid, title=TITLE, content=BODY)


# ---------------------------------------------------------------- AC1, AC12 with real rows
def test_stu03_grounding_db_member_gets_lesson_mode_with_database_title(fake):
    cid, s, lid = world()
    r = lesson_ask(s, "What is a closure?", lid)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["mode"] == "lesson" and body["reply"] == BENIGN
    assert body["sources"] == [{"lesson_id": lid, "title": TITLE}]
    assert TITLE in fake.last.all_text and BODY in fake.last.all_text
    assert_no_key_in(fake.last.all_text)


def test_stu03_grounding_db_lesson_id_spellings_resolve_to_the_canonical_id(fake):
    cid, s, lid = world()
    for spelling in (lid.upper(), lid.replace("-", ""), "{" + lid + "}", "urn:uuid:" + lid):
        r = lesson_ask(s, "What is a closure?", spelling)
        assert r.status_code == 200, (spelling, r.text)
        assert r.json()["sources"] == [{"lesson_id": lid, "title": TITLE}]


# ---------------------------------------------------------------- AC6: one 404 for every inaccessible lesson
def test_stu03_grounding_db_every_inaccessible_lesson_gives_the_identical_404(fake):
    cid, s, _ = world()
    other_cid = make_course()
    withdrawn = make_lesson(cid, title="Gone", content="WITHDRAWN-BODY-1", withdrawn=True)
    other_course = make_lesson(other_cid, title="Elsewhere", content="OTHER-COURSE-BODY-2")
    draft = make_draft(cid, title="Draft", content="DRAFT-ONLY-CONTENT-7731")
    left_cid = make_course()
    left_lesson = make_lesson(left_cid, title="Left", content="LEFT-COURSE-BODY-3")
    enroll(s, left_cid)
    unenroll(s, left_cid)
    ids = [str(uuid.uuid4()), "abc", "   ", "1'; DROP TABLE published_lesson;--", withdrawn, other_course,
           draft, left_lesson]
    results = [lesson_ask(s, "hi", i) for i in ids]
    for i, r in zip(ids, results):
        assert r.status_code == 404, i
        assert r.json() == LESSON_NOT_FOUND_BODY, i
    assert fake.calls == []


def test_stu03_grounding_db_lesson_withdrawn_during_the_model_call_gets_404_and_no_reply(fake):
    cid, s, lid = world()

    def reply(_messages):
        withdraw(lid)
        return "SECRET-REPLY-TEXT-9917"

    fake.reply = reply
    r = lesson_ask(s, "What is a closure?", lid)
    assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND_BODY
    assert "SECRET-REPLY-TEXT-9917" not in r.text
    assert len(fake.calls) == 1
    # the next request sees the withdrawal up front
    n = len(fake.calls)
    assert lesson_ask(s, "again", lid).status_code == 404
    assert len(fake.calls) == n


def test_stu03_grounding_db_membership_removed_during_the_model_call_gets_404(fake):
    cid, s, lid = world()

    def reply(_messages):
        unenroll(s, cid)
        return "SECRET-REPLY-TEXT-4402"

    fake.reply = reply
    r = lesson_ask(s, "What is a closure?", lid)
    assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND_BODY
    assert "SECRET-REPLY-TEXT-4402" not in r.text


def test_stu03_grounding_db_related_lesson_withdrawn_during_the_call_gets_404(fake):
    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid, title="Database indexing", content=f"{W1} {W2} notes")

    def reply(_messages):
        withdraw(lid)
        return "SECRET-REPLY-TEXT-3318"

    fake.reply = reply
    r = other_ask(s, f"tell me about {W1} {W2}")
    assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND_BODY
    assert "SECRET-REPLY-TEXT-3318" not in r.text


# ---------------------------------------------------------------- task 7: cross-user access
def test_stu03_grounding_db_cross_user_students_teacher_admin_and_anonymous(fake):
    cid, owner, lid = world()
    outsider = new_student()  # enrolled nowhere
    other_course_student = enrolled_student(make_course())
    assert lesson_ask(owner, "hi", lid).status_code == 200
    n = len(fake.calls)
    for who in (outsider, other_course_student):
        r = lesson_ask(who, "hi", lid)
        assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND_BODY
        r = other_ask(who, f"{TITLE} closure scope variables")
        assert r.json()["mode"] == "help" and r.json()["sources"] == []
        assert BODY not in r.text
    # a general-page request from another student never carries the lesson into its model context
    assert BODY not in fake.calls[-1].all_text
    for role in ("teacher", "admin"):
        r = lesson_ask(seeded(role), "hi", lid)
        assert r.status_code == 403 and code_of(r) == "forbidden", role
        assert other_ask(seeded(role), "closure scope").status_code == 403
    r = call("POST", URL, None, body_of("hi", page="lesson", context_extra={"lesson_id": lid}))
    assert r.status_code == 401
    # only the two "other page" requests above reached the model
    assert len(fake.calls) == n + 2


def test_stu03_grounding_db_lesson_ids_cannot_be_probed(fake):
    cid, owner, lid = world()
    other_course = make_lesson(make_course(), title="Hidden", content="HIDDEN-BODY")
    outsider = new_student()
    real_but_hidden = lesson_ask(outsider, "hi", other_course)
    never_existed = lesson_ask(outsider, "hi", str(uuid.uuid4()))
    malformed = lesson_ask(outsider, "hi", "not-a-uuid")
    assert real_but_hidden.json() == never_existed.json() == malformed.json() == LESSON_NOT_FOUND_BODY
    assert real_but_hidden.status_code == never_existed.status_code == malformed.status_code == 404


# ---------------------------------------------------------------- AC13: only visible lessons are found
def test_stu03_grounding_db_related_search_finds_member_lessons_and_skips_the_rest(fake):
    cid = make_course()
    s = enrolled_student(cid)
    visible = make_lesson(cid, title="Database indexing", content=f"{W1} {W2} are covered here",
                          published_at="2026-01-01T00:00:00Z")
    make_lesson(cid, title="Withdrawn", content=f"{W1} {W2} WITHDRAWN-MARKER", withdrawn=True)
    make_draft(cid, title="Draft", content=f"{W1} {W2} DRAFT-ONLY-CONTENT-7731")
    make_lesson(make_course(), title="Elsewhere", content=f"{W1} {W2} OTHER-COURSE-MARKER")
    left = make_course()
    make_lesson(left, title="Left", content=f"{W1} {W2} LEFT-COURSE-MARKER")
    enroll(s, left)
    unenroll(s, left)
    r = other_ask(s, f"tell me about {W1} and {W2}")
    body = r.json()
    assert body["mode"] == "lesson"
    assert body["sources"] == [{"lesson_id": visible, "title": "Database indexing"}]
    text = fake.last.all_text
    for marker in ("WITHDRAWN-MARKER", "DRAFT-ONLY-CONTENT-7731", "OTHER-COURSE-MARKER", "LEFT-COURSE-MARKER"):
        assert marker not in text
    assert_no_key_in(text)


def test_stu03_grounding_db_student_in_no_course_finds_nothing(fake):
    cid = make_course()
    make_lesson(cid, title="Database indexing", content=f"{W1} {W2}")
    r = other_ask(new_student(), f"{W1} {W2}")
    assert r.json()["mode"] == "help" and r.json()["sources"] == []


def test_stu03_grounding_db_related_search_returns_two_best_across_member_courses(fake):
    c1, c2 = make_course(), make_course()
    s = enrolled_student(c1)
    enroll(s, c2)
    make_lesson(c1, title="Old two", content=f"{W1} {W2}", published_at="2026-01-01T00:00:00Z")
    best = make_lesson(c2, title="Best", content=f"{W1} {W2} {W3}", published_at="2026-01-02T00:00:00Z")
    new_two = make_lesson(c1, title="New two", content=f"{W1} {W2}", published_at="2026-01-03T00:00:00Z")
    r = other_ask(s, f"{W1} {W2} {W3}")
    assert [x["lesson_id"] for x in r.json()["sources"]] == [best, new_two]
    assert "Old two" not in fake.last.all_text


def test_stu03_grounding_db_related_search_looks_only_at_the_newest_two_hundred(fake):
    cid = make_course()
    s = enrolled_student(cid)
    make_lesson(cid, title="Oldest", content=f"{W1} {W2}", published_at="2025-01-01T00:00:00Z")
    sql(
        "INSERT INTO published_lesson(id, course_id, topic_id, title, content, published_by, published_at) "
        "SELECT md5(random()::text || g::text)::uuid, %s, NULL, 'Filler ' || g, 'Nothing relevant', 'demo-teacher', "
        "timestamptz '2026-01-01' + g * interval '1 minute' FROM generate_series(1, 200) AS g",
        (cid,),
    )
    r = other_ask(s, f"{W1} {W2}")
    assert r.json()["mode"] == "help" and r.json()["sources"] == []


# ---------------------------------------------------------------- AC19: no connection held during the call
@pytest.mark.parametrize("kind", ["lesson_page", "related"])
def test_stu03_grounding_db_lesson_requests_hold_no_connection_during_the_model_call(fake, monkeypatch, kind):
    from sqlalchemy import create_engine

    from auth.settings import load_settings

    cid = make_course()
    s = enrolled_student(cid)
    lid = make_lesson(cid, title="Database indexing", content=f"{W1} {W2} notes")
    engine = create_engine(load_settings().database_url, pool_size=1, max_overflow=0, pool_timeout=0.25)
    for module in ("auth.db", "companion_routes", "lesson_provider"):
        monkeypatch.setattr(f"{module}.engine_for", lambda _url: engine, raising=False)
    held = []

    def reply(_messages):
        held.append(engine.pool.checkedout())
        return BENIGN

    fake.reply = reply
    try:
        r = lesson_ask(s, "What is indexing?", lid) if kind == "lesson_page" else other_ask(s, f"{W1} {W2}")
        assert r.status_code == 200, r.text
        assert r.json()["mode"] == "lesson"
        assert held == [0]
        assert engine.pool.checkedout() == 0
    finally:
        engine.dispose()


# ---------------------------------------------------------------- task 6: concurrency
def _mock_client(hits, per_minute=20):
    def handler(request):
        hits.append(1)
        return httpx.Response(200, json={"choices": [{"message": {"content": "Indexes help."}}]})

    return SoclaasClient(
        Settings("https://llm.test/v1", "sk-test-sentinel", "m"),
        limits=Limits(per_caller_per_minute=per_minute),
        transport=httpx.MockTransport(handler),
        clock=lambda: 0.0,
        sleep=lambda s: None,
    )


def test_stu03_grounding_db_concurrency_thirty_lesson_requests_admit_exactly_twenty():
    cid, s, lid = world()
    hits = []
    client = _mock_client(hits)
    app.dependency_overrides[llm_client.get_llm_client] = lambda: client
    results, errors = {}, []

    def run(i):
        try:
            results[i] = lesson_ask(s, f"question {i}", lid)
        except Exception as exc:  # pragma: no cover
            errors.append(exc)

    try:
        threads = [threading.Thread(target=run, args=(i,)) for i in range(30)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
    finally:
        app.dependency_overrides.pop(llm_client.get_llm_client, None)
    assert not errors and len(results) == 30
    ok = [r for r in results.values() if r.status_code == 200]
    limited = [r for r in results.values() if r.status_code == 429]
    assert len(ok) == 20, [r.status_code for r in results.values()]
    assert len(limited) == 10 and all(code_of(r) == "rate_limited" for r in limited)
    assert len(hits) == 20
    for r in ok:
        assert r.json()["mode"] == "lesson"
        assert r.json()["sources"] == [{"lesson_id": lid, "title": TITLE}]


def test_stu03_grounding_db_concurrency_parallel_requests_of_two_students_do_not_mix(fake):
    cid = make_course()
    a, b = enrolled_student(cid), enrolled_student(cid)
    lid_a = make_lesson(cid, title="Lesson A", content="A-BODY-MARKER")
    lid_b = make_lesson(cid, title="Lesson B", content="B-BODY-MARKER")
    results = {}

    def run(key, who, lid):
        results[key] = lesson_ask(who, f"question {key}", lid)

    threads = [threading.Thread(target=run, args=(i, a if i % 2 == 0 else b, lid_a if i % 2 == 0 else lid_b))
               for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    for i, r in results.items():
        want = ("Lesson A", lid_a) if i % 2 == 0 else ("Lesson B", lid_b)
        assert r.status_code == 200, r.text
        assert r.json()["sources"] == [{"lesson_id": want[1], "title": want[0]}]
    for c in fake.calls:
        assert ("A-BODY-MARKER" in c.all_text) != ("B-BODY-MARKER" in c.all_text)


def test_stu03_grounding_db_concurrency_withdraw_while_a_request_is_in_flight(fake):
    cid, s, lid = world()
    fake.gate = threading.Event()
    out = {}
    t = threading.Thread(target=lambda: out.__setitem__("r", lesson_ask(s, "What is a closure?", lid)))
    t.start()
    assert fake.entered.wait(15), "request never reached the model"
    withdraw(lid)  # lands while the request is in flight
    fake.gate.set()
    t.join(20)
    r = out["r"]
    assert r.status_code == 404 and r.json() == LESSON_NOT_FOUND_BODY
    assert BENIGN not in r.text


def test_stu03_grounding_db_concurrency_submit_racing_a_lesson_request_releases_nothing(fake):
    """Lesson mode has no key, so a submit racing it cannot release one (spec: concurrent requests (c))."""
    from companion_helpers import CORRECT, EXPLANATIONS, save, start, submit

    cid, s, lid = world()
    aid = start(s)
    save(aid, s, CORRECT)
    fake.gate = threading.Event()
    out = {}
    t = threading.Thread(target=lambda: out.__setitem__("r", lesson_ask(s, "What is a closure?", lid)))
    t.start()
    assert fake.entered.wait(15)
    submit(aid, s)
    fake.gate.set()
    t.join(20)
    assert out["r"].status_code == 200 and out["r"].json()["mode"] == "lesson"
    for e in EXPLANATIONS:
        assert e not in fake.calls[0].all_text
    assert SET_ID not in fake.calls[0].all_text


# ---------------------------------------------------------------- AC10 with a real session
def test_stu03_grounding_db_practice_page_ignores_a_lesson_id_even_for_a_foreign_lesson(fake):
    cid, s, _ = world()
    foreign = make_lesson(make_course(), title="Foreign", content="FOREIGN-BODY-1")
    r = ask(s, "hint please", page="practice", set_id=SET_ID, context_extra={"lesson_id": foreign})
    assert r.status_code == 200 and r.json()["mode"] == "hint"
    assert "FOREIGN-BODY-1" not in fake.last.all_text
    r = ask(s, "How do I use this app?", page="other", context_extra={"lesson_id": foreign})
    assert r.status_code == 200 and r.json()["mode"] == "help"
    assert "FOREIGN-BODY-1" not in fake.last.all_text
