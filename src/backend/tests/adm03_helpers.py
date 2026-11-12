"""ADM-03 independent fixtures. Contract only: workflow/specs/ADM-08/retained-criteria.md.

The SoC LLM is always the FakeAnalysisLlm below (dependency override of get_llm_client);
no test makes a live call. The fake tells map from reduce by the first system line.
"""
import json
import re
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

import psycopg
from psycopg.types.json import Jsonb

import llm_client
from llm_client import LlmReply
from main import app
from auth_helpers import call, psycopg_url, sql
from adm02_helpers import created, payload, question, uid

BASE = "/api/admin/feedback/analyses"
POOL = ThreadPoolExecutor(max_workers=16)
SEEDED_USERS = []  # ids of the respondent users seed() created, removed again by cleanup_from


def cleanup_from(mark):
    """Remove everything seed() inserted since registry position `mark` (FK-safe order; idempotent)."""
    users = SEEDED_USERS[mark:]
    del SEEDED_USERS[mark:]
    if not users:
        return
    with psycopg.connect(psycopg_url(), autocommit=True) as conn:
        forms = [r[0] for r in conn.execute("SELECT DISTINCT form_id FROM feedback_responses WHERE user_id = ANY(%s)", (users,)).fetchall()]
        forms += [r[0] for r in conn.execute("SELECT DISTINCT form_id FROM feedback_recipients WHERE user_id = ANY(%s)", (users,)).fetchall()]
        conn.execute("DELETE FROM feedback_analyses WHERE form_id = ANY(%s)", (forms,))
        conn.execute("DELETE FROM feedback_responses WHERE user_id = ANY(%s)", (users,))
        conn.execute("DELETE FROM feedback_recipients WHERE user_id = ANY(%s)", (users,))
        conn.execute('DELETE FROM "user" WHERE id = ANY(%s)', (users,))

# Exact message texts copied from spec.md "Failure messages".
MSG = {
    "selection_required": "No responses are selected. Select at least one response, or use Select all, then generate the analysis.",
    "no_responses": "This form has no submitted responses, so there is nothing to analyse.",
    "form_not_found": "That form is not available. It may have been deleted. Choose another form.",
    "analysis_not_found": "That analysis is not available. It does not exist or is not in your history.",
    "evidence_not_found": "This response cannot be shown. It was deleted, or the reference is not part of this analysis.",
}


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

    @property
    def kind(self):
        first = next(m.content for m in self.messages if m.role == "system").split("\n", 1)[0].strip()
        return {"TASK: MAP": "map", "TASK: REDUCE": "reduce"}[first]

    def entries(self):
        """(labels, question position, text) for each `<<<R3,R9|Q2|text>>>` data line of a map call."""
        return [(a.split(","), int(b), c) for a, b, c in
                re.findall(r"<<<([^|>]*)\|Q(\d+)\|(.*?)>>>", self.user_text, re.S)]


class FakeAnalysisLlm:
    """Implements LlmClient.complete. script[n] (1-based call number) may be an exception to raise,
    an LlmReply, a str reply text or a callable(Call) -> str."""

    def __init__(self):
        self.calls = []
        self.script = {}
        self.gate = None
        self.entered = threading.Event()
        self.lock = threading.Lock()

    def default_text(self, c):
        if c.kind == "map":
            labels = []
            for group, _, _ in c.entries():
                labels += [x for x in group if x not in labels]
            ev = labels[:2]
            if not ev:
                return '{"themes":[]}'
            return json.dumps({"themes": [{"title": "Unclear deadlines",
                                           "description": "Several students cannot find due dates.", "evidence": ev}]})
        seen = []
        for x in re.findall(r"\bR\d{1,3}\b", c.user_text):
            if x not in seen:
                seen.append(x)
        ev = seen[:2]
        themes = [{"title": "Deadlines", "description": "Unclear due dates.", "evidence": ev}] if ev else []
        sugg = [{"text": "Add a weekly digest.", "basis": "ai", "evidence": []}]
        if ev:
            sugg.insert(0, {"text": "Show due dates on the dashboard.", "basis": "feedback", "evidence": ev[:1]})
        return json.dumps({"summary": "Students want clearer deadlines.", "themes": themes, "suggestions": sugg})

    def complete(self, messages, *, max_tokens, caller_id, timeout_seconds=None,
                 max_reply_chars=None, reasoning_effort=None):
        c = Call(list(messages), max_tokens, caller_id, timeout_seconds, max_reply_chars, reasoning_effort)
        with self.lock:
            self.calls.append(c)
            n = len(self.calls)
        if self.gate is not None:
            self.entered.set()
            assert self.gate.wait(40), "test gate never released"
        step = self.script.get(n)
        if isinstance(step, BaseException):
            raise step
        if isinstance(step, LlmReply):
            return step
        text = step(c) if callable(step) else (step if step is not None else self.default_text(c))
        return LlmReply(text=text, finish_reason="stop", prompt_tokens=10, completion_tokens=5)

    def of(self, kind):
        return [c for c in self.calls if c.kind == kind]


def install(fake):
    app.dependency_overrides[llm_client.get_llm_client] = lambda: fake


def uninstall():
    app.dependency_overrides.pop(llm_client.get_llm_client, None)


# ---- data seeding (direct inserts into the verified ADM-02 tables; same columns the ADM-04 tests use) ----

T0 = datetime(2030, 1, 1, 9, 0, tzinfo=timezone.utc)


def qdef(kind, prompt=None, options=("First", "Second"), scale=(1, 5), required=False):
    q = question(kind, required)
    q["prompt"] = prompt or f"Prompt {kind} {uid()[:6]}"
    if kind in ("multiple_choice", "dropdown", "checkbox"):
        q["options"] = [{"id": uid(), "label": label} for label in options]
    if kind == "linear_scale":
        q["scale"] = {"min": scale[0], "max": scale[1], "min_label": "Low", "max_label": "High"}
    return q


def ans(q, value):
    return {"question_id": q["id"], "value": value}


def snapshot_of(form):
    return {"title": form["title"], "description": form.get("description", ""),
            "association": form.get("association"), "questions": form["questions"]}


def seed(admin, questions, rows, form=None):
    """rows: dicts with answers (list), optional submitted_at, name, snapshot. Returns (form, response ids)."""
    form = form or created(admin, payload(questions))
    ids = []
    with psycopg.connect(psycopg_url(), autocommit=True) as conn:
        for i, r in enumerate(rows):
            rid, user = str(uuid.uuid4()), "a3u-" + uuid.uuid4().hex
            SEEDED_USERS.append(user)
            name = r.get("name", f"Resp {i}")
            conn.execute(
                'INSERT INTO "user" (id,display_name,role,email,password_hash,access_status) '
                "SELECT %s,%s,'student',%s,password_hash,'enabled' FROM \"user\" WHERE id='demo-admin'",
                (user, name, f"{user}@example.com"))
            conn.execute(
                "INSERT INTO feedback_recipients(form_id,user_id,display_name_snapshot,role_snapshot,inbox_id,read_at) "
                "VALUES (%s,%s,%s,'student',%s,NULL)", (form["id"], user, name[:200], str(uuid.uuid4())))
            conn.execute(
                "INSERT INTO feedback_responses(id,form_id,user_id,display_name_snapshot,submitted_at,form_snapshot,answers) "
                "VALUES (%s,%s,%s,%s,%s,%s,%s)",
                (rid, form["id"], user, name, r.get("submitted_at", T0 + timedelta(minutes=i)),
                 Jsonb(r.get("snapshot") or snapshot_of(form)), Jsonb(r["answers"])))
            ids.append(rid)
    return form, ids


def text_rows(form, n, text=lambda i: f"unique feedback number {i} about topic {i * 7}", start=0):
    q = next(x for x in form["questions"] if x["type"] in ("short_answer", "paragraph"))
    return [{"answers": [ans(q, text(start + i))]} for i in range(n)]


def text_form(admin, n, **kw):
    form = created(admin, payload([qdef("paragraph", "What should change?")]))
    return seed(admin, None, text_rows(form, n, **kw), form=form)


# ---- requests ----

def body_for(form, ids=None, select_all=False, expected=None, request_id=None, **extra):
    b = {"form_id": form["id"] if isinstance(form, dict) else form, "request_id": request_id or uid()}
    if select_all:
        b["select_all"] = True
        if expected is not None:
            b["expected_count"] = expected
    else:
        b["response_ids"] = list(ids or [])
    b.update(extra)
    return b


def create(admin, form, ids=None, **kw):
    return call("POST", BASE, admin, body_for(form, ids, **kw))


def get(admin, aid):
    return call("GET", f"{BASE}/{aid}", admin)


def listing(admin, query=""):
    r = call("GET", BASE + query, admin)
    assert r.status_code == 200, r.text
    return r.json()


def wait_done(admin, aid, timeout=40):
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        r = get(admin, aid)
        assert r.status_code == 200, r.text
        if r.json()["ai"]["status"] != "running":
            return r.json()
        time.sleep(0.05)
    raise AssertionError("analysis still running")


def run(admin, form, ids=None, **kw):
    r = create(admin, form, ids, **kw)
    assert r.status_code == 201, r.text
    return wait_done(admin, r.json()["id"])


def start_blocked(admin, llm, form, ids=None, **kw):
    """POST while the fake holds its first call. Returns (future of the POST, analysis id)."""
    llm.gate = threading.Event()
    fut = POOL.submit(create, admin, form, ids, **kw)
    assert llm.entered.wait(30), "the AI job never reached the LLM"
    items = listing(admin)["items"]
    assert items and items[0]["ai_status"] == "running"
    return fut, items[0]["id"]


def release(llm, fut):
    llm.gate.set()
    return fut.result(60)


def expect(r, status, code, message=None):
    assert r.status_code == status, r.text
    d = r.json()["detail"]
    assert d["code"] == code, r.text
    if message is not None:
        assert d["message"] == message, d["message"]
    return d


def row_count(aid):
    return sql("SELECT count(*) FROM feedback_analyses WHERE id=%s", (aid,))[0][0]


def table_counts():
    return tuple(sql("SELECT count(*) FROM " + t)[0][0] for t in ("feedback_forms", "feedback_responses"))
