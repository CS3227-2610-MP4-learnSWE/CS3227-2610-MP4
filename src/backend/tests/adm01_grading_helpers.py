"""ADM-01 data seeding, the fake grader and run helpers (tasks 18-20).

Contract: workflow/specs/ADM-01/plan.md only (tables in "Data model", hooks, grading run, decision 7).

* Every test works inside its own far-future UTC window (`new_window`), so rows written by other tests
  never appear in a report and exact counts can be asserted.
* The SoC LLM is `FakeGrader`, installed with `app.dependency_overrides[llm_client.get_llm_client]`
  exactly as adm03_helpers.install does; it never networks.
"""
import json
import random
import re
import threading
import time
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone

import psycopg

import llm_client
from llm_client import LlmReply
from main import app
from adm01_helpers import RUNS, QUALITY, USAGE, GENERATION, url
from auth_helpers import call, psycopg_url, sql

UTC = timezone.utc
DIMS = ("relevance", "factual_accuracy", "clarity", "safety")
NO_CONTEXT_REASONS = {"No authorised context was available.", "Answer keys are not available for assessment."}
_used_windows = set()


# ------------------------------------------------------------------ windows

class Window:
    """`days` whole UTC days far in the future; `start`/`end` are the inclusive ISO dates."""

    def __init__(self, days=1):
        while True:
            base = date(2040, 1, 1) + timedelta(days=40 * random.randrange(0, 4000))
            if base not in _used_windows:
                _used_windows.add(base)
                break
        self.days = days
        self.first = base
        self.last = base + timedelta(days=days - 1)
        self.start, self.end = self.first.isoformat(), self.last.isoformat()
        self.start_dt = datetime(base.year, base.month, base.day, tzinfo=UTC)
        self.end_dt = self.start_dt + timedelta(days=days)  # exclusive

    @property
    def params(self):
        return {"period_start": self.start, "period_end": self.end}

    def at(self, minutes=0, seconds=0):
        """A timestamp inside the window: start + minutes + seconds."""
        return self.start_dt + timedelta(minutes=minutes, seconds=seconds)

    @property
    def mid(self):
        return self.start_dt + (self.end_dt - self.start_dt) / 2


def new_window(days=1):
    return Window(days)


# ------------------------------------------------------------------ seeding through the documented tables

def chat_row(user, at, outcome="success", *, activity_type="practice_attempt", activity_ref=None,
             session_id=None, duration_ms=1000):
    completed = None if outcome == "pending" else at + timedelta(milliseconds=duration_ms)
    dur = None if outcome == "pending" else duration_ms
    if activity_type == "practice_attempt" and activity_ref is None:
        activity_ref = "att-seed"
    return sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, session_id, "
               "received_at, completed_at, duration_ms, outcome) VALUES (%s,'student',%s,%s,%s,%s,%s,%s,%s) "
               "RETURNING id", (str(user), activity_type, activity_ref, session_id, at, completed, dur, outcome))[0][0]


def session_row(user, ref, started, *, last=None, ended="auto", reason="inactivity"):
    last = last or started
    ended = last if ended == "auto" else ended
    return sql("INSERT INTO analytics_session (user_id, role, activity_type, activity_ref, started_at, "
               "last_message_at, ended_at, end_reason) VALUES (%s,'student','practice_attempt',%s,%s,%s,%s,%s) "
               "RETURNING id", (str(user), ref, started, last, ended, reason if ended else None))[0][0]


def attempt_row(user, ref, started, submitted=None, set_id="set-1"):
    sql("INSERT INTO analytics_practice_attempt (attempt_ref, user_id, practice_set_id, started_at, submitted_at) "
        "VALUES (%s,%s,%s,%s,%s)", (ref, str(user), set_id, started, submitted))
    return ref


def gen_row(user, workflow, at, outcome="success", duration_ms=3000):
    completed = None if outcome == "pending" else at + timedelta(milliseconds=duration_ms)
    dur = None if outcome == "pending" else duration_ms
    return sql("INSERT INTO analytics_generation_attempt (workflow, user_id, accepted_at, completed_at, "
               "duration_ms, outcome) VALUES (%s,%s,%s,%s,%s,%s) RETURNING id",
               (workflow, str(user), at, completed, dur, outcome))[0][0]


def chat_item(user, at, *, request_text="Please give me a hint", response_text="Think about the idea.",
              context_text="", status="pending", duration_ms=1500, created_days_ago=0,
              ref=None, failure_code=None):
    """A successful student practice chat request plus its stored grading item. Returns (chat_id, item_id)."""
    rid = chat_row(user, at, "success", activity_ref=ref, duration_ms=duration_ms)
    item = sql("INSERT INTO analytics_grading_item (workflow, source_type, source_id, received_at, duration_ms, "
               "request_text, response_text, context_text, status, failure_code, created_at) VALUES "
               "('student_exercise','chat_request',%s,%s,%s,%s,%s,%s,%s,%s, now() - make_interval(days => %s::int)) "
               "RETURNING id", (rid, at, duration_ms, request_text, response_text, context_text, status,
                                failure_code, created_days_ago))[0][0]
    sql("UPDATE analytics_grading_item SET privacy_policy_version=%s WHERE id=%s",
        ("adm01-local-dlp-v1", item))
    return rid, item


def gen_item(user, at, *, generation_workflow="study_notes", request_text="Generate notes",
             response_text="Core ideas: one responsibility per function.", context_text="",
             status="pending", duration_ms=3000, created_days_ago=0, failure_code=None):
    """A successful TEA-02 generation attempt plus its stored grading item. Returns (attempt_id, item_id)."""
    aid = gen_row(user, generation_workflow, at, "success", duration_ms)
    item = sql("INSERT INTO analytics_grading_item (workflow, source_type, source_id, generation_workflow, "
               "received_at, duration_ms, request_text, response_text, context_text, status, failure_code, "
               "created_at) VALUES ('teacher_lesson_planning','generation_attempt',%s,%s,%s,%s,%s,%s,%s,%s,%s, "
               "now() - make_interval(days => %s::int)) RETURNING id",
               (aid, generation_workflow, at, duration_ms, request_text, response_text, context_text, status,
                failure_code, created_days_ago))[0][0]
    sql("UPDATE analytics_grading_item SET privacy_policy_version=%s WHERE id=%s",
        ("adm01-local-dlp-v1", item))
    return aid, item


def give_grades(item_id, scores, reason="Fine."):
    """Mark an item graded with texts removed. `scores` maps a dimension to an int or None (unassessable)."""
    for dim in DIMS:
        score = scores.get(dim, 4)
        sql("INSERT INTO analytics_grade (item_id, dimension, state, score, reason) VALUES (%s,%s,%s,%s,%s)",
            (item_id, dim, "graded" if score is not None else "unassessable", score, reason))
    sql("UPDATE analytics_grading_item SET status='graded', graded_at=now(), request_text=NULL, "
        "response_text=NULL, context_text=NULL WHERE id=%s", (item_id,))


def item_row(item_id):
    r = sql("SELECT status, failure_code, request_text, response_text, context_text, graded_at "
            "FROM analytics_grading_item WHERE id=%s", (item_id,))
    return dict(zip(("status", "failure_code", "request_text", "response_text", "context_text", "graded_at"), r[0])) if r else None


def grades_of(item_id):
    rows = sql("SELECT dimension, state, score, reason FROM analytics_grade WHERE item_id=%s", (item_id,))
    return {d: (st, sc, rs) for d, st, sc, rs in rows}


def bulk_users(n, prefix="ADM01 bulk"):
    """Insert n student users with one connection (for the 500-row cap test). Returns the ids."""
    ids = [f"u-adm01bulk{random.getrandbits(48):012x}{i:04d}" for i in range(n)]
    with psycopg.connect(psycopg_url(), autocommit=True) as conn:
        for i, uid_ in enumerate(ids):
            conn.execute('INSERT INTO "user" (id,display_name,role,email,password_hash,access_status) '
                         "SELECT %s,%s,'student',%s,password_hash,'enabled' FROM \"user\" WHERE id='demo-admin'",
                         (uid_, f"{prefix} {i:04d}", f"{uid_}@example.com"))
    return ids


def drop_users(ids):
    if ids:
        sql('DELETE FROM "user" WHERE id = ANY(%s)', (list(ids),))


def set_name(user, name):
    sql('UPDATE "user" SET display_name=%s WHERE id=%s', (name, str(user)))


class RecordingStart:
    """Temporarily set analytics_meta.recording_started_at (restored by `restore`)."""

    def __init__(self):
        self.old = sql("SELECT value FROM analytics_meta WHERE key='recording_started_at'")[0][0]

    def set(self, when):
        sql("UPDATE analytics_meta SET value=%s WHERE key='recording_started_at'", (when.isoformat(),))

    def restore(self):
        sql("UPDATE analytics_meta SET value=%s WHERE key='recording_started_at'", (self.old,))


# ------------------------------------------------------------------ requests

def get_json(user, kind, win, **extra):
    path = {"usage": USAGE, "generation": GENERATION, "quality": QUALITY}[kind]
    r = call("GET", url(path, **win.params, **extra), user)
    assert r.status_code == 200, r.text
    return r.json()


def quality(user, win, workflow="student_exercise", **extra):
    return get_json(user, "quality", win, workflow=workflow, **extra)


def start_run(admin, win, workflow="student_exercise"):
    r = call("POST", RUNS, admin, {"workflow": workflow, **win.params})
    assert r.status_code == 202, r.text
    return r.json()


def wait_run(admin, run_id, timeout=40):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        r = call("GET", f"{RUNS}/{run_id}", admin)
        assert r.status_code == 200, r.text
        if r.json()["status"] in ("completed", "failed"):
            return r.json()
        time.sleep(0.05)
    raise AssertionError("grading run did not finish")


def run_to_end(admin, win, workflow="student_exercise"):
    return wait_run(admin, start_run(admin, win, workflow)["run_id"])


def exc(cls, *args):
    """Build a shared-client exception whatever its constructor shape."""
    for a in (args, ("x",), ()):
        try:
            return cls(*a)
        except TypeError:
            continue
    raise AssertionError(f"cannot construct {cls}")


# ------------------------------------------------------------------ the fake grader (SoC LLM stand-in)

def grader_json(scores=None, reasons=None, extra=None, dim_extra=None):
    """A valid grader reply (fixed schema, plan "AI usage"). Defaults: every score 4, a generic reason."""
    scores = {**{d: 4 for d in DIMS}, **(scores or {})}
    out = {d: {"score": scores[d], "reason": (reasons or {}).get(d, f"The {d.replace('_', ' ')} is acceptable here.")}
           for d in DIMS}
    for d in (dim_extra or {}):
        out[d].update(dim_extra[d])
    out.update(extra or {})
    return json.dumps(out)


@dataclass
class Call:
    messages: list
    max_tokens: int
    caller_id: str
    timeout_seconds: float = None
    max_reply_chars: int = None
    reasoning_effort: str = None

    @property
    def system_text(self):
        return "\n".join(m.content for m in self.messages if m.role == "system")

    @property
    def user_text(self):
        return "\n".join(m.content for m in self.messages if m.role != "system")

    @property
    def all_text(self):
        return "\n".join(m.content for m in self.messages)

    def block(self, name):
        found = re.findall(rf"<{name}>(.*?)</{name}>", self.user_text, re.S)
        return found[0] if found else None


class FakeGrader:
    """Implements LlmClient.complete (plan decision 7).

    script[n] (1-based call number) may be an exception to raise, an LlmReply, a str reply text or a
    callable(Call) -> str | exception. `by_marker` maps a substring of the response block to the same
    kinds of step. Default reply: valid JSON with every score 4.
    """

    def __init__(self):
        self.calls = []
        self.script = {}
        self.by_marker = {}
        self.delay = 0.0
        self.gate = None
        self.entered = threading.Event()
        self.lock = threading.Lock()

    def complete(self, messages, *, max_tokens, caller_id, timeout_seconds=None, max_reply_chars=None,
                 reasoning_effort=None):
        c = Call(list(messages), max_tokens, caller_id, timeout_seconds, max_reply_chars, reasoning_effort)
        with self.lock:
            self.calls.append(c)
            n = len(self.calls)
        self.entered.set()
        if self.gate is not None:
            assert self.gate.wait(40), "test gate never released"
        if self.delay:
            time.sleep(self.delay)
        step = self.script.get(n)
        if step is None:
            body = c.block("response") or ""
            for marker, s in self.by_marker.items():
                if marker in body:
                    step = s
                    break
        if callable(step) and not isinstance(step, BaseException):
            step = step(c)
        if isinstance(step, BaseException):
            raise step
        if isinstance(step, LlmReply):
            return step
        return LlmReply(text=step if step is not None else grader_json(), finish_reason="stop",
                        prompt_tokens=10, completion_tokens=5)

    def markers_called(self, prefix):
        found = []
        for c in self.calls:
            m = re.search(re.escape(prefix) + r"\d+", c.block("response") or "")
            found.append(m.group(0) if m else None)
        return found


def install_grader(fake):
    app.dependency_overrides[llm_client.get_llm_client] = lambda: fake


def uninstall_grader():
    app.dependency_overrides.pop(llm_client.get_llm_client, None)
