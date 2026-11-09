"""ADM-01 helpers for the TEA-02 route tests (generation attempts and hook isolation).

Reuses the existing TEA-02 test conventions (test_tea02_notes / test_tea02_mcqs): the teacher signs in with
`teacher_headers`, the shared client is faked through `app.dependency_overrides[get_llm_client]`, and a
source file is uploaded with `upload`. The recorded analytics user is therefore `demo-teacher`.
"""
import json

import pytest

from auth_helpers import sql
from test_tea02_notes import BASE, COURSE, NotesLlm, call as tea_call, upload  # noqa: F401
from test_tea02_mcqs import output as mcq_output

TEACHER = "demo-teacher"
ROUTE = {"study_notes": "note-drafts", "mcq_batch": "mcq-drafts"}
WORKFLOWS = ["study_notes", "mcq_batch"]


def mcq_with(explanation_marker, stem_prefix="Stem"):
    """A valid 3-question MCQ output whose explanations carry a unique marker."""
    rows = [{"question": f"{stem_prefix} {i}: what does test {i} check?",
             "choices": [f"Alpha {i}", f"Beta {i}", f"Gamma {i}", f"Delta {i}"], "correct_choice_index": i % 4,
             "explanation": f"{explanation_marker} explanation {i}."} for i in range(1, 4)]
    return json.dumps({"questions": rows}), rows


def prepare(fake, workflow):
    """Make the fake return a successful output for the workflow's route."""
    fake.error = None
    fake.text = mcq_output() if workflow == "mcq_batch" else "Core ideas\n- Give each function one responsibility."


def generate(app, workflow, material, **kw):
    return tea_call(app, "POST", f"{BASE}/materials/{material['id']}/{ROUTE[workflow]}", **kw)


def max_attempt_id():
    return sql("SELECT coalesce(max(id),0) FROM analytics_generation_attempt")[0][0]


def new_attempts(since, workflow=None):
    """Attempt rows created after `since` by the teacher: [(id, workflow, outcome)] oldest first."""
    rows = sql("SELECT id, workflow, outcome FROM analytics_generation_attempt WHERE id > %s AND user_id=%s "
               "ORDER BY id", (since, TEACHER))
    return [r for r in rows if workflow is None or r[1] == workflow]


def new_items(since):
    """Grading items for attempts created after `since`."""
    return sql("SELECT i.id, i.generation_workflow, i.request_text, i.response_text, i.context_text "
               "FROM analytics_grading_item i JOIN analytics_generation_attempt a "
               "ON i.source_type='generation_attempt' AND i.source_id=a.id WHERE a.id > %s AND a.user_id=%s "
               "ORDER BY i.id", (since, TEACHER))


def cleanup(since):
    sql("DELETE FROM analytics_grading_item WHERE source_type='generation_attempt' AND source_id IN "
        "(SELECT id FROM analytics_generation_attempt WHERE id > %s AND user_id=%s)", (since, TEACHER))
    sql("DELETE FROM analytics_generation_attempt WHERE id > %s AND user_id=%s", (since, TEACHER))


@pytest.fixture
def tea(tea01_database):
    """(app, fake NotesLlm, since): the fake replaces the shared client; rows created by the test are removed."""
    from llm_client import get_llm_client
    from main import app

    fake = NotesLlm()
    app.dependency_overrides[get_llm_client] = lambda: fake
    since = max_attempt_id()
    yield app, fake, since
    app.dependency_overrides.pop(get_llm_client, None)
    cleanup(since)
