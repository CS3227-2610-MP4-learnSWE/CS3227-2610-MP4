"""ADM-07: admin-only switch that turns AI usage collection on or off for the integrated features."""
from uuid import uuid4

import pytest

from auth_helpers import SEEDED, call, code_of, login, require_db, seeded, sql, student_from_login, unique_email

PATH = "/api/admin/ai-usage/coverage"


@pytest.fixture
def admin():
    require_db()
    email = unique_email("adm07cov")
    uid = "u-" + uuid4().hex
    sql('INSERT INTO "user" (id,display_name,role,email,password_hash) '
        'SELECT %s,%s,role,%s,password_hash FROM "user" WHERE id=%s', (uid, "ADM07 admin", email, "demo-admin"))
    password = SEEDED["admin"][2]
    yield student_from_login(login(email, password), email, password)
    sql("UPDATE ai_usage_coverage SET enabled=false, covered_since=NULL, incomplete_since=NULL")


def state():
    return dict(sql("SELECT feature, enabled FROM ai_usage_coverage WHERE feature IN ('STU-03','TEA-02')"))


def test_adm07_coverage_toggle_on_then_off_keeps_start(admin):
    assert call("PUT", PATH, admin, json={"enabled": True}).json() == {"enabled": True}
    assert state() == {"STU-03": True, "TEA-02": True}
    since = sql("SELECT covered_since FROM ai_usage_coverage WHERE feature='STU-03'")[0][0]
    assert since is not None
    assert call("PUT", PATH, admin, json={"enabled": False}).json() == {"enabled": False}
    assert state() == {"STU-03": False, "TEA-02": False}
    assert sql("SELECT covered_since FROM ai_usage_coverage WHERE feature='STU-03'")[0][0] == since


@pytest.mark.parametrize("role,status", [(None, 401), ("student", 403), ("teacher", 403)])
def test_adm07_coverage_toggle_requires_admin(role, status):
    require_db()
    user = seeded(role) if role else None
    r = call("PUT", PATH, user, json={"enabled": True})
    assert r.status_code == status and code_of(r) == ("unauthenticated" if status == 401 else "forbidden")


@pytest.mark.parametrize("body", [{}, {"enabled": "yes"}, {"enabled": 1}, {"enabled": True, "feature": "ADM-03"}])
def test_adm07_coverage_toggle_rejects_bad_body(admin, body):
    assert call("PUT", PATH, admin, json=body).status_code == 422
    assert state().get("STU-03") in (None, False)


def test_adm07_coverage_toggle_needs_csrf(admin):
    assert call("PUT", PATH, admin, json={"enabled": True}, csrf=False).status_code in (401, 403)
    assert state().get("STU-03") in (None, False)
