"""SHR-01 access control: current_user order, CSRF/Origin, course access, migrated student
routes, demo-header isolation, fail-closed configuration (AC12-AC17, AC19, AC25, SEC-AUTH-02..06,
11-14). Black box; the fake LLM replaces the SoC client."""
import hashlib
import json

import pytest
from auth_helpers import COOKIE_NAME, COURSE_A, COURSE_B, call, code_of, login, new_student, seeded, signup, sql
from auth_helpers import unique_email, unique_password

SET_ID = "intro-se-1"
EXPLANATIONS = [
    "One focused responsibility makes a function easier to understand, test and change.",
    "Tests protect expected behaviour and can catch regressions introduced by later changes.",
    "len returns the number of items. The list contains three items.",
]
ANSWERS = {"q1": "a", "q2": "b", "q3": "c"}


def routes(aid):
    """Every migrated STU-02/STU-03 route: (method, path, json body)."""
    return [
        ("GET", f"/api/practice-sets/{SET_ID}", None),
        ("POST", f"/api/practice-sets/{SET_ID}/attempts", None),
        ("GET", f"/api/attempts/{aid}", None),
        ("PUT", f"/api/attempts/{aid}/answers", {"answers": {"q1": "a"}}),
        ("POST", f"/api/attempts/{aid}/submit", None),
        ("GET", f"/api/attempts/{aid}/results", None),
        ("POST", "/api/companion/messages",
         {"message": "hi", "history": [], "context": {"page": "other", "set_id": None,
                                                       "attempt_id": None, "label": None}}),
    ]


def start(student):
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", student)
    assert r.status_code == 201, r.text
    return r.json()["attempt_id"]


# ------------------------------------------------------------------ AC15 / SEC-AUTH-02, 03
def test_shr01_sec_auth_02_signed_out_is_401_on_every_migrated_route():
    aid = start(new_student())
    for method, path, body in routes(aid):
        r = call(method, path, None, body)
        assert r.status_code == 401, (method, path)
        assert code_of(r) == "unauthenticated", (method, path)


@pytest.mark.parametrize("role", ["teacher", "admin"])
def test_shr01_sec_auth_03_other_roles_are_403_forbidden_on_every_migrated_route(role, fake):
    aid = start(new_student())
    who = seeded(role)
    for method, path, body in routes(aid):
        r = call(method, path, who, body)
        assert r.status_code == 403, (role, method, path, r.text)
        assert code_of(r) == "forbidden", (role, method, path)
    assert fake.calls == []  # a wrong-role caller never reaches the model


def test_shr01_ac15_student_session_reaches_every_migrated_route(fake):
    s = new_student()
    aid = start(s)
    for method, path, body in routes(aid):
        r = call(method, path, s, body)
        assert r.status_code not in (401, 403), (method, path, r.status_code, r.text)
    assert call("GET", f"/api/practice-sets/{SET_ID}", s).status_code == 200


def test_shr01_ac15_seeded_demo_student_can_practise():
    s = seeded("student")
    assert call("POST", f"/api/practice-sets/{SET_ID}/attempts", s).status_code == 201


def test_shr01_ac15_read_set_is_now_protected():
    assert call("GET", f"/api/practice-sets/{SET_ID}").status_code == 401
    assert call("GET", "/api/practice-sets/nope").status_code == 401  # auth before set lookup


# ------------------------------------------------------------------ AC12 order of checks
def test_shr01_ac12_order_is_401_then_csrf_then_403_forbidden():
    student, teacher = new_student(), seeded("teacher")
    path = f"/api/practice-sets/{SET_ID}/attempts"
    # no session beats a missing CSRF token
    r = call("POST", path, None)
    assert r.status_code == 401 and code_of(r) == "unauthenticated"
    # a signed-in wrong-role user without the CSRF token gets csrf_failed before forbidden
    r = call("POST", path, teacher, csrf=False)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"
    r = call("POST", path, teacher)
    assert r.status_code == 403 and code_of(r) == "forbidden"
    # a student without the token
    r = call("POST", path, student, csrf=False)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"
    assert call("POST", path, student).status_code == 201


def test_shr01_ac12_role_change_takes_effect_on_next_request():
    s = new_student()
    assert call("GET", f"/api/practice-sets/{SET_ID}", s).status_code == 200
    sql('UPDATE "user" SET role = %s WHERE id = %s', ("teacher", str(s)))
    r = call("GET", f"/api/practice-sets/{SET_ID}", s)
    assert r.status_code == 403 and code_of(r) == "forbidden"
    assert call("GET", "/api/auth/me", s).json()["user"]["role"] == "teacher"


def test_shr01_ac12_deleted_user_gets_401_on_protected_route():
    s = new_student()
    sql('DELETE FROM "user" WHERE id = %s', (str(s),))
    r = call("GET", f"/api/practice-sets/{SET_ID}", s)
    assert r.status_code == 401 and code_of(r) == "unauthenticated"


# ------------------------------------------------------------------ AC13 CSRF and Origin (SEC-AUTH-06)
@pytest.mark.parametrize("method,path,body", [
    ("POST", f"/api/practice-sets/{SET_ID}/attempts", None),
    ("PUT", "/api/attempts/{aid}/answers", {"answers": {"q1": "a"}}),
    ("POST", "/api/attempts/{aid}/submit", None),
    ("POST", "/api/companion/messages", {"message": "hi", "history": [], "context": {"page": "other"}}),
])
def test_shr01_sec_auth_06_unsafe_requests_need_the_matching_csrf_token(method, path, body, fake):
    s = new_student()
    other = new_student()
    aid = start(s)
    path = path.replace("{aid}", aid)
    for csrf in (False, "", "wrong-token", other.csrf, s.csrf + "x", s.csrf.swapcase()):
        r = call(method, path, s, body, csrf=csrf)
        assert r.status_code == 403 and code_of(r) == "csrf_failed", (csrf, r.text)
    assert fake.calls == []
    # nothing changed
    assert call("GET", f"/api/attempts/{aid}", s).json()["answers"] == {}
    assert call(method, path, s, body).status_code in (200, 201, 422)


def test_shr01_ac13_safe_methods_need_no_csrf_token():
    s = new_student()
    aid = start(s)
    for path in (f"/api/practice-sets/{SET_ID}", f"/api/attempts/{aid}", "/api/auth/me",
                 f"/api/courses/{COURSE_A}"):
        who = seeded("student") if path.startswith("/api/courses") else s
        assert call("GET", path, who, csrf=False).status_code == 200, path


def test_shr01_ac13_csrf_token_is_per_session():
    s = new_student()
    second = login(s.email, s.password).json()["csrf_token"]
    assert second != s.csrf
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", s, csrf=second)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"


def test_shr01_sec_auth_06_foreign_origin_is_rejected_even_with_valid_csrf():
    s = new_student()
    path = f"/api/practice-sets/{SET_ID}/attempts"
    for origin in ("https://evil.example", "http://localhost:5174", "http://localhost:5173.evil.example",
                   "null", "http://test:8080", "https://test"):
        r = call("POST", path, s, headers={"Origin": origin})
        assert r.status_code == 403 and code_of(r) == "csrf_failed", origin
    sets = sql("SELECT count(*) FROM auth_session WHERE user_id = %s", (str(s),))
    assert sets[0][0] == 1


def test_shr01_ac13_allowed_and_same_origin_pass():
    s = new_student()
    path = f"/api/practice-sets/{SET_ID}/attempts"
    assert call("POST", path, s, headers={"Origin": "http://localhost:5173"}).status_code == 201
    assert call("POST", path, s, headers={"Origin": "http://test"}).status_code == 201
    assert call("POST", path, s).status_code == 201  # no Origin header at all


def test_shr01_sec_auth_06_foreign_origin_on_login_signup_logout():
    s = new_student()
    evil = {"Origin": "https://evil.example"}
    r = call("POST", "/api/auth/login", json={"email": s.email, "password": s.password}, headers=evil)
    assert r.status_code == 403 and code_of(r) == "csrf_failed" and not r.headers.get_list("set-cookie")
    email = unique_email("evil")
    r = call("POST", "/api/auth/signup", json={"display_name": "E", "email": email,
                                               "password": unique_password()}, headers=evil)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"
    assert sql('SELECT count(*) FROM "user" WHERE email = %s', (email,))[0][0] == 0
    r = call("POST", "/api/auth/logout", s, headers=evil)
    assert r.status_code == 403 and code_of(r) == "csrf_failed"
    assert call("GET", "/api/auth/me", s).status_code == 200
    ok = call("POST", "/api/auth/login", json={"email": s.email, "password": s.password},
              headers={"Origin": "http://localhost:5173"})
    assert ok.status_code == 200


def test_shr01_sec_auth_06_no_wildcard_cors():
    r = call("GET", "/api/auth/me", headers={"Origin": "https://evil.example"})
    assert r.headers.get("access-control-allow-origin") not in ("*", "https://evil.example")
    pre = call("OPTIONS", "/api/auth/login", headers={"Origin": "http://localhost:5173",
                                                     "Access-Control-Request-Method": "POST",
                                                     "Access-Control-Request-Headers": "x-csrf-token"})
    assert pre.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert pre.headers.get("access-control-allow-credentials") == "true"
    bad = call("OPTIONS", "/api/auth/login", headers={"Origin": "https://evil.example",
                                                     "Access-Control-Request-Method": "POST"})
    assert bad.headers.get("access-control-allow-origin") is None


# ------------------------------------------------------------------ AC14 course access (SEC-AUTH-13)
def test_shr01_ac14_member_gets_course_for_student_and_teacher():
    for role in ("student", "teacher"):
        r = call("GET", f"/api/courses/{COURSE_A}", seeded(role))
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body) == {"id", "title", "created_at"}
        assert body["id"] == COURSE_A and body["title"] == "Software Engineering"
        assert body["created_at"].endswith("Z")


def test_shr01_sec_auth_13_non_member_is_indistinguishable_from_nonexistent():
    random_id = "99999999-9999-4999-8999-999999999999"
    probes = [new_student(), seeded("admin"), seeded("student"), seeded("teacher")]
    for who in probes:
        target = COURSE_B  # an existing course none of these users belongs to
        real = call("GET", f"/api/courses/{target}", who)
        fake_ = call("GET", f"/api/courses/{random_id}", who)
        assert real.status_code == fake_.status_code == 404
        assert real.json() == fake_.json()
        assert code_of(real) == "not_found"
    # a new student is also not a member of Course A
    r = call("GET", f"/api/courses/{COURSE_A}", probes[0])
    assert r.status_code == 404 and code_of(r) == "not_found"


def test_shr01_ac14_admin_has_no_implicit_course_access():
    r = call("GET", f"/api/courses/{COURSE_A}", seeded("admin"))
    assert r.status_code == 404 and code_of(r) == "not_found"


def test_shr01_ac14_signed_out_and_invalid_id():
    r = call("GET", f"/api/courses/{COURSE_A}")
    assert r.status_code == 401 and code_of(r) == "unauthenticated"
    assert call("GET", "/api/courses/not-a-uuid").status_code == 401  # auth first
    r = call("GET", "/api/courses/not-a-uuid", new_student())
    assert r.status_code == 422 and code_of(r) == "validation_error"
    assert call("GET", "/api/courses/1", new_student()).status_code == 422


def test_shr01_ac14_course_read_is_get_only_and_leaks_nothing_extra():
    s = seeded("student")
    r = call("GET", f"/api/courses/{COURSE_A}", s)
    assert "member" not in r.text and "user" not in r.text.lower().replace("software", "")
    assert call("POST", f"/api/courses/{COURSE_A}", s).status_code in (404, 405)


# ------------------------------------------------------------------ AC16 record ownership (SEC-AUTH-05)
def test_shr01_sec_auth_05_cross_student_attempt_access_via_session():
    owner, other = new_student(), new_student()
    aid = start(owner)
    call("PUT", f"/api/attempts/{aid}/answers", owner, {"answers": {"q1": "a"}})
    ghost = "does-not-exist-123"
    for method, suffix, body in [("GET", "", None), ("PUT", "/answers", {"answers": {"q1": "b"}}),
                                 ("POST", "/submit", None), ("GET", "/results", None)]:
        a = call(method, f"/api/attempts/{aid}{suffix}", other, body)
        b = call(method, f"/api/attempts/{ghost}{suffix}", other, body)
        assert a.status_code == b.status_code == 404
        assert a.json() == b.json() and code_of(a) == "attempt_not_found"
    assert call("GET", f"/api/attempts/{aid}", owner).json()["answers"] == {"q1": "a"}


def test_shr01_sec_auth_05_leftover_x_student_id_header_never_grants_access():
    owner, attacker = new_student(), new_student()
    aid = start(owner)
    call("PUT", f"/api/attempts/{aid}/answers", owner, {"answers": ANSWERS})
    call("POST", f"/api/attempts/{aid}/submit", owner)
    for header in (str(owner), "demo-student", f" {owner} "):
        h = {"X-Student-Id": header}
        for method, suffix, body in [("GET", "", None), ("GET", "/results", None),
                                     ("PUT", "/answers", {"answers": {"q1": "a"}}), ("POST", "/submit", None)]:
            r = call(method, f"/api/attempts/{aid}{suffix}", attacker, body, headers=h)
            assert r.status_code == 404 and code_of(r) == "attempt_not_found", (header, method, suffix)
            assert not any(e in r.text for e in EXPLANATIONS)
    # Anonymous with the header is still signed out
    r = call("GET", f"/api/attempts/{aid}/results", None, headers={"X-Student-Id": str(owner)})
    assert r.status_code == 401


def test_shr01_ac16_attempts_are_owned_by_the_session_user_id():
    s = new_student()
    aid = start(s)
    # The in-memory attempt store is keyed by the session user id, so a second login still owns it.
    again = new_student()
    assert call("GET", f"/api/attempts/{aid}", again).status_code == 404
    from auth_helpers import student_from_login
    s2 = student_from_login(login(s.email, s.password), s.email, s.password)
    assert call("GET", f"/api/attempts/{aid}", s2).status_code == 200


def test_shr01_ac16_companion_context_only_from_own_attempt(fake):
    owner, other = new_student(), new_student()
    aid = start(owner)
    call("PUT", f"/api/attempts/{aid}/answers", owner, {"answers": ANSWERS})
    call("POST", f"/api/attempts/{aid}/submit", owner)
    body = {"message": "explain", "history": [], "context": {"page": "practice", "set_id": SET_ID,
                                                              "attempt_id": aid, "label": None}}
    r = call("POST", "/api/companion/messages", other, body)
    assert r.status_code == 404 and code_of(r) == "attempt_not_found"
    assert fake.calls == []
    r = call("POST", "/api/companion/messages", owner, body)
    assert r.status_code == 200 and r.json()["mode"] == "explain"
    assert fake.last.caller_id == owner


def test_shr01_ac16_companion_caller_id_is_the_session_user_not_a_header(fake):
    s = new_student()
    r = call("POST", "/api/companion/messages", s,
             {"message": "hi", "history": [], "context": {"page": "other"}},
             headers={"X-Student-Id": "demo-student", "X-Demo-User-Id": "demo-teacher"})
    assert r.status_code == 200
    assert fake.last.caller_id == s


# ------------------------------------------------------------------ AC17 / SEC-AUTH-11 answer release
def test_shr01_sec_auth_11_answer_release_unchanged_for_session_users(fake):
    s, other = new_student(), new_student()
    aid = start(s)
    call("PUT", f"/api/attempts/{aid}/answers", s, {"answers": ANSWERS})
    pre = [
        call("GET", f"/api/attempts/{aid}", s),
        call("GET", f"/api/attempts/{aid}/results", s),
        call("GET", f"/api/practice-sets/{SET_ID}", s),
        call("GET", f"/api/attempts/{aid}/results", other),
        call("POST", f"/api/attempts/{aid}/submit", s, csrf=False),  # blocked by CSRF, must not submit
        call("POST", f"/api/attempts/{aid}/submit", None),
    ]
    assert pre[1].status_code == 403 and code_of(pre[1]) == "not_submitted"
    for r in pre:
        assert "correct_choice" not in r.text and "key_version" not in r.text
        assert not any(e in r.text for e in EXPLANATIONS)
    assert call("GET", f"/api/attempts/{aid}", s).json()["status"] == "in_progress"
    # The companion never sees the key while the set is open
    r = call("POST", "/api/companion/messages", s,
             {"message": "what is the answer", "history": [], "context": {"page": "practice", "set_id": SET_ID,
                                                                           "attempt_id": None, "label": None}})
    assert r.status_code == 200
    assert not any(e in fake.last.all_text for e in EXPLANATIONS)
    # After a real submit the results are released to the owner only
    assert call("POST", f"/api/attempts/{aid}/submit", s).status_code == 200
    assert call("GET", f"/api/attempts/{aid}/results", s).status_code == 200
    assert call("GET", f"/api/attempts/{aid}/results", other).status_code == 404


# ------------------------------------------------------------------ SEC-AUTH-14 demo isolation (AC25)
DEMO_HEADERS = [
    {"X-Demo-User-Id": "demo-teacher"}, {"X-Demo-User-Id": "demo-student"}, {"X-Demo-User-Id": "demo-admin"},
    {"X-Student-Id": "demo-student"}, {"X-Student-Id": "u-anything"},
    {"X-Demo-User-Id": "demo-student", "X-Student-Id": "demo-student"},
]


def test_shr01_sec_auth_14_anonymous_demo_headers_grant_nothing():
    aid = start(new_student())
    for headers in DEMO_HEADERS:
        for method, path, body in routes(aid):
            r = call(method, path, None, body, headers=headers)
            assert r.status_code == 401 and code_of(r) == "unauthenticated", (headers, method, path)
        r = call("GET", f"/api/courses/{COURSE_A}", None, headers=headers)
        assert r.status_code == 401 and code_of(r) == "unauthenticated", headers
        r = call("GET", "/api/auth/me", None, headers=headers)
        assert r.status_code == 401, headers


def test_shr01_sec_auth_14_session_plus_demo_header_still_resolves_to_session_user():
    s = new_student()
    headers = {"X-Demo-User-Id": "demo-teacher", "X-Student-Id": "demo-student"}
    assert call("GET", "/api/auth/me", s, headers=headers).json()["user"]["id"] == s
    # demo-teacher is a Course A member; a fresh student is not
    r = call("GET", f"/api/courses/{COURSE_A}", s, headers=headers)
    assert r.status_code == 404
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", s, headers=headers)
    assert r.status_code == 201  # acts as the student, not as the (forbidden) teacher
    t = seeded("teacher")
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", t, headers={"X-Student-Id": "demo-student"})
    assert r.status_code == 403 and code_of(r) == "forbidden"


def test_shr01_sec_auth_14_teacher_demo_gate_is_unchanged():
    ok = call("GET", "/api/teacher/courses", None, headers={"X-Demo-User-Id": "demo-teacher"})
    assert ok.status_code == 200, ok.text
    assert any(c["id"] == COURSE_A for c in ok.json())
    # A real session cookie is not what the unchanged teacher routes read.
    t = seeded("teacher")
    assert call("GET", "/api/teacher/courses", t).status_code in (401, 403)


def test_shr01_sec_auth_14_demo_mode_creates_no_session_or_cookie():
    before = sql("SELECT count(*) FROM auth_session")[0][0]
    r = call("GET", "/api/health", None, headers={"X-Demo-User-Id": "demo-student"})
    r2 = call("GET", "/api/auth/me", None, headers={"X-Demo-User-Id": "demo-student"})
    for resp in (r, r2):
        assert not resp.headers.get_list("set-cookie")
    assert sql("SELECT count(*) FROM auth_session")[0][0] == before


# ------------------------------------------------------------------ AC19 fail closed (SEC-AUTH-12)
def safe_error(r):
    assert r.status_code == 503 and code_of(r) == "service_unavailable", (r.status_code, r.text)
    for bad in ("Traceback", "sqlalchemy", "psycopg", "postgres", "SELECT", ".py", "learnswe-local-only"):
        assert bad not in r.text
    assert not r.headers.get_list("set-cookie")


def exercise_all_auth_paths(s):
    safe_error(login(s.email, s.password))
    safe_error(signup(unique_email(), unique_password()))
    safe_error(call("GET", "/api/auth/me", s))
    safe_error(call("POST", f"/api/practice-sets/{SET_ID}/attempts", s))
    safe_error(call("GET", f"/api/courses/{COURSE_A}", s))


def test_shr01_sec_auth_12_production_without_secure_cookies_is_503(monkeypatch):
    s = new_student()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    exercise_all_auth_paths(s)
    monkeypatch.delenv("SESSION_COOKIE_SECURE")  # unset defaults to true: allowed in production
    r = call("GET", "/api/auth/me", s)
    assert r.status_code == 200


def test_shr01_sec_auth_12_production_with_secure_cookies_works_and_marks_secure(monkeypatch):
    s = new_student()
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    r = login(s.email, s.password)
    assert r.status_code == 200
    from auth_helpers import session_cookie
    assert "secure" in session_cookie(r)[1]


def test_shr01_sec_auth_12_production_never_falls_back_to_demo_identity(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    r = call("POST", f"/api/practice-sets/{SET_ID}/attempts", None,
             headers={"X-Demo-User-Id": "demo-student", "X-Student-Id": "demo-student"})
    assert r.status_code in (401, 503)
    assert r.status_code != 201


@pytest.mark.parametrize("samesite,secure", [("none", "false"), ("weird", "true")])
def test_shr01_sec_auth_12_invalid_samesite_combinations_are_503(monkeypatch, samesite, secure):
    s = new_student()
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", samesite)
    monkeypatch.setenv("SESSION_COOKIE_SECURE", secure)
    safe_error(login(s.email, s.password))
    safe_error(call("GET", "/api/auth/me", s))


def test_shr01_sec_auth_12_database_unavailable_is_503_and_never_unauthenticated_fallback(monkeypatch):
    s = new_student()
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://nobody:nopass@127.0.0.1:1/none")
    exercise_all_auth_paths(s)
    safe_error(call("POST", f"/api/practice-sets/{SET_ID}/attempts", None,
                    headers={"X-Demo-User-Id": "demo-student"}))


def test_shr01_sec_auth_12_missing_database_url_is_503(monkeypatch):
    s = new_student()
    monkeypatch.delenv("DATABASE_URL")
    safe_error(login(s.email, s.password))
    safe_error(call("GET", "/api/auth/me", s))


def test_shr01_sec_auth_12_health_stays_up_under_bad_auth_config(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "false")
    assert call("GET", "/api/health").status_code == 200


# ------------------------------------------------------------------ SEC-AUTH-10 DB plaintext
def test_shr01_sec_auth_10_no_plaintext_token_or_password_in_db():
    s = new_student()
    digest = hashlib.sha256(s.token.encode()).hexdigest()
    rows = sql("SELECT token_hash FROM auth_session WHERE user_id = %s", (str(s),))
    assert [r[0] for r in rows] == [digest]
    pw_rows = sql('SELECT password_hash FROM "user" WHERE id = %s', (str(s),))
    assert s.password not in pw_rows[0][0] and pw_rows[0][0].startswith("scrypt$")
    assert json.dumps(rows).count(s.token) == 0


def test_shr01_sec_auth_10_cookie_name_constant_matches_contract():
    s = new_student()
    r = login(s.email, s.password)
    assert any(c.startswith(f"{COOKIE_NAME}=") for c in r.headers.get_list("set-cookie"))
