"""ADM-08 AC24: `python -m feedback_dev_seed` (development only, idempotent, no AI call, no analysis, no message).

Contract: workflow/specs/ADM-08/plan.md "Backend" (dev seed). Run through a subprocess against the isolated test schema.
"""
import os
import subprocess
import sys
from pathlib import Path

import pytest

from auth_helpers import call, require_db, seeded, sql

BACKEND = Path(__file__).resolve().parents[1]
TABLES = ("feedback_forms", "feedback_responses", "feedback_analyses", "admin_messages", "admin_message_previews",
          "admin_message_deliveries")


def counts():
    return {t: sql("SELECT count(*) FROM " + t)[0][0] for t in TABLES}


def run_seed(app_env):
    env = {k: v for k, v in os.environ.items() if k != "APP_ENV"}
    if app_env is not None:
        env["APP_ENV"] = app_env
    return subprocess.run([sys.executable, "-m", "feedback_dev_seed"], cwd=BACKEND, env=env,
                          capture_output=True, text=True, timeout=120)


@pytest.fixture(autouse=True)
def database():
    require_db()


@pytest.mark.parametrize("app_env", ["production", "staging", "Development ", None])
def test_adm08_dev_seed_refuses_outside_development_and_creates_nothing(app_env):
    before = counts()
    assert run_seed(app_env).returncode != 0
    assert counts() == before


def test_adm08_dev_seed_creates_form_and_responses_once_and_is_idempotent():
    before = counts()
    first = run_seed("development")
    assert first.returncode == 0, first.stdout + first.stderr
    mid = counts()
    assert mid["feedback_forms"] == before["feedback_forms"] + 1 or mid["feedback_forms"] == before["feedback_forms"]
    assert mid["feedback_responses"] >= before["feedback_responses"]
    second = run_seed("development")
    assert second.returncode == 0, second.stdout + second.stderr
    assert counts() == mid


def test_adm08_dev_seed_makes_no_analysis_or_message():
    run_seed("development")
    before = counts()
    assert run_seed("development").returncode == 0
    after = counts()
    for table in ("feedback_analyses", "admin_messages", "admin_message_previews", "admin_message_deliveries"):
        assert after[table] == before[table]


def test_adm08_dev_seed_published_form_with_six_question_types_and_responses_visible_to_admin():
    assert run_seed("development").returncode == 0
    admin = seeded("admin")
    listing = call("GET", "/api/admin/feedback/forms?limit=100&offset=0", admin).json()["items"]
    found = []
    for item in listing:
        if item["state"] != "open" or not item["response_count"]:
            continue
        detail = call("GET", f"/api/admin/feedback/forms/{item['id']}", admin).json()
        if {q["type"] for q in detail["questions"]} >= {"short_answer", "paragraph", "multiple_choice", "dropdown",
                                                        "checkbox", "linear_scale"}:
            found.append(item)
    assert found, "the seed should leave one open form with all six question types and some responses"


def test_adm08_dev_seed_is_registered_in_the_shared_dev_seed_after_the_existing_steps():
    text = (BACKEND / "dev_seed.py").read_text(encoding="utf-8")
    assert "feedback_dev_seed" in text
    assert text.index("teacher_publications") < text.index("feedback_dev_seed")
