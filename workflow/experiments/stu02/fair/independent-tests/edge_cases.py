"""Edge-case battery for the STU-02 practice attempt API (designed from spec.md and plan.md only).

Usage: python edge_cases.py <app_dir> [--slow MODULE:ATTR] [--list]
Prints one JSON list: [{id, category, kind, scenario, expected, result, detail}].
"""
import argparse
import asyncio
import contextlib
import functools
import importlib
import inspect
import json
import os
import random
import re
import sys
import traceback
import uuid

import httpx

# ----------------------------------------------------------------- fixture knowledge (from spec)
QIDS = ["q1", "q2", "q3"]
KEY = {"q1": "a", "q2": "b", "q3": "c"}
EXPL = {
    "q1": "One focused responsibility makes a function easier to understand, test and change.",
    "q2": "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "q3": "len returns the number of items. The list contains three items.",
}
EXPL_SNIPS = ["easier to understand, test and change", "catch regressions introduced", "number of items",
              "focused responsibility makes", "tests protect expected", "len returns"]
TEXTS = {
    "q1": "What should a well-designed function have?",
    "q2": "Why do we keep automated tests alongside our code?",
    "q3": "What does this Python code print?",
}
CHOICES = {
    "q1": ["A single, focused responsibility", "As many responsibilities as possible", "No descriptive name"],
    "q2": ["To make the repository larger", "To catch regressions when code changes", "To avoid ever reviewing code"],
    "q3": ["2", "4", "3"],
}
CODE = {"q1": None, "q2": None, "q3": "values = [1, 2, 3]\nprint(len(values))"}
ALL_OK = {"q1": "a", "q2": "b", "q3": "c"}
ALL_BAD = {"q1": "b", "q2": "a", "q3": "a"}
MIX2 = {"q1": "a", "q2": "b", "q3": "a"}
SET = "intro-se-1"
LEAK_KEYS = {"correct_choice", "explanation", "key_version", "correct_answer", "correct_answers", "answer_key",
             "correct_option", "solution", "is_correct", "answer"}

CAT_WHY = {
    "identity": "The header is the only identity; every access decision rests on reading it exactly and strictly.",
    "set": "AC1: the set is the one public surface and must never carry the key.",
    "start": "AC2/AC10: attempt creation, unguessable ids, independence.",
    "save": "AC3: saving, merging, validation, atomic rejection and hostile bodies.",
    "submit": "AC4/AC5: completeness check, ordering of 'missing', server-side scoring.",
    "results": "AC7: what is released after submission and exactly when.",
    "lock": "AC6: nothing changes after submission.",
    "order": "Plan check order: 401, then 404, then 409/403, then 422. Wrong order leaks existence or state.",
    "cross-student": "AC9: no access to, and no knowledge of, other students' attempts.",
    "leak": "AC8: no key or explanation in any pre-submission response, including errors.",
    "errors": "Plan: one error body shape for every documented error.",
    "methods": "Unsupported methods must not mutate, expose or crash.",
    "concurrency": "Exactly-once submit and consistent state under simultaneous requests.",
    "state": "Read-your-writes and state-machine consistency.",
}

SCEN = []


def sc(id, cat, kind, scenario, expected):
    def deco(f):
        SCEN.append(dict(id=id, category=cat, kind=kind, scenario=scenario, expected=expected, fn=f))
        return f
    return deco


# ----------------------------------------------------------------- helpers
class Cx:
    def __init__(self, client, slow):
        self.c = client
        self.slow = slow

    async def req(self, method, path, sid=None, headers=None, **kw):
        if isinstance(headers, list):
            h = list(headers)
            if sid is not None:
                h.append(("X-Student-Id", sid))
        else:
            h = dict(headers or {})
            if sid is not None:
                h["X-Student-Id"] = sid
        return await self.c.request(method, path, headers=h, **kw)


def check(cond, msg):
    if not cond:
        raise AssertionError(msg)


def J(r):
    try:
        return r.json()
    except Exception:
        return None


def short(r):
    return f"{r.status_code} {r.text[:200]!r}"


def newsid(p="s"):
    return f"{p}-{uuid.uuid4().hex[:10]}"


def A(aid):
    return f"/api/attempts/{aid}"


async def mk(cx, sid=None, set_id=SET):
    sid = sid or newsid()
    r = await cx.req("POST", f"/api/practice-sets/{set_id}/attempts", sid)
    check(r.status_code == 201, f"setup: start attempt expected 201, got {short(r)}")
    return sid, J(r)["attempt_id"]


async def save(cx, sid, aid, answers, **kw):
    return await cx.req("PUT", A(aid) + "/answers", sid, json={"answers": answers}, **kw)


async def fill(cx, sid, aid, answers):
    r = await save(cx, sid, aid, answers)
    check(r.status_code == 200, f"setup: save expected 200, got {short(r)}")


async def submit(cx, sid, aid, **kw):
    return await cx.req("POST", A(aid) + "/submit", sid, **kw)


async def done(cx, answers=ALL_OK, sid=None):
    sid, aid = await mk(cx, sid)
    await fill(cx, sid, aid, answers)
    r = await submit(cx, sid, aid)
    check(r.status_code == 200, f"setup: submit expected 200, got {short(r)}")
    return sid, aid, J(r)


async def get_attempt(cx, sid, aid):
    r = await cx.req("GET", A(aid), sid)
    check(r.status_code == 200, f"GET attempt expected 200, got {short(r)}")
    return J(r)


def code_of(r):
    j = J(r)
    d = j.get("detail") if isinstance(j, dict) else None
    return d.get("code") if isinstance(d, dict) else None


def expect_err(r, status, code, label=""):
    check(r.status_code == status and code_of(r) == code,
          f"{label}expected {status} {code}, got {short(r)}")


def exp_score(ans):
    return sum(1 for q in QIDS if ans.get(q) == KEY[q])


def walk(o):
    if isinstance(o, dict):
        for k, v in o.items():
            yield ("key", k, v)
            yield from walk(v)
    elif isinstance(o, list):
        for v in o:
            yield from walk(v)
    elif isinstance(o, str):
        yield ("str", o, None)


def leak_problems(r):
    probs = []
    t = r.text.lower()
    for s in EXPL_SNIPS:
        if s.lower() in t:
            probs.append(f"explanation text '{s}'")
    if re.search(r"(correct|right)\s+(answer|choice|option)|answer\s+key", r.text, re.I):
        probs.append("phrase naming the correct answer/key")
    j = J(r)
    for kind, a, b in walk(j):
        if kind == "key" and (a in LEAK_KEYS or (a == "correct" and isinstance(b, bool))):
            probs.append(f"field '{a}'")
    return probs


def assert_noleak(r, label=""):
    p = leak_problems(r)
    check(not p, f"{label}leak in {r.request.method} {r.request.url.path} -> {short(r)}: {p}")


def shape(o):
    if isinstance(o, dict):
        return {k: shape(v) for k, v in o.items()}
    if isinstance(o, list):
        return [shape(v) for v in o]
    return type(o).__name__


def strict_ids(ids):
    return all(isinstance(i, str) for i in ids)


# ================================================================= IDENTITY
@sc("ID-01", "identity", "contract", "POST start attempt with no X-Student-Id header", "401 missing_student")
async def _(cx):
    expect_err(await cx.req("POST", f"/api/practice-sets/{SET}/attempts"), 401, "missing_student")


@sc("ID-02", "identity", "contract", "POST start attempt with an empty X-Student-Id header", "401 missing_student")
async def _(cx):
    expect_err(await cx.req("POST", f"/api/practice-sets/{SET}/attempts", ""), 401, "missing_student")


@sc("ID-03", "identity", "robustness", "Whitespace-only X-Student-Id ('   ', tab)",
    "No 5xx; either rejected 401/400, or accepted as an ordinary id that only that same value can use")
async def _(cx):
    for v in ["   ", "\t"]:
        r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", v)
        check(r.status_code in (201, 400, 401), f"{v!r}: got {short(r)}")
        if r.status_code == 201:
            aid = J(r)["attempt_id"]
            check((await cx.req("GET", A(aid), v)).status_code == 200, "same whitespace id cannot read own attempt")
            check((await cx.req("GET", A(aid), newsid())).status_code == 404, "other student read whitespace-id attempt")
            check((await cx.req("GET", A(aid))).status_code == 401, "no header read whitespace-id attempt")


@sc("ID-04", "identity", "contract", "Header name case: create with 'x-student-id', read with 'X-STUDENT-ID'",
    "HTTP header names are case-insensitive: both work as the same student")
async def _(cx):
    sid = newsid()
    r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", headers={"x-student-id": sid})
    check(r.status_code == 201, short(r))
    aid = J(r)["attempt_id"]
    r2 = await cx.req("GET", A(aid), headers={"X-STUDENT-ID": sid})
    check(r2.status_code == 200, short(r2))


@sc("ID-05", "identity", "robustness", "Padded ids: ' id', 'id ', '\\tid' are not the same student as 'id'",
    "404 (or 401); never 200")
async def _(cx):
    sid, aid = await mk(cx)
    for v in [" " + sid, sid + " ", "\t" + sid, sid + "\t"]:
        r = await cx.req("GET", A(aid), v)
        check(r.status_code in (401, 404), f"padded {v!r} got {short(r)}")
    # reverse direction
    padded = f" {newsid()} "
    r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", padded)
    if r.status_code == 201:
        aid2 = J(r)["attempt_id"]
        r2 = await cx.req("GET", A(aid2), padded.strip())
        check(r2.status_code in (401, 404), f"stripped id read padded-id attempt: {short(r2)}")


@sc("ID-06", "identity", "robustness", "Student ids differing only by case ('Alice' vs 'alice')",
    "Different students: 404 for the other-cased id")
async def _(cx):
    base = "Ab" + uuid.uuid4().hex[:8]
    sid, aid = await mk(cx, base)
    for v in [base.lower(), base.upper()]:
        check((await cx.req("GET", A(aid), v)).status_code == 404, f"{v} could read {base}'s attempt")


@sc("ID-07", "identity", "robustness", "Very long student id (100,000 chars)",
    "No 5xx; if accepted, the same id can use its attempt")
async def _(cx):
    sid = "L" * 100000
    r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", sid)
    check(r.status_code < 500, short(r))
    if r.status_code == 201:
        check((await cx.req("GET", A(J(r)["attempt_id"]), sid)).status_code == 200, "cannot read own attempt")


@sc("ID-08", "identity", "robustness", "Two X-Student-Id headers with different values",
    "No 5xx; 201/400/401; if accepted, a third student cannot read the attempt")
async def _(cx):
    a, b, c = newsid(), newsid(), newsid()
    r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", headers=[("X-Student-Id", a), ("X-Student-Id", b)])
    check(r.status_code in (201, 400, 401), short(r))
    if r.status_code == 201:
        check((await cx.req("GET", A(J(r)["attempt_id"]), c)).status_code == 404, "third student read it")


@sc("ID-09", "identity", "robustness", "Non-ASCII (UTF-8 bytes) in the student header",
    "No 5xx; if accepted, same bytes can read it and a different student cannot")
async def _(cx):
    raw = ("\u00e9\u5b66\u751f-" + uuid.uuid4().hex[:6]).encode("utf-8")
    r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", headers=[(b"x-student-id", raw)])
    check(r.status_code < 500, short(r))
    if r.status_code == 201:
        aid = J(r)["attempt_id"]
        check((await cx.req("GET", A(aid), headers=[(b"x-student-id", raw)])).status_code == 200, "own read failed")
        check((await cx.req("GET", A(aid), newsid())).status_code == 404, "other read it")


@sc("ID-10", "identity", "contract", "Existing attempt, no header, on GET attempt / PUT answers / submit / results",
    "401 missing_student on each; same for an empty header")
async def _(cx):
    sid, aid = await mk(cx)
    for hdr in (None, ""):
        for m, p, kw in [("GET", A(aid), {}), ("PUT", A(aid) + "/answers", {"json": {"answers": {"q1": "a"}}}),
                         ("POST", A(aid) + "/submit", {}), ("GET", A(aid) + "/results", {})]:
            expect_err(await cx.req(m, p, hdr, **kw), 401, "missing_student", f"{m} {p} hdr={hdr!r}: ")
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "unauthenticated PUT changed state")


@sc("ID-11", "identity", "contract", "GET set without header and with a header", "200 both, identical bodies")
async def _(cx):
    r1 = await cx.req("GET", f"/api/practice-sets/{SET}")
    r2 = await cx.req("GET", f"/api/practice-sets/{SET}", newsid())
    check(r1.status_code == 200 and r2.status_code == 200 and J(r1) == J(r2), f"{short(r1)} / {short(r2)}")


@sc("ID-12", "identity", "robustness", "Student ids that look like injection / wildcards ('*', \"' OR '1'='1\", '%', '..', 'admin', 'null')",
    "Treated as ordinary ids: 201 and only that id can read its attempt (admin/teacher get no special rights)")
async def _(cx):
    for v in ["*", "' OR '1'='1", "%", "..", "admin", "teacher", "null", "None", "0", "<script>alert(1)</script>"]:
        v = v + "-" + uuid.uuid4().hex[:4] if v in ("*", "%") else v
        r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", v)
        check(r.status_code == 201, f"id {v!r}: {short(r)}")
        aid = J(r)["attempt_id"]
        check((await cx.req("GET", A(aid), v)).status_code == 200, f"id {v!r} cannot read own attempt")
        other = await cx.req("GET", A(aid), newsid())
        check(other.status_code == 404, f"id {v!r}: stranger got {short(other)}")
    # wildcards must not match other students' attempts
    sid, aid = await mk(cx)
    for v in ["*", "%", "", ".*"]:
        if v == "":
            continue
        check((await cx.req("GET", A(aid), v)).status_code == 404, f"wildcard {v!r} read someone's attempt")


@sc("ID-13", "identity", "contract", "Unknown attempt id, no header, on all four attempt endpoints",
    "401 missing_student (header is checked before existence)")
async def _(cx):
    for m, p, kw in [("GET", "/api/attempts/doesnotexist1", {}),
                     ("PUT", "/api/attempts/doesnotexist1/answers", {"json": {"answers": {}}}),
                     ("POST", "/api/attempts/doesnotexist1/submit", {}), ("GET", "/api/attempts/doesnotexist1/results", {})]:
        expect_err(await cx.req(m, p, **kw), 401, "missing_student", f"{m} {p}: ")


@sc("ID-14", "identity", "contract", "Start attempt on an unknown set with no header", "401 missing_student (header first)")
async def _(cx):
    expect_err(await cx.req("POST", "/api/practice-sets/nope/attempts"), 401, "missing_student")


@sc("ID-15", "identity", "contract", "Student id that is a numeric string / looks like a boolean ('0', 'false')",
    "Any non-empty string is a valid id: 201")
async def _(cx):
    for v in ["0", "false", "null", "1"]:
        v = v + "x" + uuid.uuid4().hex[:3] if False else v
        r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", v)
        check(r.status_code == 201, f"{v!r}: {short(r)}")


# ================================================================= SET
@sc("SET-01", "set", "contract", "GET the set; compare to the fixture exactly (title, order, text, code, choices)",
    "200; id, title, questions q1..q3 in order; code null for q1,q2; choices a,b,c with fixture text")
async def _(cx):
    r = await cx.req("GET", f"/api/practice-sets/{SET}")
    check(r.status_code == 200, short(r))
    j = J(r)
    check(j["id"] == SET and j["title"] == "Software engineering basics", f"id/title {j.get('id')} {j.get('title')}")
    check([q["id"] for q in j["questions"]] == QIDS, "question order")
    for q in j["questions"]:
        i = q["id"]
        check(q["text"] == TEXTS[i], f"{i} text {q['text']!r}")
        check(q["code"] == CODE[i], f"{i} code {q['code']!r}")
        check([c["id"] for c in q["choices"]] == ["a", "b", "c"], f"{i} choice ids")
        check([c["text"] for c in q["choices"]] == CHOICES[i], f"{i} choice texts")


@sc("SET-02", "set", "contract", "GET the set and inspect every key",
    "Exactly {id,title,questions}; question {id,text,code,choices}; choice {id,text}; no key/explanation/key_version")
async def _(cx):
    r = await cx.req("GET", f"/api/practice-sets/{SET}")
    j = J(r)
    check(set(j) == {"id", "title", "questions"}, f"top keys {sorted(j)}")
    for q in j["questions"]:
        check(set(q) == {"id", "text", "code", "choices"}, f"question keys {sorted(q)}")
        for c in q["choices"]:
            check(set(c) == {"id", "text"}, f"choice keys {sorted(c)}")
    assert_noleak(r)


@sc("SET-03", "set", "contract", "GET unknown set ids: 'nope', 'INTRO-SE-1', 'intro-se-2', 'intro-se-1x', ' intro-se-1', long, unicode",
    "404 set_not_found for each (case-sensitive, exact match)")
async def _(cx):
    for v in ["nope", "INTRO-SE-1", "Intro-Se-1", "intro-se-2", "intro-se-1x", "intro-se", "%20intro-se-1", "intro-se-1%20",
              "x" * 5000, "%E5%AD%A6", "0", "null"]:
        r = await cx.req("GET", f"/api/practice-sets/{v}")
        expect_err(r, 404, "set_not_found", f"{v[:30]!r}: ")


@sc("SET-04", "set", "robustness", "GET set after other students started, saved and submitted attempts",
    "Set response unchanged (no per-attempt state bleeds into the set)")
async def _(cx):
    before = (await cx.req("GET", f"/api/practice-sets/{SET}")).text
    await done(cx, ALL_BAD)
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    after = (await cx.req("GET", f"/api/practice-sets/{SET}")).text
    check(before == after, "set body changed after attempts")


@sc("SET-05", "set", "robustness", "GET set with an empty-ish POST/odd path: trailing slash and double slash",
    "No 5xx; any 2xx body has no key/explanation")
async def _(cx):
    for p in [f"/api/practice-sets/{SET}/", f"/api/practice-sets//{SET}", f"/api/practice-sets/{SET}/../{SET}"]:
        r = await cx.req("GET", p, follow_redirects=True)
        check(r.status_code < 500, f"{p}: {short(r)}")
        assert_noleak(r)


# ================================================================= START
@sc("START-01", "start", "contract", "POST start attempt on intro-se-1", "201 {attempt_id,set_id,status:in_progress,answers:{}}")
async def _(cx):
    r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", newsid())
    check(r.status_code == 201, short(r))
    j = J(r)
    check(isinstance(j["attempt_id"], str) and len(j["attempt_id"]) >= 8, f"id {j['attempt_id']!r}")
    check(j["set_id"] == SET and j["status"] == "in_progress" and j["answers"] == {}, f"body {j}")
    check(set(j) == {"attempt_id", "set_id", "status", "answers"}, f"keys {sorted(j)}")
    assert_noleak(r)


@sc("START-02", "start", "contract", "Start on an unknown set with a valid header", "404 set_not_found")
async def _(cx):
    for v in ["nope", "INTRO-SE-1", "intro-se-1x"]:
        expect_err(await cx.req("POST", f"/api/practice-sets/{v}/attempts", newsid()), 404, "set_not_found", f"{v}: ")


@sc("START-03", "start", "contract", "AC10: two attempts by one student; save/submit one",
    "Independent: other stays empty and in_progress; a third start is fresh")
async def _(cx):
    sid, a1 = await mk(cx)
    _, a2 = await mk(cx, sid)
    check(a1 != a2, "same attempt id returned twice")
    await fill(cx, sid, a1, ALL_OK)
    check((await get_attempt(cx, sid, a2))["answers"] == {}, "answers leaked into sibling attempt")
    check((await submit(cx, sid, a1)).status_code == 200, "submit a1")
    j2 = await get_attempt(cx, sid, a2)
    check(j2["status"] == "in_progress" and j2["answers"] == {}, f"sibling affected {j2}")
    _, a3 = await mk(cx, sid)
    j3 = await get_attempt(cx, sid, a3)
    check(j3["status"] == "in_progress" and j3["answers"] == {}, f"new attempt not fresh {j3}")
    check((await cx.req("GET", A(a2) + "/results", sid)).status_code == 403, "sibling results not 403")


@sc("START-04", "start", "contract", "Attempt ids: 40 creations are strings >= 8 chars, unique, not sequential integers",
    "All unique, len >= 8, not consecutive numbers")
async def _(cx):
    sid = newsid()
    ids = [(await mk(cx, sid))[1] for _ in range(40)]
    check(all(isinstance(i, str) and len(i) >= 8 for i in ids), f"short/non-string ids: {[i for i in ids if len(str(i)) < 8][:3]}")
    check(len(set(ids)) == 40, "duplicate attempt ids")
    if all(i.isdigit() for i in ids):
        nums = [int(i) for i in ids]
        check(False, f"ids are all numeric ({nums[:3]}...): guessable")
    nums = []
    for i in ids:
        m = re.search(r"(\d+)$", i)
        nums.append(int(m.group(1)) if m else None)
    if all(n is not None for n in nums):
        diffs = {b - a for a, b in zip(nums, nums[1:])}
        check(diffs != {1}, f"ids end in consecutive counter: {ids[:3]}")


@sc("START-05", "start", "robustness", "Attempt id shape: URL-safe, no student id inside, ids of different students differ",
    "Opaque: charset [A-Za-z0-9_.~-], does not contain the student id, no shared long prefix")
async def _(cx):
    sid = newsid()
    ids = [(await mk(cx, sid))[1] for _ in range(6)] + [(await mk(cx))[1] for _ in range(6)]
    for i in ids:
        check(re.fullmatch(r"[A-Za-z0-9_.~\-]+", i), f"id {i!r} not URL-safe")
        check(sid not in i and sid.split("-")[1] not in i, f"id {i!r} embeds the student id")
    check(len({i[:6] for i in ids}) > 3, f"ids share a common prefix: {ids[:4]}")


@sc("START-06", "start", "robustness", "Start with a body that tries to set state ({status:submitted, answers, attempt_id, score}) or garbage",
    "No 5xx; if 201 the attempt is in_progress, empty, with a server-chosen id")
async def _(cx):
    bodies = [dict(json={"status": "submitted", "answers": {"q1": "a"}, "attempt_id": "chosen-by-client",
                         "score": {"correct": 3, "total": 3}}),
              dict(content=b"not json", headers={"content-type": "application/json"}),
              dict(content=b"\xff\xfe"), dict(content=b"x" * 500000)]
    for kw in bodies:
        r = await cx.req("POST", f"/api/practice-sets/{SET}/attempts", newsid(), **kw)
        check(r.status_code < 500, short(r))
        if r.status_code == 201:
            j = J(r)
            check(j["status"] == "in_progress" and j["answers"] == {} and j["attempt_id"] != "chosen-by-client", f"state {j}")


@sc("START-07", "start", "contract", "GET a fresh attempt", "200 {attempt_id,set_id,status:in_progress,answers:{}}, same id")
async def _(cx):
    sid, aid = await mk(cx)
    r = await cx.req("GET", A(aid), sid)
    j = J(r)
    check(r.status_code == 200 and j == {"attempt_id": aid, "set_id": SET, "status": "in_progress", "answers": {}}, short(r))


# ================================================================= SAVE
@sc("SAVE-01", "save", "contract", "Save one answer", "200 {attempt_id,status:in_progress,answers:{q1:a}}; GET agrees")
async def _(cx):
    sid, aid = await mk(cx)
    r = await save(cx, sid, aid, {"q1": "a"})
    check(r.status_code == 200 and J(r) == {"attempt_id": aid, "status": "in_progress", "answers": {"q1": "a"}}, short(r))
    check((await get_attempt(cx, sid, aid))["answers"] == {"q1": "a"}, "GET disagrees")


@sc("SAVE-02", "save", "contract", "Revise the same answer 12 times (a,b,c,...)", "Always 200; last value wins")
async def _(cx):
    sid, aid = await mk(cx)
    last = None
    for i in range(12):
        last = "abc"[i % 3]
        r = await save(cx, sid, aid, {"q2": last})
        check(r.status_code == 200 and J(r)["answers"] == {"q2": last}, f"rev {i}: {short(r)}")
    check((await get_attempt(cx, sid, aid))["answers"] == {"q2": last}, "final value")


@sc("SAVE-03", "save", "contract", "Save q1, then q2, then revise q1 (merge semantics)", "Responses contain all saved answers")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    r = await save(cx, sid, aid, {"q2": "c"})
    check(J(r)["answers"] == {"q1": "a", "q2": "c"}, f"merge failed {short(r)}")
    r = await save(cx, sid, aid, {"q1": "b"})
    check(J(r)["answers"] == {"q1": "b", "q2": "c"}, f"revise failed {short(r)}")


@sc("SAVE-04", "save", "contract", "Save all three answers in one request", "200 with all three")
async def _(cx):
    sid, aid = await mk(cx)
    r = await save(cx, sid, aid, ALL_BAD)
    check(r.status_code == 200 and J(r)["answers"] == ALL_BAD, short(r))


@sc("SAVE-05", "save", "contract",
    "Unknown question ids: q4, Q1, 'q1 ', ' q1', '', q0, __proto__, q1\\u0000, fullwidth ｑ１, '1'",
    "422 unknown_question each; nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    for q in ["q4", "Q1", "q1 ", " q1", "", "q0", "__proto__", "q1\u0000", "\uff51\uff11", "1", "q1.0", "constructor"]:
        r = await save(cx, sid, aid, {q: "a"})
        expect_err(r, 422, "unknown_question", f"{q!r}: ")
        assert_noleak(r)
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "unknown question was stored")


@sc("SAVE-06", "save", "contract",
    "Invalid choice ids for q2: d, A, 'a ', '', ab, q1, 1, null, fullwidth ａ, ' a', 'a\\n'",
    "422 invalid_choice each; nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    for c in ["d", "A", "a ", "", "ab", "q1", "1", "null", "\uff41", " a", "a\n", "a\u0000", "0"]:
        r = await save(cx, sid, aid, {"q2": c})
        expect_err(r, 422, "invalid_choice", f"{c!r}: ")
        assert_noleak(r)
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "invalid choice was stored")


@sc("SAVE-07", "save", "contract", "Mixed request: valid q1 plus invalid q2 choice / unknown q9, with earlier saved answers present",
    "422; the valid entry of the same request is NOT saved; earlier answers untouched")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q3": "c"})
    for body, code in [({"q1": "a", "q2": "z"}, "invalid_choice"), ({"q1": "a", "q9": "a"}, "unknown_question"),
                       ({"q2": "z", "q1": "a"}, "invalid_choice"), ({"q9": "a", "q1": "a", "q3": "a"}, "unknown_question")]:
        expect_err(await save(cx, sid, aid, body), 422, code, f"{body}: ")
        check((await get_attempt(cx, sid, aid))["answers"] == {"q3": "c"}, f"partial save after rejecting {body}")


@sc("SAVE-08", "save", "robustness", "One request with both an unknown question and an invalid choice",
    "422 with code unknown_question or invalid_choice; nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    r = await save(cx, sid, aid, {"q1": "a", "q9": "a", "q2": "zz"})
    check(r.status_code == 422 and code_of(r) in ("unknown_question", "invalid_choice"), short(r))
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "partial save")


@sc("SAVE-09", "save", "robustness", "Wrong value types for a choice: 1, null, true, false, ['a'], {'a':1}, 1.5, [], {}",
    "400/422 (never 200, never 5xx); nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    for v in [1, None, True, False, ["a"], {"a": 1}, 1.5, [], {}, 0]:
        r = await save(cx, sid, aid, {"q1": v})
        check(r.status_code in (400, 422), f"{v!r}: {short(r)}")
        assert_noleak(r)
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "wrong-typed value stored")


@sc("SAVE-10", "save", "robustness", "Wrong body shapes: {}, answers null/list/string/number, top-level list/null/string/number, wrong key name, nested objects",
    "400/422; nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    bodies = [{}, {"answers": None}, {"answers": []}, {"answers": "a"}, {"answers": 5}, [], None, "str", 5, True,
              {"answer": {"q1": "a"}}, {"Answers": {"q1": "a"}}, {"answers": [["q1", "a"]]}, {"answers": [{"q1": "a"}]},
              {"answers": {"q1": {"choice": "a"}}}, {"answers": {"q1": ["a"]}}, {"data": {"answers": {"q1": "a"}}},
              {"q1": "a"}, {"answers": {"answers": {"q1": "a"}}}]
    for b in bodies:
        r = await cx.req("PUT", A(aid) + "/answers", sid, content=json.dumps(b), headers={"content-type": "application/json"})
        check(r.status_code in (400, 422), f"{b!r}: {short(r)}")
        assert_noleak(r)
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "something was stored")


@sc("SAVE-11", "save", "robustness", "Empty answers object {'answers': {}} on an attempt with a saved answer",
    "200 (merge of nothing) or 422; saved answers unchanged either way")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    r = await save(cx, sid, aid, {})
    check(r.status_code in (200, 422), short(r))
    if r.status_code == 200:
        check(J(r)["answers"] == {"q1": "a"}, short(r))
    check((await get_attempt(cx, sid, aid))["answers"] == {"q1": "a"}, "answers changed")


@sc("SAVE-12", "save", "robustness", "Non-JSON / malformed bodies: text, truncated JSON, empty, invalid UTF-8, single quotes, trailing comma, trailing garbage, NULs",
    "4xx (400-499, never 5xx); nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    bad = [b"not json", b'{"answers": {', b"", b"\xff\xfe\xfd", b"{'answers': {'q1': 'a'}}", b'{"answers":{"q1":"a"},}',
           b'{"answers": {"q1": "a"}} trailing', b"\x00" * 10, b"<xml/>", b'{"answers": {"q1": "a"}', b"answers=q1"]
    for raw in bad:
        r = await cx.req("PUT", A(aid) + "/answers", sid, content=raw, headers={"content-type": "application/json"})
        check(400 <= r.status_code < 500, f"{raw[:20]!r}: {short(r)}")
        assert_noleak(r)
    r = await cx.req("PUT", A(aid) + "/answers", sid, content=b"not json", headers={"content-type": "text/plain"})
    check(400 <= r.status_code < 500, f"text/plain: {short(r)}")
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "something was stored")


@sc("SAVE-13", "save", "robustness", "Huge payloads: 20,000 unknown keys; a 3 MB choice string; q1 valid plus 5,000 unknown keys",
    "4xx or 413 (never 5xx / hang); nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    for body in [{"answers": {f"k{i}": "a" for i in range(20000)}}, {"answers": {"q1": "a" * 3_000_000}},
                 {"answers": {"q1": "a", **{f"x{i}": "a" for i in range(5000)}}}]:
        r = await save(cx, sid, aid, body["answers"])
        check(400 <= r.status_code < 500, f"{short(r)[:120]}")
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "something was stored")


@sc("SAVE-14", "save", "robustness", "Deeply nested JSON (100,000 levels) as the body and as a choice value",
    "4xx, no 5xx / crash; nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    deep = b"[" * 100000 + b"]" * 100000
    r = await cx.req("PUT", A(aid) + "/answers", sid, content=deep, headers={"content-type": "application/json"})
    check(400 <= r.status_code < 500, f"top-level: {short(r)}")
    body = b'{"answers": {"q1": ' + deep + b"}}"
    r = await cx.req("PUT", A(aid) + "/answers", sid, content=body, headers={"content-type": "application/json"})
    check(400 <= r.status_code < 500, f"nested value: {short(r)}")
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "something was stored")


@sc("SAVE-15", "save", "robustness",
    "PUT with extra client fields: status:'submitted', score, attempt_id, key_version alongside valid answers",
    "Extras ignored (200, in_progress, only the answers saved) or the request rejected 4xx with nothing saved; never submitted")
async def _(cx):
    sid, aid = await mk(cx)
    body = {"answers": {"q1": "a"}, "status": "submitted", "score": {"correct": 3, "total": 3},
            "attempt_id": "zzz-other", "key_version": "v9", "set_id": "other"}
    r = await cx.req("PUT", A(aid) + "/answers", sid, json=body)
    check(r.status_code == 200 or 400 <= r.status_code < 500, short(r))
    if r.status_code == 200:
        j = J(r)
        check(j["status"] == "in_progress" and j["attempt_id"] == aid and j["answers"] == {"q1": "a"}, f"body {j}")
    j = await get_attempt(cx, sid, aid)
    check(j["status"] == "in_progress" and j["set_id"] == SET and j["attempt_id"] == aid, f"state {j}")
    expect_err(await submit(cx, sid, aid), 422, "incomplete")


@sc("SAVE-16", "save", "robustness", "Duplicate JSON keys in one body: {\"answers\":{\"q1\":\"a\",\"q1\":\"b\"}}",
    "No 5xx; 200 with one of the values (consistent with GET) or 4xx with nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    r = await cx.req("PUT", A(aid) + "/answers", sid, content=b'{"answers":{"q1":"a","q1":"b"}}',
                     headers={"content-type": "application/json"})
    check(r.status_code == 200 or 400 <= r.status_code < 500, short(r))
    cur = (await get_attempt(cx, sid, aid))["answers"]
    if r.status_code == 200:
        check(J(r)["answers"] == cur and cur.get("q1") in ("a", "b"), f"{short(r)} vs {cur}")
    else:
        check(cur == {}, f"stored {cur} despite rejection")


@sc("SAVE-17", "save", "robustness", "PUT with answers in the query string (?q1=a&answers=...) and an empty body",
    "Query string is not an input: nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    r = await cx.req("PUT", A(aid) + "/answers?q1=a&q2=b&answers=%7B%22q1%22%3A%22a%22%7D", sid)
    check(r.status_code < 500, short(r))
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "query string saved an answer")


@sc("SAVE-18", "save", "contract", "PUT valid answers to an unknown attempt id", "404 attempt_not_found")
async def _(cx):
    expect_err(await save(cx, newsid(), "doesnotexist-1", {"q1": "a"}), 404, "attempt_not_found")


@sc("SAVE-19", "save", "contract", "PUT keeps answers for questions not in the request and returns the full map each time",
    "Response answers always equals GET answers")
async def _(cx):
    sid, aid = await mk(cx)
    for body in [{"q3": "a"}, {"q1": "c"}, {"q3": "c"}, {"q2": "b", "q1": "a"}]:
        r = await save(cx, sid, aid, body)
        check(J(r)["answers"] == (await get_attempt(cx, sid, aid))["answers"], f"after {body}")


@sc("SAVE-20", "save", "robustness", "Large but valid-looking repeated saves (200 requests) do not break the attempt",
    "All 200; final state correct; submit works")
async def _(cx):
    sid, aid = await mk(cx)
    for i in range(200):
        r = await save(cx, sid, aid, {QIDS[i % 3]: "abc"[i % 3]})
        check(r.status_code == 200, f"iteration {i}: {short(r)}")
    j = await get_attempt(cx, sid, aid)
    check(j["answers"] == {"q1": "a", "q2": "b", "q3": "c"}, f"{j}")
    check((await submit(cx, sid, aid)).status_code == 200, "submit failed")


# ================================================================= SUBMIT
@sc("SUB-01", "submit", "contract", "Submit an attempt with nothing answered",
    "422 incomplete, missing == [q1,q2,q3]; shape {code,message,missing}; attempt stays in_progress")
async def _(cx):
    sid, aid = await mk(cx)
    r = await submit(cx, sid, aid)
    expect_err(r, 422, "incomplete")
    d = J(r)["detail"]
    check(d["missing"] == QIDS, f"missing {d.get('missing')}")
    check(set(J(r)) == {"detail"} and set(d) == {"code", "message", "missing"} and isinstance(d["message"], str), f"shape {J(r)}")
    check((await get_attempt(cx, sid, aid))["status"] == "in_progress", "status changed")


@sc("SUB-02", "submit", "contract", "Missing lists after each partial save (q3 only; q2 only; q1 only; q3+q2; q3 then q1)",
    "missing is in set order: [q1,q2], [q1,q3], [q2,q3], [q1], [q2]")
async def _(cx):
    for ans, exp in [({"q3": "a"}, ["q1", "q2"]), ({"q2": "a"}, ["q1", "q3"]), ({"q1": "a"}, ["q2", "q3"]),
                     ({"q3": "a", "q2": "a"}, ["q1"]), ({"q1": "a", "q3": "a"}, ["q2"])]:
        sid, aid = await mk(cx)
        await fill(cx, sid, aid, ans)
        r = await submit(cx, sid, aid)
        expect_err(r, 422, "incomplete", f"{ans}: ")
        check(J(r)["detail"]["missing"] == exp, f"{ans}: missing {J(r)['detail'].get('missing')} expected {exp}")
    # insertion order differs from set order
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q3": "a"})
    await fill(cx, sid, aid, {"q2": "a"})
    r = await submit(cx, sid, aid)
    check(J(r)["detail"]["missing"] == ["q1"], "q3,q2 saved: missing q1")


@sc("SUB-03", "submit", "contract", "Rejected submit leaves answers, status and results gate untouched; attempt still usable",
    "Answers preserved, status in_progress, results 403 not_submitted, can save the rest and then submit")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a", "q3": "c"})
    for _ in range(3):
        expect_err(await submit(cx, sid, aid), 422, "incomplete")
    j = await get_attempt(cx, sid, aid)
    check(j["status"] == "in_progress" and j["answers"] == {"q1": "a", "q3": "c"}, f"state {j}")
    expect_err(await cx.req("GET", A(aid) + "/results", sid), 403, "not_submitted")
    r = await save(cx, sid, aid, {"q2": "b"})
    check(r.status_code == 200, f"save after failed submit: {short(r)}")
    r = await submit(cx, sid, aid)
    check(r.status_code == 200 and J(r)["score"] == {"correct": 3, "total": 3}, short(r))


@sc("SUB-04", "submit", "contract", "Submit a complete all-correct attempt",
    "200 {attempt_id,status:submitted,score:{correct:3,total:3}}")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    r = await submit(cx, sid, aid)
    j = J(r)
    check(r.status_code == 200 and j["attempt_id"] == aid and j["status"] == "submitted"
          and j["score"] == {"correct": 3, "total": 3}, short(r))
    check((await get_attempt(cx, sid, aid))["status"] == "submitted", "GET status")


@sc("SUB-05", "submit", "contract", "Scores for all-wrong, 2/3, 1/3 and 0/3 variants incl. each question wrong in turn",
    "Server-computed correct/total (total always 3)")
async def _(cx):
    cases = [ALL_BAD, MIX2, {"q1": "a", "q2": "a", "q3": "a"}, {"q1": "b", "q2": "b", "q3": "c"},
             {"q1": "c", "q2": "c", "q3": "b"}, {"q1": "a", "q2": "c", "q3": "c"}]
    for ans in cases:
        _, _, j = await done(cx, ans)
        check(j["score"] == {"correct": exp_score(ans), "total": 3}, f"{ans}: {j['score']}")


@sc("SUB-06", "submit", "contract", "AC5: client-supplied scores on submit (body {score}, {correct,total}, {score:3}, ?score=3) for an all-wrong attempt",
    "Ignored: score is 0/3")
async def _(cx):
    variants = [dict(json={"score": {"correct": 3, "total": 3}}), dict(json={"correct": 3, "total": 3}),
                dict(json={"score": 3}), dict(json={"score": {"correct": 99, "total": 99}, "status": "submitted"}),
                dict(params={"score": 3, "correct": 3, "total": 3}),
                dict(json={"score": {"correct": 3, "total": 3}}, params={"score": 3})]
    for kw in variants:
        sid, aid = await mk(cx)
        await fill(cx, sid, aid, ALL_BAD)
        r = await submit(cx, sid, aid, **kw)
        check(r.status_code == 200 and J(r)["score"] == {"correct": 0, "total": 3}, f"{kw}: {short(r)}")
        res = await cx.req("GET", A(aid) + "/results", sid)
        check(J(res)["score"] == {"correct": 0, "total": 3}, f"results score {J(res).get('score')}")


@sc("SUB-07", "submit", "contract", "Submit body ignored: none, 'not json', [], invalid UTF-8, 1 MB of x, answers in body, text/plain, multipart junk",
    "Always processed as a plain submit: 200 with the true score; body answers not applied")
async def _(cx):
    variants = [dict(), dict(content=b"not json", headers={"content-type": "application/json"}), dict(content=b"[]", headers={"content-type": "application/json"}),
                dict(content=b"\xff\xfe", headers={"content-type": "application/json"}), dict(content=b"x" * 1_000_000),
                dict(json={"answers": {"q1": "b", "q2": "a", "q3": "a"}}),
                dict(content=b"q1=b", headers={"content-type": "application/x-www-form-urlencoded"}),
                dict(content=b"--x\r\n", headers={"content-type": "multipart/form-data; boundary=x"})]
    for kw in variants:
        sid, aid = await mk(cx)
        await fill(cx, sid, aid, ALL_OK)
        r = await submit(cx, sid, aid, **kw)
        check(r.status_code == 200 and J(r)["score"] == {"correct": 3, "total": 3}, f"{str(kw)[:80]}: {short(r)}")
        res = J(await cx.req("GET", A(aid) + "/results", sid))
        check(res["answers"] == ALL_OK, f"answers altered by submit body: {res['answers']}")


@sc("SUB-08", "submit", "contract", "Submit twice (and three times)", "2nd+ gives 409 already_submitted; score and results unchanged")
async def _(cx):
    sid, aid, j = await done(cx, MIX2)
    before = (await cx.req("GET", A(aid) + "/results", sid)).text
    for _ in range(3):
        r = await submit(cx, sid, aid)
        expect_err(r, 409, "already_submitted")
        assert set(J(r)["detail"]) == {"code", "message"}
    check((await cx.req("GET", A(aid) + "/results", sid)).text == before, "results changed after repeat submits")


@sc("SUB-09", "submit", "contract", "Resubmit with a client score of 3/3 after a 0/3 submit", "409; results still 0/3")
async def _(cx):
    sid, aid, j = await done(cx, ALL_BAD)
    r = await submit(cx, sid, aid, json={"score": {"correct": 3, "total": 3}})
    expect_err(r, 409, "already_submitted")
    check(J(await cx.req("GET", A(aid) + "/results", sid))["score"] == {"correct": 0, "total": 3}, "score overwritten")


@sc("SUB-10", "submit", "contract", "Submit an unknown attempt id", "404 attempt_not_found")
async def _(cx):
    expect_err(await submit(cx, newsid(), "doesnotexist-1"), 404, "attempt_not_found")


@sc("SUB-11", "submit", "contract", "Wrong answers revised to right before submit; and right revised to wrong",
    "Score uses the latest saved answers")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_BAD)
    await fill(cx, sid, aid, ALL_OK)
    check(J(await submit(cx, sid, aid))["score"]["correct"] == 3, "revised-to-right not 3")
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    await fill(cx, sid, aid, {"q2": "a"})
    check(J(await submit(cx, sid, aid))["score"]["correct"] == 2, "revised-to-wrong not 2")


@sc("SUB-12", "submit", "contract", "Submit response shape", "keys attempt_id, status, score{correct,total} ints present")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    j = J(await submit(cx, sid, aid))
    check({"attempt_id", "status", "score"} <= set(j) and set(j["score"]) == {"correct", "total"}, f"{j}")
    check(all(type(v) is int for v in j["score"].values()), f"non-int score {j['score']}")


@sc("SUB-13", "submit", "contract", "Incomplete attempt submitted with a body claiming answers / a perfect score",
    "Still 422 incomplete with the true missing list; nothing saved from the body")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    r = await submit(cx, sid, aid, json={"answers": {"q2": "b", "q3": "c"}, "score": {"correct": 3, "total": 3}})
    expect_err(r, 422, "incomplete")
    check(J(r)["detail"]["missing"] == ["q2", "q3"], f"missing {J(r)['detail'].get('missing')}")
    check((await get_attempt(cx, sid, aid))["answers"] == {"q1": "a"}, "body answers were applied")


# ================================================================= RESULTS
def exp_results(aid, ans, score=None):
    qs = [{"id": q, "selected": ans[q], "correct_choice": KEY[q], "correct": ans[q] == KEY[q], "explanation": EXPL[q]} for q in QIDS]
    return {"attempt_id": aid, "set_id": SET, "key_version": "v1", "score": {"correct": exp_score(ans), "total": 3},
            "answers": ans, "questions": qs}


def cmp_results(j, exp):
    for k in ("attempt_id", "set_id", "key_version", "score", "answers"):
        check(j.get(k) == exp[k], f"{k}: got {j.get(k)!r} expected {exp[k]!r}")
    check([q.get("id") for q in j["questions"]] == QIDS, "question order/ids")
    for g, e in zip(j["questions"], exp["questions"]):
        for k, v in e.items():
            check(g.get(k) == v, f"{e['id']}.{k}: got {g.get(k)!r} expected {v!r}")


@sc("RES-01", "results", "contract", "Results of an unsubmitted attempt (empty, partial, complete-but-unsubmitted)",
    "403 not_submitted each, body without key/explanation")
async def _(cx):
    sid, aid = await mk(cx)
    for ans in [None, {"q1": "a"}, ALL_OK]:
        if ans:
            await fill(cx, sid, aid, ans)
        r = await cx.req("GET", A(aid) + "/results", sid)
        expect_err(r, 403, "not_submitted", f"{ans}: ")
        assert_noleak(r)


@sc("RES-02", "results", "contract", "Results of a perfect attempt, full comparison",
    "key_version v1, 3/3, answers, per-question selected/correct_choice/correct/explanation in set order")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    r = await cx.req("GET", A(aid) + "/results", sid)
    check(r.status_code == 200, short(r))
    cmp_results(J(r), exp_results(aid, ALL_OK))


@sc("RES-03", "results", "contract", "Results of all-wrong and mixed attempts", "correct flags false/true per question; explanations and correct_choice still present")
async def _(cx):
    for ans in [ALL_BAD, MIX2, {"q1": "c", "q2": "b", "q3": "b"}]:
        sid, aid, _ = await done(cx, ans)
        r = await cx.req("GET", A(aid) + "/results", sid)
        check(r.status_code == 200, short(r))
        cmp_results(J(r), exp_results(aid, ans))


@sc("RES-04", "results", "contract", "Results fetched repeatedly; compared with submit response and GET attempt",
    "Identical bodies; score equals submit score; GET attempt shows submitted with same answers")
async def _(cx):
    sid, aid, sj = await done(cx, MIX2)
    r1 = await cx.req("GET", A(aid) + "/results", sid)
    r2 = await cx.req("GET", A(aid) + "/results", sid)
    check(r1.text == r2.text, "results differ between reads")
    check(J(r1)["score"] == sj["score"], "score differs from submit response")
    g = await get_attempt(cx, sid, aid)
    check(g["status"] == "submitted" and g["answers"] == MIX2 == J(r1)["answers"], f"{g}")


@sc("RES-05", "results", "contract", "Results of unknown attempt", "404 attempt_not_found")
async def _(cx):
    expect_err(await cx.req("GET", A("doesnotexist-1") + "/results", newsid()), 404, "attempt_not_found")


@sc("RES-06", "results", "contract", "Results use revised answers, and 'selected' equals the saved answer for every question",
    "selected/answers reflect the final saved values")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_BAD)
    await fill(cx, sid, aid, {"q1": "c"})
    await fill(cx, sid, aid, {"q2": "b", "q3": "b"})
    await submit(cx, sid, aid)
    final = {"q1": "c", "q2": "b", "q3": "b"}
    cmp_results(J(await cx.req("GET", A(aid) + "/results", sid)), exp_results(aid, final))


@sc("RES-07", "results", "robustness", "Results with query parameters (?include=x, ?debug=1) and trailing slash",
    "Same body as plain results or a clean 4xx; no 5xx")
async def _(cx):
    sid, aid, _ = await done(cx, MIX2)
    base = (await cx.req("GET", A(aid) + "/results", sid)).text
    for q in ["?debug=1", "?include=everything", "?version=v2", "?student=other"]:
        r = await cx.req("GET", A(aid) + "/results" + q, sid)
        check(r.status_code < 500, short(r))
        if r.status_code == 200:
            check(r.text == base, f"results changed with {q}")


# ================================================================= LOCK
@sc("LOCK-01", "lock", "contract", "Save after submit (same values, changed values, a wrong value)",
    "409 already_submitted; stored answers, results and score unchanged")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    before = (await cx.req("GET", A(aid) + "/results", sid)).text
    for body in [ALL_OK, {"q1": "b"}, ALL_BAD, {"q3": "a"}]:
        r = await save(cx, sid, aid, body)
        expect_err(r, 409, "already_submitted", f"{body}: ")
        check(set(J(r)["detail"]) == {"code", "message"}, "409 shape")
    check((await cx.req("GET", A(aid) + "/results", sid)).text == before, "results changed")
    g = await get_attempt(cx, sid, aid)
    check(g["answers"] == ALL_OK and g["status"] == "submitted", f"{g}")


@sc("LOCK-02", "lock", "contract", "Save after submit with an unknown question / invalid choice / empty answers",
    "409 (state check precedes validation)")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    for body in [{"q9": "a"}, {"q1": "zzz"}, {}, {"q1": 5}]:
        expect_err(await save(cx, sid, aid, body), 409, "already_submitted", f"{body}: ")


@sc("LOCK-03", "lock", "contract", "Save after submit with a malformed body", "409 (state precedes input validation)")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    for raw in [b"not json", b"", b"[]", b"\xff"]:
        r = await cx.req("PUT", A(aid) + "/answers", sid, content=raw, headers={"content-type": "application/json"})
        expect_err(r, 409, "already_submitted", f"{raw!r}: ")


@sc("LOCK-04", "lock", "contract", "Status after submit via GET attempt, and PUT answers response never says in_progress again",
    "submitted forever")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    for _ in range(3):
        await save(cx, sid, aid, {"q1": "b"})
        check((await get_attempt(cx, sid, aid))["status"] == "submitted", "status reverted")


# ================================================================= ORDER
@sc("ORD-01", "order", "contract", "No header + unknown attempt + garbage PUT body", "401 (header before everything)")
async def _(cx):
    r = await cx.req("PUT", A("doesnotexist-1") + "/answers", content=b"garbage", headers={"content-type": "application/json"})
    expect_err(r, 401, "missing_student")


@sc("ORD-02", "order", "contract", "No header + existing attempt + malformed / invalid PUT bodies", "401, nothing saved")
async def _(cx):
    sid, aid = await mk(cx)
    for raw in [b"garbage", json.dumps({"answers": {"q9": "z"}}).encode(), b""]:
        r = await cx.req("PUT", A(aid) + "/answers", content=raw, headers={"content-type": "application/json"})
        expect_err(r, 401, "missing_student", f"{raw[:20]!r}: ")


@sc("ORD-03", "order", "contract", "Another student PUTs an invalid body (unknown question / invalid choice) to my attempt",
    "404 attempt_not_found, not 422")
async def _(cx):
    sid, aid = await mk(cx)
    other = newsid()
    for body in [{"q9": "a"}, {"q1": "zzz"}]:
        expect_err(await save(cx, other, aid, body), 404, "attempt_not_found", f"{body}: ")


@sc("ORD-04", "order", "contract", "Another student PUTs a malformed / wrong-shaped body to my attempt",
    "404 attempt_not_found, not 422 (ownership before input validation)")
async def _(cx):
    sid, aid = await mk(cx)
    other = newsid()
    for raw in [b"garbage", b"[]", b'{"answers": 5}', b""]:
        r = await cx.req("PUT", A(aid) + "/answers", other, content=raw, headers={"content-type": "application/json"})
        expect_err(r, 404, "attempt_not_found", f"{raw!r}: ")


@sc("ORD-05", "order", "contract", "Another student PUTs to my SUBMITTED attempt", "404, not 409")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    expect_err(await save(cx, newsid(), aid, {"q1": "a"}), 404, "attempt_not_found")
    expect_err(await save(cx, newsid(), aid, {"q9": "z"}), 404, "attempt_not_found")


@sc("ORD-06", "order", "contract", "Another student asks for results of my UNSUBMITTED attempt", "404, not 403")
async def _(cx):
    sid, aid = await mk(cx)
    expect_err(await cx.req("GET", A(aid) + "/results", newsid()), 404, "attempt_not_found")


@sc("ORD-07", "order", "contract", "Another student submits my incomplete / complete attempt", "404, not 422 / 200; my attempt untouched")
async def _(cx):
    sid, aid = await mk(cx)
    other = newsid()
    expect_err(await submit(cx, other, aid), 404, "attempt_not_found")
    await fill(cx, sid, aid, ALL_OK)
    expect_err(await submit(cx, other, aid), 404, "attempt_not_found")
    check((await get_attempt(cx, sid, aid))["status"] == "in_progress", "other student submitted my attempt")


@sc("ORD-08", "order", "contract", "Owner PUTs an invalid body to own submitted attempt", "409, not 422 (state before validation)")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    expect_err(await save(cx, sid, aid, {"q9": "a"}), 409, "already_submitted")
    expect_err(await save(cx, sid, aid, {"q1": "zzz"}), 409, "already_submitted")


@sc("ORD-09", "order", "contract", "Owner submits an incomplete attempt with a garbage body", "422 incomplete (body ignored)")
async def _(cx):
    sid, aid = await mk(cx)
    r = await submit(cx, sid, aid, content=b"garbage", headers={"content-type": "application/json"})
    expect_err(r, 422, "incomplete")


@sc("ORD-10", "order", "contract", "Unknown attempt + invalid PUT body (with header)", "404, not 422")
async def _(cx):
    expect_err(await save(cx, newsid(), "doesnotexist-1", {"q9": "z"}), 404, "attempt_not_found")
    r = await cx.req("PUT", A("doesnotexist-1") + "/answers", newsid(), content=b"garbage",
                     headers={"content-type": "application/json"})
    expect_err(r, 404, "attempt_not_found")


@sc("ORD-11", "order", "contract", "Other student results/submit/PUT on someone's attempt that is in each state (empty, partial, complete, submitted)",
    "Always 404 attempt_not_found")
async def _(cx):
    other = newsid()
    sid, aid = await mk(cx)
    for ans in [None, {"q1": "a"}, ALL_OK, "submit"]:
        if ans == "submit":
            await submit(cx, sid, aid)
        elif ans:
            await fill(cx, sid, aid, ans)
        for m, p, kw in [("GET", A(aid), {}), ("PUT", A(aid) + "/answers", {"json": {"answers": {"q1": "a"}}}),
                         ("POST", A(aid) + "/submit", {}), ("GET", A(aid) + "/results", {})]:
            expect_err(await cx.req(m, p, other, **kw), 404, "attempt_not_found", f"{ans} {m} {p[-8:]}: ")


# ================================================================= CROSS-STUDENT
@sc("XS-01", "cross-student", "contract", "Another student GETs my attempt", "404 attempt_not_found, no answers/status in body")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    r = await cx.req("GET", A(aid), newsid())
    expect_err(r, 404, "attempt_not_found")
    check(set(J(r)) == {"detail"} and aid not in r.text, f"body {r.text}")


@sc("XS-02", "cross-student", "contract", "Another student saves to my attempt", "404; my answers unchanged")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    expect_err(await save(cx, newsid(), aid, {"q1": "b", "q2": "b"}), 404, "attempt_not_found")
    check((await get_attempt(cx, sid, aid))["answers"] == {"q1": "a"}, "foreign write landed")


@sc("XS-03", "cross-student", "contract", "Another student submits my complete attempt", "404; I can still submit it, once")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    expect_err(await submit(cx, newsid(), aid), 404, "attempt_not_found")
    check((await submit(cx, sid, aid)).status_code == 200, "owner submit failed after foreign attempt")


@sc("XS-04", "cross-student", "contract", "Another student asks for results of my submitted attempt", "404, body has no answers/explanations")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    r = await cx.req("GET", A(aid) + "/results", newsid())
    expect_err(r, 404, "attempt_not_found")
    check(not leak_problems(r) and "score" not in r.text, f"body {r.text}")


@sc("XS-05", "cross-student", "contract",
    "Existence oracle: for every attempt endpoint compare not-owned vs nonexistent id (incl. same-length id), in each state",
    "Identical status and body (code and message), so existence cannot be inferred")
async def _(cx):
    sid, aid = await mk(cx)
    sid2, aid2, _ = await done(cx, ALL_OK)
    other = newsid()
    ghost = "".join(random.choice("abcdefghijklmnopqrstuvwxyz0123456789") for _ in range(len(aid)))
    for owner_aid in (aid, aid2):
        for m, p, kw in [("GET", "", {}), ("PUT", "/answers", {"json": {"answers": {"q1": "a"}}}),
                         ("PUT", "/answers", {"json": {"answers": {"q9": "bad"}}}), ("POST", "/submit", {}), ("GET", "/results", {})]:
            r1 = await cx.req(m, A(owner_aid) + p, other, **kw)
            r2 = await cx.req(m, A(ghost) + p, other, **kw)
            check(r1.status_code == r2.status_code and J(r1) == J(r2),
                  f"{m} {p or '/'}: not-owned {short(r1)} vs unknown {short(r2)}")
            check(r1.headers.get("content-type") == r2.headers.get("content-type"), "content-type differs")


@sc("XS-06", "cross-student", "contract", "Two students, same set, each with attempts: no answers visible across, each sees only own",
    "Own GET shows own answers only; foreign GET 404; new attempts empty")
async def _(cx):
    a, b = newsid(), newsid()
    _, aa = await mk(cx, a)
    _, ab = await mk(cx, b)
    await fill(cx, a, aa, {"q1": "a"})
    await fill(cx, b, ab, {"q1": "c", "q2": "c"})
    check((await get_attempt(cx, a, aa))["answers"] == {"q1": "a"}, "A sees wrong data")
    check((await get_attempt(cx, b, ab))["answers"] == {"q1": "c", "q2": "c"}, "B sees wrong data")
    check((await cx.req("GET", A(ab), a)).status_code == 404 and (await cx.req("GET", A(aa), b)).status_code == 404, "cross read")


@sc("XS-07", "cross-student", "robustness", "Student ids that are prefixes / substrings of one another ('bob' vs 'bobby', 's1' vs 's10')",
    "Exact match only: 404 both ways")
async def _(cx):
    base = "bob" + uuid.uuid4().hex[:5]
    sid, aid = await mk(cx, base)
    sid2, aid2 = await mk(cx, base + "by")
    check((await cx.req("GET", A(aid), base + "by")).status_code == 404, "longer id read shorter's attempt")
    check((await cx.req("GET", A(aid2), base)).status_code == 404, "shorter id read longer's attempt")
    check((await cx.req("GET", A(aid), base[:-1])).status_code == 404, "prefix id read attempt")


@sc("XS-08", "cross-student", "robustness", "Enumeration probes: GET /api/attempts, /api/attempts/, /api/practice-sets/intro-se-1/attempts, /api/students/x/attempts, ?student=other",
    "404/405 (or redirect) and the body never contains other students' attempt ids")
async def _(cx):
    sid, aid = await mk(cx)
    for p in ["/api/attempts", "/api/attempts/", f"/api/practice-sets/{SET}/attempts", f"/api/practice-sets/{SET}/attempts/",
              f"/api/students/{sid}/attempts", "/api/attempts?student=" + sid, "/api/attempts/*", "/api/attempts/%25"]:
        other = newsid()
        r = await cx.req("GET", p, other, follow_redirects=True)
        check(r.status_code < 500, f"{p}: {short(r)}")
        check(aid not in r.text, f"{p} exposes another student's attempt id")
        check(r.status_code != 200, f"{p} returned 200: {short(r)}")


@sc("XS-09", "cross-student", "robustness", "Probing attempt ids: swapped case, 8-char prefix, trailing space/slash, id with %2e, uppercase",
    "404 for every variant (exact id match only) when requested by the owner")
async def _(cx):
    sid, aid = await mk(cx)
    variants = {aid[:8], aid[:-1], aid + "x", aid.swapcase(), aid.upper(), aid.lower(), aid + "%20", aid + "/", aid + "%00"}
    variants.discard(aid)
    for v in variants:
        r = await cx.req("GET", f"/api/attempts/{v}", sid)
        check(r.status_code in (404, 307, 308), f"variant {v!r}: {short(r)}")
        if r.status_code == 307 or r.status_code == 308:
            continue
        check(r.status_code != 200, f"variant {v!r} resolved to an attempt")


@sc("XS-10", "cross-student", "robustness", "Random unknown ids of many shapes (empty-ish, long, unicode, injection, path traversal, 100 random) for all endpoints",
    "404 attempt_not_found (documented shape) with a valid header; never 5xx; never 200")
async def _(cx):
    ids = ["x", "0", "-1", "null", "../../etc/passwd", "%2e%2e%2f", "' OR 1=1 --", "\u5b66\u751f", "a" * 5000, "%00", "{}", "undefined",
           "*", "..", "attempt-1", "00000001", "00000000"]
    ids += [uuid.uuid4().hex for _ in range(10)]
    for i in ids:
        for m, p, kw in [("GET", "", {}), ("PUT", "/answers", {"json": {"answers": {"q1": "a"}}}), ("POST", "/submit", {}),
                         ("GET", "/results", {})]:
            r = await cx.req(m, f"/api/attempts/{i}{p}", newsid(), **kw)
            check(r.status_code < 500 and r.status_code != 200, f"{m} {i[:20]!r}{p}: {short(r)}")
            if "/" not in i and "%2" not in i.lower() and ".." not in i:
                expect_err(r, 404, "attempt_not_found", f"{m} {i[:20]!r}{p}: ")


# ================================================================= LEAK (AC8)
@sc("LEAK-01", "leak", "contract",
    "Sweep ~60 pre-submission calls (start, GET set, GET attempt, valid/invalid PUTs, incomplete submits, early results, 401s, 404s, other-student calls) with a fully answered but unsubmitted attempt",
    "No response contains an explanation, correct choice field/phrase, key_version or answer-key wording")
async def _(cx):
    resps = []

    async def R(*a, **k):
        r = await cx.req(*a, **k)
        resps.append(r)
        return r

    other = newsid()
    await R("GET", f"/api/practice-sets/{SET}")
    await R("GET", "/api/practice-sets/nope")
    sid, aid = await mk(cx)
    await R("GET", A(aid), sid)
    await R("GET", A(aid) + "/results", sid)
    await R("POST", A(aid) + "/submit", sid)
    for q in QIDS:
        for c in (["a", "b", "c"] if q == "q1" else []) + ["z", "", None, 1]:
            await R("PUT", A(aid) + "/answers", sid, json={"answers": {q: c}})
    await R("PUT", A(aid) + "/answers", sid, json={"answers": {"q9": "a"}})
    await R("PUT", A(aid) + "/answers", sid, content=b"garbage", headers={"content-type": "application/json"})
    await R("POST", A(aid) + "/submit", sid)  # partial
    await R("GET", A(aid) + "/results", sid)
    await R("GET", A(aid), other)
    await R("PUT", A(aid) + "/answers", other, json={"answers": {"q1": "a"}})
    await R("POST", A(aid) + "/submit", other)
    await R("GET", A(aid) + "/results", other)
    await R("GET", A(aid))
    await R("GET", A(aid) + "/results")
    await R("POST", f"/api/practice-sets/{SET}/attempts")
    await R("POST", "/api/practice-sets/nope/attempts", sid)
    await R("GET", A("nope-nope-1"), sid)
    await R("GET", A("nope-nope-1") + "/results", sid)
    await R("DELETE", A(aid), sid)
    await R("PATCH", A(aid), sid)
    await R("POST", A(aid) + "/results", sid)
    await R("PUT", A(aid) + "/answers", sid, json={"answers": ALL_OK})
    await R("GET", A(aid), sid)
    await R("GET", A(aid) + "/results", sid)  # complete but unsubmitted
    await R("POST", A(aid) + "/submit", sid, json={"score": {"correct": 3, "total": 3}})  # this one submits
    bad = []
    # last submit success is post-submission: exclude it from the leak scan
    for r in resps[:-1]:
        p = leak_problems(r)
        if p:
            bad.append(f"{r.request.method} {r.request.url.path} {short(r)[:120]}: {p}")
    check(not bad, " | ".join(bad[:4]))


@sc("LEAK-02", "leak", "contract", "invalid_choice / unknown_question messages compared across q1..q3 and several bad values",
    "Message does not depend on which choice is correct (identical once the question id is normalised)")
async def _(cx):
    sid, aid = await mk(cx)
    for bad in ["z", "d", "A"]:
        msgs = {}
        for q in QIDS:
            r = await save(cx, sid, aid, {q: bad})
            expect_err(r, 422, "invalid_choice")
            m = J(r)["detail"]["message"]
            for tok in [q, TEXTS[q]] + ([CODE[q]] if CODE[q] else []):
                m = m.replace(tok, "QID")
            m = m.replace(bad, "BAD")
            msgs[q] = m
        check(len(set(msgs.values())) == 1, f"messages depend on the question (key leak?): {msgs}")
    # same for answers already holding the right/wrong value
    await fill(cx, sid, aid, {"q1": "a"})
    r1 = J(await save(cx, sid, aid, {"q1": "z"}))["detail"]["message"]
    await fill(cx, sid, aid, {"q1": "b"})
    r2 = J(await save(cx, sid, aid, {"q1": "z"}))["detail"]["message"]
    check(r1 == r2, f"message depends on the saved answer's correctness: {r1!r} vs {r2!r}")


@sc("LEAK-03", "leak", "robustness", "Query-string probes (?debug=1, ?include_answers=true, ?show_key=1, ?admin=true, ?include=explanation, ?version=v1) on set, attempt, PUT, results",
    "No leak; no extra fields compared to the plain response")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    qs = ["debug=1", "include_answers=true", "show_key=1", "admin=true", "include=explanation", "version=v1", "answers=1",
          "expand=results", "teacher=1", "reveal=true"]
    plain_set = (await cx.req("GET", f"/api/practice-sets/{SET}")).text
    plain_get = shape(J(await cx.req("GET", A(aid), sid)))
    for q in qs:
        r = await cx.req("GET", f"/api/practice-sets/{SET}?{q}")
        assert_noleak(r)
        check(r.text == plain_set, f"set changed with ?{q}")
        r = await cx.req("GET", A(aid) + "?" + q, sid)
        assert_noleak(r)
        check(shape(J(r)) == plain_get, f"GET attempt changed shape with ?{q}")
        assert_noleak(await cx.req("PUT", A(aid) + "/answers?" + q, sid, json={"answers": {"q1": "a"}}))
        r = await cx.req("GET", A(aid) + "/results?" + q, sid)
        expect_err(r, 403, "not_submitted", f"?{q}: ")
        assert_noleak(r)


@sc("LEAK-04", "leak", "robustness", "Privilege probes: X-Student-Id 'admin'/'teacher'/'root'/'*', extra headers X-Admin, X-Role, Authorization, X-Debug",
    "No special rights: foreign attempt 404, results of unsubmitted 403/404, no leak")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    for v in ["admin", "teacher", "root", "*", "system", "ADMIN"]:
        for p in ["", "/results"]:
            r = await cx.req("GET", A(aid) + p, v)
            check(r.status_code == 404, f"student {v!r} on {p or '/'}: {short(r)}")
            assert_noleak(r)
    hdrs = {"X-Admin": "true", "X-Role": "teacher", "Authorization": "Bearer admin", "X-Debug": "1", "X-Forwarded-For": "127.0.0.1"}
    r = await cx.req("GET", A(aid) + "/results", sid, headers=hdrs)
    expect_err(r, 403, "not_submitted")
    r = await cx.req("GET", A(aid), newsid(), headers=hdrs)
    expect_err(r, 404, "attempt_not_found")
    assert_noleak(await cx.req("GET", f"/api/practice-sets/{SET}", headers=hdrs))


@sc("LEAK-05", "leak", "contract", "Differential: PUT/GET responses after saving the CORRECT vs a WRONG choice for q1",
    "Same structure (keys/types) either way: nothing reveals correctness (no score, flags, feedback)")
async def _(cx):
    s1, a1 = await mk(cx)
    s2, a2 = await mk(cx)
    r1 = await save(cx, s1, a1, {"q1": "a"})
    r2 = await save(cx, s2, a2, {"q1": "b"})
    check(shape(J(r1)) == shape(J(r2)), f"PUT shape differs: {J(r1)} vs {J(r2)}")
    g1 = await cx.req("GET", A(a1), s1)
    g2 = await cx.req("GET", A(a2), s2)
    check(shape(J(g1)) == shape(J(g2)), f"GET shape differs: {J(g1)} vs {J(g2)}")
    for r in (r1, g1):
        j = J(r)
        extra = set(j) - {"attempt_id", "set_id", "status", "answers"}
        check(not extra, f"unexpected pre-submit fields {extra}: {j}")
    # same for the invalid_choice error
    e1 = await save(cx, s1, a1, {"q2": "z"})
    e2 = await save(cx, s2, a2, {"q2": "z"})
    check(shape(J(e1)) == shape(J(e2)), "error shape differs by saved correctness")


@sc("LEAK-06", "leak", "contract", "Incomplete-submit error body in detail (every partial state)",
    "Only code, message and missing (ids); message contains no explanation, no choice ids tied to the key")
async def _(cx):
    msgs = []
    for ans in [{}, {"q1": "a"}, {"q2": "b"}, {"q3": "c"}, {"q1": "b", "q2": "a"}]:
        sid, aid = await mk(cx)
        if ans:
            await fill(cx, sid, aid, ans)
        r = await submit(cx, sid, aid)
        expect_err(r, 422, "incomplete")
        d = J(r)["detail"]
        check(set(d) == {"code", "message", "missing"}, f"keys {sorted(d)}")
        check(all(m in QIDS for m in d["missing"]), f"non-id in missing {d['missing']}")
        assert_noleak(r)
        msgs.append((ans, d))
    # message must not depend on whether the saved answers are right
    sA, aA = await mk(cx)
    sB, aB = await mk(cx)
    await fill(cx, sA, aA, {"q1": "a", "q2": "b"})
    await fill(cx, sB, aB, {"q1": "b", "q2": "a"})
    mA = J(await submit(cx, sA, aA))["detail"]["message"]
    mB = J(await submit(cx, sB, aB))["detail"]["message"]
    check(mA == mB, f"incomplete message differs with answer correctness: {mA!r} vs {mB!r}")


# ================================================================= ERRORS
@sc("ERR-01", "errors", "contract", "Collect every documented 401/403/404/409 error and check the body",
    "Exactly {detail:{code,message}}; right code; message a non-empty string; JSON content type")
async def _(cx):
    sid, aid = await mk(cx)
    sid2, aid2, _ = await done(cx, ALL_OK)
    other = newsid()
    cases = [
        (await cx.req("POST", f"/api/practice-sets/{SET}/attempts"), 401, "missing_student"),
        (await cx.req("GET", A(aid)), 401, "missing_student"),
        (await cx.req("PUT", A(aid) + "/answers", json={"answers": {}}), 401, "missing_student"),
        (await cx.req("POST", A(aid) + "/submit"), 401, "missing_student"),
        (await cx.req("GET", A(aid) + "/results"), 401, "missing_student"),
        (await cx.req("GET", "/api/practice-sets/nope"), 404, "set_not_found"),
        (await cx.req("POST", "/api/practice-sets/nope/attempts", sid), 404, "set_not_found"),
        (await cx.req("GET", A(aid), other), 404, "attempt_not_found"),
        (await cx.req("GET", A("nope-nope-1"), sid), 404, "attempt_not_found"),
        (await cx.req("PUT", A("nope-nope-1") + "/answers", sid, json={"answers": {}}), 404, "attempt_not_found"),
        (await cx.req("POST", A("nope-nope-1") + "/submit", sid), 404, "attempt_not_found"),
        (await cx.req("GET", A("nope-nope-1") + "/results", sid), 404, "attempt_not_found"),
        (await cx.req("GET", A(aid) + "/results", sid), 403, "not_submitted"),
        (await save(cx, sid2, aid2, {"q1": "a"}), 409, "already_submitted"),
        (await submit(cx, sid2, aid2), 409, "already_submitted"),
    ]
    bad = []
    for r, st, code in cases:
        j = J(r)
        ok = (r.status_code == st and isinstance(j, dict) and set(j) == {"detail"} and isinstance(j["detail"], dict)
              and set(j["detail"]) == {"code", "message"} and j["detail"]["code"] == code
              and isinstance(j["detail"]["message"], str) and j["detail"]["message"].strip()
              and "json" in r.headers.get("content-type", ""))
        if not ok:
            bad.append(f"{r.request.method} {r.request.url.path} expected {st} {code}, got {short(r)} ct={r.headers.get('content-type')}")
    check(not bad, " | ".join(bad[:3]))


@sc("ERR-02", "errors", "contract", "Collect 422 errors: unknown_question, invalid_choice, incomplete",
    "{detail:{code,message}} (+missing for incomplete); right codes and status 422")
async def _(cx):
    sid, aid = await mk(cx)
    cases = [(await save(cx, sid, aid, {"q9": "a"}), "unknown_question", {"code", "message"}),
             (await save(cx, sid, aid, {"q1": "z"}), "invalid_choice", {"code", "message"}),
             (await submit(cx, sid, aid), "incomplete", {"code", "message", "missing"})]
    for r, code, keys in cases:
        j = J(r)
        check(r.status_code == 422 and isinstance(j, dict) and set(j) == {"detail"} and isinstance(j["detail"], dict)
              and set(j["detail"]) == keys and j["detail"]["code"] == code and isinstance(j["detail"]["message"], str)
              and j["detail"]["message"].strip(), f"{code}: {short(r)}")


@sc("ERR-03", "errors", "robustness", "Error messages for documented errors and malformed bodies: no stack traces, exception class names, file paths, or the caller's student id",
    "Clean human-readable messages")
async def _(cx):
    sid, aid = await mk(cx)
    rs = [await cx.req("GET", A(aid), newsid()), await cx.req("GET", A("nope-nope-1"), sid),
          await cx.req("PUT", A(aid) + "/answers", sid, content=b"\xff{", headers={"content-type": "application/json"}),
          await cx.req("PUT", A(aid) + "/answers", sid, content=b"[" * 100000, headers={"content-type": "application/json"}),
          await cx.req("PUT", A(aid) + "/answers", sid, content=b"not json", headers={"content-type": "application/json"}),
          await save(cx, sid, aid, {"q1": 5}), await save(cx, sid, aid, {"q9": "a"}), await save(cx, sid, aid, {"q1": "z"}),
          await submit(cx, sid, aid), await cx.req("GET", A(aid) + "/results", sid)]
    pat = re.compile(r"Traceback|File \"|\.py\b|\b[A-Z][A-Za-z]*(Error|Exception)\b|/usr/|site-packages|C:\\\\")
    for r in rs:
        check(not pat.search(r.text), f"{r.request.method} {r.request.url.path}: internals in body {r.text[:150]!r}")
        if r.status_code != 422 or code_of(r):  # documented errors may not echo the student id
            check(sid not in r.text, f"student id echoed in {r.text[:120]!r}")


@sc("ERR-04", "errors", "robustness", "Malformed-body 422s (default FastAPI body allowed): status/shape sanity",
    "400-499, JSON content type, JSON-parseable body")
async def _(cx):
    sid, aid = await mk(cx)
    for raw in [b"garbage", b'{"answers": []}', b"[]"]:
        r = await cx.req("PUT", A(aid) + "/answers", sid, content=raw, headers={"content-type": "application/json"})
        check(400 <= r.status_code < 500 and "json" in r.headers.get("content-type", "") and J(r) is not None, short(r))


# ================================================================= METHODS
@sc("METH-01", "methods", "robustness",
    "Unsupported methods on every route (DELETE/PATCH/POST/PUT as applicable, with valid auth and body)",
    "404/405; the attempt and the set are unchanged and still readable afterwards")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    body = dict(json={"answers": ALL_OK})
    cases = [("DELETE", A(aid)), ("PATCH", A(aid)), ("POST", A(aid)), ("PUT", A(aid)),
             ("GET", A(aid) + "/answers"), ("POST", A(aid) + "/answers"), ("PATCH", A(aid) + "/answers"), ("DELETE", A(aid) + "/answers"),
             ("GET", A(aid) + "/submit"), ("PUT", A(aid) + "/submit"), ("DELETE", A(aid) + "/submit"), ("PATCH", A(aid) + "/submit"),
             ("POST", A(aid) + "/results"), ("PUT", A(aid) + "/results"), ("DELETE", A(aid) + "/results"), ("PATCH", A(aid) + "/results"),
             ("POST", f"/api/practice-sets/{SET}"), ("PUT", f"/api/practice-sets/{SET}"), ("DELETE", f"/api/practice-sets/{SET}"),
             ("PATCH", f"/api/practice-sets/{SET}"), ("GET", f"/api/practice-sets/{SET}/attempts"),
             ("PUT", f"/api/practice-sets/{SET}/attempts"), ("DELETE", f"/api/practice-sets/{SET}/attempts")]
    for m, p in cases:
        r = await cx.req(m, p, sid, **body)
        check(r.status_code in (404, 405), f"{m} {p[-40:]}: {short(r)}")
        assert_noleak(r)
    j = await get_attempt(cx, sid, aid)
    check(j["answers"] == {"q1": "a"} and j["status"] == "in_progress", f"state changed {j}")
    check((await cx.req("GET", f"/api/practice-sets/{SET}")).status_code == 200, "set gone")


@sc("METH-02", "methods", "robustness", "HEAD and OPTIONS on all routes; HEAD by non-owner / no header",
    "No 5xx; HEAD/OPTIONS never 200 for someone else's attempt; no leak")
async def _(cx):
    sid, aid, _ = await done(cx, ALL_OK)
    paths = [A(aid), A(aid) + "/answers", A(aid) + "/submit", A(aid) + "/results", f"/api/practice-sets/{SET}",
             f"/api/practice-sets/{SET}/attempts"]
    for m in ["HEAD", "OPTIONS"]:
        for p in paths:
            r = await cx.req(m, p, sid)
            check(r.status_code < 500, f"{m} {p}: {short(r)}")
            assert_noleak(r)
            if p.startswith("/api/attempts"):
                for who in (newsid(), None):
                    r = await cx.req(m, p, who)
                    check(r.status_code < 500, f"{m} {p} who={who}: {short(r)}")
                    if m == "HEAD":
                        check(r.status_code != 200, f"HEAD {p} revealed an attempt to {who}")


# ================================================================= STATE
@sc("STATE-01", "state", "contract", "GET attempt after each action (start, save, failed submit, submit)",
    "Read-your-writes; answers contain only saved question ids (no null placeholders)")
async def _(cx):
    sid, aid = await mk(cx)
    check((await get_attempt(cx, sid, aid))["answers"] == {}, "start")
    await fill(cx, sid, aid, {"q2": "a"})
    check((await get_attempt(cx, sid, aid))["answers"] == {"q2": "a"}, "after save")
    await submit(cx, sid, aid)
    check((await get_attempt(cx, sid, aid))["answers"] == {"q2": "a"}, "after failed submit")
    await fill(cx, sid, aid, {"q1": "c", "q3": "b"})
    r = await submit(cx, sid, aid)
    check(r.status_code == 200, short(r))
    g = await get_attempt(cx, sid, aid)
    check(g["status"] == "submitted" and g["answers"] == {"q1": "c", "q2": "a", "q3": "b"}, f"{g}")


@sc("STATE-02", "state", "contract", "Full lifecycle then replay every endpoint", "Each endpoint answers per the state machine")
async def _(cx):
    sid, aid = await mk(cx)
    expect_err(await cx.req("GET", A(aid) + "/results", sid), 403, "not_submitted")
    expect_err(await submit(cx, sid, aid), 422, "incomplete")
    await fill(cx, sid, aid, ALL_OK)
    expect_err(await cx.req("GET", A(aid) + "/results", sid), 403, "not_submitted")
    check((await submit(cx, sid, aid)).status_code == 200, "submit")
    check((await cx.req("GET", A(aid) + "/results", sid)).status_code == 200, "results")
    expect_err(await submit(cx, sid, aid), 409, "already_submitted")
    expect_err(await save(cx, sid, aid, {"q1": "b"}), 409, "already_submitted")
    check((await cx.req("GET", A(aid), sid)).status_code == 200, "get after submit")


@sc("STATE-03", "state", "robustness", "All successful responses use a JSON content type", "application/json")
async def _(cx):
    sid, aid = await mk(cx)
    rs = [await cx.req("GET", f"/api/practice-sets/{SET}"), await cx.req("GET", A(aid), sid),
          await save(cx, sid, aid, ALL_OK), await submit(cx, sid, aid), await cx.req("GET", A(aid) + "/results", sid)]
    for r in rs:
        check(r.status_code == 200 and "application/json" in r.headers.get("content-type", ""), f"{r.request.url.path}: {short(r)}")


# ================================================================= CONCURRENCY
@sc("CONC-01", "concurrency", "contract", "25 simultaneous submits on one complete attempt (2/3 score)",
    "Exactly one 200; all others 409 already_submitted; no 5xx; results consistent")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, MIX2)
    rs = await asyncio.gather(*[submit(cx, sid, aid) for _ in range(25)])
    ok = [r for r in rs if r.status_code == 200]
    codes = sorted({(r.status_code, code_of(r)) for r in rs})
    check(len(ok) == 1, f"{len(ok)} submits succeeded (expected exactly 1); outcomes {codes}")
    check(all(r.status_code == 409 and code_of(r) == "already_submitted" for r in rs if r not in ok), f"outcomes {codes}")
    check(J(ok[0])["score"] == {"correct": 2, "total": 3}, "score")
    check(J(await cx.req("GET", A(aid) + "/results", sid))["score"] == {"correct": 2, "total": 3}, "results score")


@sc("CONC-02", "concurrency", "robustness", "Simultaneous submits by the owner and 10 other students on the same attempt",
    "Owner exactly one 200 or 409 combos; every other student 404; nothing changes for them")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)
    tasks = [submit(cx, sid, aid) for _ in range(3)] + [submit(cx, newsid(), aid) for _ in range(10)]
    rs = await asyncio.gather(*tasks)
    check(sum(1 for r in rs[:3] if r.status_code == 200) == 1, f"owner outcomes {[r.status_code for r in rs[:3]]}")
    check(all(r.status_code == 404 for r in rs[3:]), f"others {[r.status_code for r in rs[3:]]}")


@sc("CONC-03", "concurrency", "robustness", "30 simultaneous saves of different questions on one attempt",
    "All 200 and no lost update: all three answers stored")
async def _(cx):
    sid, aid = await mk(cx)
    rs = await asyncio.gather(*[save(cx, sid, aid, {QIDS[i % 3]: KEY[QIDS[i % 3]]}) for i in range(30)])
    check(all(r.status_code == 200 for r in rs), f"statuses {sorted({r.status_code for r in rs})}")
    got = (await get_attempt(cx, sid, aid))["answers"]
    check(got == ALL_OK, f"lost updates: stored {got}")


@sc("CONC-04", "concurrency", "robustness", "60 simultaneous attempt creations (some by the same student)",
    "All 201, all ids unique, all independent")
async def _(cx):
    s = newsid()
    rs = await asyncio.gather(*[cx.req("POST", f"/api/practice-sets/{SET}/attempts", s if i % 2 else newsid()) for i in range(60)])
    check(all(r.status_code == 201 for r in rs), f"statuses {sorted({r.status_code for r in rs})}")
    ids = [J(r)["attempt_id"] for r in rs]
    check(len(set(ids)) == 60, "duplicate attempt ids under concurrency")


@sc("CONC-05", "concurrency", "robustness", "20 simultaneous submits on an INCOMPLETE attempt, then complete and submit it",
    "All 422 incomplete; attempt not locked; later submit succeeds")
async def _(cx):
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, {"q1": "a"})
    rs = await asyncio.gather(*[submit(cx, sid, aid) for _ in range(20)])
    check(all(r.status_code == 422 and code_of(r) == "incomplete" for r in rs), f"{sorted({(r.status_code, code_of(r)) for r in rs})}")
    check((await get_attempt(cx, sid, aid))["answers"] == {"q1": "a"}, "answers changed")
    await fill(cx, sid, aid, {"q2": "b", "q3": "c"})
    check((await submit(cx, sid, aid)).status_code == 200, "later submit failed")


@sc("CONC-06", "concurrency", "robustness", "12 different attempts submitted simultaneously with different answers",
    "Each gets its own true score; no cross-talk")
async def _(cx):
    sets = [ALL_OK, ALL_BAD, MIX2, {"q1": "b", "q2": "b", "q3": "c"}] * 3
    made = []
    for ans in sets:
        sid, aid = await mk(cx)
        await fill(cx, sid, aid, ans)
        made.append((sid, aid, ans))
    rs = await asyncio.gather(*[submit(cx, s, a) for s, a, _ in made])
    for (s, a, ans), r in zip(made, rs):
        check(r.status_code == 200 and J(r)["score"]["correct"] == exp_score(ans) and J(r)["attempt_id"] == a, f"{ans}: {short(r)}")


@sc("CONC-07", "concurrency", "robustness", "30 simultaneous saves to the same question with values a/b/c",
    "No 5xx; the final stored value is one of the sent values and equals GET")
async def _(cx):
    sid, aid = await mk(cx)
    rs = await asyncio.gather(*[save(cx, sid, aid, {"q1": "abc"[i % 3]}) for i in range(30)])
    check(all(r.status_code == 200 for r in rs), f"{sorted({r.status_code for r in rs})}")
    check((await get_attempt(cx, sid, aid))["answers"]["q1"] in ("a", "b", "c"), "bad final value")


def apply_slow(spec):
    modname, attr = spec.split(":", 1)
    mod = importlib.import_module(modname)
    parts = attr.split(".")
    holder = mod
    for p in parts[:-1]:
        holder = getattr(holder, p)
    orig = getattr(holder, parts[-1])
    if inspect.iscoroutinefunction(orig):
        @functools.wraps(orig)
        async def wrapper(*a, **k):
            await asyncio.sleep(0.3)
            return await orig(*a, **k)
    else:
        @functools.wraps(orig)
        def wrapper(*a, **k):
            import time
            time.sleep(0.3)
            return orig(*a, **k)
    patched = []
    setattr(holder, parts[-1], wrapper)
    patched.append((holder, parts[-1], orig))
    for m in list(sys.modules.values()):
        try:
            d = vars(m)
        except TypeError:
            continue
        for k, v in list(d.items()):
            if v is orig and (m, k) != (holder, parts[-1]):
                setattr(m, k, wrapper)
                patched.append((m, k, orig))

    def restore():
        for h, k, o in patched:
            setattr(h, k, o)
    return restore


async def race_once(cx, delay):
    """A save (q3 -> wrong) races a submit of an otherwise complete, all-correct attempt."""
    sid, aid = await mk(cx)
    await fill(cx, sid, aid, ALL_OK)

    async def do_save():
        return await save(cx, sid, aid, {"q3": "a"})

    async def do_sub():
        if delay:
            await asyncio.sleep(delay)
        return await submit(cx, sid, aid)

    if not delay and random.random() < 0.5:
        rb, rs = await asyncio.gather(do_sub(), do_save())
    else:
        rs, rb = await asyncio.gather(do_save(), do_sub())
    probs = []
    if rs.status_code >= 500 or rb.status_code >= 500:
        return [f"5xx: save {short(rs)} submit {short(rb)}"]
    if rb.status_code != 200:
        return [f"submit of a complete attempt returned {short(rb)}"]
    fin = await cx.req("GET", A(aid), sid)
    fa = J(fin)["answers"]
    reported = J(rb)["score"]["correct"]
    if J(fin)["status"] != "submitted":
        probs.append("status not submitted after successful submit")
    if rs.status_code == 200 and fa.get("q3") != "a":
        probs.append("save reported 200 but final q3 != 'a'")
    if rs.status_code == 409 and fa.get("q3") != "c":
        probs.append(f"save rejected (409) but final q3 == {fa.get('q3')!r}")
    if rs.status_code not in (200, 409):
        probs.append(f"save returned {short(rs)}")
    if reported != exp_score(fa):
        probs.append(f"submit reported {reported}/3 but the stored answers score {exp_score(fa)}/3 (save {rs.status_code}, final {fa})")
    res = await cx.req("GET", A(aid) + "/results", sid)
    if res.status_code == 200:
        jr = J(res)
        if jr["score"]["correct"] != reported or jr["answers"] != fa:
            probs.append(f"results disagree with submit/answers: {jr['score']} {jr['answers']} vs {reported} {fa}")
    else:
        probs.append(f"results {short(res)}")
    return probs


@sc("CONC-08", "concurrency", "contract",
    "Save racing a submit. With --slow: the named function is delayed 0.3 s, save starts, 0.1 s later submit starts. Without --slow: 40 simultaneous save+submit pairs (kind reported as robustness)",
    "Final stored state matches what submit reported: a save that succeeded before the submit counts in the score; one after gets 409 and leaves answers unchanged")
async def _(cx):
    if cx.slow:
        restore = apply_slow(cx.slow)
        try:
            probs = await race_once(cx, 0.1)
        finally:
            restore()
        check(not probs, "; ".join(probs))
    else:
        bad = []
        for _ in range(40):
            bad += await race_once(cx, 0)
            if bad:
                break
        check(not bad, "; ".join(bad))


# ----------------------------------------------------------------- runner
def load_app(app_dir):
    sys.path.insert(0, os.path.abspath(app_dir))
    os.chdir(os.path.abspath(app_dir))
    with contextlib.redirect_stdout(sys.stderr):
        mod = importlib.import_module("main")
    return mod.app


async def run(app, slow):
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    out = []
    async with httpx.AsyncClient(transport=transport, base_url="http://t", timeout=60) as client:
        cx = Cx(client, slow)
        for s in SCEN:
            kind = s["kind"]
            if s["id"] == "CONC-08" and not slow:
                kind = "robustness"
            row = dict(id=s["id"], category=s["category"], kind=kind, scenario=s["scenario"], expected=s["expected"],
                       result="pass", detail="")
            try:
                with contextlib.redirect_stdout(sys.stderr):
                    await asyncio.wait_for(s["fn"](cx), timeout=120)
            except AssertionError as e:
                row.update(result="fail", detail=str(e)[:700])
            except BaseException as e:  # never crash the runner
                if isinstance(e, (KeyboardInterrupt, SystemExit)):
                    raise
                row.update(result="fail", detail=f"{type(e).__name__}: {e}"[:300] + " @ " + traceback.format_exc().splitlines()[-3].strip()[:200])
            out.append(row)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("app_dir", nargs="?")
    ap.add_argument("--slow", default=None)
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args()
    if a.list:
        print(json.dumps([{k: v for k, v in s.items() if k != "fn"} for s in SCEN], indent=1))
        return
    try:
        app = load_app(a.app_dir)
    except BaseException as e:
        print(json.dumps([{"id": "IMPORT", "category": "setup", "kind": "contract", "scenario": "import main:app",
                           "expected": "app imports", "result": "fail", "detail": f"{type(e).__name__}: {e}"}]))
        return
    res = asyncio.run(run(app, a.slow))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
