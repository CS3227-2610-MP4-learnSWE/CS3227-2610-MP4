"""SHR-01 accounts, signup, login, session cookie, logout (AC2-AC11, AC20).

Black box from workflow/specs/SHR-01/plan.md. Real isolated PostgreSQL schema, no LLM.
"""
import hashlib
import json
import logging
import re
import statistics
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest
from auth_helpers import (
    COOKIE_NAME,
    SEEDED,
    SEED_ENV,
    call,
    code_of,
    login,
    new_student,
    seeded,
    session_cookie,
    signup,
    sql,
    student_from_login,
    unique_email,
    unique_password,
)


def user_rows(email):
    return sql('SELECT id, email, display_name, role, password_hash FROM "user" WHERE email = %s', (email,))


def count_users():
    return sql('SELECT count(*) FROM "user"')[0][0]


# ------------------------------------------------------------------ AC2 signup success
def test_shr01_ac2_signup_creates_one_student_with_hash_only():
    email, password = unique_email(), unique_password()
    r = signup(email, password, display_name="  Ada Lovelace ")
    assert r.status_code == 202
    assert r.json() == {"status": "accepted"}
    assert not r.headers.get_list("set-cookie")
    rows = user_rows(email)
    assert len(rows) == 1
    uid, stored_email, name, role, pw_hash = rows[0]
    assert role == "student"
    assert re.fullmatch(r"u-[0-9a-f]{32}", uid)
    assert name == "Ada Lovelace"
    assert pw_hash and password not in pw_hash
    assert pw_hash.startswith("scrypt$16384$8$1$")
    assert len(pw_hash.split("$")) == 6


def test_shr01_ac2_every_signup_user_is_a_student():
    new_student()
    roles = {r[0] for r in sql('SELECT role FROM "user" WHERE id LIKE %s', ("u-%",))}
    assert roles == {"student"}


def test_shr01_ac2_password_never_stored_anywhere():
    password = unique_password()
    email = unique_email()
    assert signup(email, password).status_code == 202
    login(email, password)
    found = sql('SELECT count(*) FROM "user" WHERE password_hash LIKE %s OR display_name LIKE %s',
                (f"%{password}%", f"%{password}%"))
    assert found[0][0] == 0
    sessions = sql("SELECT count(*) FROM auth_session WHERE token_hash LIKE %s OR csrf_token LIKE %s",
                   (f"%{password}%", f"%{password}%"))
    assert sessions[0][0] == 0


# ------------------------------------------------------------------ AC3 strict body (SEC-AUTH-01)
@pytest.mark.parametrize("field,value", [
    ("role", "admin"), ("role", "teacher"), ("role", "student"), ("id", "demo-admin"),
    ("is_admin", True), ("course_id", "11111111-1111-4111-8111-111111111111"), ("extra", "x"),
])
def test_shr01_sec_auth_01_signup_rejects_unknown_fields_and_creates_nothing(field, value):
    email = unique_email("esc")
    body = {"display_name": "Mallory", "email": email, "password": unique_password(), field: value}
    before = count_users()
    r = call("POST", "/api/auth/signup", json=body)
    assert r.status_code == 422
    assert code_of(r) == "validation_error"
    assert user_rows(email) == []
    assert count_users() == before


def test_shr01_sec_auth_01_no_privileged_account_can_come_from_signup():
    for role in ("admin", "teacher"):
        email = unique_email(role)
        call("POST", "/api/auth/signup", json={"display_name": "M", "email": email,
                                               "password": unique_password(), "role": role})
        assert user_rows(email) == []
    assert sql('SELECT count(*) FROM "user" WHERE id LIKE %s AND role <> %s', ("u-%", "student"))[0][0] == 0


@pytest.mark.parametrize("body", [
    {"email": "a@example.com", "password": "x" * 12},
    {"display_name": "A", "password": "x" * 12},
    {"display_name": "A", "email": "a@example.com"},
    {},
])
def test_shr01_ac3_missing_fields_are_422(body):
    r = call("POST", "/api/auth/signup", json=body)
    assert r.status_code == 422 and code_of(r) == "validation_error"
    assert isinstance(r.json()["detail"]["fields"], list)


@pytest.mark.parametrize("field,value", [
    ("display_name", 5), ("email", ["a@example.com"]), ("password", 1234567890123), ("email", None),
])
def test_shr01_ac3_strict_types(field, value):
    body = {"display_name": "A", "email": unique_email(), "password": unique_password()}
    body[field] = value
    r = call("POST", "/api/auth/signup", json=body)
    assert r.status_code == 422 and code_of(r) == "validation_error"
    assert field in r.json()["detail"]["fields"]


def test_shr01_ac3_validation_error_never_echoes_values():
    pw = "secretvalue-" + uuid.uuid4().hex
    r = call("POST", "/api/auth/signup", json={"display_name": "A", "email": "bad", "password": pw})
    assert r.status_code == 422
    assert pw not in r.text


# ------------------------------------------------------------------ AC4 email
def test_shr01_ac4_email_is_trimmed_and_lowercased():
    local = "Mixed" + uuid.uuid4().hex[:8]
    password = unique_password()
    assert signup(f"  {local}@Example.COM ", password).status_code == 202
    assert len(user_rows(f"{local.lower()}@example.com")) == 1
    r = login(f" {local.upper()}@EXAMPLE.com ", password)
    assert r.status_code == 200
    assert r.json()["user"]["email"] == f"{local.lower()}@example.com"


@pytest.mark.parametrize("email", [
    "", "   ", "no-at-sign", "a@b", "@example.com", "a b@example.com", "a@@example.com",
    "a@b@example.com", "a\u0001b@example.com", "a@exa mple.com", "x@" + "d" * 250 + ".com",
])
def test_shr01_ac4_invalid_email_is_422_with_email_field(email):
    before = count_users()
    r = signup(email, unique_password())
    assert r.status_code == 422 and code_of(r) == "validation_error"
    assert "email" in r.json()["detail"]["fields"]
    assert count_users() == before


def test_shr01_ac4_email_length_bounds():
    ok = "a" * (254 - len("@example.com")) + "@example.com"
    assert len(ok) == 254
    assert signup(ok, unique_password()).status_code == 202
    too_long = "a" * (255 - len("@example.com")) + "@example.com"
    assert signup(too_long, unique_password()).status_code == 422


# ------------------------------------------------------------------ AC5 password and display name
@pytest.mark.parametrize("length,status", [(9, 422), (10, 202), (128, 202), (129, 422)])
def test_shr01_ac5_password_length_boundaries(length, status):
    pw = ("Zq" * 100)[:length]
    r = signup(unique_email(), pw)
    assert r.status_code == status, r.text
    if status == 422:
        assert "password" in r.json()["detail"]["fields"]


def test_shr01_ac5_length_counts_code_points_not_bytes():
    assert signup(unique_email(), "\U0001F600" * 10).status_code == 202
    assert signup(unique_email(), "\U0001F600" * 9).status_code == 422
    assert signup(unique_email(), "é" * 128).status_code == 202


def test_shr01_ac5_password_is_not_stripped():
    email = unique_email()
    pw = "   padded password   "
    assert signup(email, pw).status_code == 202
    assert login(email, pw).status_code == 200
    assert login(email, pw.strip()).status_code == 401


def test_shr01_ac5_password_equal_to_email_or_local_part_rejected():
    local = "longlocalpart" + uuid.uuid4().hex[:6]
    email = f"{local}@example.com"
    for pw in (email.upper(), email, local, local.upper(), local.title()):
        r = signup(email, pw)
        assert r.status_code == 422, pw
        assert "password" in r.json()["detail"]["fields"]
    assert user_rows(email) == []


@pytest.mark.parametrize("pw", ["1234567890", "password12", "qwertyuiop"])
def test_shr01_ac5_common_passwords_rejected(pw):
    r = signup(unique_email(), pw)
    assert r.status_code == 422 and "password" in r.json()["detail"]["fields"]


def test_shr01_ac5_no_composition_rules():
    assert signup(unique_email(), "alllowercaseletters").status_code == 202
    assert signup(unique_email(), "only a few words here").status_code == 202


def test_shr01_ac5_nul_and_unpaired_surrogate_in_password_rejected():
    for escaped in ("\\u0000", "\\ud800"):
        raw = ('{"display_name":"A","email":"%s","password":"valid-prefix-%s-suffix"}'
               % (unique_email(), escaped)).encode()
        r = call("POST", "/api/auth/signup", content=raw, headers={"Content-Type": "application/json"})
        assert r.status_code == 422, escaped
        assert "password" in r.json()["detail"]["fields"]


@pytest.mark.parametrize("name,status", [
    ("", 422), ("    ", 422), ("A", 202), ("x" * 100, 202), ("x" * 101, 422), ("bad\u0007name", 422),
    ("tab\there", 422), ("  padded  ", 202),
])
def test_shr01_ac5_display_name_bounds(name, status):
    r = signup(unique_email(), unique_password(), display_name=name)
    assert r.status_code == status, r.text
    if status == 422:
        assert "display_name" in r.json()["detail"]["fields"]


def test_shr01_ac5_display_name_is_trimmed():
    email, pw = unique_email(), unique_password()
    signup(email, pw, display_name="   Grace   ")
    assert login(email, pw).json()["user"]["display_name"] == "Grace"


# ------------------------------------------------------------------ AC6 duplicate email (SEC-AUTH-07)
def comparable(r):
    return (r.status_code, r.json(), {k: v for k, v in r.headers.items()
                                      if k.lower() not in {"date", "content-length", "server"}})


def test_shr01_sec_auth_07_duplicate_signup_is_indistinguishable_and_changes_nothing():
    email, pw = unique_email(), unique_password()
    first = signup(email, pw, display_name="Original")
    second = signup(email.upper(), unique_password(), display_name="Intruder")
    other_new = signup(unique_email(), unique_password(), display_name="Fresh")
    assert comparable(first) == comparable(second) == comparable(other_new)
    assert second.status_code == 202 and second.json() == {"status": "accepted"}
    assert len(user_rows(email)) == 1
    assert user_rows(email)[0][2] == "Original"
    assert login(email, pw).status_code == 200


def test_shr01_sec_auth_07_duplicate_signup_does_not_replace_password():
    email, pw = unique_email(), unique_password()
    signup(email, pw)
    attacker_pw = unique_password()
    assert signup(email, attacker_pw).status_code == 202
    assert login(email, attacker_pw).status_code == 401
    assert login(email, pw).status_code == 200


def test_shr01_sec_auth_07_signup_with_admin_email_leaves_admin_untouched():
    _, admin_email, admin_pw = SEEDED["admin"]
    attacker_pw = unique_password()
    r = signup(admin_email, attacker_pw)
    assert r.status_code == 202 and r.json() == {"status": "accepted"}
    assert login(admin_email, attacker_pw).status_code == 401
    admin = login(admin_email, admin_pw)
    assert admin.status_code == 200 and admin.json()["user"]["role"] == "admin"
    assert admin.json()["user"]["id"] == "demo-admin"


def test_shr01_ac6_concurrent_signups_same_email_create_one_user():
    email = unique_email()
    pws = [unique_password() for _ in range(6)]
    with ThreadPoolExecutor(6) as pool:
        results = list(pool.map(lambda p: signup(email, p), pws))
    assert [r.status_code for r in results] == [202] * 6
    assert all(r.json() == {"status": "accepted"} for r in results)
    assert len(user_rows(email)) == 1


def test_shr01_sec_auth_07_signup_timing_parity_is_loose():
    def timed(fn):
        samples = []
        for _ in range(3):
            t = time.perf_counter()
            fn()
            samples.append(time.perf_counter() - t)
        return statistics.median(samples)

    existing = unique_email()
    signup(existing, unique_password())
    new_t = timed(lambda: signup(unique_email(), unique_password()))
    dup_t = timed(lambda: signup(existing, unique_password()))
    # Both paths hash once. Loose bound so the test is not flaky; the real value is logged.
    print(f"signup timing new={new_t:.4f}s duplicate={dup_t:.4f}s")
    assert dup_t > new_t * 0.3, (new_t, dup_t)


# ------------------------------------------------------------------ AC8 login success
def test_shr01_ac8_login_success_shape_for_each_seeded_role():
    for role, (uid, email, pw) in SEEDED.items():
        r = login(email, pw)
        assert r.status_code == 200, r.text
        body = r.json()
        assert set(body) == {"user", "csrf_token"}
        assert set(body["user"]) == {"id", "email", "display_name", "role"}
        assert body["user"]["id"] == uid and body["user"]["role"] == role
        assert body["user"]["email"] == email
        assert isinstance(body["csrf_token"], str) and len(body["csrf_token"]) >= 32
        assert pw not in r.text and "scrypt" not in r.text and "password_hash" not in r.text
        assert session_cookie(r) is not None


def test_shr01_ac8_signup_user_login_returns_own_data_only():
    s = new_student()
    me = call("GET", "/api/auth/me", s).json()["user"]
    assert me["id"] == s and me["email"] == s.email and me["role"] == "student"


def test_shr01_ac8_login_input_validation():
    base = {"email": "a@example.com", "password": "whatever"}
    for body in ({**base, "role": "admin"}, {**base, "extra": 1}, {"email": "a@example.com"},
                 {"password": "x"}, {"email": 5, "password": "x"}, {"email": "a@example.com", "password": 5},
                 {"email": "a@example.com", "password": "p" * 1025}):
        r = call("POST", "/api/auth/login", json=body)
        assert r.status_code == 422 and code_of(r) == "validation_error", body
        assert not r.headers.get_list("set-cookie")


def test_shr01_ac8_login_does_not_apply_signup_password_rules():
    # A short, valid-size password is a credentials failure (401), not a validation error.
    r = login(unique_email(), "short")
    assert r.status_code == 401


# ------------------------------------------------------------------ AC9 identical 401 (SEC-AUTH-07)
def test_shr01_sec_auth_07_login_failures_are_identical():
    s = new_student()
    wrong_pw = login(s.email, unique_password())
    unknown = login(unique_email("nobody"), unique_password())
    malformed = login("not-an-email", "x")
    odd_unicode = login("  ÉÉ@example.com ", "p")
    # A user without a password hash (an unseeded demo-style user) must fail the same way.
    nohash_email = unique_email("nohash")
    sql('INSERT INTO "user"(id, display_name, role, email, password_hash) VALUES (%s, %s, %s, %s, NULL)',
        ("nohash-" + uuid.uuid4().hex[:8], "No Hash", "student", nohash_email))
    nohash = login(nohash_email, "anything-at-all-123")
    responses = [wrong_pw, unknown, malformed, odd_unicode, nohash]
    for r in responses:
        assert r.status_code == 401 and code_of(r) == "invalid_credentials"
        assert not r.headers.get_list("set-cookie")
    assert len({json.dumps(r.json(), sort_keys=True) for r in responses}) == 1


def test_shr01_sec_auth_07_unknown_email_still_spends_a_password_hash():
    s = new_student()

    def timed(email):
        samples = []
        for _ in range(3):
            t = time.perf_counter()
            assert login(email, unique_password()).status_code == 401
            samples.append(time.perf_counter() - t)
        return statistics.median(samples)

    known = timed(s.email)
    unknown = timed(unique_email("ghost"))
    print(f"login timing known={known:.4f}s unknown={unknown:.4f}s")
    assert unknown > known * 0.3, (known, unknown)


# ------------------------------------------------------------------ AC10 cookie (SEC-AUTH-09)
def test_shr01_sec_auth_09_cookie_attributes_default():
    s = new_student()
    r = login(s.email, s.password)
    value, attrs = session_cookie(r)
    assert "httponly" in attrs
    assert attrs["path"] == "/"
    assert attrs["samesite"].lower() == "lax"
    assert attrs["max-age"] == "43200"
    assert "secure" not in attrs  # test env has SESSION_COOKIE_SECURE=false
    assert "domain" not in attrs
    assert len(value) >= 43  # 256 bits as base64url


def test_shr01_sec_auth_09_cookie_attributes_follow_configuration(monkeypatch):
    s = new_student()
    monkeypatch.setenv("SESSION_COOKIE_SECURE", "true")
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "strict")
    monkeypatch.setenv("SESSION_TTL_SECONDS", "600")
    _, attrs = session_cookie(login(s.email, s.password))
    assert "secure" in attrs and attrs["samesite"].lower() == "strict" and attrs["max-age"] == "600"
    monkeypatch.setenv("SESSION_COOKIE_SAMESITE", "none")
    _, attrs = session_cookie(login(s.email, s.password))
    assert "secure" in attrs and attrs["samesite"].lower() == "none"


def test_shr01_sec_auth_09_custom_cookie_name(monkeypatch):
    s = new_student()
    monkeypatch.setenv("SESSION_COOKIE_NAME", "other_name")
    r = login(s.email, s.password)
    names = [c.split("=")[0] for c in r.headers.get_list("set-cookie")]
    assert names == ["other_name"]


@pytest.mark.parametrize("bad", ["abc", "0", "-5", "", "1.5"])
def test_shr01_ac10_invalid_ttl_uses_default(monkeypatch, bad):
    s = new_student()
    monkeypatch.setenv("SESSION_TTL_SECONDS", bad)
    assert session_cookie(login(s.email, s.password))[1]["max-age"] == "43200"


def test_shr01_sec_auth_10_database_stores_only_sha256_of_token():
    s = new_student()
    digest = hashlib.sha256(s.token.encode()).hexdigest()
    rows = sql("SELECT token_hash, user_id, csrf_token FROM auth_session WHERE token_hash = %s", (digest,))
    assert len(rows) == 1 and rows[0][1] == s
    assert rows[0][0] != s.token
    assert sql("SELECT count(*) FROM auth_session WHERE token_hash = %s OR csrf_token = %s",
               (s.token, s.token))[0][0] == 0
    assert rows[0][2] == s.csrf
    ttl = sql("SELECT extract(epoch FROM (expires_at - created_at)) FROM auth_session WHERE token_hash = %s",
              (digest,))[0][0]
    assert int(ttl) == 43200


def test_shr01_ac10_each_login_issues_a_fresh_token():
    s = new_student()
    tokens = set()
    for _ in range(3):
        t, _ = session_cookie(login(s.email, s.password))
        tokens.add(t)
    assert len(tokens) == 3 and s.token not in tokens


def test_shr01_sec_auth_09_client_supplied_session_id_is_never_adopted():
    s = new_student()
    attacker_value = "attacker-chosen-" + uuid.uuid4().hex * 2
    r = login(s.email, s.password, headers={"Cookie": f"{COOKIE_NAME}={attacker_value}"})
    value, _ = session_cookie(r)
    assert value != attacker_value
    stale = call("GET", "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={attacker_value}"})
    assert stale.status_code == 401 and code_of(stale) == "unauthenticated"


def test_shr01_ac10_concurrent_logins_create_independent_sessions():
    s = new_student()
    with ThreadPoolExecutor(2) as pool:
        rs = list(pool.map(lambda _: login(s.email, s.password), range(2)))
    a, b = (student_from_login(r, s.email, s.password) for r in rs)
    assert a.token != b.token
    assert call("GET", "/api/auth/me", a).status_code == 200
    assert call("GET", "/api/auth/me", b).status_code == 200
    assert call("POST", "/api/auth/logout", a).status_code == 200
    assert call("GET", "/api/auth/me", a).status_code == 401
    assert call("GET", "/api/auth/me", b).status_code == 200


# ------------------------------------------------------------------ AC11 me, expiry, logout (SEC-AUTH-04)
def test_shr01_ac11_me_with_and_without_session():
    s = new_student()
    r = call("GET", "/api/auth/me", s)
    assert r.status_code == 200
    assert r.json() == {"user": {"id": s, "email": s.email, "display_name": "Student stu", "role": "student"},
                        "csrf_token": s.csrf}
    r = call("GET", "/api/auth/me")
    assert r.status_code == 401 and code_of(r) == "unauthenticated"


@pytest.mark.parametrize("cookie", [
    f"{COOKIE_NAME}=", f"{COOKIE_NAME}=forged", f"{COOKIE_NAME}=" + "A" * 43, f"{COOKIE_NAME}=" + "a" * 5000,
    f"{COOKIE_NAME}='; DROP TABLE auth_session;--", "other=thing",
])
def test_shr01_sec_auth_04_forged_cookie_is_401(cookie):
    r = call("GET", "/api/auth/me", headers={"Cookie": cookie})
    assert r.status_code == 401 and code_of(r) == "unauthenticated"
    r = call("POST", "/api/practice-sets/intro-se-1/attempts", headers={"Cookie": cookie})
    assert r.status_code == 401 and code_of(r) == "unauthenticated"


def test_shr01_sec_auth_04_token_hash_value_is_not_a_valid_cookie():
    s = new_student()
    digest = hashlib.sha256(s.token.encode()).hexdigest()
    r = call("GET", "/api/auth/me", headers={"Cookie": f"{COOKIE_NAME}={digest}"})
    assert r.status_code == 401


def test_shr01_sec_auth_04_expired_session_rejected_and_row_deleted():
    s = new_student()
    digest = hashlib.sha256(s.token.encode()).hexdigest()
    sql("UPDATE auth_session SET expires_at = now() - interval '1 second' WHERE token_hash = %s", (digest,))
    r = call("GET", "/api/auth/me", s)
    assert r.status_code == 401 and code_of(r) == "unauthenticated"
    assert sql("SELECT count(*) FROM auth_session WHERE token_hash = %s", (digest,))[0][0] == 0
    r = call("POST", "/api/practice-sets/intro-se-1/attempts", s)
    assert r.status_code == 401


def test_shr01_ac11_session_expires_after_ttl(monkeypatch):
    s = new_student()
    monkeypatch.setenv("SESSION_TTL_SECONDS", "1")
    short = student_from_login(login(s.email, s.password), s.email, s.password)
    assert call("GET", "/api/auth/me", short).status_code == 200
    time.sleep(1.5)
    assert call("GET", "/api/auth/me", short).status_code == 401
    monkeypatch.delenv("SESSION_TTL_SECONDS")
    assert call("GET", "/api/auth/me", s).status_code == 200  # a normal session is unaffected


def test_shr01_ac11_logout_revokes_session_and_clears_cookie():
    s = new_student()
    digest = hashlib.sha256(s.token.encode()).hexdigest()
    r = call("POST", "/api/auth/logout", s)
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    value, attrs = session_cookie(r)
    assert value == "" or attrs.get("max-age") == "0"
    assert attrs["max-age"] == "0" and attrs["path"] == "/" and "httponly" in attrs
    assert sql("SELECT count(*) FROM auth_session WHERE token_hash = %s", (digest,))[0][0] == 0
    assert call("GET", "/api/auth/me", s).status_code == 401
    assert call("POST", "/api/practice-sets/intro-se-1/attempts", s).status_code == 401


def test_shr01_ac11_logout_without_session_is_harmless():
    r = call("POST", "/api/auth/logout")
    assert r.status_code == 200 and r.json() == {"status": "ok"}
    assert session_cookie(r)[1]["max-age"] == "0"
    r = call("POST", "/api/auth/logout", headers={"Cookie": f"{COOKIE_NAME}=forged"})
    assert r.status_code == 200


def test_shr01_ac11_logout_with_session_requires_csrf():
    s = new_student()
    for csrf in (False, "wrong-token"):
        r = call("POST", "/api/auth/logout", s, csrf=csrf)
        assert r.status_code == 403 and code_of(r) == "csrf_failed"
    assert call("GET", "/api/auth/me", s).status_code == 200  # still signed in
    assert call("POST", "/api/auth/logout", s).status_code == 200


def test_shr01_ac11_logout_revokes_only_that_session():
    s = new_student()
    other = student_from_login(login(s.email, s.password), s.email, s.password)
    call("POST", "/api/auth/logout", s)
    assert call("GET", "/api/auth/me", other).status_code == 200


def test_shr01_ac11_deleted_user_loses_access_immediately():
    s = new_student()
    sql('DELETE FROM "user" WHERE id = %s', (str(s),))
    r = call("GET", "/api/auth/me", s)
    assert r.status_code == 401 and code_of(r) == "unauthenticated"


# ------------------------------------------------------------------ AC20 headers and logs (SEC-AUTH-10)
def test_shr01_ac20_cache_control_no_store_on_all_auth_responses():
    s = new_student()
    responses = [
        signup(unique_email(), unique_password()),
        signup("bad", "x"),
        login(s.email, s.password),
        login(s.email, "wrong-password-xyz"),
        call("POST", "/api/auth/login", json={"x": 1}),
        call("GET", "/api/auth/me", s),
        call("GET", "/api/auth/me"),
        call("POST", "/api/auth/logout", s),
        call("POST", "/api/auth/logout"),
    ]
    for r in responses:
        assert "no-store" in r.headers.get("cache-control", ""), (r.status_code, r.headers)


def test_shr01_sec_auth_10_secrets_never_logged(caplog):
    caplog.set_level(logging.DEBUG)
    email, pw = unique_email(), unique_password()
    signup(email, pw)
    r = login(email, pw)
    token, _ = session_cookie(r)
    csrf = r.json()["csrf_token"]
    login(email, "Wrong-" + pw)
    s = student_from_login(r, email, pw)
    call("POST", "/api/auth/logout", s)
    text = caplog.text
    for secret in (pw, "Wrong-" + pw, token, csrf, "scrypt$"):
        assert secret not in text


def test_shr01_sec_auth_10_responses_contain_no_hash_or_other_users():
    a, b = new_student(), new_student()
    for r in (login(a.email, a.password), call("GET", "/api/auth/me", a)):
        assert b not in r.text and b.email not in r.text
        assert "scrypt" not in r.text
        assert "token_hash" not in r.text and "password_hash" not in r.text


def test_shr01_ac20_health_stays_public_and_openapi_is_schema_only():
    assert call("GET", "/api/health").status_code == 200
    assert call("GET", "/api/health/ready").status_code == 200
    r = call("GET", "/openapi.json")
    assert r.status_code == 200
    for pw in SEED_ENV.values():
        assert pw not in r.text
    assert "/api/auth/login" in r.json()["paths"]


def test_shr01_ac20_errors_have_no_stack_trace_or_sql():
    bodies = [
        call("POST", "/api/auth/login", content=b"{not json", headers={"Content-Type": "application/json"}),
        call("POST", "/api/auth/signup", content=b"[]", headers={"Content-Type": "application/json"}),
        call("POST", "/api/auth/login", content=b"\xff\xfe", headers={"Content-Type": "application/json"}),
    ]
    for r in bodies:
        assert r.status_code in (400, 422)
        for bad in ("Traceback", "sqlalchemy", "psycopg"):
            assert bad not in r.text


def test_shr01_ac8_user_ids_are_distinct_from_demo_ids():
    s = new_student()
    assert not str(s).startswith("demo-")
    assert seeded("student") == "demo-student"
