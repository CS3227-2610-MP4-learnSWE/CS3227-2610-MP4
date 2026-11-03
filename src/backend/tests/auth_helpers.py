"""Shared SHR-01 test helpers (contract: workflow/specs/SHR-01/plan.md).

Only the HTTP contract is used. `main.app` is imported lazily so conftest can set
the environment first. A Student is a `str` subclass whose value is the server
user id, so older assertions such as `fake.last.caller_id == student` still read
naturally. It also carries the session cookie value and the CSRF token.
"""
import asyncio
import itertools
import os
import random
import uuid
from dataclasses import dataclass

import httpx
import pytest

COOKIE_NAME = "learnswe_session"
COURSE_A = "11111111-1111-4111-8111-111111111111"
COURSE_B = "22222222-2222-4222-8222-222222222222"

# Test-only values, never real credentials. Exported by conftest before the seed runs.
SEED_ENV = {
    "SEED_STUDENT_EMAIL": "demo-student@learnswe.test",
    "SEED_STUDENT_PASSWORD": "seed-student-Pw-7391-xq",
    "SEED_TEACHER_EMAIL": "demo-teacher@learnswe.test",
    "SEED_TEACHER_PASSWORD": "seed-teacher-Pw-4827-mz",
    "SEED_ADMIN_EMAIL": "demo-admin@learnswe.test",
    "SEED_ADMIN_PASSWORD": "seed-admin-Pw-9163-kd",
}
AUTH_ENV = {
    "SESSION_COOKIE_SECURE": "false",
    "SESSION_COOKIE_SAMESITE": "lax",
    "ALLOWED_ORIGINS": "http://localhost:5173",
    "TRUST_PROXY_HEADERS": "true",
}
SEEDED = {
    "student": ("demo-student", SEED_ENV["SEED_STUDENT_EMAIL"], SEED_ENV["SEED_STUDENT_PASSWORD"]),
    "teacher": ("demo-teacher", SEED_ENV["SEED_TEACHER_EMAIL"], SEED_ENV["SEED_TEACHER_PASSWORD"]),
    "admin": ("demo-admin", SEED_ENV["SEED_ADMIN_EMAIL"], SEED_ENV["SEED_ADMIN_PASSWORD"]),
}
UNSAFE = {"POST", "PUT", "PATCH", "DELETE"}

# Set by conftest after the session-level seed attempt.
seed_state = {"ready": False, "error": None}

_ip_counter = itertools.count(random.randint(1, 60000))


def require_db(check_seed=True):
    """Skip without a test database; fail loudly if the auth seed did not run."""
    if not os.environ.get("TEA01_TEST_DATABASE_URL"):
        pytest.skip("TEA01_TEST_DATABASE_URL is not set")
    if check_seed and not seed_state["ready"]:
        pytest.fail(f"auth seed (python -m auth.seed) failed or did not run: {seed_state['error']}")


def fresh_ip():
    n = next(_ip_counter)
    return f"10.{(n >> 16) & 255}.{(n >> 8) & 255}.{n & 255}"


class Student(str):
    """A signed-in user: the str value is the server user id."""

    def __new__(cls, user_id, *, email, password, token, csrf, role="student"):
        obj = super().__new__(cls, user_id)
        obj.email, obj.password, obj.token, obj.csrf, obj.role = email, password, token, csrf, role
        return obj

    @property
    def cookie(self):
        return f"{COOKIE_NAME}={self.token}"


def call(method, path, student=None, json=None, headers=None, *, content=None, data=None,
         files=None, csrf=True, ip=None, base_url="http://test"):
    """Send one request through the ASGI app.

    student: a Student (cookie and, for unsafe methods, X-CSRF-Token are added) or None
    (no cookie). csrf: True = the session token, False = omit, str = send that value.
    ip: X-Forwarded-For (a distinct value per call by default so shared-IP limits do not interfere).
    """
    require_db(check_seed=not path.startswith("/api/health"))
    from main import app

    hdrs = dict(headers or {})
    lower = {k.lower() for k in hdrs}
    if "x-forwarded-for" not in lower:
        hdrs["X-Forwarded-For"] = ip or fresh_ip()
    if isinstance(student, Student):
        if "cookie" not in lower:
            hdrs["Cookie"] = student.cookie
        if method.upper() in UNSAFE and "x-csrf-token" not in lower:
            if csrf is True:
                hdrs["X-CSRF-Token"] = student.csrf
            elif isinstance(csrf, str):
                hdrs["X-CSRF-Token"] = csrf
    elif student is not None:
        raise TypeError("student must be a Student or None (X-Student-Id is no longer an identity)")

    async def send():
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app, raise_app_exceptions=False), base_url=base_url
        ) as client:
            return await client.request(method, path, headers=hdrs, json=json, content=content,
                                        data=data, files=files)

    return asyncio.run(send())


def signup(email, password, display_name="Test User", ip=None, **kw):
    body = {"display_name": display_name, "email": email, "password": password}
    return call("POST", "/api/auth/signup", json=body, ip=ip, **kw)


def login(email, password, ip=None, **kw):
    return call("POST", "/api/auth/login", json={"email": email, "password": password}, ip=ip, **kw)


def session_cookie(response):
    """Return (value, attributes dict lower-cased keys) of the session Set-Cookie, or None."""
    for raw in response.headers.get_list("set-cookie"):
        parts = [p.strip() for p in raw.split(";")]
        name, _, value = parts[0].partition("=")
        if name == COOKIE_NAME:
            attrs = {}
            for p in parts[1:]:
                k, _, v = p.partition("=")
                attrs[k.strip().lower()] = v.strip()
            return value, attrs
    return None


def student_from_login(response, email, password, role=None):
    assert response.status_code == 200, response.text
    token, _ = session_cookie(response)
    body = response.json()
    return Student(body["user"]["id"], email=email, password=password, token=token,
                   csrf=body["csrf_token"], role=role or body["user"]["role"])


def unique_email(prefix="stu"):
    return f"{prefix}-{uuid.uuid4().hex[:12]}@example.com"


def unique_password():
    return "Pw-" + uuid.uuid4().hex


def new_student(prefix="stu"):
    """Sign up a fresh student, sign in, and return the Student."""
    email, password = unique_email(prefix), unique_password()
    r = signup(email, password, display_name=f"Student {prefix}")
    assert r.status_code == 202, r.text
    return student_from_login(login(email, password), email, password)


def seeded(role):
    """Sign in as the seeded demo user of a role (a fresh session each call)."""
    user_id, email, password = SEEDED[role]
    s = student_from_login(login(email, password), email, password)
    assert s == user_id
    return s


# ---- direct database access (reads, plus the few setup writes the plan names) ----

def psycopg_url(url=None):
    return (url or os.environ["DATABASE_URL"]).replace("postgresql+psycopg://", "postgresql://", 1)


def sql(statement, params=(), url=None):
    import psycopg

    with psycopg.connect(psycopg_url(url), autocommit=True) as conn:
        cur = conn.execute(statement, params)
        return cur.fetchall() if cur.description else None


def schema_url(base, schema):
    from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

    parts = urlsplit(base)
    query = dict(parse_qsl(parts.query))
    query["options"] = f"-csearch_path={schema}"
    return urlunsplit(parts._replace(query=urlencode(query)))


def code_of(r):
    return r.json()["detail"]["code"]
