"""ADM-02 test fixtures from the approved HTTP/table contract, not implementation."""
from copy import deepcopy
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

from auth_helpers import (SEED_ENV, call, code_of, login, require_db, sql,
                          student_from_login)

ADMIN = "/api/admin/feedback"
PUBLIC = "/api/feedback"


def uid():
    return str(uuid.uuid4())


def actor(role="student"):
    require_db()
    user_id, email = "u-" + uuid.uuid4().hex, f"adm02-{uuid.uuid4().hex}@example.com"
    sql('INSERT INTO "user" (id,display_name,role,email,password_hash,access_status) '
        'SELECT %s,%s,%s,%s,password_hash,\'enabled\' FROM "user" WHERE id=\'demo-admin\'',
        (user_id, f"ADM02 {role} {user_id}", role, email))
    password = SEED_ENV["SEED_ADMIN_PASSWORD"]
    return student_from_login(login(email, password), email, password)


def question(kind="short_answer", required=True):
    result = {"id": uid(), "type": kind, "prompt": f"Question {kind}",
              "required": required, "options": [], "scale": None}
    if kind in ("multiple_choice", "dropdown", "checkbox"):
        result["options"] = [{"id": uid(), "label": "First"}, {"id": uid(), "label": "Second"}]
    if kind == "linear_scale":
        result["scale"] = {"min": 0, "max": 5, "min_label": "Low", "max_label": "High"}
    return result


def payload(questions=None, association=None):
    return {"title": f"ADM02 Form {uid()}", "description": "Feedback only",
            "association": association, "questions": questions or [question()]}


def created(admin, body=None):
    r = call("POST", ADMIN + "/forms", admin, body or payload())
    assert r.status_code == 201, r.text
    return r.json()


def published(admin, users, body=None):
    form = created(admin, body)
    r = publish(admin, form, users)
    assert r.status_code == 200, r.text
    return r.json()


def publish(admin, form, users):
    return call("POST", f"{ADMIN}/forms/{form['id']}/publish", admin,
                {"version": form["version"], "audience_role": users[0].role,
                 "recipient_ids": [str(u) for u in users]})


def form_get(user, form):
    return call("GET", f"{PUBLIC}/forms/{form['id']}", user)


def save(user, form, answers, version=0):
    return call("PUT", f"{PUBLIC}/forms/{form['id']}/draft", user,
                {"version": version, "answers": answers})


def submit(user, form, answers, version=0):
    return call("POST", f"{PUBLIC}/forms/{form['id']}/responses", user,
                {"draft_version": version, "answers": answers})


def close(admin, form):
    return call("POST", f"{ADMIN}/forms/{form['id']}/close", admin,
                {"version": form["version"]})


def answers(form, optional_null=False):
    result = []
    for q in form["questions"]:
        value = "  text\nanswer  "
        if q["type"] in ("multiple_choice", "dropdown"):
            value = q["options"][0]["id"]
        elif q["type"] == "checkbox":
            value = [q["options"][1]["id"], q["options"][0]["id"]]
        elif q["type"] == "linear_scale":
            value = q["scale"]["min"]
        if optional_null and not q["required"]:
            value = None
        result.append({"question_id": q["id"], "value": value})
    return result


def inbox(user, form):
    r = call("GET", PUBLIC + "/inbox", user)
    assert r.status_code == 200, r.text
    return next((item for item in r.json()["items"] if item["form_id"] == form["id"]), None)


def response(admin, form, receipt):
    r = call("GET", f"{ADMIN}/forms/{form['id']}/responses/{receipt['id']}", admin)
    assert r.status_code == 200, r.text
    return r.json()


def error(r, status, code):
    assert r.status_code == status, r.text
    assert code_of(r) == code, r.text
    assert "no-store" in r.headers.get("cache-control", "")


def race(*operations):
    barrier = threading.Barrier(len(operations))
    def start(operation):
        barrier.wait(timeout=10)
        return operation()
    with ThreadPoolExecutor(max_workers=len(operations)) as pool:
        return list(pool.map(start, operations))
