"""Independent ADM-06 persistence, aggregates, security and concurrency tests."""
from concurrent.futures import ThreadPoolExecutor
from datetime import date, datetime, timedelta, timezone
import importlib
import threading
from uuid import uuid4

import pytest

from auth_helpers import (call, code_of, login, require_db, SEEDED, seeded, sql,
                          student_from_login, unique_email)

DAY = date(2026, 1, 15)
START = datetime(2026, 1, 15, 0, 0, tzinfo=timezone.utc)
METRICS = ("requests", "failures", "rate_limit_failures", "other_failures",
           "input_tokens", "output_tokens", "total_tokens")
FEATURES = ["STU-03", "TEA-02", "ADM-03"]
PATH = "/api/admin/ai-usage"
QUERY = "?feature=all&start_date=2026-01-15&end_date=2026-01-15"


@pytest.fixture
def service():
    require_db()
    module = importlib.import_module("ai_usage.service")
    sql("DELETE FROM ai_service_attempts")
    sql("UPDATE ai_usage_coverage SET enabled=false, covered_since=NULL, incomplete_since=NULL")
    yield module
    sql("DELETE FROM ai_service_attempts")
    sql("UPDATE ai_usage_coverage SET enabled=false, covered_since=NULL, incomplete_since=NULL")


@pytest.fixture
def admin(service):
    email = unique_email("adm06")
    uid = "u-" + uuid4().hex
    sql('INSERT INTO "user" (id,display_name,role,email,password_hash) '
        'SELECT %s,%s,role,%s,password_hash FROM "user" WHERE id=%s',
        (uid, "ADM06 admin", email, "demo-admin"))
    password = SEEDED["admin"][2]
    return student_from_login(login(email, password), email, password)


def enable(feature="STU-03", since=None, gap=None):
    sql("UPDATE ai_usage_coverage SET enabled=true, covered_since=%s, incomplete_since=%s WHERE feature=%s",
        (since or START - timedelta(days=1), gap, feature))


def add_attempt(feature="STU-03", outcome="success", tokens=(11, 7, 99), when=None, finished=None):
    aid = uuid4()
    sql("INSERT INTO ai_service_attempts (id,feature,started_at,finished_at,outcome,input_tokens,output_tokens,total_tokens) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
        (aid, feature, when or START + timedelta(hours=12),
         None if outcome == "pending" else finished or START + timedelta(hours=13), outcome, *tokens))
    return aid


def report(service, feature="STU-03", first=DAY, last=DAY):
    return service.read_usage_report(feature, first, last)


def row(service, **kwargs):
    return report(service, **kwargs)["rows"][0]


def available(value):
    return {"value": value, "reason": None}


def unavailable(reason):
    return {"value": None, "reason": reason}


def test_adm06_ac2_3_7_exact_breakdown_and_independent_totals(service):
    enable()
    for outcome in ["success", "rate_limit", "other_failure"]:
        add_attempt(outcome=outcome)
    got = report(service)
    assert set(got) == {"feature", "start_date", "end_date", "timezone", "as_of", "rows"}
    assert (got["feature"], got["start_date"], got["end_date"], got["timezone"]) == (
        "STU-03", "2026-01-15", "2026-01-15", "UTC")
    assert datetime.fromisoformat(got["as_of"].replace("Z", "+00:00")).utcoffset() == timedelta(0)
    r = got["rows"][0]
    assert set(r) == {"feature", "coverage_start", *METRICS}
    assert [r[k] for k in METRICS] == [available(n) for n in [3, 2, 1, 1, 33, 21, 297]]


def test_adm06_ac4_all_features_stable_order_covered_zero_and_uninstrumented(service):
    enable()
    got = report(service, "all")
    assert [r["feature"] for r in got["rows"]] == FEATURES
    for key in METRICS[:4]:
        assert got["rows"][0][key] == available(0)
    for key in METRICS[4:]:
        assert got["rows"][0][key] == unavailable("no_measurements")
    for r in got["rows"][1:]:
        assert r["coverage_start"] is None
        assert all(r[k] == unavailable("not_enabled") for k in METRICS)


@pytest.mark.parametrize("scenario", ["before_activation", "gap", "pending"])
def test_adm06_ac4_incomplete_and_unresolved_dispatch_never_show_partial_totals(service, scenario):
    enable(since=START + timedelta(hours=1) if scenario == "before_activation" else None,
           gap=START + timedelta(hours=5) if scenario == "gap" else None)
    add_attempt()
    if scenario == "pending":
        add_attempt(outcome="pending", tokens=(None, None, None))
    r = row(service)
    reason = "pending_attempts" if scenario == "pending" else "incomplete_coverage"
    assert all(r[k] == unavailable(reason) for k in METRICS)


def test_adm06_ac4_gap_does_not_invalidate_earlier_complete_period(service):
    enable(gap=START + timedelta(days=1))
    add_attempt()
    assert row(service)["requests"] == available(1)


def test_adm06_ac8_partial_tokens_independent_zero_and_never_derive_total(service):
    enable()
    add_attempt(tokens=(0, 4, None))
    add_attempt(tokens=(0, 6, 100))
    r = row(service)
    assert r["input_tokens"] == available(0)
    assert r["output_tokens"] == available(10)
    assert r["total_tokens"] == unavailable("missing_measurement")


def test_adm06_ac8_unsafe_javascript_sum_is_unavailable(service):
    enable()
    add_attempt(tokens=(2**53 - 1, 1, None))
    add_attempt(tokens=(1, 1, None))
    r = row(service)
    assert r["input_tokens"] == unavailable("missing_measurement")
    assert r["output_tokens"] == available(2)


def test_adm06_ac11_utc_start_inclusive_end_exclusive_and_feature_isolation(service):
    enable()
    add_attempt(when=START - timedelta(microseconds=1))
    add_attempt(when=START)
    add_attempt(when=START + timedelta(days=1) - timedelta(microseconds=1))
    add_attempt(when=START + timedelta(days=1))
    add_attempt(feature="TEA-02")
    assert row(service)["requests"] == available(2)


def test_adm06_ac11_today_cutoff_excludes_future_attempts_and_late_finalisation(service):
    today = datetime.now(timezone.utc)
    enable(since=today - timedelta(days=3))
    add_attempt(when=today - timedelta(minutes=1), finished=today + timedelta(days=1))
    add_attempt(when=today + timedelta(days=1), finished=today + timedelta(days=1))
    r = row(service, first=today.date(), last=today.date())
    assert all(r[k] == unavailable("pending_attempts") for k in METRICS)


def test_adm06_ac11_reservation_durable_finalisation_idempotent_and_conflict_preserves(service):
    aid = service.reserve_attempt("TEA-02")
    saved = sql("SELECT feature,outcome,finished_at FROM ai_service_attempts WHERE id=%s", (aid,))
    assert saved == [("TEA-02", "pending", None)]
    assert service.finish_attempt(aid, "success", input_tokens=11, total_tokens=99) is True
    original = sql("SELECT finished_at FROM ai_service_attempts WHERE id=%s", (aid,))
    assert service.finish_attempt(aid, "success", input_tokens=11, total_tokens=99) is True
    assert service.finish_attempt(aid, "other_failure", input_tokens=11, total_tokens=99) is False
    assert sql("SELECT outcome,input_tokens,output_tokens,total_tokens FROM ai_service_attempts WHERE id=%s", (aid,)) == [
        ("success", 11, None, 99)]
    assert sql("SELECT finished_at FROM ai_service_attempts WHERE id=%s", (aid,)) == original
    assert service.finish_attempt(uuid4(), "success") is False


@pytest.mark.parametrize("value", [-1, True, "12", 1.5, 2**63, {}, []])
def test_adm06_ac8_finalisation_normalises_invalid_measurement_fields_independently(service, value):
    aid = service.reserve_attempt("STU-03")
    assert service.finish_attempt(aid, "success", input_tokens=value, output_tokens=0, total_tokens=value)
    assert sql("SELECT input_tokens,output_tokens,total_tokens FROM ai_service_attempts WHERE id=%s", (aid,)) == [(None, 0, None)]


def test_adm06_ac11_concurrent_conflicting_finalisers_have_one_winner(service):
    aid = service.reserve_attempt("STU-03")
    barrier = threading.Barrier(8)

    def finish(index):
        barrier.wait(timeout=5)
        return service.finish_attempt(aid, "success" if index % 2 else "other_failure", input_tokens=index)

    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(finish, range(8)))
    assert results.count(True) == 1
    assert len(sql("SELECT id FROM ai_service_attempts WHERE id=%s", (aid,))) == 1


def test_adm06_ac11_concurrent_distinct_attempts_are_never_lost_or_duplicated(service):
    enable()
    barrier = threading.Barrier(8)

    def record(index):
        barrier.wait(timeout=5)
        aid = service.reserve_attempt("STU-03")
        assert service.finish_attempt(aid, "rate_limit" if index % 2 else "success")
        return aid

    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(pool.map(record, range(8)))
    assert len(set(ids)) == 8
    now = datetime.now(timezone.utc).date()
    r = row(service, first=now, last=now)
    assert [r[k] for k in METRICS[:4]] == [available(n) for n in [8, 4, 4, 0]]


def test_adm06_ac12_activation_idempotent_durable_and_rejects_future_feature_atomically(service):
    service.activate_coverage(["STU-03", "TEA-02"])
    original = sql("SELECT feature,enabled,covered_since,incomplete_since FROM ai_usage_coverage ORDER BY feature")
    service.activate_coverage(["TEA-02", "STU-03"])
    assert sql("SELECT feature,enabled,covered_since,incomplete_since FROM ai_usage_coverage ORDER BY feature") == original
    assert [r[1] for r in original] == [False, True, True]
    sql("UPDATE ai_usage_coverage SET enabled=false,covered_since=NULL WHERE feature='TEA-02'")
    with pytest.raises(Exception):
        service.activate_coverage(["TEA-02", "ADM-03"])
    assert sql("SELECT enabled FROM ai_usage_coverage WHERE feature='TEA-02'") == [(False,)]


def test_adm06_ac12_activation_never_clears_existing_coverage_gap(service):
    enable(gap=START)
    service.activate_coverage(["STU-03"])
    assert sql("SELECT covered_since,incomplete_since FROM ai_usage_coverage WHERE feature='STU-03'") == [(
        START - timedelta(days=1), START)]


@pytest.mark.parametrize("role,status", [(None, 401), ("student", 403), ("teacher", 403)])
def test_adm06_ac10_direct_api_auth_role_and_no_store(service, role, status):
    user = seeded(role) if role else None
    r = call("GET", PATH + QUERY, user, headers={"X-Demo-User-Id": "demo-admin"})
    assert r.status_code == status, r.text
    assert code_of(r) == ("unauthenticated" if status == 401 else "forbidden")
    assert "no-store" in r.headers.get("cache-control", "")
    assert "cookie" in r.headers.get("vary", "").lower()


def test_adm06_ac5_6_admin_report_fixed_content_free_schema(admin):
    enable()
    add_attempt()
    r = call("GET", PATH + QUERY, admin)
    assert r.status_code == 200, r.text
    assert set(r.json()) == {"feature", "start_date", "end_date", "timezone", "as_of", "rows"}
    assert "no-store" in r.headers.get("cache-control", "")
    assert "cookie" in r.headers.get("vary", "").lower()
    assert str(admin) not in r.text and admin.email not in r.text and admin.token not in r.text
    assert "%" not in r.text
    columns = {x[0] for x in sql("SELECT column_name FROM information_schema.columns "
                               "WHERE table_schema=current_schema() AND table_name='ai_service_attempts'")}
    assert columns == {"id", "feature", "started_at", "finished_at", "outcome", "input_tokens", "output_tokens", "total_tokens"}


@pytest.mark.parametrize("query", [
    "", "?feature=all", "?feature=all&start_date=2026-01-15", QUERY + "&feature=TEA-02",
    QUERY + "&user_id=demo-admin", QUERY.replace("all", "stu-03"), QUERY.replace("all", "unknown"),
    QUERY.replace("2026-01-15", "2026-02-30"), QUERY.replace("2026-01-15", "2026-1-15"),
    "?feature=all&start_date=2026-01-16&end_date=2026-01-15",
    "?feature=all&start_date=2026-01-01&end_date=2026-02-01",
    "?feature=all&start_date=2099-01-01&end_date=2099-01-02",
    QUERY.replace("all", "all%00"), QUERY.replace("all", "all%0Ainject"),
])
def test_adm06_ac11_invalid_filters_have_specific_422(admin, query):
    r = call("GET", PATH + query, admin)
    assert r.status_code == 422, r.text
    assert code_of(r) == "invalid_ai_usage_filters"


def test_adm06_ac11_ascii_outer_whitespace_is_normalised_and_31_days_allowed(admin):
    r = call("GET", PATH + "?feature=%20all%09&start_date=%202026-01-01%20&end_date=2026-01-31", admin)
    assert r.status_code == 200, r.text
    assert r.json()["feature"] == "all" and r.json()["start_date"] == "2026-01-01"


@pytest.mark.parametrize("status", ["disabled", "archived"])
def test_adm06_ac10_revoked_admin_session_cannot_read_aggregates(admin, status):
    sql('UPDATE "user" SET access_status=%s WHERE id=%s', (status, str(admin)))
    r = call("GET", PATH + QUERY, admin)
    assert r.status_code == 401


def test_adm06_ac10_expired_admin_session_cannot_read_aggregates(admin):
    sql('UPDATE auth_session SET expires_at=now()-interval \'1 day\' WHERE user_id=%s', (str(admin),))
    assert call("GET", PATH + QUERY, admin).status_code == 401


def test_adm06_ac11_report_throttle_30_per_60_seconds_has_retry_after(admin, monkeypatch):
    from auth import rate_limit
    now = [10000.0]
    monkeypatch.setattr(rate_limit.time, "monotonic", lambda: now[0])
    # Prior API tests may already have constructed this shared limiter with a real clock.
    # Isolate its cache so this test actually installs the mocked clock at construction.
    monkeypatch.setattr(rate_limit, "_limiters", {})
    for _ in range(30):
        r = call("GET", PATH + QUERY, admin)
        assert r.status_code == 200, r.text
    r = call("GET", PATH + QUERY, admin)
    assert r.status_code == 429 and code_of(r) == "ai_usage_report_rate_limited"
    assert 1 <= int(r.headers["retry-after"]) <= 60
    now[0] += 61
    assert call("GET", PATH + QUERY, admin).status_code == 200


def test_adm06_ac4_database_report_outage_is_safe_503_not_zero(admin):
    enable()
    sql("ALTER TABLE ai_usage_coverage RENAME TO adm06_temporarily_unavailable")
    try:
        r = call("GET", PATH + QUERY, admin)
        assert r.status_code == 503, r.text
        assert code_of(r) == "ai_usage_unavailable"
        assert "ai_usage_coverage" not in r.text and "SELECT" not in r.text
    finally:
        sql("ALTER TABLE adm06_temporarily_unavailable RENAME TO ai_usage_coverage")


def test_adm06_ac13_report_read_never_invokes_model(admin):
    from main import app
    from llm_client import get_llm_client

    def forbidden_model():
        pytest.fail("Reporting must never instantiate or invoke a model")

    app.dependency_overrides[get_llm_client] = forbidden_model
    try:
        assert call("GET", PATH + QUERY, admin).status_code == 200
    finally:
        app.dependency_overrides.pop(get_llm_client, None)


def test_adm06_ac11_readers_during_finalisation_get_consistent_snapshot(service):
    enable()
    ids = [add_attempt(outcome="pending", tokens=(None, None, None)) for _ in range(8)]
    barrier = threading.Barrier(2)

    def finalise():
        barrier.wait(timeout=5)
        for aid in ids:
            assert service.finish_attempt(aid, "other_failure", input_tokens=0, output_tokens=0, total_tokens=0)

    def read():
        barrier.wait(timeout=5)
        for _ in range(20):
            r = row(service)
            if r["requests"]["value"] is None:
                assert all(r[k] == unavailable("pending_attempts") for k in METRICS)
            else:
                assert [r[k] for k in METRICS[:4]] == [available(n) for n in [8, 8, 0, 8]]

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(finalise), pool.submit(read)]
        for future in futures:
            future.result(timeout=15)
