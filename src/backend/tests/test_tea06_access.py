"""TEA-06 teacher view of ADM-02 feedback and ADM-04 inbox: audience, cross-user and role tests.

Contracts only: workflow/specs/TEA-06/plan.md (which reuses ADM-02 and ADM-04). No SoC LLM is
involved (feedback and messages never enter AI context), so no LLM mock is needed.
"""
import pytest

from auth_helpers import call, code_of, login, student_from_login
from adm02_helpers import (PUBLIC, actor, answers, close, created, error, form_get, inbox,
                          payload, published, question, save, submit)
from adm04_helpers import INBOX, announcement, check_error, delivered, messages, preview

COUNT = '/api/messaging/unread-count'
MISSING = f"{'0' * 8}-0000-4000-8000-{'0' * 12}"


@pytest.fixture
def admin():
    return actor('admin')


@pytest.fixture
def teacher():
    return actor('teacher')


def inbox_items(user):
    reply = call('GET', PUBLIC + '/inbox', user)
    assert reply.status_code == 200, reply.text
    return reply.json()


def counts(user):
    reply = call('GET', COUNT, user)
    assert reply.status_code == 200, reply.text
    return reply.json()


def one_message(admin, user, **changes):
    delivered(admin, preview(admin, announcement([user], role=user.role, **changes)))
    return messages(user)['items'][0]['id']


def test_tea06_teacher_inbox_lists_only_forms_addressed_to_them_by_name(admin):
    a, b, student, none = actor('teacher'), actor('teacher'), actor(), actor('teacher')
    form_a, form_b, form_s = published(admin, [a]), published(admin, [b]), published(admin, [student])
    unpublished = created(admin)
    assert [i['form_id'] for i in inbox_items(a)['items']] == [form_a['id']]
    assert [i['form_id'] for i in inbox_items(b)['items']] == [form_b['id']]
    assert [i['form_id'] for i in inbox_items(student)['items']] == [form_s['id']]
    assert inbox_items(none) == {'items': [], 'next_offset': None, 'unread_count': 0}
    for user in (a, b, student, none):
        assert inbox(user, unpublished) is None
    assert inbox(a, form_b) is None and inbox(b, form_a) is None and inbox(a, form_s) is None
    assert inbox_items(a)['unread_count'] == 1


def test_tea06_teacher_added_later_is_not_a_recipient(admin):
    named, late = actor('teacher'), actor('teacher')
    form = published(admin, [named])
    assert inbox(late, form) is None
    error(form_get(late, form), 404, 'feedback_not_found')


def test_tea06_teacher_submit_requires_required_answers_then_201_and_inbox_completed(admin, teacher):
    form = published(admin, [teacher], payload([question('short_answer'), question('paragraph', False)]))
    required = form['questions'][0]['id']
    for bad in ([], [{'question_id': required, 'value': None}]):
        error(submit(teacher, form, bad), 422, 'invalid_feedback_answers')
    assert inbox(teacher, form)['response_status'] == 'not_started'
    receipt = submit(teacher, form, answers(form, optional_null=True))
    assert receipt.status_code == 201, receipt.text
    assert set(receipt.json()) == {'id', 'form_id', 'submitted_at'}
    assert receipt.json()['form_id'] == form['id']
    assert inbox(teacher, form)['response_status'] == 'completed'
    assert inbox(teacher, form)['submitted'] is True


@pytest.mark.parametrize('method,suffix', [('GET', ''), ('PUT', '/draft'), ('POST', '/responses')])
def test_tea06_second_teacher_and_student_get_404_on_teachers_form_draft_response_and_submit(admin, teacher, method, suffix):
    form = published(admin, [teacher])
    assert save(teacher, form, answers(form)).status_code == 200
    body = None if method == 'GET' else (
        {'version': 0, 'answers': []} if method == 'PUT' else {'draft_version': 0, 'answers': []})
    missing = call(method, f"{PUBLIC}/forms/{MISSING}{suffix}", teacher, body)
    for intruder in (actor('teacher'), actor()):
        reply = call(method, f"{PUBLIC}/forms/{form['id']}{suffix}", intruder, body)
        error(reply, 404, 'feedback_not_found')
        assert reply.json() == missing.json()
        assert inbox_items(intruder)['items'] == []
    # The owner's draft is untouched by the failed attempts and can still be submitted.
    assert form_get(teacher, form).json()['draft']['version'] == 1
    assert submit(teacher, form, answers(form), 1).status_code == 201


def test_tea06_teacher_response_absent_from_other_teacher_payloads(admin, teacher):
    other, student = actor('teacher'), actor()
    secret = 'TEA06 PRIVATE ANSWER <script>1</script>'
    form = published(admin, [teacher, other])
    mine = answers(form)
    mine[0]['value'] = secret
    assert save(teacher, form, mine).status_code == 200
    receipt = submit(teacher, form, mine, 1)
    assert receipt.status_code == 201, receipt.text
    own = form_get(teacher, form)
    assert own.json()['submitted'] is True and secret not in own.text
    other_view = form_get(other, form)
    assert other_view.json()['submitted'] is False and secret not in other_view.text
    assert other_view.json()['draft']['answers'] == []
    for reader in (other, student):
        assert secret not in call('GET', PUBLIC + '/inbox', reader).text
        assert secret not in call('GET', INBOX + '?limit=20&offset=0', reader).text
    for reader in (teacher, other, student):
        path = f"/api/admin/feedback/forms/{form['id']}/responses/{receipt.json()['id']}"
        error(call('GET', path, reader), 403, 'forbidden')
        error(call('GET', f"/api/admin/feedback/forms/{form['id']}/responses", reader), 403, 'forbidden')


def test_tea06_non_recipient_teacher_form_open_is_404_and_does_not_mark_read(admin, teacher):
    other = actor('teacher')
    form = published(admin, [teacher])
    assert inbox(teacher, form)['read_at'] is None
    error(form_get(other, form), 404, 'feedback_not_found')
    assert inbox(teacher, form)['read_at'] is None
    assert counts(teacher)['unread_requests'] == 1 and counts(other)['unread_requests'] == 0
    assert form_get(teacher, form).status_code == 200
    assert inbox(teacher, form)['read_at'] is not None
    assert counts(teacher)['unread_requests'] == 0


def test_tea06_form_published_to_students_is_404_for_a_teacher_and_the_reverse(admin, teacher):
    student = actor()
    for_students, for_teachers = published(admin, [student]), published(admin, [teacher])
    error(form_get(teacher, for_students), 404, 'feedback_not_found')
    error(submit(teacher, for_students, answers(for_students)), 404, 'feedback_not_found')
    error(form_get(student, for_teachers), 404, 'feedback_not_found')
    assert inbox(teacher, for_students) is None and inbox(student, for_teachers) is None
    assert inbox(student, for_students)['read_at'] is None


def test_tea06_malformed_ids_get_not_found(admin, teacher):
    error(call('GET', PUBLIC + '/forms/not-a-uuid', teacher), 404, 'feedback_not_found')
    delivered(admin, preview(admin, announcement([teacher], role='teacher')))
    # Spec open question 5 allows "not found or the existing strict-input error" for a malformed delivery id.
    malformed = call('POST', f'{INBOX}/not-a-uuid/read', teacher, {})
    assert (malformed.status_code, code_of(malformed)) in {(404, 'MESSAGE_UNAVAILABLE'), (422, 'INVALID_REQUEST')}
    assert messages(teacher)['items'][0]['read_at'] is None
    check_error(call('POST', f'{INBOX}/{MISSING}/read', teacher, {}), 404, 'MESSAGE_UNAVAILABLE')


def test_tea06_other_teacher_and_student_cannot_list_or_read_a_teachers_delivery(admin, teacher):
    other, student = actor('teacher'), actor()
    mid = one_message(admin, teacher)
    for intruder in (other, student):
        check_error(call('POST', f'{INBOX}/{mid}/read', intruder, {}), 404, 'MESSAGE_UNAVAILABLE')
        assert messages(intruder) == {'items': [], 'next_offset': None, 'unread_count': 0}
        assert counts(intruder) == {'unread_count': 0, 'unread_messages': 0, 'unread_requests': 0}
    foreign = call('POST', f'{INBOX}/{mid}/read', other, {})
    missing = call('POST', f'{INBOX}/{MISSING}/read', other, {})
    assert foreign.json() == missing.json()
    assert messages(teacher)['items'][0]['read_at'] is None
    assert counts(teacher)['unread_messages'] == 1


def test_tea06_teacher_message_with_html_is_returned_as_inert_text_to_the_recipient_only(admin, teacher):
    html = '<img src=x onerror="alert(1)">\n<script>steal()</script>'
    delivered(admin, preview(admin, announcement([teacher], role='teacher', body=html, subject='<b>Hi</b>')))
    item = messages(teacher)['items'][0]
    assert item['body'] == html and item['subject'] == '<b>Hi</b>'
    assert messages(actor('teacher'))['items'] == []


def test_tea06_student_and_admin_roles_on_teacher_data_return_404_or_403(admin, teacher):
    student = actor()
    form = published(admin, [teacher])
    assert save(teacher, form, answers(form)).status_code == 200
    mid = one_message(admin, teacher)
    requests = [('GET', f"{PUBLIC}/forms/{form['id']}", None),
                ('PUT', f"{PUBLIC}/forms/{form['id']}/draft", {'version': 0, 'answers': []}),
                ('POST', f"{PUBLIC}/forms/{form['id']}/responses", {'draft_version': 0, 'answers': []})]
    for method, path, body in requests:
        error(call(method, path, student, body), 404, 'feedback_not_found')
        error(call(method, path, admin, body), 403, 'forbidden')
    check_error(call('POST', f'{INBOX}/{mid}/read', student, {}), 404, 'MESSAGE_UNAVAILABLE')
    assert call('POST', f'{INBOX}/{mid}/read', admin, {}).status_code == 403
    assert form_get(teacher, form).json()['draft']['version'] == 1
    assert messages(teacher)['items'][0]['read_at'] is None


@pytest.mark.parametrize('method,path', [('GET', PUBLIC + '/inbox'), ('GET', INBOX), ('GET', COUNT),
                                          ('GET', PUBLIC + f'/forms/{MISSING}'),
                                          ('PUT', PUBLIC + f'/forms/{MISSING}/draft'),
                                          ('POST', PUBLIC + f'/forms/{MISSING}/responses'),
                                          ('POST', f'{INBOX}/{MISSING}/read')])
def test_tea06_admin_and_anonymous_refused_on_recipient_endpoints(admin, method, path):
    body = {} if method == 'POST' and path.endswith('/read') else (
        {'version': 0, 'answers': []} if method == 'PUT' else (
            {'draft_version': 0, 'answers': []} if method == 'POST' else None))
    reply = call(method, path, None, body)
    assert reply.status_code == 401, reply.text
    assert 'no-store' in reply.headers.get('cache-control', '')
    refused = call(method, path, admin, body)
    assert refused.status_code == 403, refused.text
    assert code_of(refused) == 'forbidden'


def test_tea06_teacher_closed_form_rejects_draft_and_submit_409_feedback_closed(admin, teacher):
    form = published(admin, [teacher])
    assert close(admin, form).status_code == 200
    error(save(teacher, form, answers(form)), 409, 'feedback_closed')
    error(submit(teacher, form, answers(form)), 409, 'feedback_closed')
    view = form_get(teacher, form).json()
    assert view['state'] == 'closed' and view['questions'] == [] and view['draft'] is None
    assert inbox(teacher, form)['response_status'] == 'closed'


def test_tea06_teacher_completed_form_resubmit_409_already_submitted(admin, teacher):
    form = published(admin, [teacher])
    assert submit(teacher, form, answers(form)).status_code == 201
    error(submit(teacher, form, answers(form)), 409, 'feedback_already_submitted')
    error(save(teacher, form, answers(form)), 409, 'feedback_already_submitted')
    assert inbox(teacher, form)['response_status'] == 'completed'


def test_tea06_read_state_and_counts_persist_across_new_login(admin, teacher):
    form = published(admin, [teacher])
    delivered(admin, preview(admin, announcement([teacher], role='teacher')))
    delivered(admin, preview(admin, announcement([teacher], role='teacher', subject='Second')))
    assert counts(teacher) == {'unread_count': 3, 'unread_messages': 2, 'unread_requests': 1}
    mid = messages(teacher)['items'][0]['id']
    assert call('POST', f'{INBOX}/{mid}/read', teacher, {}).status_code == 200
    assert form_get(teacher, form).status_code == 200
    fresh = student_from_login(login(teacher.email, teacher.password), teacher.email, teacher.password)
    summary = counts(fresh)
    assert summary == {'unread_count': 1, 'unread_messages': 1, 'unread_requests': 0}
    assert messages(fresh)['unread_count'] == summary['unread_messages']
    assert inbox_items(fresh)['unread_count'] == summary['unread_requests']
    assert inbox(fresh, form)['read_at'] is not None
