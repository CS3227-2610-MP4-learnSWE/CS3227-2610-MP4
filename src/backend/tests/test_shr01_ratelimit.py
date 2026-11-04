"""SHR-01 rate limiting on login and signup (AC18, SEC-AUTH-08).

Limits are read from the environment on each request, so tests lower them with monkeypatch.
Every test uses its own emails and X-Forwarded-For addresses so counters never overlap.
"""
import time

import pytest
from auth_helpers import call, code_of, fresh_ip, login, new_student, signup, unique_email, unique_password


def assert_429(r):
    assert r.status_code == 429, r.text
    detail = r.json()["detail"]
    assert detail["code"] == "rate_limited"
    seconds = detail["retry_after_seconds"]
    assert isinstance(seconds, int) and not isinstance(seconds, bool) and seconds > 0
    assert r.headers["retry-after"] == str(seconds)
    assert "Cache-Control".lower() in r.headers and "no-store" in r.headers["cache-control"]
    return detail


@pytest.fixture
def low_email_limit(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "3")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "1000")


def test_shr01_sec_auth_08_per_email_limit_blocks_even_the_correct_password(low_email_limit):
    s = new_student()
    ip = fresh_ip()
    for _ in range(3):
        assert login(s.email, "wrong-" + unique_password(), ip=ip).status_code == 401
    r = login(s.email, "wrong-" + unique_password(), ip=ip)
    assert_429(r)
    # blocked before any password check: the right password is refused as well, and no cookie is set
    r = login(s.email, s.password, ip=ip)
    assert_429(r)
    assert not r.headers.get_list("set-cookie")
    # another IP does not help while the email is limited
    assert_429(login(s.email, s.password, ip=fresh_ip()))


def test_shr01_sec_auth_08_limit_shape_is_identical_for_existing_and_unknown_emails(low_email_limit):
    s = new_student()
    ghost = unique_email("ghost")
    bodies = []
    for email in (s.email, ghost):
        for _ in range(3):
            assert login(email, "wrong-" + unique_password()).status_code == 401
        r = login(email, "wrong-" + unique_password())
        detail = assert_429(r)
        bodies.append((r.status_code, set(detail), detail["code"], detail["message"]))
    assert bodies[0] == bodies[1]


def test_shr01_sec_auth_08_email_case_and_space_variants_share_one_counter(low_email_limit):
    s = new_student()
    variants = [s.email.upper(), f"  {s.email} ", s.email.title()]
    for v in variants:
        assert login(v, "wrong-" + unique_password()).status_code == 401
    assert_429(login(s.email, "wrong-" + unique_password()))
    assert_429(login(f" {s.email.upper()}  ", s.password))


def test_shr01_sec_auth_08_other_accounts_are_not_limited_by_one_victim(low_email_limit):
    victim, bystander = new_student(), new_student()
    for _ in range(3):
        login(victim.email, "wrong-" + unique_password())
    assert_429(login(victim.email, victim.password))
    assert login(bystander.email, bystander.password).status_code == 200


def test_shr01_ac18_successful_logins_do_not_count_as_failures(low_email_limit):
    s = new_student()
    for _ in range(8):
        assert login(s.email, s.password).status_code == 200


def test_shr01_sec_auth_08_per_ip_limit_applies_across_emails(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "3")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "1000")
    ip = fresh_ip()
    for _ in range(3):
        assert login(unique_email("ghost"), "wrong-" + unique_password(), ip=ip).status_code == 401
    assert_429(login(unique_email("ghost"), "wrong-" + unique_password(), ip=ip))
    s = new_student()
    assert_429(login(s.email, s.password, ip=ip))  # a valid login from the limited IP is refused too
    assert login(s.email, s.password, ip=fresh_ip()).status_code == 200  # other addresses unaffected


def test_shr01_sec_auth_08_spoofed_forwarded_for_prefix_does_not_bypass_ip_limit(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "3")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "1000")
    real = fresh_ip()
    for i in range(3):
        r = login(unique_email("ghost"), "wrong-" + unique_password(), ip=f"203.0.113.{i + 1}, {real}")
        assert r.status_code == 401
    assert_429(login(unique_email("ghost"), "x", ip=f"198.51.100.77, {real}"))  # last entry is used


def test_shr01_ac18_forwarded_for_ignored_when_proxy_headers_untrusted(monkeypatch):
    monkeypatch.setenv("TRUST_PROXY_HEADERS", "false")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "3")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "1000")
    # Every request now shares request.client.host, whatever X-Forwarded-For says.
    for _ in range(3):
        login(unique_email("ghost"), "wrong-" + unique_password())
    assert_429(login(unique_email("ghost"), "wrong-" + unique_password()))


def test_shr01_ac18_signup_is_limited_per_ip(monkeypatch):
    monkeypatch.setenv("AUTH_SIGNUP_MAX_PER_IP", "2")
    ip = fresh_ip()
    assert signup(unique_email(), unique_password(), ip=ip).status_code == 202
    assert signup(unique_email(), unique_password(), ip=ip).status_code == 202
    r = signup(unique_email(), unique_password(), ip=ip)
    assert_429(r)
    refused = unique_email()
    assert_429(signup(refused, unique_password(), ip=ip))
    from auth_helpers import sql
    assert sql('SELECT count(*) FROM "user" WHERE email = %s', (refused,))[0][0] == 0
    assert signup(unique_email(), unique_password(), ip=fresh_ip()).status_code == 202


def test_shr01_ac18_signup_limit_does_not_depend_on_email_being_new(monkeypatch):
    monkeypatch.setenv("AUTH_SIGNUP_MAX_PER_IP", "2")
    ip = fresh_ip()
    s = new_student()
    assert signup(s.email, unique_password(), ip=ip).status_code == 202  # duplicate, counted
    assert signup(s.email, unique_password(), ip=ip).status_code == 202
    assert_429(signup(s.email, unique_password(), ip=ip))


@pytest.mark.parametrize("bad", ["abc", "-3", "", "1.5"])
def test_shr01_ac18_invalid_limit_value_falls_back_to_default_fail_closed(monkeypatch, bad):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", bad)
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "1000")
    s = new_student()
    for _ in range(5):  # the default is 5 failures per email
        assert login(s.email, "wrong-" + unique_password()).status_code == 401
    assert_429(login(s.email, "wrong-" + unique_password()))


@pytest.mark.parametrize("bad", ["abc", "-3", ""])
def test_shr01_ac18_invalid_signup_limit_falls_back_to_default(monkeypatch, bad):
    monkeypatch.setenv("AUTH_SIGNUP_MAX_PER_IP", bad)
    ip = fresh_ip()
    for _ in range(10):  # the default is 10 per hour
        assert signup(unique_email(), unique_password(), ip=ip).status_code == 202
    assert_429(signup(unique_email(), unique_password(), ip=ip))


def test_shr01_ac18_limit_recovers_after_the_window(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "2")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "1000")
    monkeypatch.setenv("AUTH_LOGIN_WINDOW_SECONDS", "2")
    s = new_student()
    for _ in range(2):
        assert login(s.email, "wrong-" + unique_password()).status_code == 401
    detail = assert_429(login(s.email, s.password))
    assert detail["retry_after_seconds"] <= 2
    time.sleep(2.3)
    assert login(s.email, s.password).status_code == 200


def test_shr01_ac18_rate_limited_response_before_validation_free_of_secrets(low_email_limit):
    s = new_student()
    pw = "wrong-" + unique_password()
    for _ in range(3):
        login(s.email, pw)
    r = login(s.email, pw)
    assert_429(r)
    assert pw not in r.text and s.email not in r.text
    assert code_of(r) == "rate_limited"


# ------------------------------------------------------------------ concurrency (verifier B1)
def burst(fn, n):
    """Run fn(i) in n threads released together, so every request is in flight at once."""
    from concurrent.futures import ThreadPoolExecutor
    from threading import Barrier

    barrier = Barrier(n)

    def run(i):
        barrier.wait()
        return fn(i)

    with ThreadPoolExecutor(n) as pool:
        return list(pool.map(run, range(n)))


def test_shr01_sec_auth_08_parallel_wrong_passwords_cannot_exceed_the_per_email_limit(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "3")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "1000")
    s = new_student()
    results = burst(lambda i: login(s.email, f"wrong-{i}-" + unique_password()), 10)
    statuses = [r.status_code for r in results]
    assert set(statuses) <= {401, 429}, statuses
    assert statuses.count(401) <= 3, statuses
    assert statuses.count(429) >= 7, statuses
    for r in results:
        if r.status_code == 429:
            assert_429(r)
        else:
            assert code_of(r) == "invalid_credentials"
    # The window is now full: even the correct password is refused.
    assert_429(login(s.email, s.password))


def test_shr01_sec_auth_08_parallel_wrong_passwords_cannot_exceed_the_per_ip_limit(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "3")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "1000")
    ip = fresh_ip()
    results = burst(lambda i: login(unique_email("ghost"), "wrong-" + unique_password(), ip=ip), 10)
    statuses = [r.status_code for r in results]
    assert set(statuses) <= {401, 429}, statuses
    assert statuses.count(401) <= 3, statuses
    assert statuses.count(429) >= 7, statuses
    for r in results:
        if r.status_code == 429:
            assert_429(r)
    assert login(unique_email("ghost"), "x", ip=fresh_ip()).status_code == 401  # other IPs unaffected


def test_shr01_sec_auth_08_parallel_mixed_attempts_still_respect_the_email_limit(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "2")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "1000")
    s = new_student()
    results = burst(
        lambda i: login(s.email, "wrong-" + unique_password()) if i % 2 else login(s.email, s.password), 10
    )
    assert len([r for r in results if r.status_code == 401]) <= 2, [r.status_code for r in results]


def test_shr01_ac18_parallel_successful_logins_are_not_throttled_by_the_failure_limit(monkeypatch):
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_EMAIL", "2")
    monkeypatch.setenv("AUTH_LOGIN_MAX_FAILURES_PER_IP", "2")
    s = new_student()
    ip = fresh_ip()
    results = burst(lambda i: login(s.email, s.password, ip=ip), 10)
    assert [r.status_code for r in results] == [200] * 10
    # successes left the failure counters untouched: exactly two failures are still allowed
    assert login(s.email, "wrong-" + unique_password(), ip=ip).status_code == 401
    assert login(s.email, "wrong-" + unique_password(), ip=ip).status_code == 401
    assert_429(login(s.email, "wrong-" + unique_password(), ip=ip))


# Unbounded limiter state (many distinct emails) cannot be observed over HTTP from the plan's
# contract, so no test is written for it.
