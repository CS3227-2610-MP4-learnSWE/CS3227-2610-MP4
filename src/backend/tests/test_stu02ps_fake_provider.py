"""STU-02-published-sets on FakeSetProvider: AC17 (grant/revoke), AC19 (companion) and AC20 (build_progress)."""
import os
import uuid

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from attempt_store import Attempt, SetSummary
from auth_helpers import call, code_of, new_student
from companion_helpers import (BENIGN, CORRECT, EXPLANATIONS, SET_ID, ask, assert_no_key_in, save, start, submit,
                               submitted_attempt)
from datetime import datetime, timezone
from fake_sets import FIXTURE_SET, UNKNOWN_SET_ID, FakeSetProvider
from practice_data import PracticeSet, Question
from progress_service import build_progress

pytestmark = pytest.mark.usefixtures("fake_provider")

NOT_FOUND = {"detail": {"code": "set_not_found", "message": "Practice set not found."}}
BAD_UUID = {"detail": {"code": "validation_error", "message": "A valid UUID is required."}}
OTHER_SET_ID = "c0000000-0000-4000-8000-0000000000aa"
OTHER_Q = "Which keyword starts a function definition in Python?"


def other_set():
    q = Question("z1", OTHER_Q, None, (("a", "Zebra alpha"), ("b", "Zebra beta")), "a", "OTHER-SET-EXPLANATION", None)
    return PracticeSet(OTHER_SET_ID, "Other", (q,))


# ---------------------------------------------------------------- AC17
def test_stu02ps_fake_ac17_revoke_then_every_attempt_endpoint_is_404_and_grant_restores(fake_provider):
    s = new_student()
    aid = start(s)
    save(aid, s, {"q1": "a", "q2": "b"})
    done = submitted_attempt(s)
    fake_provider.revoke(s, SET_ID)
    got = [call("GET", f"/api/attempts/{aid}", s), call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": CORRECT}),
           call("POST", f"/api/attempts/{aid}/submit", s), call("GET", f"/api/attempts/{aid}/results", s),
           call("GET", f"/api/attempts/{done}/results", s), call("GET", f"/api/practice-sets/{SET_ID}", s),
           call("POST", f"/api/practice-sets/{SET_ID}/attempts", s)]
    for r in got:
        assert r.status_code == 404 and r.json() == NOT_FOUND
    assert call("GET", "/api/progress", s).json()["practice"]["sets"] == []
    fake_provider.grant(s, SET_ID)
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {"q1": "a", "q2": "b"}
    assert call("GET", f"/api/attempts/{done}/results", s).status_code == 200
    assert call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": CORRECT}).status_code == 200


def test_stu02ps_fake_ac17_revoking_one_student_does_not_affect_another(fake_provider):
    a, b = new_student(), new_student()
    fake_provider.revoke(a, SET_ID)
    assert call("GET", f"/api/practice-sets/{SET_ID}", a).status_code == 404
    assert call("GET", f"/api/practice-sets/{SET_ID}", b).status_code == 200


# ---------------------------------------------------------------- AC19 companion
def test_stu02ps_fake_ac19_inaccessible_set_is_404_with_no_model_call(fake, fake_provider):
    s = new_student()
    fake_provider.revoke(s, SET_ID)
    r = ask(s, "hint please", page="practice", set_id=SET_ID)
    assert r.status_code == 404 and r.json() == NOT_FOUND
    r = ask(s, "hint please", page="practice", set_id=UNKNOWN_SET_ID)
    assert r.status_code == 404 and r.json() == NOT_FOUND
    assert fake.calls == []


@pytest.mark.parametrize("bad", ["intro-se-1", "nope", " ", "a" * 5000, "a\u0000b", "x' OR 1=1 --", "a0000000-0000-4000-8000-00000000000"])
def test_stu02ps_fake_ac19_a_set_id_that_is_not_a_uuid_is_422_with_no_model_call(fake, bad):
    r = ask(new_student(), "hint please", page="practice", set_id=bad)
    assert r.status_code == 422 and r.json() == BAD_UUID
    assert fake.calls == []


def test_stu02ps_fake_ac19_uppercase_set_id_without_an_attempt_finds_the_set(fake):
    r = ask(new_student(), "hint please", page="practice", set_id=SET_ID.upper())
    assert r.status_code == 200 and r.json()["mode"] == "hint"


def test_stu02ps_fake_ac19_an_old_attempt_on_a_non_uuid_set_is_404_and_a_revoked_attempt_is_404(fake, fake_provider):
    from stu04_helpers import insert_attempt

    s = new_student()
    old = insert_attempt(s, answers={}, correct_ids=[], status="in_progress", set_id="intro-se-1")
    r = ask(s, "hi", page="practice", attempt_id=old)
    assert r.status_code == 404 and r.json() == NOT_FOUND
    aid = submitted_attempt(s)
    fake_provider.revoke(s, SET_ID)
    r = ask(s, "why", page="practice", attempt_id=aid)
    assert r.status_code == 404 and r.json() == NOT_FOUND
    assert fake.calls == []


def test_stu02ps_fake_ac19_check_order_attempt_then_consistency_then_set(fake):
    s = new_student()
    aid = start(s)
    r = ask(s, "hi", page="practice", attempt_id="nope")
    assert r.status_code == 404 and code_of(r) == "attempt_not_found"
    r = ask(s, "hi", page="practice", set_id=OTHER_SET_ID, attempt_id=aid)  # inconsistent: 422 before any set lookup
    assert r.status_code == 422 and code_of(r) == "invalid_context"
    r = ask(s, "hi", page="practice")
    assert r.status_code == 422 and code_of(r) == "invalid_context"
    assert fake.calls == []


def test_stu02ps_fake_ac19_a_pasted_question_of_an_inaccessible_set_is_not_matched_but_an_accessible_one_is(fake, fake_provider):
    fake_provider.add(other_set())
    s = new_student()
    r = ask(s, OTHER_Q, page="other")
    assert r.status_code == 200
    assert "OTHER-SET-EXPLANATION" not in fake.last.all_text
    fake_provider.revoke(s, OTHER_SET_ID)
    ask(s, OTHER_Q, page="other")
    assert "Zebra" not in fake.last.all_text and "OTHER-SET-EXPLANATION" not in fake.last.all_text


def test_stu02ps_fake_ac19_hint_context_has_no_key_or_explanation_before_submit_and_explain_works_after(fake):
    s = new_student()
    r = ask(s, "I am stuck on the first question", page="practice", set_id=SET_ID)
    assert r.status_code == 200 and r.json()["mode"] == "hint"
    assert_no_key_in(fake.last.all_text)
    aid = submitted_attempt(s)
    r = ask(s, "why?", page="practice", attempt_id=aid)
    assert r.status_code == 200 and r.json()["mode"] == "explain"
    assert any(e in fake.last.all_text for e in EXPLANATIONS)


# ---------------------------------------------------------------- AC20 build_progress
class Store:
    def __init__(self, summaries):
        self.summaries = summaries

    def submitted_summaries(self, student_id):
        return list(self.summaries)


def summary(set_id, answered, correct_ids):
    latest = Attempt(id="a-" + uuid.uuid4().hex[:10], student_id="s", set_id=set_id, status="submitted",
                     answers={q: "a" for q in answered}, score_correct=len(correct_ids), score_total=len(answered),
                     key_version="v1", correct_question_ids=list(correct_ids),
                     submitted_at=datetime(2026, 3, 1, tzinfo=timezone.utc))
    return SetSummary(set_id, 1, len(correct_ids), len(answered), latest)


@pytest.fixture
def db():
    if not os.environ.get("TEA01_TEST_DATABASE_URL"):
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    engine = create_engine(os.environ["DATABASE_URL"])
    with Session(engine) as session:
        yield session
    engine.dispose()


def test_stu02ps_fake_ac20_inaccessible_and_unresolvable_sets_are_skipped(db):
    provider = FakeSetProvider([FIXTURE_SET, other_set()])
    provider.revoke("s1", OTHER_SET_ID)
    store = Store([summary(FIXTURE_SET.id, ["q1", "q2", "q3"], ["q1", "q2"]),
                   summary(OTHER_SET_ID, ["z1"], ["z1"]), summary("intro-se-1", ["q1"], ["q1"])])
    body = build_progress(db, "s1", store, provider).model_dump(mode="json")
    assert [r["set_id"] for r in body["practice"]["sets"]] == [FIXTURE_SET.id]
    assert [i["topic"]["name"] for i in body["topics"]["items"]] == ["Software engineering basics"]
    assert body["topics"]["items"][0]["answered"] == 3


def test_stu02ps_fake_ac20_every_question_of_a_set_counts_under_the_sets_topic(db):
    provider = FakeSetProvider([FIXTURE_SET])
    store = Store([summary(FIXTURE_SET.id, ["q1", "q2", "q3"], ["q1", "q2", "q3"])])
    body = build_progress(db, "s1", store, provider).model_dump(mode="json")
    assert len(body["topics"]["items"]) == 1
    item = body["topics"]["items"][0]
    assert (item["answered"], item["correct"], item["status"]) == (3, 3, "on_track")


def test_stu02ps_fake_ac20_the_provider_is_asked_once_for_the_students_sets(db):
    provider = FakeSetProvider([FIXTURE_SET])
    build_progress(db, "s1", Store([summary(FIXTURE_SET.id, ["q1"], ["q1"])]), provider)
    assert [c[0] for c in provider.calls] == ["get_many_for_student"]
    assert provider.calls[0][2] == "s1"
