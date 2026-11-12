"""ADM-04 independent HTTP fixtures; public contracts and approved tables only."""
from datetime import datetime
from uuid import UUID
from auth_helpers import call, code_of, sql
from adm02_helpers import actor, answers, payload, published, submit, uid

ADMIN = '/api/admin/messaging'
INBOX = '/api/messaging/inbox'
PREVIEWS = ADMIN + '/previews'


def announcement(users=None, role='student', **changes):
    result = dict(kind='announcement', audience_role=role, audience_mode='selected',
                  recipient_ids=[str(user) for user in users or []],
                  subject='Learning improvements', body='Thank you.\nWe reviewed your feedback.')
    result.update(changes)
    return result


def preview(admin, body):
    reply = call('POST', PREVIEWS, admin, body)
    assert reply.status_code == 201, reply.text
    value = reply.json()
    assert set(value) == {'id', 'kind', 'response_id', 'audience_role', 'audience_mode',
                          'subject', 'body', 'recipients', 'recipient_count', 'created_at', 'expires_at'}
    UUID(value['id'])
    assert value['recipient_count'] == len(value['recipients'])
    assert [item['id'] for item in value['recipients']] == sorted(item['id'] for item in value['recipients'])
    for item in value['recipients']:
        assert set(item) == {'id', 'display_name', 'role'}
    assert 'no-store' in reply.headers.get('cache-control', '')
    return value


def send(admin, value):
    return call('POST', f"{PREVIEWS}/{value['id']}/send", admin, {})


def delivered(admin, value):
    reply = send(admin, value)
    assert reply.status_code == 200, reply.text
    result = reply.json()
    assert set(result) == {'message_id', 'preview_id', 'kind', 'recipient_count', 'sent_at'}
    assert result['preview_id'] == value['id']
    assert result['recipient_count'] == value['recipient_count']
    assert result['kind'] == value['kind']
    UUID(result['message_id'])
    return result


def messages(user, query='?limit=20&offset=0'):
    reply = call('GET', INBOX + query, user)
    assert reply.status_code == 200, reply.text
    value = reply.json()
    assert set(value) == {'items', 'next_offset', 'unread_count'}
    assert 'no-store' in reply.headers.get('cache-control', '')
    for item in value['items']:
        # form_title: added by ADM-08 follow-up (user request 2026-11-12); null unless a reply answers a form response.
        assert set(item) == {'id', 'kind', 'subject', 'body', 'sent_at', 'read_at', 'form_title'}
        UUID(item['id'])
    return value


def check_error(reply, status, code):
    assert reply.status_code == status, reply.text
    assert code_of(reply) == code, reply.text
    assert set(reply.json()) == {'detail'}
    assert 'message' in reply.json()['detail']
    assert 'no-store' in reply.headers.get('cache-control', '')


def feedback(admin, user):
    form = published(admin, [user], payload())
    reply = submit(user, form, answers(form))
    assert reply.status_code == 201, reply.text
    return form, reply.json()['id']


def counts():
    return tuple(sql('SELECT count(*) FROM ' + table)[0][0] for table in
                 ('admin_message_previews', 'admin_messages', 'admin_message_deliveries'))


def dt(value):
    return datetime.fromisoformat(value.replace('Z', '+00:00'))
