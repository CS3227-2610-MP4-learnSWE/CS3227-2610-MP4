"""Neutral reference implementation of the STU-02 contract, used only for mutation testing.

Set MUTANT to one of the names in MUTANTS to switch on a single planted bug.
"""
import json
import os
import secrets
import threading

from fastapi import FastAPI, Header, HTTPException, Request

MUTANT = os.environ.get("MUTANT", "")
MUTANTS = {
    "leak_explanation_in_set": "Set response includes each question's explanation",
    "no_owner_check": "Any student can use any attempt",
    "owner_403": "Another student's attempt gives 403 (reveals it exists) instead of 404",
    "anonymous_student": "Missing X-Student-Id is accepted as 'anonymous'",
    "replace_not_merge": "Saving replaces all answers instead of merging",
    "no_question_check": "Unknown question ids are accepted",
    "no_choice_check": "Choices that do not belong to the question are accepted",
    "partial_save": "A rejected save still stores its valid answers",
    "save_after_submit": "Answers can be changed after submission",
    "double_submit": "An attempt can be submitted twice",
    "accept_incomplete": "Submitting with questions unanswered is accepted",
    "wrong_missing": "The missing list is not in set order",
    "client_score": "A score sent by the client is trusted",
    "results_before_submit": "Results are shown before submission",
    "score_wrong": "Score counts one extra correct answer",
    "results_mark_all_correct": "Results report every answer as correct",
    "leak_key_in_incomplete": "The 'incomplete' error message reveals the correct answers",
    "leak_in_403": "The not_submitted error body includes the saved answers' correctness",
    "set_has_key_version": "Set response includes key_version",
    "distinguishable_404": "Another student's attempt gives a different 404 body than an unknown one",
    "sequential_ids": "Attempt ids are sequential numbers (guessable)",
    "short_ids": "Attempt ids are 4 characters",
    "whitespace_student": "A whitespace-only X-Student-Id is accepted",
    "case_insensitive_owner": "Ownership ignores letter case",
    "empty_save_rejected": "Saving {} is rejected instead of being a no-op",
    "missing_includes_answered": "The missing list includes answered questions",
    "order_422_before_404": "Body errors are checked before ownership",
    "submit_ignores_saved": "Submit scores the submitted body's answers, not the saved ones",
    "no_lock": "Save and submit are not atomic (race)",
}

app = FastAPI()
QUESTIONS = [
    ("q1", "What should a well-designed function have?", None, [("a", "A single, focused responsibility"), ("b", "As many responsibilities as possible"), ("c", "No descriptive name")], "a", "One focused responsibility makes a function easier to understand, test and change."),
    ("q2", "Why do we keep automated tests alongside our code?", None, [("a", "To make the repository larger"), ("b", "To catch regressions when code changes"), ("c", "To avoid ever reviewing code")], "b", "Tests protect expected behaviour and can catch regressions introduced by later changes."),
    ("q3", "What does this Python code print?", "values = [1, 2, 3]\nprint(len(values))", [("a", "2"), ("b", "4"), ("c", "3")], "c", "len returns the number of items. The list contains three items."),
]
KEY = {q[0]: q[4] for q in QUESTIONS}
ATTEMPTS: dict = {}
LOCK = threading.Lock()


class _Null:
    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


@app.get("/api/health")
def health():
    return {"status": "ok"}


@app.get("/api/health/ready")
def ready():
    return {"status": "ready"}


def err(status, code, message="error", **extra):
    raise HTTPException(status, {"code": code, "message": message, **extra})


def student_of(header):
    s = (header or "") if MUTANT == "whitespace_student" else (header or "").strip()
    if not s:
        if MUTANT == "anonymous_student":
            return "anonymous"
        err(401, "missing_student")
    return s


def owned(aid, student):
    a = ATTEMPTS.get(aid)
    if a is None:
        err(404, "attempt_not_found")
    same = a["owner"].lower() == student.lower() if MUTANT == "case_insensitive_owner" else a["owner"] == student
    if not same and MUTANT != "no_owner_check":
        if MUTANT == "distinguishable_404":
            err(404, "attempt_not_found", "This attempt belongs to another student.")
        err(403 if MUTANT == "owner_403" else 404, "forbidden" if MUTANT == "owner_403" else "attempt_not_found")
    return a


def score(answers):
    n = sum(answers.get(q) == k for q, k in KEY.items())
    return {"correct": min(n + 1, 3) if MUTANT == "score_wrong" else n, "total": 3}


@app.get("/api/practice-sets/{set_id}")
def get_set(set_id: str):
    if set_id != "intro-se-1":
        err(404, "set_not_found")
    qs = []
    for qid, text, code, choices, _, expl in QUESTIONS:
        item = {"id": qid, "text": text, "code": code, "choices": [{"id": c, "text": t} for c, t in choices]}
        if MUTANT == "leak_explanation_in_set":
            item["explanation"] = expl
        qs.append(item)
    out = {"id": set_id, "title": "Software engineering basics", "questions": qs}
    if MUTANT == "set_has_key_version":
        out["key_version"] = "v1"
    return out


@app.post("/api/practice-sets/{set_id}/attempts", status_code=201)
def start(set_id: str, x_student_id: str | None = Header(None)):
    student = student_of(x_student_id)
    if set_id != "intro-se-1":
        err(404, "set_not_found")
    aid = str(len(ATTEMPTS) + 1) if MUTANT == "sequential_ids" else secrets.token_urlsafe(2)[:4] if MUTANT == "short_ids" else secrets.token_urlsafe(16)
    ATTEMPTS[aid] = {"owner": student, "set": set_id, "status": "in_progress", "answers": {}}
    return {"attempt_id": aid, "set_id": set_id, "status": "in_progress", "answers": {}}


@app.get("/api/attempts/{aid}")
def show(aid: str, x_student_id: str | None = Header(None)):
    a = owned(aid, student_of(x_student_id))
    return {"attempt_id": aid, "set_id": a["set"], "status": a["status"], "answers": dict(a["answers"])}


@app.put("/api/attempts/{aid}/answers")
async def save(aid: str, request: Request, x_student_id: str | None = Header(None)):
    student = student_of(x_student_id)
    raw = await request.body()
    if MUTANT == "order_422_before_404":
        try:
            pre = json.loads(raw)
        except ValueError:
            pre = None
        if not isinstance(pre, dict) or not isinstance(pre.get("answers"), dict):
            err(422, "invalid_body")
    with (LOCK if MUTANT != "no_lock" else _Null()):
        a = owned(aid, student)
        if a["status"] == "submitted" and MUTANT != "save_after_submit":
            err(409, "already_submitted")
        try:
            body = json.loads(raw)
        except (ValueError, RecursionError):
            body = None
        answers = body.get("answers") if isinstance(body, dict) else None
        if not isinstance(answers, dict):
            err(422, "invalid_body")
        if not answers and MUTANT == "empty_save_rejected":
            err(422, "invalid_body")
        valid = {}
        problem = None
        for q, c in answers.items():
            if q not in KEY and MUTANT != "no_question_check":
                problem = problem or "unknown_question"
                continue
            choices = {cid for qq, _, _, ch, _, _ in QUESTIONS if qq == q for cid, _ in ch}
            if q in KEY and c not in choices and MUTANT != "no_choice_check":
                problem = problem or "invalid_choice"
                continue
            valid[q] = c
        if problem:
            if MUTANT == "partial_save":
                a["answers"].update(valid)
            err(422, problem)
        if MUTANT == "replace_not_merge":
            a["answers"] = dict(valid)
        else:
            a["answers"].update(valid)
        return {"attempt_id": aid, "status": "in_progress", "answers": dict(a["answers"])}


@app.post("/api/attempts/{aid}/submit")
async def submit(aid: str, request: Request, x_student_id: str | None = Header(None)):
    student = student_of(x_student_id)
    raw = await request.body()
    with (LOCK if MUTANT != "no_lock" else _Null()):
        a = owned(aid, student)
        if a["status"] == "submitted" and MUTANT != "double_submit":
            err(409, "already_submitted")
        missing = list(KEY) if MUTANT == "missing_includes_answered" else [q for q in KEY if q not in a["answers"]]
        if MUTANT == "wrong_missing":
            missing = list(reversed(missing))
        if [q for q in KEY if q not in a["answers"]] and MUTANT != "accept_incomplete":
            if MUTANT == "leak_key_in_incomplete":
                err(422, "incomplete", f"Answer all questions (q1 is a, q2 is b, q3 is c).", missing=missing)
            err(422, "incomplete", missing=missing)
        a["status"] = "submitted"
        s = score(a["answers"])
        if MUTANT == "submit_ignores_saved":
            try:
                sent = json.loads(raw or b"{}").get("answers")
                if isinstance(sent, dict):
                    s = score(sent)
            except (ValueError, AttributeError):
                pass
        if MUTANT == "client_score":
            try:
                sent = json.loads(raw or b"{}").get("score")
                if isinstance(sent, dict):
                    s = sent
            except (ValueError, AttributeError):
                pass
        a["score"] = s
        return {"attempt_id": aid, "status": "submitted", "score": s}


@app.get("/api/attempts/{aid}/results")
def results(aid: str, x_student_id: str | None = Header(None)):
    a = owned(aid, student_of(x_student_id))
    if a["status"] != "submitted" and MUTANT != "results_before_submit":
        if MUTANT == "leak_in_403":
            err(403, "not_submitted", correct={q: a["answers"].get(q) == k for q, k in KEY.items()})
        err(403, "not_submitted")
    ans = a["answers"]
    qs = [{"id": q, "selected": ans.get(q), "correct_choice": k, "correct": True if MUTANT == "results_mark_all_correct" else ans.get(q) == k, "explanation": e}
          for q, _, _, _, k, e in QUESTIONS]
    return {"attempt_id": aid, "set_id": a["set"], "key_version": "v1", "score": a.get("score") or score(ans), "answers": dict(ans), "questions": qs}
