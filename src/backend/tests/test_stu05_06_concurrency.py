"""STU-05-06 concurrent requests on one student's records (real database through the HTTP contract)."""
from auth_helpers import call, code_of, sql
from adm02_helpers import PUBLIC, actor, answers, form_get, inbox, published, race, submit
from adm04_helpers import INBOX, announcement, delivered, messages, preview

COUNT = '/api/messaging/unread-count'


def one_message(admin, user):
    delivered(admin, preview(admin, announcement([user])))
    return messages(user)['items'][0]['id']


def test_stu06_concurrent_mark_read_of_one_delivery_keeps_one_read_time():
    admin, user = actor('admin'), actor()
    mid = one_message(admin, user)
    replies = race(*[lambda: call('POST', f'{INBOX}/{mid}/read', user, {}) for _ in range(8)])
    assert [r.status_code for r in replies] == [200] * 8, [(r.status_code, r.text) for r in replies]
    assert len({r.json()['read_at'] for r in replies}) == 1
    assert messages(user)['items'][0]['read_at'] == replies[0].json()['read_at']
    assert messages(user)['unread_count'] == 0
    assert sql('SELECT count(*) FROM admin_message_deliveries WHERE recipient_id=%s', (str(user),))[0][0] == 1


def test_stu06_badge_count_racing_mark_read_is_old_or_new_never_negative_and_settles():
    admin, user = actor('admin'), actor()
    mid = one_message(admin, user)
    replies = race(lambda: call('GET', COUNT, user), lambda: call('POST', f'{INBOX}/{mid}/read', user, {}),
                   lambda: call('GET', COUNT, user), lambda: call('POST', f'{INBOX}/{mid}/read', user, {}),
                   lambda: call('GET', COUNT, user))
    assert [r.status_code for r in replies] == [200] * 5
    for index in (0, 2, 4):
        body = replies[index].json()
        assert body['unread_messages'] in (0, 1) and body['unread_requests'] == 0
        assert body['unread_count'] == body['unread_messages'] + body['unread_requests']
    assert call('GET', COUNT, user).json() == {'unread_count': 0, 'unread_messages': 0, 'unread_requests': 0}


def test_stu06_concurrent_form_opens_mark_the_request_read_once_and_keep_the_first_read_time():
    admin, user = actor('admin'), actor()
    form = published(admin, [user])
    replies = race(*[lambda: form_get(user, form) for _ in range(6)])
    assert [r.status_code for r in replies] == [200] * 6
    first = inbox(user, form)['read_at']
    assert first is not None
    assert form_get(user, form).status_code == 200
    assert inbox(user, form)['read_at'] == first
    assert call('GET', COUNT, user).json()['unread_requests'] == 0


def test_stu05_concurrent_submissions_by_different_students_keep_separate_responses():
    admin, a, b = actor('admin'), actor(), actor()
    form = published(admin, [a, b])
    replies = race(lambda: submit(a, form, answers(form)), lambda: submit(b, form, answers(form)))
    assert [r.status_code for r in replies] == [201, 201]
    assert replies[0].json()['id'] != replies[1].json()['id']
    assert sql('SELECT count(*) FROM feedback_responses WHERE form_id=%s', (form['id'],))[0][0] == 2
    assert inbox(a, form)['submitted'] is True and inbox(b, form)['submitted'] is True


def test_stu05_four_simultaneous_submissions_by_one_student_leave_one_response_and_three_c05():
    admin, user = actor('admin'), actor()
    form = published(admin, [user])
    replies = race(*[lambda: submit(user, form, answers(form)) for _ in range(4)])
    assert sorted(r.status_code for r in replies) == [201, 409, 409, 409]
    assert {code_of(r) for r in replies if r.status_code == 409} == {'feedback_already_submitted'}
    assert sql('SELECT count(*) FROM feedback_responses WHERE form_id=%s', (form['id'],))[0][0] == 1
    assert form_get(user, form).json()['submitted'] is True
    assert call('GET', PUBLIC + '/inbox', user).json()['items'][0]['response_status'] == 'completed'


def test_stu06_other_students_stay_unread_while_one_student_races_reads():
    admin, a, b = actor('admin'), actor(), actor()
    delivered(admin, preview(admin, announcement([a, b])))
    mid = messages(a)['items'][0]['id']
    replies = race(*[lambda: call('POST', f'{INBOX}/{mid}/read', a, {}) for _ in range(4)],
                   *[lambda: call('POST', f'{INBOX}/{mid}/read', b, {}) for _ in range(4)])
    assert [r.status_code for r in replies[:4]] == [200] * 4
    assert [r.status_code for r in replies[4:]] == [404] * 4
    assert messages(a)['unread_count'] == 0 and messages(b)['unread_count'] == 1
