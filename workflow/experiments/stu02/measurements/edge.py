"""Edge-case battery for one STU-02 implementation. Usage: python edge.py <version_dir> <race_module> <race_attr>

Prints a JSON list of {id, area, scenario, result, detail}; result is pass, fail or info.
"""
import asyncio
import importlib
import json
import sys
import threading
import time
import uuid

VERSION, RACE_MODULE, RACE_ATTR = sys.argv[1], sys.argv[2], sys.argv[3]
sys.path.insert(0, VERSION)
import httpx  # noqa: E402
from main import app  # noqa: E402

SET = "/api/practice-sets/intro-se-1"
KEY = {"q1": "a", "q2": "b", "q3": "c"}
EXPL = [
    "One focused responsibility makes a function easier to understand",
    "Tests protect expected behaviour",
    "len returns the number of items",
]
SEEN = []  # every response before any submission, for the leak sweep
ERRORS = []  # every non-2xx response, for the error-shape check


def call(method, path, student=None, json_body=None, content=None, headers=None, track=True):
    hdrs = list((headers or {}).items())
    if student is not None:
        hdrs.append(("X-Student-Id", student))
    kwargs = {"headers": hdrs}
    if json_body is not None:
        kwargs["json"] = json_body
    if content is not None:
        kwargs["content"] = content

    async def send():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url="http://t") as c:
            return await c.request(method, path, **kwargs)

    r = asyncio.run(send())
    if r.status_code >= 400:
        ERRORS.append(r)
    if track:
        SEEN.append(r)
    return r


def sid():
    return "s-" + uuid.uuid4().hex[:10]


def start(student):
    return call("POST", f"{SET}/attempts", student).json()["attempt_id"]


def code(r):
    try:
        d = r.json().get("detail")
        return d.get("code") if isinstance(d, dict) else ("<list>" if isinstance(d, list) else str(d))
    except Exception:
        return "<non-json>"


def ok(cond, detail):
    return ("pass" if cond else "fail", detail)


def show(r):
    return f"{r.status_code} {code(r)}"


RESULTS = []


def scenario(sid_, area, text):
    def wrap(fn):
        try:
            result, detail = fn()
        except Exception as e:  # a crash in the harness call path counts against the version
            result, detail = "fail", f"exception: {type(e).__name__}: {str(e)[:120]}"
        RESULTS.append({"id": sid_, "area": area, "scenario": text, "result": result, "detail": detail})
        return fn
    return wrap


# ---- identity ----
@scenario("E01", "identity", "Start attempt with no X-Student-Id")
def _():
    r = call("POST", f"{SET}/attempts")
    return ok(r.status_code == 401 and code(r) == "missing_student", show(r))


@scenario("E02", "identity", "Start attempt with whitespace-only id")
def _():
    r = call("POST", f"{SET}/attempts", "   ")
    return ok(r.status_code == 401, show(r))


@scenario("E03", "identity", "Id with spaces at start, then same id without spaces")
def _():
    n = sid()
    a = start(f"  {n} ")
    r = call("GET", f"/api/attempts/{a}", n)
    return ok(r.status_code == 200, f"{show(r)} (200 = treated as same student)")


@scenario("E04", "identity", "Same letters, different case, is a different student")
def _():
    n = sid()
    a = start(n)
    r = call("GET", f"/api/attempts/{a}", n.upper())
    return ok(r.status_code == 404, show(r))


@scenario("E05", "identity", "10,000-character student id")
def _():
    r = call("POST", f"{SET}/attempts", "x" * 10000)
    return ok(r.status_code < 500, show(r))


@scenario("E07", "identity", "Two X-Student-Id headers: owner's id plus another")
def _():
    owner = sid()
    a = start(owner)
    r = call("GET", f"/api/attempts/{a}", headers={"X-Student-Id": "intruder"}, student=owner)
    return ("pass" if r.status_code < 500 else "fail", f"{show(r)} (behaviour recorded)")


# ---- sets and ids ----
@scenario("E08", "lookup", "Set id in a different case")
def _():
    r = call("GET", "/api/practice-sets/INTRO-SE-1")
    return ok(r.status_code == 404, show(r))


@scenario("E09", "lookup", "Start attempt on an unknown set")
def _():
    r = call("POST", "/api/practice-sets/nope/attempts", sid())
    return ok(r.status_code == 404 and code(r) == "set_not_found", show(r))


@scenario("E10", "lookup", "5,000-character attempt id")
def _():
    r = call("GET", "/api/attempts/" + "a" * 5000, sid())
    return ok(r.status_code == 404, show(r))


@scenario("E11", "lookup", "Attempt id with quotes and percent signs")
def _():
    r = call("GET", "/api/attempts/'%20OR%201=1--", sid())
    return ok(r.status_code == 404, show(r))


# ---- answer bodies ----
def fresh():
    s = sid()
    return s, start(s)


def saved(s, a):
    return call("GET", f"/api/attempts/{a}", s).json().get("answers")


@scenario("E12", "input", "Empty answers object")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {}})
    return ok(r.status_code == 200 and saved(s, a) == {}, show(r))


@scenario("E13", "input", "Extra top-level field next to answers")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": "a"}, "score": 99})
    return ("pass" if r.status_code in (200, 422) else "fail", f"{show(r)} saved={saved(s, a)}")


@scenario("E14", "input", "Answer value is a number; nothing saved")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": 1}})
    return ok(r.status_code == 422 and saved(s, a) == {}, f"{show(r)} saved={saved(s, a)}")


@scenario("E15", "input", "Answer value is null; nothing saved")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": None}})
    return ok(r.status_code == 422 and saved(s, a) == {}, f"{show(r)} saved={saved(s, a)}")


@scenario("E16", "input", "Answer value is a list; nothing saved")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": ["a"]}})
    return ok(r.status_code == 422 and saved(s, a) == {}, show(r))


@scenario("E17", "input", "Question id in upper case (Q1)")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"Q1": "a"}})
    return ok(r.status_code == 422 and code(r) == "unknown_question", show(r))


@scenario("E18", "input", "Choice id in upper case (A)")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": "A"}})
    return ok(r.status_code == 422 and code(r) == "invalid_choice", show(r))


@scenario("E19", "input", "1,000 unknown question ids in one save")
def _():
    s, a = fresh()
    t = time.time()
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {f"x{i}": "a" for i in range(1000)}})
    return ok(r.status_code == 422 and time.time() - t < 2, f"{show(r)} in {time.time() - t:.2f}s")


@scenario("E20", "input", "Malformed JSON body")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, content=b"{bad", headers={"content-type": "application/json"})
    return ok(r.status_code == 422, show(r))


@scenario("E21", "input", "No body at all")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s)
    return ok(r.status_code == 422, show(r))


@scenario("E22", "input", "Deeply nested JSON (5,000 levels)")
def _():
    s, a = fresh()
    body = ('{"answers":' + "[" * 5000 + "]" * 5000 + "}").encode()
    r = call("PUT", f"/api/attempts/{a}/answers", s, content=body, headers={"content-type": "application/json"})
    return ok(400 <= r.status_code < 500, show(r))


@scenario("E23", "input", "Form-encoded body instead of JSON")
def _():
    s, a = fresh()
    r = call("PUT", f"/api/attempts/{a}/answers", s, content=b"answers=q1", headers={"content-type": "application/x-www-form-urlencoded"})
    return ok(r.status_code == 422, show(r))


# ---- check order (plan: 401, then 404, then 409/403, then 422) ----
@scenario("E24", "order", "Another student's attempt with a malformed body")
def _():
    owner = sid()
    a = start(owner)
    r = call("PUT", f"/api/attempts/{a}/answers", sid(), content=b"{bad", headers={"content-type": "application/json"})
    return ok(r.status_code == 404, show(r))


@scenario("E25", "order", "Unknown attempt with a malformed body")
def _():
    r = call("PUT", "/api/attempts/does-not-exist/answers", sid(), content=b"{bad", headers={"content-type": "application/json"})
    return ok(r.status_code == 404, show(r))


@scenario("E26", "order", "Submitted attempt with a malformed body")
def _():
    s, a = fresh()
    call("PUT", f"/api/attempts/{a}/answers", s, {"answers": KEY})
    call("POST", f"/api/attempts/{a}/submit", s, track=False)
    r = call("PUT", f"/api/attempts/{a}/answers", s, content=b"{bad", headers={"content-type": "application/json"}, track=False)
    return ok(r.status_code == 409, show(r))


# ---- submission ----
@scenario("E27", "submission", "Submit with answers in the body (must be ignored)")
def _():
    s, a = fresh()
    r = call("POST", f"/api/attempts/{a}/submit", s, {"answers": KEY})
    return ok(r.status_code == 422 and code(r) == "incomplete", show(r))


@scenario("E28", "submission", "Save after submit is refused and changes nothing")
def _():
    s, a = fresh()
    call("PUT", f"/api/attempts/{a}/answers", s, {"answers": KEY})
    call("POST", f"/api/attempts/{a}/submit", s, track=False)
    r = call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": "b"}}, track=False)
    return ok(r.status_code == 409 and saved(s, a) == KEY, show(r))


@scenario("E29", "concurrency", "10 simultaneous submits: exactly one succeeds")
def _():
    s, a = fresh()
    call("PUT", f"/api/attempts/{a}/answers", s, {"answers": KEY})
    out = []
    threads = [threading.Thread(target=lambda: out.append(call("POST", f"/api/attempts/{a}/submit", s, track=False).status_code)) for _ in range(10)]
    [t.start() for t in threads]
    [t.join() for t in threads]
    return ok(out.count(200) == 1 and out.count(409) == 9, f"200s={out.count(200)} 409s={out.count(409)}")


@scenario("E30", "concurrency", "Save racing a submit cannot change a submitted attempt")
def _():
    s, a = fresh()
    call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": "b", "q2": "b", "q3": "c"}})
    mod = importlib.import_module(RACE_MODULE)
    real = getattr(mod, RACE_ATTR)

    def slow(*args, **kw):
        time.sleep(0.3)
        return real(*args, **kw)

    setattr(mod, RACE_ATTR, slow)
    res = {}
    try:
        t1 = threading.Thread(target=lambda: res.__setitem__("save", call("PUT", f"/api/attempts/{a}/answers", s, {"answers": {"q1": "a"}}, track=False)))
        t2 = threading.Thread(target=lambda: res.__setitem__("submit", call("POST", f"/api/attempts/{a}/submit", s, track=False)))
        t1.start(); time.sleep(0.1); t2.start(); t1.join(); t2.join()
    finally:
        setattr(mod, RACE_ATTR, real)
    sub = res["submit"].json().get("score")
    final = call("GET", f"/api/attempts/{a}/results", s, track=False).json().get("score")
    return ok(final == sub, f"submit score {sub}, stored result {final}, save {res['save'].status_code}")


@scenario("E31", "privacy", "Another student reading a submitted attempt's results")
def _():
    owner = sid()
    a = start(owner)
    call("PUT", f"/api/attempts/{a}/answers", owner, {"answers": KEY})
    call("POST", f"/api/attempts/{a}/submit", owner, track=False)
    r = call("GET", f"/api/attempts/{a}/results", sid())
    return ok(r.status_code == 404 and "explanation" not in r.text, show(r))


@scenario("E32", "methods", "DELETE on an attempt")
def _():
    s, a = fresh()
    r = call("DELETE", f"/api/attempts/{a}", s)
    return ok(r.status_code == 405, show(r))


@scenario("E33", "privacy", "No answer or explanation in any response before submission")
def _():
    leaky = [r for r in SEEN if any(e in r.text for e in EXPL) or "correct_choice" in r.text]
    return ok(not leaky, f"{len(leaky)} leaking of {len(SEEN)} responses")


@scenario("E34", "robustness", "No server error (5xx) in any response")
def _():
    crashes = [r for r in ERRORS if r.status_code >= 500]
    return ok(not crashes, f"{len(crashes)} server errors")


@scenario("E35", "consistency", "Every error body has the documented {code, message} shape")
def _():
    errs = [r for r in ERRORS if r.status_code != 405]
    good = [r for r in errs if isinstance((r.json() if r.headers.get("content-type", "").startswith("application/json") else {}).get("detail"), dict)]
    return ok(len(good) == len(errs), f"{len(good)} of {len(errs)} error responses")


print(json.dumps(RESULTS))
