"""Reference implementation of the STU-02 practice attempt API, with planted bugs.

Clean behaviour is the default. Set the environment variable MUTANT=<name> to switch
on exactly one planted bug (see MUTANTS). Single file on purpose.
"""
import asyncio
import itertools
import json
import os
import secrets

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

M = os.environ.get("MUTANT", "")

MUTANTS = {
    "no_ownership_check": "Any student can read, change, submit and fetch results of any attempt.",
    "results_before_submit": "Results are returned for unsubmitted attempts (no 403).",
    "leak_set_correct": "GET set marks the correct choice (choice.correct = true).",
    "leak_set_explanation": "GET set includes the explanation for each question.",
    "leak_put_key_version": "PUT answers response includes key_version.",
    "leak_error_invalid_choice": "invalid_choice error message states the correct answer.",
    "leak_error_incomplete_explanation": "incomplete error message includes a hint copied from the explanation.",
    "leak_attempt_get_score": "GET attempt (in progress) includes a running score (reveals correctness).",
    "leak_query_debug": "GET attempt?debug=1 returns the answer key (backdoor).",
    "admin_bypass": "Student id 'admin' bypasses ownership and the not_submitted gate.",
    "not_owned_403": "Another student's attempt gives 403 instead of 404 (reveals existence).",
    "not_owned_distinct_message": "404 for another student's attempt has a different message than for a missing one.",
    "echo_student_in_404": "404 attempt_not_found message echoes the caller's student id.",
    "sequential_ids": "Attempt ids are zero-padded sequential integers (8 digits).",
    "short_ids": "Attempt ids are only 6 characters long.",
    "id_embeds_student": "Attempt id embeds the student id.",
    "id_prefix_match": "An attempt id is resolved by prefix, so its first 8 characters work.",
    "id_case_insensitive": "Attempt ids are matched case-insensitively.",
    "order_422_before_404": "Body validation (422) runs before ownership/existence (404).",
    "order_422_before_409": "Body validation (422) runs before the submitted-state check (409).",
    "order_404_before_401": "Unknown attempt id gives 404 even when the student header is missing.",
    "order_403_before_404": "Results for someone else's unsubmitted attempt give 403 not 404.",
    "order_409_before_404": "Saving to someone else's submitted attempt gives 409 not 404.",
    "missing_reversed": "The 'missing' list is in reverse set order.",
    "incomplete_no_missing": "The incomplete error has no 'missing' field.",
    "client_score_trusted": "A score sent in the submit body replaces the computed score.",
    "submit_body_fills_answers": "Answers sent in the submit body are merged into the attempt before checking.",
    "partial_save_on_reject": "Valid entries before an invalid one are kept when a request is rejected.",
    "submit_allows_incomplete": "Submit succeeds with unanswered questions (counted wrong).",
    "double_submit_ok": "A second submit returns 200 again instead of 409.",
    "save_after_submit_ok": "Answers can still be changed after submission.",
    "failed_submit_locks": "A rejected (incomplete) submit still marks the attempt submitted.",
    "failed_submit_clears_answers": "A rejected (incomplete) submit wipes the saved answers.",
    "non_atomic_submit": "Submit checks state, yields, then writes: concurrent submits can all succeed.",
    "non_atomic_save": "Save checks state in the route, then writes later without re-checking.",
    "lost_update_save": "Save merges onto a stale snapshot: concurrent saves lose updates.",
    "replace_answers": "PUT replaces all saved answers instead of merging.",
    "student_lower": "Student ids are lower-cased, so 'Alice' is 'alice'.",
    "student_strip": "Student ids are stripped, so ' alice ' is 'alice'.",
    "empty_header_ok": "An empty X-Student-Id is accepted as a student.",
    "set_requires_header": "Reading a set demands the student header (401 without).",
    "start_no_header": "Starting an attempt without a header works (anonymous student).",
    "start_unknown_set_ok": "Starting an attempt on an unknown set returns 201.",
    "start_reuses_attempt": "Starting again returns the student's existing in-progress attempt.",
    "accept_unknown_choice": "Any string is accepted as a choice id.",
    "accept_unknown_question": "Unknown question ids are accepted and saved.",
    "null_answer_accepted": "A null answer value is silently accepted (200) and ignored.",
    "type_500": "Non-object bodies / wrong-typed 'answers' crash with a 500.",
    "status_trust_put": "A 'status' field in the PUT body can mark the attempt submitted.",
    "error_shape_flat_409": "409 errors use {\"detail\": \"text\"} instead of the code/message object.",
    "error_shape_no_message_401": "401 errors omit 'message'.",
    "incomplete_status_400": "The incomplete error returns status 400 instead of 422.",
    "score_ignores_q1": "Scoring never counts q1 (off-by-one over the questions).",
    "results_reversed": "Results questions are in reverse set order.",
    "results_correct_always_true": "Results 'correct' flag is true whenever an answer exists.",
    "results_explanation_swapped": "Results swap the explanations of q2 and q3.",
    "results_no_key_version": "Results omit key_version.",
    "delete_attempt_route": "DELETE /api/attempts/{id} exists and deletes the attempt.",
    "list_attempts_route": "GET /api/practice-sets/{id}/attempts lists every student's attempt ids.",
    "start_status_200": "Starting an attempt returns 200 instead of 201.",
    "set_case_insensitive": "Set ids are matched case-insensitively.",
    "traceback_in_error": "Malformed-body errors expose the exception class name.",
}
if M and M not in MUTANTS:
    raise RuntimeError(f"unknown mutant {M!r}")

# ---------------------------------------------------------------- fixture
SET_ID = "intro-se-1"
TITLE = "Software engineering basics"
QUESTIONS = [
    {
        "id": "q1",
        "text": "What should a well-designed function have?",
        "code": None,
        "choices": [
            {"id": "a", "text": "A single, focused responsibility"},
            {"id": "b", "text": "As many responsibilities as possible"},
            {"id": "c", "text": "No descriptive name"},
        ],
        "correct": "a",
        "explanation": "One focused responsibility makes a function easier to understand, test and change.",
    },
    {
        "id": "q2",
        "text": "Why do we keep automated tests alongside our code?",
        "code": None,
        "choices": [
            {"id": "a", "text": "To make the repository larger"},
            {"id": "b", "text": "To catch regressions when code changes"},
            {"id": "c", "text": "To avoid ever reviewing code"},
        ],
        "correct": "b",
        "explanation": "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    },
    {
        "id": "q3",
        "text": "What does this Python code print?",
        "code": "values = [1, 2, 3]\nprint(len(values))",
        "choices": [
            {"id": "a", "text": "2"},
            {"id": "b", "text": "4"},
            {"id": "c", "text": "3"},
        ],
        "correct": "c",
        "explanation": "len returns the number of items. The list contains three items.",
    },
]
QIDS = [q["id"] for q in QUESTIONS]
QBY = {q["id"]: q for q in QUESTIONS}
KEY_VERSION = "v1"

ATTEMPTS: dict = {}
_counter = itertools.count(1)

app = FastAPI()


class ApiError(Exception):
    def __init__(self, status, code, message, **extra):
        self.status, self.code, self.message, self.extra = status, code, message, extra


@app.exception_handler(ApiError)
async def _api_error(request, exc):
    detail = {"code": exc.code, "message": exc.message, **exc.extra}
    if M == "error_shape_flat_409" and exc.status == 409:
        return JSONResponse(status_code=409, content={"detail": exc.message})
    if M == "error_shape_no_message_401" and exc.status == 401:
        detail.pop("message")
    return JSONResponse(status_code=exc.status, content={"detail": detail})


@app.get("/health")
async def health():
    return {"status": "ok"}


# ---------------------------------------------------------------- helpers
def need_student(request: Request) -> str:
    vals = request.headers.getlist("x-student-id")
    if M == "empty_header_ok":
        if not vals:
            raise ApiError(401, "missing_student", "X-Student-Id header is required.")
        return vals[0]
    if len(vals) != 1 or vals[0].strip() == "":
        raise ApiError(401, "missing_student", "X-Student-Id header is required.")
    v = vals[0]
    if M == "student_strip":
        v = v.strip()
    if M == "student_lower":
        v = v.lower()
    return v


def find(aid):
    a = ATTEMPTS.get(aid)
    if a is None and M == "id_prefix_match" and len(aid) >= 8:
        for k, v in ATTEMPTS.items():
            if k.startswith(aid):
                return v
    if a is None and M == "id_case_insensitive":
        for k, v in ATTEMPTS.items():
            if k.lower() == aid.lower():
                return v
    return a


def auth(request, aid=None):
    if M == "order_404_before_401" and aid is not None and find(aid) is None:
        raise ApiError(404, "attempt_not_found", "Attempt not found.")
    return need_student(request)


def owned(aid, sid):
    a = find(aid)
    if a is not None and M == "no_ownership_check":
        return a
    if a is not None and M == "admin_bypass" and sid == "admin":
        return a
    if a is None:
        msg = "Attempt not found."
        if M == "echo_student_in_404":
            msg = f"Attempt not found for student {sid}."
        raise ApiError(404, "attempt_not_found", msg)
    if a["owner"] != sid:
        if M == "not_owned_403":
            raise ApiError(403, "forbidden", "This attempt belongs to another student.")
        if M == "not_owned_distinct_message":
            raise ApiError(404, "attempt_not_found", "Attempt belongs to another student.")
        msg = "Attempt not found."
        if M == "echo_student_in_404":
            msg = f"Attempt not found for student {sid}."
        raise ApiError(404, "attempt_not_found", msg)
    return a


def new_id(sid):
    if M == "sequential_ids":
        return f"{next(_counter):08d}"
    if M == "short_ids":
        return secrets.token_hex(3)
    if M == "id_embeds_student":
        return f"{sid}-{secrets.token_hex(4)}"
    return secrets.token_urlsafe(12)


def compute(a):
    qs = QUESTIONS[1:] if M == "score_ignores_q1" else QUESTIONS
    correct = sum(1 for q in qs if a["answers"].get(q["id"]) == q["correct"])
    total = len(QUESTIONS)
    return {"correct": correct, "total": total}


def view(a, request=None):
    out = {"attempt_id": a["id"], "set_id": a["set_id"], "status": a["status"], "answers": dict(a["answers"])}
    if M == "leak_attempt_get_score" and a["status"] == "in_progress":
        out["score"] = compute(a)
    if M == "leak_query_debug" and request is not None and request.query_params.get("debug"):
        out["correct_choice"] = {q["id"]: q["correct"] for q in QUESTIONS}
    return out


def public_set():
    qs = []
    for q in QUESTIONS:
        item = {"id": q["id"], "text": q["text"], "code": q["code"], "choices": [dict(c) for c in q["choices"]]}
        if M == "leak_set_explanation":
            item["explanation"] = q["explanation"]
        if M == "leak_set_correct":
            for c in item["choices"]:
                c["correct"] = c["id"] == q["correct"]
        qs.append(item)
    return {"id": SET_ID, "title": TITLE, "questions": qs}


def set_key(set_id):
    return set_id.lower() if M == "set_case_insensitive" else set_id


def parse_answers(raw, a=None):
    try:
        body = json.loads(raw)
    except (ValueError, RecursionError) as e:
        msg = "Request body must be valid JSON."
        if M == "traceback_in_error":
            msg = f"Invalid JSON: {type(e).__name__}: {e}"
        raise ApiError(422, "invalid_body", msg)
    if M == "type_500":
        answers = body["answers"]
        answers.items  # AttributeError for non-dicts -> 500
    else:
        if not isinstance(body, dict) or not isinstance(body.get("answers"), dict):
            raise ApiError(422, "invalid_body", "Body must be an object with an 'answers' object.")
        answers = body["answers"]
    new = {}
    for q, c in answers.items():
        if c is None and M == "null_answer_accepted":
            continue
        if q not in QBY and M != "accept_unknown_question":
            raise ApiError(422, "unknown_question", "Unknown question.")
        valid = {x["id"] for x in QBY[q]["choices"]} if q in QBY else {"a", "b", "c"}
        ok = isinstance(c, str) if M == "accept_unknown_choice" else (isinstance(c, str) and c in valid)
        if not ok:
            msg = f"Choice is not valid for question {q}."
            if M == "leak_error_invalid_choice" and q in QBY:
                msg += f" The correct answer is {QBY[q]['correct']}."
            raise ApiError(422, "invalid_choice", msg)
        new[q] = c
        if M == "partial_save_on_reject" and a is not None:
            a["answers"][q] = c
    return new, body


# ---------------------------------------------------------------- routes
@app.get("/api/practice-sets/{set_id}")
async def get_set(set_id: str, request: Request):
    if M == "set_requires_header":
        need_student(request)
    if set_key(set_id) != SET_ID:
        raise ApiError(404, "set_not_found", "Practice set not found.")
    return JSONResponse(public_set())


@app.post("/api/practice-sets/{set_id}/attempts")
async def start(set_id: str, request: Request):
    if M == "start_no_header":
        vals = request.headers.getlist("x-student-id")
        sid = vals[0] if vals and vals[0] else "anonymous"
    else:
        sid = need_student(request)
    if set_key(set_id) != SET_ID and M != "start_unknown_set_ok":
        raise ApiError(404, "set_not_found", "Practice set not found.")
    code = 200 if M == "start_status_200" else 201
    if M == "start_reuses_attempt":
        for a in ATTEMPTS.values():
            if a["owner"] == sid and a["status"] == "in_progress":
                return JSONResponse(view(a), status_code=code)
    aid = new_id(sid)
    a = {"id": aid, "owner": sid, "set_id": set_id if M == "start_unknown_set_ok" else SET_ID,
         "status": "in_progress", "answers": {}}
    ATTEMPTS[aid] = a
    return JSONResponse(view(a), status_code=code)


@app.get("/api/attempts/{aid}")
async def get_attempt(aid: str, request: Request):
    sid = auth(request, aid)
    a = owned(aid, sid)
    return JSONResponse(view(a, request))


async def do_save(a, raw):
    """State check, validation and write in one step with no await in between."""
    if M == "non_atomic_save":
        pass  # the state check was done earlier, in the route
    elif a["status"] == "submitted" and M != "save_after_submit_ok":
        raise ApiError(409, "already_submitted", "Attempt already submitted.")
    new, body = parse_answers(raw, a)
    if M == "lost_update_save":
        snap = dict(a["answers"])
        await asyncio.sleep(0.01)
        a["answers"] = {**snap, **new}
    elif M == "replace_answers":
        a["answers"] = dict(new)
    else:
        a["answers"].update(new)
    if M == "status_trust_put" and isinstance(body, dict) and body.get("status") == "submitted":
        a["status"] = "submitted"
    out = {"attempt_id": a["id"], "status": "in_progress", "answers": dict(a["answers"])}
    if M == "status_trust_put":
        out["status"] = a["status"]
    if M == "save_after_submit_ok":
        out["status"] = "in_progress"
    if M == "leak_put_key_version":
        out["key_version"] = KEY_VERSION
    return JSONResponse(out)


@app.put("/api/attempts/{aid}/answers")
async def put_answers(aid: str, request: Request):
    sid = auth(request, aid)
    raw = await request.body()
    if M == "order_422_before_404":
        parse_answers(raw)
    if M == "order_409_before_404":
        a0 = find(aid)
        if a0 is not None and a0["status"] == "submitted":
            raise ApiError(409, "already_submitted", "Attempt already submitted.")
    a = owned(aid, sid)
    if M == "order_422_before_409":
        parse_answers(raw)
    if M == "non_atomic_save":
        if a["status"] == "submitted":
            raise ApiError(409, "already_submitted", "Attempt already submitted.")
        await asyncio.sleep(0.01)
    return await do_save(a, raw)


async def do_submit(a, raw):
    claimed = {}
    try:
        c = json.loads(raw) if raw else {}
        claimed = c if isinstance(c, dict) else {}
    except (ValueError, RecursionError):
        claimed = {}
    if a["status"] == "submitted":
        if M == "double_submit_ok":
            return JSONResponse({"attempt_id": a["id"], "status": "submitted", "score": a["score"]})
        raise ApiError(409, "already_submitted", "Attempt already submitted.")
    if M == "non_atomic_submit":
        await asyncio.sleep(0.01)
    if M == "submit_body_fills_answers" and isinstance(claimed.get("answers"), dict):
        a["answers"].update(claimed["answers"])
    missing = [q for q in QIDS if q not in a["answers"]]
    if M == "missing_reversed":
        missing.reverse()
    if missing and M != "submit_allows_incomplete":
        if M == "failed_submit_locks":
            a["status"] = "submitted"
        if M == "failed_submit_clears_answers":
            a["answers"].clear()
        msg = "All questions must be answered before submitting."
        if M == "leak_error_incomplete_explanation":
            msg += f" Hint for {missing[0]}: {QBY[missing[0]]['explanation']}"
        extra = {} if M == "incomplete_no_missing" else {"missing": missing}
        raise ApiError(400 if M == "incomplete_status_400" else 422, "incomplete", msg, **extra)
    score = compute(a)
    if M == "client_score_trusted" and isinstance(claimed.get("score"), dict):
        score = claimed["score"]
    a["status"] = "submitted"
    a["score"] = score
    return JSONResponse({"attempt_id": a["id"], "status": "submitted", "score": score})


@app.post("/api/attempts/{aid}/submit")
async def submit(aid: str, request: Request):
    sid = auth(request, aid)
    raw = await request.body()
    a = owned(aid, sid)
    return await do_submit(a, raw)


@app.get("/api/attempts/{aid}/results")
async def results(aid: str, request: Request):
    sid = auth(request, aid)
    if M == "order_403_before_404":
        a0 = find(aid)
        if a0 is not None and a0["status"] != "submitted":
            raise ApiError(403, "not_submitted", "Attempt has not been submitted.")
    a = owned(aid, sid)
    bypass = (M == "results_before_submit") or (M == "admin_bypass" and sid == "admin")
    if a["status"] != "submitted" and not bypass:
        raise ApiError(403, "not_submitted", "Attempt has not been submitted.")
    score = a.get("score") or compute(a)
    items = []
    for q in QUESTIONS:
        sel = a["answers"].get(q["id"])
        correct = sel == q["correct"]
        if M == "results_correct_always_true":
            correct = sel is not None
        items.append({"id": q["id"], "selected": sel, "correct_choice": q["correct"],
                      "correct": correct, "explanation": q["explanation"]})
    if M == "results_explanation_swapped":
        items[1]["explanation"], items[2]["explanation"] = items[2]["explanation"], items[1]["explanation"]
    if M == "results_reversed":
        items.reverse()
    out = {"attempt_id": a["id"], "set_id": a["set_id"], "key_version": KEY_VERSION,
           "score": score, "answers": dict(a["answers"]), "questions": items}
    if M == "results_no_key_version":
        out.pop("key_version")
    return JSONResponse(out)


if M == "delete_attempt_route":
    @app.delete("/api/attempts/{aid}")
    async def delete_attempt(aid: str, request: Request):
        sid = auth(request, aid)
        a = owned(aid, sid)
        del ATTEMPTS[a["id"]]
        return JSONResponse({"deleted": True})

if M == "list_attempts_route":
    @app.get("/api/practice-sets/{set_id}/attempts")
    async def list_attempts(set_id: str, request: Request):
        need_student(request)
        return JSONResponse({"attempts": [{"attempt_id": k, "status": v["status"]} for k, v in ATTEMPTS.items()]})
