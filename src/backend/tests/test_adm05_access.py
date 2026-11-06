"""Independent ADM-05 endpoint tests written from the approved contract only."""
from concurrent.futures import ThreadPoolExecutor
import threading
import uuid

import pytest

from auth_helpers import (call, code_of, login, seeded, signup, sql,
                          student_from_login, unique_email)
from stu01_helpers import make_lesson, put_completion, get_lesson, completion_rows

BASE = "/api/admin"
PASSWORD = "ExampleOnly!7Qm#42vL"  # Test-only illustration, never a default credential.


@pytest.fixture
def admin():
    return seeded("admin")


def create(admin, role="student", name="ADM05 Test", email=None):
    email = email or unique_email("adm05")
    response = call("POST", f"{BASE}/accounts", admin,
                    {"display_name": name, "email": email, "password": PASSWORD, "role": role})
    assert response.status_code == 201, response.text
    account = response.json()
    assert set(account) == {"id", "email", "display_name", "role", "status"}
    assert account["status"] == "enabled" and account["role"] == role
    assert account["id"].startswith("u-")
    return account


def signed(account):
    return student_from_login(login(account["email"], PASSWORD), account["email"], PASSWORD)


def course(admin, title=None):
    response = call("POST", f"{BASE}/courses", admin, {"title": title or f"ADM05 {uuid.uuid4().hex}"})
    assert response.status_code == 201, response.text
    assert set(response.json()) == {"id", "title"}
    uuid.UUID(response.json()["id"])
    return response.json()


def access(admin, account, crs, method="PUT"):
    return call(method, f"{BASE}/accounts/{account['id']}/courses/{crs['id']}", admin)


def status(admin, account, value):
    return call("PUT", f"{BASE}/accounts/{account['id']}/status", admin, {"status": value})


def detail(admin, account):
    response = call("GET", f"{BASE}/accounts/{account['id']}", admin)
    assert response.status_code == 200, response.text
    assert set(response.json()) == {"account", "courses"}
    return response.json()


@pytest.mark.parametrize("role", ["student", "teacher", "admin"])
def test_adm05_ac5_7_8_create_each_fixed_role_hashes_password_and_allows_login(admin, role):
    account = create(admin, role)
    assert detail(admin, account)["courses"] == []
    user = signed(account)
    assert user.role == role
    me = call("GET", "/api/auth/me", user)
    assert me.status_code == 200
    stored = sql('SELECT password_hash FROM "user" WHERE id=%s', (account["id"],))[0][0]
    assert stored and stored != PASSWORD and PASSWORD not in stored
    assert PASSWORD not in str(account) + str(detail(admin, account))


def test_adm05_ac1_2_3_disable_all_sessions_preserves_permissions_and_reenable_requires_login(admin):
    account = create(admin)
    first, second = signed(account), signed(account)
    crs = course(admin)
    assert access(admin, account, crs).status_code == 200
    assert status(admin, account, "disabled").json()["status"] == "disabled"
    for user in (first, second):
        assert call("GET", "/api/auth/me", user).status_code == 401
    denied = login(account["email"], PASSWORD)
    assert denied.status_code == 401 and code_of(denied) == "invalid_credentials"
    assert [c["id"] for c in detail(admin, account)["courses"]] == [crs["id"]]
    another = course(admin)
    assert access(admin, account, another).status_code == 200
    assert access(admin, account, crs, "DELETE").status_code == 200
    assert status(admin, account, "enabled").status_code == 200
    assert call("GET", "/api/auth/me", first).status_code == 401
    assert call("GET", "/api/auth/me", signed(account)).status_code == 200


@pytest.mark.parametrize("action", ["disable", "archive"])
def test_adm05_ac4_15_self_management_rejected(admin, action):
    if action == "disable":
        response = status(admin, {"id": str(admin)}, "disabled")
    else:
        response = call("POST", f"{BASE}/accounts/{admin}/archive", admin)
    assert response.status_code == 409 and code_of(response) == "self_change"
    assert call("GET", "/api/auth/me", admin).status_code == 200


def test_adm05_ac9_10_11_12_grant_revoke_regrant_preserves_completion(admin):
    account, crs = create(admin), course(admin)
    user = signed(account)
    lesson = make_lesson(crs["id"])
    assert get_lesson(user, lesson).status_code == 404
    for _ in range(2):
        assert access(admin, account, crs).status_code == 200
    assert get_lesson(user, lesson).status_code == 200
    assert put_completion(user, lesson, True).status_code == 200
    before = completion_rows(user, lesson)
    for _ in range(2):
        assert access(admin, account, crs, "DELETE").status_code == 200
    assert get_lesson(user, lesson).status_code == 404
    assert put_completion(user, lesson, False).status_code == 404
    assert completion_rows(user, lesson) == before
    assert access(admin, account, crs).status_code == 200
    assert get_lesson(user, lesson).json()["completed"] is True


def test_adm05_ac9_16_17_teacher_only_manages_explicitly_assigned_courses(admin):
    account, crs = create(admin, "teacher"), course(admin, "  ADM05 teacher course  ")
    user = signed(account)
    path = f"/api/teacher/courses/{crs['id']}/topics"
    assert crs["title"] == "ADM05 teacher course"
    assert call("GET", path, user).status_code == 404
    assert access(admin, account, crs).status_code == 200
    assert call("GET", path, user).status_code == 200
    assert access(admin, account, crs, "DELETE").status_code == 200
    assert call("GET", path, user).status_code == 404


def test_adm05_ac13_14_archive_retains_history_reserves_email_and_is_irreversible(admin):
    account, crs = create(admin), course(admin)
    user = signed(account)
    assert access(admin, account, crs).status_code == 200
    lesson = make_lesson(crs["id"])
    assert put_completion(user, lesson, True).status_code == 200
    before = completion_rows(user, lesson)
    path = f"{BASE}/accounts/{account['id']}/archive"
    for _ in range(2):
        archived = call("POST", path, admin)
        assert archived.status_code == 200 and archived.json()["status"] == "archived"
    assert detail(admin, account)["courses"] == []
    assert completion_rows(user, lesson) == before
    assert sql('SELECT archived_at FROM "user" WHERE id=%s', (account["id"],))[0][0] is not None
    assert not sql("SELECT id FROM auth_session WHERE user_id=%s", (account["id"],))
    assert call("GET", "/api/auth/me", user).status_code == 401
    assert login(account["email"], PASSWORD).status_code == 401
    assert status(admin, account, "enabled").status_code == 409
    assert access(admin, account, crs).status_code == 409
    assert signup(account["email"], "Another-valid-Pw-9999").status_code == 202
    duplicate = call("POST", f"{BASE}/accounts", admin, {
        "display_name": "Duplicate", "email": account["email"].upper(), "password": PASSWORD, "role": "admin"})
    assert duplicate.status_code == 409 and code_of(duplicate) == "email_exists"
    assert sql('SELECT count(*) FROM "user" WHERE email=%s', (account["email"],))[0][0] == 1


def test_adm05_ac13_archive_preserves_teacher_authorship(admin):
    account, crs = create(admin, "teacher"), course(admin)
    lesson = make_lesson(crs["id"], published_by=account["id"])
    assert call("POST", f"{BASE}/accounts/{account['id']}/archive", admin).status_code == 200
    assert sql("SELECT published_by FROM published_lesson WHERE id=%s", (lesson,))[0][0] == account["id"]


def test_adm05_ac18_search_is_literal_case_insensitive_and_pagination_has_total(admin):
    prefix = "ADM05" + uuid.uuid4().hex[:8]
    a = create(admin, name=prefix + " Alpha_%")
    b = create(admin, "teacher", name=prefix + " Beta")
    assert status(admin, b, "disabled").status_code == 200
    response = call("GET", f"{BASE}/accounts", admin)
    assert response.status_code == 200
    assert response.headers.get("cache-control") == "no-store"
    page = call("GET", f"{BASE}/accounts?search={prefix}&status=all&page_size=1&page=1", admin).json()
    assert page["total"] == 2 and page["page_size"] == 1 and page["page"] == 1
    assert page["accounts"][0]["id"] == a["id"]
    second = call("GET", f"{BASE}/accounts?search={prefix}&status=all&page_size=1&page=2", admin).json()
    assert second["accounts"][0]["id"] == b["id"]
    literal = call("GET", f"{BASE}/accounts?search=%25&status=all", admin).json()
    assert a["id"] in {u["id"] for u in literal["accounts"]}
    assert b["id"] not in {u["id"] for u in literal["accounts"]}
    email = call("GET", f"{BASE}/accounts?search={a['email'].upper()}&role=student", admin).json()
    assert [u["id"] for u in email["accounts"]] == [a["id"]]
    disabled = call("GET", f"{BASE}/accounts?search={prefix}&status=disabled", admin).json()
    assert [u["id"] for u in disabled["accounts"]] == [b["id"]]
    empty = call("GET", f"{BASE}/accounts?search={prefix}&status=all&page=999", admin).json()
    assert empty["accounts"] == [] and empty["total"] == 2


ENDPOINTS = [
    ("GET", "/accounts", None), ("POST", "/accounts", {}),
    ("GET", "/accounts/unknown", None), ("PUT", "/accounts/unknown/status", {"status": "disabled"}),
    ("POST", "/accounts/unknown/archive", None),
    ("PUT", "/accounts/unknown/courses/11111111-1111-4111-8111-111111111111", None),
    ("DELETE", "/accounts/unknown/courses/11111111-1111-4111-8111-111111111111", None),
    ("GET", "/courses", None), ("POST", "/courses", {"title": "Forbidden"}),
]


@pytest.mark.parametrize("method,path,body", ENDPOINTS)
@pytest.mark.parametrize("role", [None, "student", "teacher"])
def test_adm05_ac20_all_endpoints_enforce_auth_role_and_no_store(admin, method, path, body, role):
    user = seeded(role) if role else None
    response = call(method, BASE + path, user, body, headers={"X-Demo-User-Id": str(admin), "X-Student-Id": str(admin)})
    assert response.status_code == (403 if role else 401), response.text
    assert response.headers.get("cache-control") == "no-store"


@pytest.mark.parametrize("method,path,body", [e for e in ENDPOINTS if e[0] != "GET"])
@pytest.mark.parametrize("csrf,headers", [(False, {}), (True, {"Origin": "https://evil.example"})])
def test_adm05_ac20_unsafe_endpoints_require_csrf_and_origin(admin, method, path, body, csrf, headers):
    response = call(method, BASE + path, admin, body, csrf=csrf, headers=headers)
    assert response.status_code == 403 and code_of(response) == "csrf_failed"


@pytest.mark.parametrize("query", ["page=0", "page_size=101", "page_size=0", "role=root", "status=deleted", "search=" + "x" * 201, "unknown=1"])
def test_adm05_ac21_list_rejects_invalid_query(admin, query):
    response = call("GET", f"{BASE}/accounts?{query}", admin)
    assert response.status_code == 422 and code_of(response) == "validation_error"


@pytest.mark.parametrize("patch", [{"role": "root"}, {"password": "password123"}, {"email": "bad"}, {"display_name": "x" * 81}, {"status": "enabled"}, {"password_hash": "forged"}])
def test_adm05_ac6_7_21_create_rejects_invalid_or_privilege_payloads(admin, patch):
    body = {"display_name": "ADM05 Invalid", "email": unique_email(), "password": PASSWORD, "role": "student", **patch}
    response = call("POST", f"{BASE}/accounts", admin, body)
    assert response.status_code == 422 and code_of(response) == "validation_error"


def test_adm05_ac6_21_no_role_change_api_or_admin_course_assignment(admin):
    account, crs = create(admin, "admin"), course(admin)
    response = status(admin, account, "disabled")
    assert response.status_code == 200
    for method in ("PUT", "PATCH"):
        response = call(method, f"{BASE}/accounts/{account['id']}", admin, {"role": "student"})
        assert response.status_code in (404, 405)
    extra = call("PUT", f"{BASE}/accounts/{account['id']}/status", admin, {"status": "enabled", "role": "teacher"})
    assert extra.status_code == 422
    denied = access(admin, account, crs)
    assert denied.status_code == 409 and code_of(denied) == "invalid_assignment"
    assert detail(admin, account)["account"]["role"] == "admin"


@pytest.mark.parametrize("title", ["", "   ", "x" * 201, "bad\x00title"])
def test_adm05_ac16_21_course_title_validation(admin, title):
    response = call("POST", f"{BASE}/courses", admin, {"title": title})
    assert response.status_code == 422 and code_of(response) == "validation_error"


def parallel(*actions):
    barrier = threading.Barrier(len(actions))
    def run(action):
        barrier.wait(timeout=10)
        return action()
    with ThreadPoolExecutor(max_workers=len(actions)) as pool:
        futures = [pool.submit(run, a) for a in actions]
        return [f.result(timeout=30) for f in futures]


def test_adm05_ac11_concurrent_duplicate_grants_and_archive_grant_consistent(admin):
    account, crs = create(admin), course(admin)
    responses = parallel(*[lambda: access(admin, account, crs) for _ in range(4)])
    assert all(r.status_code == 200 for r in responses)
    assert len(detail(admin, account)["courses"]) == 1
    responses = parallel(lambda: access(admin, account, crs),
                         lambda: call("POST", f"{BASE}/accounts/{account['id']}/archive", admin))
    assert all(r.status_code in (200, 409) for r in responses)
    result = detail(admin, account)
    assert result["account"]["status"] == "archived" and result["courses"] == []


def test_adm05_ac11_concurrent_opposite_membership_changes_leave_one_consistent_state(admin):
    account, crs = create(admin), course(admin)
    responses = parallel(lambda: access(admin, account, crs), lambda: access(admin, account, crs, "DELETE"))
    assert all(r.status_code == 200 for r in responses)
    assert len(detail(admin, account)["courses"]) in (0, 1)
    assert access(admin, account, crs, "DELETE").json()["courses"] == []


def test_adm05_ac7_21_concurrent_duplicate_email_creates_exactly_one_account(admin):
    email = unique_email("adm05-concurrent")
    body = {"display_name": "Concurrent account", "email": email, "password": PASSWORD, "role": "teacher"}
    responses = parallel(*[lambda: call("POST", f"{BASE}/accounts", admin, body) for _ in range(3)])
    assert sorted(r.status_code for r in responses) == [201, 409, 409]
    assert sql('SELECT count(*) FROM "user" WHERE email=%s', (email,))[0][0] == 1


def test_adm05_ac4_15_concurrent_admins_cannot_disable_each_other_and_leave_no_enabled_admin(admin):
    a, b = create(admin, "admin"), create(admin, "admin")
    actor_a, actor_b = signed(a), signed(b)
    others = sql('SELECT id,access_status FROM "user" WHERE role=\'admin\' AND id NOT IN (%s,%s)', (a["id"], b["id"]))
    try:
        sql('UPDATE "user" SET access_status=\'disabled\' WHERE role=\'admin\' AND id NOT IN (%s,%s)', (a["id"], b["id"]))
        responses = parallel(lambda: status(actor_a, b, "disabled"), lambda: status(actor_b, a, "disabled"))
        assert sum(r.status_code == 200 for r in responses) == 1
        assert all(r.status_code in (200, 401, 409) for r in responses)
        assert sql('SELECT count(*) FROM "user" WHERE role=\'admin\' AND access_status=\'enabled\'')[0][0] == 1
    finally:
        for uid, old in others:
            sql('UPDATE "user" SET access_status=%s WHERE id=%s', (old, uid))


@pytest.mark.parametrize("action", ["disable", "archive"])
def test_adm05_ac10_ai_result_discarded_when_account_revoked_during_inference(admin, fake, action):
    from companion_helpers import ask
    account = create(admin)
    user = signed(account)
    fake.gate = threading.Event()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(ask, user, "Explain modularity")
            assert fake.entered.wait(10), "request never reached mocked AI"
            if action == "disable":
                response = status(admin, account, "disabled")
            else:
                response = call("POST", f"{BASE}/accounts/{account['id']}/archive", admin)
            assert response.status_code == 200, response.text
            fake.gate.set()
            reply = future.result(timeout=20)
        assert reply.status_code == 401 and code_of(reply) == "unauthenticated"
        assert fake.reply not in reply.text
    finally:
        fake.gate.set()

@pytest.mark.parametrize("user_id", ["bad%00id", "x" * 65])
@pytest.mark.parametrize("method,suffix,body", [("GET", "", None), ("PUT", "/status", {"status": "disabled"}), ("POST", "/archive", None)])
def test_adm05_ac21_invalid_opaque_user_ids_are_422_after_auth(admin, user_id, method, suffix, body):
    path = f"{BASE}/accounts/{user_id}{suffix}"
    anonymous = call(method, path, json=body)
    assert anonymous.status_code == 401
    rejected = call(method, path, admin, body)
    assert rejected.status_code == 422 and code_of(rejected) == "validation_error"
