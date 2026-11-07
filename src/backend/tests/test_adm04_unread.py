"""ADM-04 redesign: private metadata-only navigation count."""
import pytest
from auth_helpers import call
from adm02_helpers import actor, form_get
from adm04_helpers import announcement, preview, delivered, feedback, messages


@pytest.mark.parametrize('role', ['student', 'teacher'])
def test_adm04_unread_summary_owned_components_and_read_updates(role):
    admin, user, other = actor('admin'), actor(role), actor(role)
    form, _ = feedback(admin, user)
    assert form_get(user, form).status_code == 200
    # The completed form has been read; create a separate unread request.
    from adm02_helpers import published
    request = published(admin, [user])
    delivered(admin, preview(admin, announcement([user], role=role)))
    delivered(admin, preview(admin, announcement([other], role=role)))
    response = call('GET', '/api/messaging/unread-count', user)
    assert response.status_code == 200
    assert response.json() == {'unread_count': 2, 'unread_messages': 1, 'unread_requests': 1}
    assert 'no-store' in response.headers['cache-control']
    item = messages(user)['items'][0]
    assert call('POST', f"/api/messaging/inbox/{item['id']}/read", user, {}).status_code == 200
    assert form_get(user, request).status_code == 200
    assert call('GET', '/api/messaging/unread-count', user).json() == {
        'unread_count': 0, 'unread_messages': 0, 'unread_requests': 0}
    assert call('GET', '/api/messaging/unread-count', other).json()['unread_count'] == 1


@pytest.mark.parametrize('role,status', [(None, 401), ('admin', 403)])
def test_adm04_unread_summary_auth_and_no_store(role, status):
    response = call('GET', '/api/messaging/unread-count', actor(role) if role else None)
    assert response.status_code == status
    assert 'no-store' in response.headers['cache-control']


def test_adm04_unread_summary_rejects_query_identity():
    response = call('GET', '/api/messaging/unread-count?user_id=other', actor())
    assert response.status_code == 422
    assert response.json()['detail']['code'] == 'INVALID_REQUEST'
