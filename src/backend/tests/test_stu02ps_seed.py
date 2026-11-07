"""STU-02-published-sets AC23: the development seed `python -m teacher_publications.seed`.

Contract: workflow/specs/STU-02-published-sets/plan.md "Development seed". Runs against the isolated test schema.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from auth_helpers import call, code_of, new_student, seeded
from stu01_helpers import sql

COURSE = "11111111-1111-4111-8111-111111111111"
TOPIC = "66666666-6666-4666-8666-666666666661"
SET_ID = "77777777-7777-4777-8777-777777777774"
MATERIAL = "77777777-7777-4777-8777-777777777771"
BATCH = "77777777-7777-4777-8777-777777777772"
DRAFTS = [f"77777777-7777-4777-8777-77777777773{i}" for i in (1, 2, 3)]
PUBLISHED = [f"77777777-7777-4777-8777-77777777775{i}" for i in (1, 2, 3)]
TITLE = "Software engineering practice"


@pytest.fixture
def seed_module():
    pytest.importorskip("teacher_publications.seed")
    import teacher_publications.seed as seed

    return seed


@pytest.fixture
def clean():
    """Prerequisites present (course, topic, demo-student membership), seed rows absent before and after."""
    sql("INSERT INTO topic(id, course_id, name) VALUES (%s, %s, 'Software engineering basics') ON CONFLICT DO NOTHING",
        (TOPIC, COURSE))
    sql("INSERT INTO course_membership(course_id, user_id) VALUES (%s, 'demo-student') ON CONFLICT DO NOTHING", (COURSE,))
    wipe()
    yield
    wipe()


def wipe():
    sql("DELETE FROM practice_attempt WHERE set_id = %s", (SET_ID,))
    sql("DELETE FROM published_practice_question WHERE set_id = %s", (SET_ID,))
    sql("DELETE FROM published_practice_set WHERE id = %s", (SET_ID,))
    sql("DELETE FROM mcq_draft_question WHERE batch_id = %s", (BATCH,))
    sql("DELETE FROM mcq_draft_batch WHERE id = %s", (BATCH,))
    sql("DELETE FROM material_file WHERE material_id = %s", (MATERIAL,))
    sql("DELETE FROM material WHERE id = %s", (MATERIAL,))


def counts():
    return {
        "set": sql("SELECT count(*) FROM published_practice_set WHERE id = %s", (SET_ID,))[0][0],
        "questions": sql("SELECT count(*) FROM published_practice_question WHERE set_id = %s", (SET_ID,))[0][0],
        "batch": sql("SELECT count(*) FROM mcq_draft_batch WHERE id = %s", (BATCH,))[0][0],
        "drafts": sql("SELECT count(*) FROM mcq_draft_question WHERE batch_id = %s", (BATCH,))[0][0],
        "material": sql("SELECT count(*) FROM material WHERE id = %s", (MATERIAL,))[0][0],
        "file": sql("SELECT count(*) FROM material_file WHERE material_id = %s", (MATERIAL,))[0][0],
    }


ONE_SET = {"set": 1, "questions": 3, "batch": 1, "drafts": 3, "material": 1, "file": 1}
NOTHING = {k: 0 for k in ONE_SET}


def run_seed(seed_module):
    engine = create_engine(os.environ["DATABASE_URL"])
    try:
        with Session(engine) as session:
            seed_module.seed_practice_set(session)
    finally:
        engine.dispose()


def test_stu02ps_seed_creates_one_published_set_with_three_questions_and_its_foreign_key_rows(seed_module, clean):
    assert seed_module.SEED_SET_ID.__class__.__name__ == "UUID" and str(seed_module.SEED_SET_ID) == SET_ID
    run_seed(seed_module)
    assert counts() == ONE_SET
    row = sql("SELECT course_id::text, topic_id::text, title, source_draft_id::text, source_version, published_by "
              "FROM published_practice_set WHERE id = %s", (SET_ID,))[0]
    assert row == (COURSE, TOPIC, TITLE, BATCH, 1, "demo-teacher")
    qs = sql("SELECT id::text, position, source_question_id::text, correct_choice_index, jsonb_array_length(choices) "
             "FROM published_practice_question WHERE set_id = %s ORDER BY position", (SET_ID,))
    assert [q[0] for q in qs] == PUBLISHED and [q[1] for q in qs] == [1, 2, 3]
    assert [q[2] for q in qs] == DRAFTS and [q[3] for q in qs] == [0, 1, 2] and all(q[4] == 4 for q in qs)
    size = sql("SELECT m.size_bytes, octet_length(f.content) FROM material m JOIN material_file f ON f.material_id = m.id "
               "WHERE m.id = %s", (MATERIAL,))[0]
    assert size[1] >= 1 and size[0] == size[1]


def test_stu02ps_seed_running_twice_changes_nothing(seed_module, clean):
    run_seed(seed_module)
    snapshot = sql("SELECT id::text, title, published_at FROM published_practice_set WHERE id = %s", (SET_ID,))
    run_seed(seed_module)
    assert counts() == ONE_SET
    assert sql("SELECT id::text, title, published_at FROM published_practice_set WHERE id = %s", (SET_ID,)) == snapshot


def test_stu02ps_seed_never_overwrites_an_existing_row(seed_module, clean):
    run_seed(seed_module)
    sql("UPDATE published_practice_set SET title = 'Edited by hand' WHERE id = %s", (SET_ID,))
    sql("UPDATE published_practice_question SET question = 'Edited question?' WHERE id = %s", (PUBLISHED[0],))
    sql("UPDATE material SET title = 'Edited material' WHERE id = %s", (MATERIAL,))
    run_seed(seed_module)
    assert sql("SELECT title FROM published_practice_set WHERE id = %s", (SET_ID,)) == [("Edited by hand",)]
    assert sql("SELECT question FROM published_practice_question WHERE id = %s", (PUBLISHED[0],)) == [("Edited question?",)]
    assert sql("SELECT title FROM material WHERE id = %s", (MATERIAL,)) == [("Edited material",)]
    assert counts() == ONE_SET


def test_stu02ps_seed_completes_a_partly_seeded_database(seed_module, clean):
    run_seed(seed_module)
    sql("DELETE FROM published_practice_question WHERE id = %s", (PUBLISHED[2],))
    run_seed(seed_module)
    assert counts() == ONE_SET


@pytest.mark.parametrize("env", [{"APP_ENV": "production"}, {"APP_ENV": "staging"}, {"APP_ENV": "Development "}, {}])
def test_stu02ps_seed_main_refuses_outside_development_and_creates_nothing(seed_module, clean, env, capsys):
    full = {**env, "DATABASE_URL": os.environ["DATABASE_URL"]}
    assert seed_module.main(full) == 1
    assert "development databases only" in capsys.readouterr().out
    assert counts() == NOTHING


def test_stu02ps_seed_main_in_development_returns_zero_and_seeds(seed_module, clean):
    assert seed_module.main({"APP_ENV": "development", "DATABASE_URL": os.environ["DATABASE_URL"]}) == 0
    assert counts() == ONE_SET
    assert seed_module.main({"APP_ENV": "development", "DATABASE_URL": os.environ["DATABASE_URL"]}) == 0
    assert counts() == ONE_SET


def test_stu02ps_seed_command_exits_non_zero_with_a_production_environment(clean):
    backend = Path(__file__).resolve().parents[1]
    env = {**os.environ, "APP_ENV": "production"}
    done = subprocess.run([sys.executable, "-m", "teacher_publications.seed"], cwd=backend, env=env,
                          capture_output=True, text=True)
    assert done.returncode != 0
    assert counts() == NOTHING
    env["APP_ENV"] = "development"
    done = subprocess.run([sys.executable, "-m", "teacher_publications.seed"], cwd=backend, env=env,
                          capture_output=True, text=True)
    assert done.returncode == 0, done.stderr
    assert counts() == ONE_SET


def test_stu02ps_seed_set_is_readable_by_demo_student_and_not_by_another_course(seed_module, clean):
    run_seed(seed_module)
    demo = seeded("student")
    r = call("GET", f"/api/practice-sets/{SET_ID}", demo)
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["title"] == TITLE and len(body["questions"]) == 3
    assert [q["text"] for q in body["questions"]][0] == "What should a well-designed function have?"
    assert "Explanation" not in r.text and "explanation" not in r.text
    picker = call("GET", "/api/practice-sets", demo).json()["courses"]
    mine = [x for c in picker if c["id"] == COURSE for x in c["sets"] if x["id"] == SET_ID]
    assert len(mine) == 1 and mine[0]["topic"]["id"] == TOPIC and mine[0]["question_count"] == 3
    stranger = call("GET", f"/api/practice-sets/{SET_ID}", new_student())
    assert stranger.status_code == 404 and code_of(stranger) == "set_not_found"
