"""ADM-01 independent helpers. Contract only: workflow/specs/ADM-01/plan.md (decision 7 fake seam).

No test here ever reaches the SoC LLM: `BlockedAiClient` is installed through
`app.dependency_overrides[llm_client.get_llm_client]` (the pattern of adm03_helpers.install) and the
background job start `feature_analytics.jobs.start` is a no-op, so a started run stays `queued`.
Any call that still reaches the client is recorded and fails. Tests that need a grading run to
really execute use `adm01_grading_helpers.FakeGrader` instead.
"""
import threading
from datetime import date, datetime, timedelta, timezone
from urllib.parse import quote

from auth_helpers import call, sql

BASE = "/api/admin/analytics"
USAGE = BASE + "/usage"
GENERATION = BASE + "/generation"
QUALITY = BASE + "/quality"
RUNS = BASE + "/grading-runs"

# Exact feature errors (plan.md "API endpoints" table): code -> (status, message).
ERRORS = {
    "invalid_date": (422, "Enter dates as YYYY-MM-DD."),
    "period_order": (422, "The start date must be on or before the end date."),
    "period_too_long": (422, "The period can be at most 366 days."),
    "invalid_workflow": (422, "Choose student_exercise or teacher_lesson_planning."),
    "invalid_paging": (422, "limit must be 1 to 100 and offset must be 0 or more."),
    "run_not_found": (404, "Grading run not found."),
    "grading_run_active": (409, "A grading run is already in progress."),
    "grading_quota": (429, "Grading run limit reached. Try again later."),
}

RUN_KEYS = {"run_id", "workflow", "period_start", "period_end", "status", "items_total", "items_graded",
            "items_failed", "failure_code", "created_at", "started_at", "finished_at"}

# Every endpoint of the module; (kind, method, path template).
ENDPOINTS = [("usage", "GET", USAGE), ("generation", "GET", GENERATION), ("quality", "GET", QUALITY),
             ("start", "POST", RUNS), ("run", "GET", RUNS + "/1")]


def utc_today():
    return datetime.now(timezone.utc).date()


def day(offset=0):
    """ISO date `offset` days before today (UTC)."""
    return (utc_today() - timedelta(days=offset)).isoformat()


def url(path, **params):
    """Query string built by hand so spaces and non-ASCII are percent-encoded; None omits the field."""
    parts = [f"{k}={quote(str(v), safe='')}" for k, v in params.items() if v is not None]
    return path + ("?" + "&".join(parts) if parts else "")


def send(user, kind, *, period_start=None, period_end=None, workflow="student_exercise", **extra):
    """Send one request of `kind` ('usage', 'generation', 'quality', 'start') for the period.

    GET kinds use the query string, 'start' uses the JSON body. A value of None is omitted.
    """
    if kind == "start":
        body = {"workflow": workflow, "period_start": period_start, "period_end": period_end, **extra}
        return call("POST", RUNS, user, {k: v for k, v in body.items() if v is not None})
    params = {"period_start": period_start, "period_end": period_end}
    if kind == "quality":
        params["workflow"] = workflow
    params.update(extra)
    return call("GET", url({"usage": USAGE, "generation": GENERATION, "quality": QUALITY}[kind], **params), user)


def error_body(r, status, code):
    """Assert the feature error shape, status, exact message and no-store; return the body."""
    exp_status, message = ERRORS[code]
    assert r.status_code == status == exp_status, (r.status_code, r.text)
    assert r.json() == {"detail": {"code": code, "message": message}}, r.text
    assert "no-store" in r.headers.get("cache-control", ""), r.headers
    return r.json()


def run_count():
    return sql("SELECT count(*) FROM analytics_grading_run")[0][0]


def active_run_count():
    return sql("SELECT count(*) FROM analytics_grading_run WHERE status IN ('queued','running')")[0][0]


def wipe_runs():
    sql("DELETE FROM analytics_grading_run")


def wipe_user_rows(user_ids):
    """Remove every analytics row written for these users (FK-safe order; idempotent)."""
    ids = [str(u) for u in user_ids]
    if not ids:
        return
    sql("DELETE FROM analytics_grading_item WHERE source_type='chat_request' AND source_id IN "
        "(SELECT id FROM analytics_chat_request WHERE user_id = ANY(%s))", (ids,))
    sql("DELETE FROM analytics_grading_item WHERE source_type='generation_attempt' AND source_id IN "
        "(SELECT id FROM analytics_generation_attempt WHERE user_id = ANY(%s))", (ids,))
    sql("DELETE FROM analytics_chat_request WHERE user_id = ANY(%s)", (ids,))
    sql("DELETE FROM analytics_session WHERE user_id = ANY(%s)", (ids,))
    sql("DELETE FROM analytics_practice_attempt WHERE user_id = ANY(%s)", (ids,))
    sql("DELETE FROM analytics_generation_attempt WHERE user_id = ANY(%s)", (ids,))


# ---- seeding through the documented tables (not through hooks) ----

def seed_student_response(user_id, *, request_text, response_text, context_text=None, duration_ms=1200,
                          status="pending", ref=None):
    """A successful student practice-attempt chat request received now plus its stored grading item."""
    rid = sql("INSERT INTO analytics_chat_request (user_id, role, activity_type, activity_ref, received_at, "
              "completed_at, duration_ms, outcome) VALUES (%s,'student','practice_attempt',%s,now(),now(),%s,'success') "
              "RETURNING id", (str(user_id), ref or "att-seed", duration_ms))[0][0]
    item = sql("INSERT INTO analytics_grading_item (workflow, source_type, source_id, received_at, duration_ms, "
               "request_text, response_text, context_text, status) VALUES "
               "('student_exercise','chat_request',%s,now(),%s,%s,%s,%s,%s) RETURNING id",
               (rid, duration_ms, request_text, response_text, context_text, status))[0][0]
    return rid, item


def seed_generation_response(user_id, *, response_text, request_text="Generate", context_text=None,
                             generation_workflow="mcq_batch", duration_ms=3000):
    """A successful TEA-02 generation attempt accepted now plus its stored grading item."""
    aid = sql("INSERT INTO analytics_generation_attempt (workflow, user_id, accepted_at, completed_at, duration_ms, "
              "outcome) VALUES (%s,%s,now(),now(),%s,'success') RETURNING id",
              (generation_workflow, str(user_id), duration_ms))[0][0]
    item = sql("INSERT INTO analytics_grading_item (workflow, source_type, source_id, generation_workflow, "
               "received_at, duration_ms, request_text, response_text, context_text, status) VALUES "
               "('teacher_lesson_planning','generation_attempt',%s,%s,now(),%s,%s,%s,%s,'pending') RETURNING id",
               (aid, generation_workflow, duration_ms, request_text, response_text, context_text))[0][0]
    return aid, item


# ---- the AI seam ----

class BlockedAiClient:
    """Stands in for the shared SoC LLM client. Records every use, never answers, never networks.

    Any attribute is a callable and the object itself is callable, so it stands in whatever call
    shape the shared client has. If `gate` is set, a call waits for it (at most 30 s) before failing.
    """

    def __init__(self, gate=None):
        self.calls = []
        self.gate = gate
        self.entered = threading.Event()

    def _use(self, name):
        self.calls.append(name)
        self.entered.set()
        if self.gate is not None:
            self.gate.wait(30)
        raise RuntimeError("ADM-01 test: the AI is blocked")

    def __getattr__(self, name):
        if name.startswith("__"):
            raise AttributeError(name)
        return lambda *a, **k: self._use(name)

    def __call__(self, *a, **k):
        return self._use("__call__")


def install_ai_block(monkeypatch, client):
    """Route the shared client dependency to `client` and make the background run a no-op.

    Seams named by the plan: `app.dependency_overrides[llm_client.get_llm_client]` (decision 7) and
    `jobs.start(run_id, llm, admin_id)` (run execution). The no-op keeps a started run `queued`, so
    an active run stays active for the next request. If the route bound `start` by name before this
    patch, the blocked client still catches the call and the run fails.
    """
    import llm_client
    from feature_analytics import jobs
    from main import app

    monkeypatch.setitem(app.dependency_overrides, llm_client.get_llm_client, lambda: client)
    monkeypatch.setattr(jobs, "start", lambda *a, **k: None)
    return client
