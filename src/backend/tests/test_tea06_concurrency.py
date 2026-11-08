"""TEA-06 concurrent requests on one teacher's records (real database through the HTTP contract)."""
from auth_helpers import call, code_of, sql
from adm02_helpers import actor, answers, form_get, inbox, published, race, submit
from adm04_helpers import INBOX, announcement, delivered, messages, preview

COUNT = '/api/messaging/unread-count'


def test_tea06_concurrent_mark_read_one_delivery_leaves_one_read_time():
    admin, teacher = actor('admin'), actor('teacher')
    delivered(admin, preview(admin, announcement([teacher], role='teacher')))
    mid = messages(teacher)['items'][0]['id']
    replies = race(*[lambda: call('POST', f'{INBOX}/{mid}/read', teacher, {}) for _ in range(8)])
    assert [r.status_code for r in replies] == [200] * 8, [(r.status_code, r.text) for r in replies]
    assert len({r.json()['read_at'] for r in replies}) == 1
    assert messages(teacher)['items'][0]['read_at'] == replies[0].json()['read_at']
    assert messages(teacher)['unread_count'] == 0
    assert call('GET', COUNT, teacher).json() == {'unread_count': 0, 'unread_messages': 0, 'unread_requests': 0}
    assert sql('SELECT count(*) FROM admin_message_deliveries WHERE recipient_id=%s', (str(teacher),))[0][0] == 1


def test_tea06_concurrent_submit_one_form_leaves_one_response_and_one_409():
    admin, teacher = actor('admin'), actor('teacher')
    form = published(admin, [teacher])
    replies = race(lambda: submit(teacher, form, answers(form)), lambda: submit(teacher, form, answers(form)))
    assert sorted(r.status_code for r in replies) == [201, 409], [(r.status_code, r.text) for r in replies]
    assert {code_of(r) for r in replies if r.status_code == 409} == {'feedback_already_submitted'}
    assert sql('SELECT count(*) FROM feedback_responses WHERE form_id=%s', (form['id'],))[0][0] == 1
    assert form_get(teacher, form).json()['submitted'] is True
    assert inbox(teacher, form)['response_status'] == 'completed'


def test_tea06_other_teachers_stay_unread_while_one_teacher_races_reads():
    admin, a, b = actor('admin'), actor('teacher'), actor('teacher')
    delivered(admin, preview(admin, announcement([a, b], role='teacher')))
    mid = messages(a)['items'][0]['id']
    replies = race(*[lambda: call('POST', f'{INBOX}/{mid}/read', a, {}) for _ in range(4)],
                   *[lambda: call('POST', f'{INBOX}/{mid}/read', b, {}) for _ in range(4)])
    assert [r.status_code for r in replies[:4]] == [200] * 4
    assert [r.status_code for r in replies[4:]] == [404] * 4
    assert messages(a)['unread_count'] == 0 and messages(b)['unread_count'] == 1


def test_tea06_count_racing_mark_read_is_old_or_new_never_negative_and_settles():
    admin, teacher = actor('admin'), actor('teacher')
    delivered(admin, preview(admin, announcement([teacher], role='teacher')))
    mid = messages(teacher)['items'][0]['id']
    replies = race(lambda: call('GET', COUNT, teacher), lambda: call('POST', f'{INBOX}/{mid}/read', teacher, {}),
                   lambda: call('GET', COUNT, teacher), lambda: call('POST', f'{INBOX}/{mid}/read', teacher, {}),
                   lambda: call('GET', COUNT, teacher))
    assert [r.status_code for r in replies] == [200] * 5
    for index in (0, 2, 4):
        body = replies[index].json()
        assert body['unread_messages'] in (0, 1) and body['unread_requests'] == 0
        assert body['unread_count'] == body['unread_messages'] + body['unread_requests']
    assert call('GET', COUNT, teacher).json() == {'unread_count': 0, 'unread_messages': 0, 'unread_requests': 0}
