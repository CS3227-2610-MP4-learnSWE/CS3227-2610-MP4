"""STU-05-06 student view of ADM-02 feedback and ADM-04 inbox: audience, cross-user and unread tests.

Contracts only: workflow/specs/ADM-02/plan.md and workflow/specs/ADM-04/plan.md. No SoC LLM is
involved (feedback and messages never enter AI context), so no LLM mock is needed.
"""
import pytest

from auth_helpers import call, code_of, login, student_from_login
from adm02_helpers import (PUBLIC, actor, answers, close, error, form_get, inbox,
                          published, response, save, submit)
from adm04_helpers import (INBOX, announcement, check_error, delivered, messages,
                          preview)

COUNT = '/api/messaging/unread-count'


@pytest.fixture
def admin():
    return actor('admin')


@pytest.fixture
def student():
    return actor()


def inbox_items(user):
    reply = call('GET', PUBLIC + '/inbox', user)
    assert reply.status_code == 200, reply.text
    return reply.json()


def counts(user):
    reply = call('GET', COUNT, user)
    assert reply.status_code == 200, reply.text
    return reply.json()


def test_stu05_ac01_each_student_sees_only_requests_addressed_to_them(admin):
    a, b, none = actor(), actor(), actor()
    form_a, form_b = published(admin, [a]), published(admin, [b])
    assert [i['form_id'] for i in inbox_items(a)['items']] == [form_a['id']]
    assert [i['form_id'] for i in inbox_items(b)['items']] == [form_b['id']]
    assert inbox_items(none) == {'items': [], 'next_offset': None, 'unread_count': 0}
    assert inbox(a, form_b) is None and inbox(b, form_a) is None


def test_stu05_ac01_a_student_added_later_or_never_named_is_not_a_recipient(admin):
    named, late = actor(), actor()
    form = published(admin, [named])
    # Publication is frozen (ADM-02: no retroactive targeting): a later account sees nothing.
    assert inbox(late, form) is None
    error(form_get(late, form), 404, 'feedback_not_found')


def test_stu05_ac03_saved_response_belongs_to_its_form_and_respondent(admin):
    a, b = actor(), actor()
    form_a, form_b = published(admin, [a, b]), published(admin, [a])
    receipt_a = submit(a, form_a, answers(form_a))
    receipt_b = submit(b, form_a, answers(form_a))
    assert receipt_a.status_code == receipt_b.status_code == 201
    assert receipt_a.json()['form_id'] == form_a['id']
    stored_a = response(admin, form_a, receipt_a.json())
    stored_b = response(admin, form_a, receipt_b.json())
    assert stored_a['form_id'] == form_a['id'] and stored_a['respondent']['id'] == str(a)
    assert stored_b['form_id'] == form_a['id'] and stored_b['respondent']['id'] == str(b)
    # The other form is untouched, and a response cannot be read through the wrong form.
    assert inbox(a, form_b)['submitted'] is False
    error(call('GET', f"/api/admin/feedback/forms/{form_b['id']}/responses/{receipt_a.json()['id']}", admin),
          404, 'feedback_not_found')


@pytest.mark.parametrize('method,suffix', [('GET', ''), ('PUT', '/draft'), ('POST', '/responses')])
def test_stu05_ac03_second_student_and_teacher_get_the_same_not_found_as_a_missing_form(admin, student, method, suffix):
    form = published(admin, [student])
    assert save(student, form, answers(form)).status_code == 200
    body = None if method == 'GET' else (
        {'version': 0, 'answers': []} if method == 'PUT' else {'draft_version': 0, 'answers': []})
    missing = call(method, f"{PUBLIC}/forms/{'0' * 8}-0000-4000-8000-{'0' * 12}{suffix}", student, body)
    for intruder in (actor(), actor('teacher')):
        reply = call(method, f"{PUBLIC}/forms/{form['id']}{suffix}", intruder, body)
        error(reply, 404, 'feedback_not_found')
        assert reply.json() == missing.json()
    # The owner's draft is unchanged by the failed attempts.
    assert form_get(student, form).json()['draft']['version'] == 1


def test_stu05_ac03_submitted_response_is_unavailable_to_other_students_and_not_echoed_to_the_owner(admin, student):
    other = actor()
    form = published(admin, [student, other])
    receipt = submit(student, form, answers(form))
    assert receipt.status_code == 201
    assert set(receipt.json()) == {'id', 'form_id', 'submitted_at'}
    own = form_get(student, form).json()
    assert own['submitted'] is True and own['questions'] == [] and own['draft'] is None
    other_view = form_get(other, form).json()
    assert other_view['submitted'] is False and other_view['draft']['answers'] == []
    for reader in (student, other):
        error(call('GET', f"/api/admin/feedback/forms/{form['id']}/responses/{receipt.json()['id']}", reader),
              403, 'forbidden')
        error(call('GET', f"/api/admin/feedback/forms/{form['id']}/responses", reader), 403, 'forbidden')


def test_stu05_ac03_closed_form_for_a_student_without_a_recipient_row_is_still_not_found(admin, student):
    outsider = actor()
    form = published(admin, [student])
    assert close(admin, form).status_code == 200
    error(form_get(outsider, form), 404, 'feedback_not_found')
    error(submit(outsider, form, answers(form)), 404, 'feedback_not_found')
    assert form_get(student, form).json()['state'] == 'closed'


def test_stu06_ac05_student_without_any_row_sees_empty_inbox_and_zero_counts(admin):
    lonely, other = actor(), actor()
    published(admin, [other])
    delivered(admin, preview(admin, announcement([other])))
    assert messages(lonely) == {'items': [], 'next_offset': None, 'unread_count': 0}
    assert inbox_items(lonely)['unread_count'] == 0
    assert counts(lonely) == {'unread_count': 0, 'unread_messages': 0, 'unread_requests': 0}
    assert counts(other) == {'unread_count': 2, 'unread_messages': 1, 'unread_requests': 1}


def test_stu06_ac05_other_students_and_teachers_cannot_read_or_mark_a_delivery(admin, student):
    other, teacher = actor(), actor('teacher')
    delivered(admin, preview(admin, announcement([student])))
    mid = messages(student)['items'][0]['id']
    for intruder in (other, teacher, actor()):
        check_error(call('POST', f'{INBOX}/{mid}/read', intruder, {}), 404, 'MESSAGE_UNAVAILABLE')
        assert messages(intruder)['items'] == []
    # A missing delivery is indistinguishable from a foreign one.
    foreign = call('POST', f'{INBOX}/{mid}/read', other, {})
    missing = call('POST', f'{INBOX}/{"0" * 8}-0000-4000-8000-{"0" * 12}/read', other, {})
    assert foreign.json() == missing.json()
    assert messages(student)['items'][0]['read_at'] is None
    assert counts(student)['unread_messages'] == 1


@pytest.mark.parametrize('method,path', [('GET', INBOX), ('GET', COUNT),
                                          ('POST', INBOX + '/0/read'), ('GET', PUBLIC + '/inbox')])
def test_stu06_ac05_student_endpoints_require_a_session_and_reject_admins(admin, method, path):
    reply = call(method, path, None, {} if method == 'POST' else None)
    assert reply.status_code == 401, reply.text
    assert 'no-store' in reply.headers.get('cache-control', '')
    assert call(method, path, admin, {} if method == 'POST' else None).status_code == 403


def test_stu06_ac05_message_html_is_returned_as_inert_text_to_the_recipient_only(admin, student):
    other = actor()
    html = '<img src=x onerror="alert(1)">\n<script>steal()</script>'
    delivered(admin, preview(admin, announcement([student], body=html, subject='<b>Hi</b>')))
    item = messages(student)['items'][0]
    assert item['body'] == html and item['subject'] == '<b>Hi</b>'
    assert messages(other)['items'] == []


def test_stu06_ac08_opening_a_request_marks_it_read_for_that_student_only(admin):
    a, b = actor(), actor()
    form = published(admin, [a, b])
    assert inbox(a, form)['read_at'] is None and inbox(b, form)['read_at'] is None
    assert form_get(a, form).status_code == 200
    assert inbox(a, form)['read_at'] is not None
    assert inbox(b, form)['read_at'] is None
    assert counts(a)['unread_requests'] == 0 and counts(b)['unread_requests'] == 1
    again = inbox(a, form)['read_at']
    assert form_get(a, form).status_code == 200
    assert inbox(a, form)['read_at'] == again


def test_stu06_ac08_reading_a_shared_message_marks_it_read_for_that_student_only(admin):
    a, b = actor(), actor()
    delivered(admin, preview(admin, announcement([a, b])))
    mid = messages(a)['items'][0]['id']
    assert messages(a)['items'][0]['id'] != messages(b)['items'][0]['id']
    assert call('POST', f'{INBOX}/{mid}/read', a, {}).status_code == 200
    assert messages(a)['unread_count'] == 0
    assert messages(b)['unread_count'] == 1
    assert counts(b)['unread_messages'] == 1


def test_stu06_ac09_read_state_and_counts_persist_after_signing_in_again(admin, student):
    form = published(admin, [student])
    delivered(admin, preview(admin, announcement([student])))
    delivered(admin, preview(admin, announcement([student], subject='Second')))
    assert counts(student) == {'unread_count': 3, 'unread_messages': 2, 'unread_requests': 1}
    mid = messages(student)['items'][0]['id']
    assert call('POST', f'{INBOX}/{mid}/read', student, {}).status_code == 200
    assert form_get(student, form).status_code == 200
    fresh = student_from_login(login(student.email, student.password), student.email, student.password)
    summary = counts(fresh)
    assert summary == {'unread_count': 1, 'unread_messages': 1, 'unread_requests': 0}
    # The count equals what the same student can see as unread.
    assert messages(fresh)['unread_count'] == summary['unread_messages']
    assert inbox_items(fresh)['unread_count'] == summary['unread_requests']
    assert sum(1 for m in messages(fresh)['items'] if m['read_at'] is None) == 1


def test_stu06_ac07_a_closed_or_completed_form_rejects_the_student_with_the_dictionary_codes(admin, student):
    closed_form, done_form = published(admin, [student]), published(admin, [student])
    assert close(admin, closed_form).status_code == 200
    assert submit(student, done_form, answers(done_form)).status_code == 201
    reply = submit(student, closed_form, answers(closed_form))
    error(reply, 409, 'feedback_closed')
    assert code_of(save(student, closed_form, answers(closed_form))) == 'feedback_closed'
    error(submit(student, done_form, answers(done_form)), 409, 'feedback_already_submitted')
    rows = {i['form_id']: i['response_status'] for i in inbox_items(student)['items']}
    assert rows == {closed_form['id']: 'closed', done_form['id']: 'completed'}
