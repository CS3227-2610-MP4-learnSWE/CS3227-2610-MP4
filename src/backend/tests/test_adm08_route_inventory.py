"""ADM-08 AC1, AC2 (SHR-01, SHR-05): the frozen set of 30 feedback and messaging routes and their access rules.

Contract: workflow/specs/ADM-08/plan.md "API endpoints" (frozen route inventory). Written before the endpoint code.
"""
import pytest

from auth_helpers import call
from adm02_helpers import actor, uid

PREFIXES = ("/api/admin/feedback", "/api/admin/messaging", "/api/feedback", "/api/messaging")

ADMIN_ROUTES = {
    ("GET", "/api/admin/feedback/forms"),
    ("POST", "/api/admin/feedback/forms"),
    ("GET", "/api/admin/feedback/associations"),
    ("GET", "/api/admin/feedback/forms/{form_id}"),
    ("PUT", "/api/admin/feedback/forms/{form_id}"),
    ("GET", "/api/admin/feedback/forms/{form_id}/audience"),
    ("POST", "/api/admin/feedback/forms/{form_id}/publish"),
    ("POST", "/api/admin/feedback/forms/{form_id}/close"),
    ("GET", "/api/admin/feedback/forms/{form_id}/responses"),
    ("GET", "/api/admin/feedback/forms/{form_id}/responses/{response_id}"),
    ("DELETE", "/api/admin/feedback/forms/{form_id}/responses/{response_id}"),
    ("GET", "/api/admin/feedback/forms/{form_id}/response-count"),
    ("POST", "/api/admin/feedback/analyses"),
    ("GET", "/api/admin/feedback/analyses"),
    ("GET", "/api/admin/feedback/analyses/{analysis_id}"),
    ("DELETE", "/api/admin/feedback/analyses/{analysis_id}"),
    ("GET", "/api/admin/feedback/analyses/{analysis_id}/responses/{label}"),
    ("GET", "/api/admin/messaging/feedback-responses/{response_id}/recipient"),
    ("GET", "/api/admin/messaging/recipients"),
    ("POST", "/api/admin/messaging/previews"),
    ("GET", "/api/admin/messaging/previews/{preview_id}"),
    ("POST", "/api/admin/messaging/previews/{preview_id}/send"),
    ("GET", "/api/admin/messaging/followup-counts"),
}
RECIPIENT_ROUTES = {
    ("GET", "/api/feedback/inbox"),
    ("GET", "/api/feedback/forms/{form_id}"),
    ("PUT", "/api/feedback/forms/{form_id}/draft"),
    ("POST", "/api/feedback/forms/{form_id}/responses"),
    ("GET", "/api/messaging/inbox"),
    ("GET", "/api/messaging/unread-count"),
    ("POST", "/api/messaging/inbox/{delivery_id}/read"),
}
FROZEN = ADMIN_ROUTES | RECIPIENT_ROUTES


def application_routes():
    from main import app

    found = set()
    for route in app.routes:
        path = getattr(route, "path", "")
        if not any(path == p or path.startswith(p + "/") for p in PREFIXES):
            continue
        for method in getattr(route, "methods", None) or ():
            if method not in ("HEAD", "OPTIONS"):
                found.add((method, path))
    return found


def concrete(path):
    return (path.replace("{form_id}", uid()).replace("{response_id}", uid()).replace("{analysis_id}", uid())
            .replace("{preview_id}", uid()).replace("{delivery_id}", uid()).replace("{label}", "R1"))


def body_for(method):
    return {} if method in ("POST", "PUT") else None


def test_adm08_ac1_frozen_inventory_has_thirty_routes():
    assert len(ADMIN_ROUTES) == 23 and len(RECIPIENT_ROUTES) == 7 and len(FROZEN) == 30


def test_adm08_ac1_application_routes_equal_the_frozen_set_exactly():
    found = application_routes()
    assert found - FROZEN == set(), f"unexpected routes: {sorted(found - FROZEN)}"
    assert FROZEN - found == set(), f"missing routes: {sorted(FROZEN - found)}"


def test_adm08_ac1_the_new_count_route_is_admin_messaging_only():
    found = application_routes()
    assert ("GET", "/api/admin/messaging/followup-counts") in found
    assert not any("followup-counts" in p and not p.startswith("/api/admin/messaging/") for _, p in found)


@pytest.mark.parametrize("method,path", sorted(ADMIN_ROUTES))
def test_adm08_ac1_admin_route_rejects_anonymous_with_401_and_no_store(method, path):
    reply = call(method, concrete(path), None, body_for(method))
    assert reply.status_code == 401, (method, path, reply.status_code, reply.text)
    assert "no-store" in reply.headers.get("cache-control", "")


@pytest.mark.parametrize("role", ["student", "teacher"])
@pytest.mark.parametrize("method,path", sorted(ADMIN_ROUTES))
def test_adm08_ac1_admin_route_rejects_student_and_teacher_with_403_and_no_store(method, path, role):
    reply = call(method, concrete(path), actor(role), body_for(method))
    assert reply.status_code == 403, (role, method, path, reply.status_code, reply.text)
    assert "no-store" in reply.headers.get("cache-control", "")


@pytest.mark.parametrize("method,path", sorted(RECIPIENT_ROUTES))
def test_adm08_ac1_recipient_route_rejects_anonymous_with_401(method, path):
    reply = call(method, concrete(path), None, body_for(method))
    assert reply.status_code == 401, (method, path, reply.status_code, reply.text)


def test_adm08_ac2_the_two_list_count_urls_are_existing_admin_only_routes():
    for path in ("/api/admin/feedback/forms?limit=100&offset=0", "/api/admin/feedback/analyses?limit=50&offset=0"):
        anon = call("GET", path, None)
        assert anon.status_code == 401 and "no-store" in anon.headers.get("cache-control", "")
        for role in ("student", "teacher"):
            reply = call("GET", path, actor(role))
            assert reply.status_code == 403 and "no-store" in reply.headers.get("cache-control", "")


def test_adm08_ac2_the_list_count_urls_still_answer_an_admin_with_their_existing_shape():
    admin = actor("admin")
    forms = call("GET", "/api/admin/feedback/forms?limit=100&offset=0", admin)
    assert forms.status_code == 200 and set(forms.json()) == {"items", "next_offset"}
    analyses = call("GET", "/api/admin/feedback/analyses?limit=50&offset=0", admin)
    assert analyses.status_code == 200 and set(analyses.json()) == {"items", "next_offset"}
