"""Privacy at storage/dispatch boundaries, with a fake SoC grader only."""
import pytest

from feature_analytics import privacy
from adm01_fixtures import analytics_admin, grader, tracked_users  # noqa: F401
from adm01_grading_helpers import (chat_item, grader_json, grades_of, item_row, new_window,
                                   quality, run_to_end)
from adm01_helpers import RUNS
from adm02_helpers import actor
from auth_helpers import call, sql


@pytest.fixture
def ready_scanner(monkeypatch):
    monkeypatch.setattr(privacy, "privacy_ready", lambda: True)
    monkeypatch.setattr(privacy, "scan_person_spans", lambda text: ())


def pending(tracked_users, win, **kwargs):
    user = actor("student")
    tracked_users.append(user)
    _, item = chat_item(user, win.at(1), context_text="", **kwargs)
    sql("UPDATE analytics_grading_item SET privacy_policy_version=%s WHERE id=%s",
        ("adm01-local-dlp-v1", item))
    return item


def test_adm01_privacy_scanner_unready_start_is_503_without_run_or_quota(
        analytics_admin, grader, monkeypatch):
    monkeypatch.setattr(privacy, "privacy_ready", lambda: False)
    win = new_window()
    before = sql("SELECT count(*) FROM analytics_grading_run")[0][0]
    for _ in range(2):
        response = call("POST", RUNS, analytics_admin, {"workflow": "student_exercise", **win.params})
        assert response.status_code == 503
        assert response.json() == {"detail": {"code": "privacy_scanner_unavailable", "message":
            "AI grading is unavailable because the local privacy scanner is not ready. Try again later."}}
    assert sql("SELECT count(*) FROM analytics_grading_run")[0][0] == before
    assert grader.calls == []


def test_adm01_privacy_strict_start_is_409_without_run_or_quota(
        analytics_admin, grader, monkeypatch):
    monkeypatch.setenv("ANALYTICS_PRIVACY_MODE", "strict")
    win = new_window()
    before = sql("SELECT count(*) FROM analytics_grading_run")[0][0]
    response = call("POST", RUNS, analytics_admin, {"workflow": "student_exercise", **win.params})
    assert response.status_code == 409
    assert response.json() == {"detail": {"code": "privacy_grading_disabled", "message":
        "AI grading is disabled because free-text privacy protection has not been approved."}}
    assert sql("SELECT count(*) FROM analytics_grading_run")[0][0] == before
    assert grader.calls == []


def test_adm01_privacy_dispatch_rescans_and_sends_exact_sanitised_payload(
        analytics_admin, grader, tracked_users, ready_scanner, monkeypatch):
    win = new_window()
    item = pending(tracked_users, win, request_text="Please give a hint.",
                   response_text="Alice considers loops.")
    seen = []

    def scan(text):
        seen.append(text)
        return ((0, 5),) if text.startswith("Alice") else ()

    monkeypatch.setattr(privacy, "scan_person_spans", scan)
    result = run_to_end(analytics_admin, win)
    assert result["status"] == "completed"
    assert len(grader.calls) == 1
    sent = grader.calls[0]
    assert sent.block("request") == "Please give a hint."
    assert sent.block("response") == "[REDACTED] considers loops."
    assert sent.block("context") in (None, "")
    assert "Alice" not in sent.all_text
    assert "[REDACTED] considers loops." in seen
    assert item_row(item)["request_text"] is None
    assert item_row(item)["response_text"] is None
    assert grades_of(item)["factual_accuracy"][:2] == ("unassessable", None)


@pytest.mark.parametrize("version", [None, "outdated-policy"])
def test_adm01_privacy_policy_mismatch_purges_without_dispatch(
        analytics_admin, grader, tracked_users, ready_scanner, version):
    win = new_window()
    item = pending(tracked_users, win, response_text="PRIVATE legacy content.")
    sql("UPDATE analytics_grading_item SET privacy_policy_version=%s WHERE id=%s", (version, item))
    run_to_end(analytics_admin, win)
    row = item_row(item)
    assert row["status"] == "privacy_blocked"
    assert all(row[key] is None for key in ("request_text", "response_text", "context_text"))
    assert grader.calls == []
    report = quality(analytics_admin, win)
    assert report["grades"]["privacy_blocked_count"] == 1
    assert report["grades"]["privacy_mode"] == "local_dlp"
    assert report["grades"]["pending_count"] == 0
    assert "PRIVATE" not in str(report)


def test_adm01_privacy_new_name_in_grade_reason_is_never_saved_or_displayed(
        analytics_admin, grader, tracked_users, ready_scanner, monkeypatch):
    win = new_window()
    item = pending(tracked_users, win)
    grader.script[1] = grader_json(reasons={"clarity": "Alice wrote a clear response."})
    monkeypatch.setattr(privacy, "scan_person_spans", lambda text: ((0, 5),) if text.startswith("Alice") else ())
    run_to_end(analytics_admin, win)
    assert len(grader.calls) == 1
    assert grades_of(item) == {}
    assert item_row(item)["status"] == "grading_failed"
    assert "Alice" not in str(quality(analytics_admin, win))


def test_adm01_privacy_scanner_failure_midrun_purges_current_item_without_ai(
        analytics_admin, grader, tracked_users, ready_scanner, monkeypatch):
    win = new_window()
    item = pending(tracked_users, win)

    def failed(text):
        raise RuntimeError("private scanner failure")

    monkeypatch.setattr(privacy, "scan_person_spans", failed)
    result = run_to_end(analytics_admin, win)
    assert (result["status"], result["failure_code"]) == ("failed", "privacy_scanner_unavailable")
    row = item_row(item)
    assert row["status"] == "privacy_blocked"
    assert all(row[key] is None for key in ("request_text", "response_text", "context_text"))
    assert grader.calls == []
