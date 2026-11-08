# Plan: TEA-06 Teacher feedback and inbox (verification slice)

Status: Approved by the user on 2026-11-09 (Open question 1 answered: option A, redirect signed-in teachers only). Spec: `workflow/specs/TEA-06/spec.md`. Model: `workflow/specs/STU-05-06/plan.md`.

## Data model
No change. No new table, column or migration. Reused: `feedback_forms`, `feedback_recipients` (`user_id`, `role_snapshot`, `read_at`), `feedback_response_drafts`, `feedback_responses` (ADM-02) and `message_deliveries` (`recipient_id`, `read_at`) with `admin_messages` (ADM-04).

## API endpoints
No new endpoint. Existing contract, roles accepted: `student` and `teacher` (verified in `src/backend/feedback.py` and `messaging.py`). Wrong role (admin) gets 403 `forbidden`; no session gets 401 (shared auth); mutations need the session CSRF and origin checks of the shared auth. Responses are `no-store`.

| Method and path | Request | Success | Errors (status `code`) |
|---|---|---|---|
| GET `/api/feedback/inbox?limit=&offset=` (limit 1-100 default 20; offset 0-100000; no other query) | none | 200 `{items:[{id, form_id, title, created_at, read_at, state, submitted, response_status}], next_offset, unread_count}`; `response_status` is `completed`, `closed`, `draft` or `not_started`; only the caller's rows with `role_snapshot == caller role` and form state not `draft` | 422 `invalid_feedback_input`; 429 `feedback_rate_limited` (read 120/min); 503 `feedback_unavailable`; 500 `feedback_error` |
| GET `/api/feedback/forms/{form_id}` | none | 200 `{id, title, description, association, state, submitted, questions, draft}`; sets the caller's `read_at` if null; `questions` is `[]` and `draft` is null unless the form is open and not submitted | 404 `feedback_not_found` (unknown, malformed id, not a recipient, draft form, role mismatch); 422 `invalid_feedback_input` (any query); 429; 503; 500 |
| PUT `/api/feedback/forms/{form_id}/draft` | `{version:int>=0, answers:[...]}` (exact keys) | 200 draft `{version, answers, updated_at}` | 404 `feedback_not_found`; 409 `feedback_closed`; 409 `feedback_already_submitted`; 409 `feedback_draft_version_conflict`; 422 `invalid_feedback_draft_answers`; 413 `feedback_too_large` (over 262144 bytes); 429 (draft 120/min); 503; 500 |
| POST `/api/feedback/forms/{form_id}/responses` | `{draft_version:int>=0, answers:[...]}` (exact keys) | 201 `{id, form_id, submitted_at}`; deletes the draft | 404 `feedback_not_found`; 409 `feedback_closed`; 409 `feedback_already_submitted`; 409 `feedback_draft_version_conflict`; 422 `invalid_feedback_answers` (message `Answer every required question and check that all answers match their question type.`); 413; 429 (submit 10/min); 503; 500 |
| GET `/api/messaging/inbox?limit=20&offset=` (limit only `20`) | none | 200 `{items:[{id, kind, subject, body, sent_at, read_at}], next_offset, unread_count}`; `kind` is `announcement` or `feedback_response`; newest first; only the caller's deliveries | 422 `INVALID_REQUEST`; 429 `MESSAGING_RATE_LIMITED` (60/min shared with mark-read); 503 `MESSAGING_UNAVAILABLE`; 500 `MESSAGING_ERROR` |
| GET `/api/messaging/unread-count` (no query) | none | 200 `{unread_count, unread_messages, unread_requests}` with `unread_count` = sum, counting requests with `role_snapshot == caller role`; a request becomes read only when its form is opened (GET form), not by submitting | 422 `INVALID_REQUEST`; 429; 503; 500 |
| POST `/api/messaging/inbox/{delivery_id}/read` | `{}` (no fields) | 200 `{id, read_at}`; idempotent; first read time is never overwritten | 404 `MESSAGE_UNAVAILABLE` (another user's or unknown well-formed id); 422 `INVALID_REQUEST` (malformed id; corrected 2026-11-09 from test-designer report); 429; 503; 500 |

Error bodies and messages are the dictionaries in `src/backend/feedback_errors.py` and `messaging_errors.py` (quoted in the spec's UI table). Every role check is server-side (`current_user(role=("student","teacher"))`).

## Components and modules
Reused unchanged: `pages/FeedbackInbox.tsx`, `pages/RecipientFeedback.tsx`, `components/MessagesInbox.tsx`, `components/Shell.tsx`, `hooks/useInboxUnread.ts`, `hooks/useFeedbackRead.ts`, `services/feedbackApi.ts`, `auth/RequireRole.tsx`, `pages/Inbox.tsx` (including the exported sample `FeedbackForm`), backend `feedback.py`, `feedback_store.py`, `messaging.py`, `messaging_store.py`.

One change, `src/frontend/src/App.tsx`, `/teacher` route block only: replace the element of `<Route path="feedback" element={<FeedbackForm notify={notify} />} />` with a signed-in redirect. Contract:
- Add a small component in `App.tsx` beside `Inbox` and `LiveFeedback`: `function TeacherFeedbackIndex({ notify }: { notify: (message?: string) => void })`. If `useAuth().status === "authenticated"` it returns `<Navigate to="/teacher/inbox" replace />`; otherwise it returns `<FeedbackForm notify={notify} />` (default per spec Open question 1, option A; if the user chooses option B it always returns the Navigate and `FeedbackForm` stays imported for the student route).
- `/teacher/feedback/:formId` (`LiveFeedback`) and the student block are untouched. No other file under `src/` changes.

Docs (developer, same change): `docs/UserGuide.md`: add a section `### Teacher inbox: what you see and what is not available` mirroring the student inbox section at about line 280 (Feedback requests; Messages with `From: Administrator`; the form page and privacy sentence; badge; named recipients only, teacher groups not available; email and push not available; `/teacher/feedback` opens the inbox), and correct the teacher paragraph near line 35 (it must state that the signed-in Inbox shows real requests and messages with sender label, and not mention or imply a sample feedback form for signed-in teachers). `docs/DeveloperGuide.md`: add `### TEA-06: teacher inbox verification notes` next to `### STU-05-06: student inbox verification notes` (line 605): shared components, route redirect, evidence files, the Open question 2 note for the ADM-02 owner. Claim only what works.

## UI contract
Same components as the student inbox, so the same accessible names:
- Sidebar (`navigation` label `teacher navigation`): link named `Inbox`; badge `status` named `{n} unread inbox items`, text `99+` above 99, absent at 0.
- Page: level-1 heading `Inbox`; level-2 headings `Feedback requests` and `Messages`; statuses `Unread requests: {count}` and `{count} unread messages`; request links named by form title; chips `Unread`/`Read` and `Not started`/`Draft`/`Completed`/`Closed`; buttons `Retry`, `Retry messages`, `Previous page`, `Next page`, `Load more messages`, `Mark as read`; message card `article` named by subject; text `From: Administrator`; sent time in a `time` element with `dateTime` = `sent_at`; empty texts `No feedback requests yet.` and `No messages yet.`; loading texts `Loading feedback requests...` and `Loading messages…`.
- Form: level-1 heading is the form title; fields named `{n}. {prompt}`; button `Submit feedback`; completed `Completed` with `Feedback submitted. Thank you.`; `You have already submitted feedback.`; closed `This form is closed.`; link `Back to inbox` to `/teacher/inbox`.
- Control types: `Inbox` is a link; request titles are links; `Mark as read`, `Retry`, `Submit feedback` are buttons (not tabs).

- Requests per load and per retry: as in the spec: inbox page one GET `/api/feedback/inbox` plus one GET `/api/messaging/inbox`, shell one GET `/api/messaging/unread-count` on mount; `Retry` or `Retry messages` repeats only its own section's read once; form open one form GET then one forced count GET; mark-read one POST and no list re-read; the `/teacher/feedback` redirect adds no request of its own. Tests count with StrictMode-style double effects.
- Wrong role: student or admin on any `/teacher/...` inbox or feedback URL: `RequireRole` replaces to `/student/overview` or `/admin/overview`; no page request; API 403 `forbidden`.
- Link history: push or replace: push for `Inbox` link, form title links and `Back to inbox`; replace for `/teacher/feedback` redirect (signed in), wrong-role and session-expiry redirects; none for retry, mark-read, load more or badge refresh.
- Refresh: server state; same counts and read markers after reload.
- Back and Forward: fresh reads on return; no cached answers.
- Expired session or logout: timers stop, badge gone, sign-in screen; 401 copy `Your session has expired. Sign in again.`; reads persist after sign-in.
- Backend down: per-section network message and retry; badge keeps last value.
- Longest wait before an error: 15 seconds (feedback and messaging); timeout copy per the spec's UI table.
- No generic failure message: dictionary copy only; the two network wordings differ by section and are asserted as is; the badge shows no error text.

## AI usage
Not applicable: no SoC LLM call is added or changed; inbox and feedback content never enter AI context.

## Test plan
Backend `src/backend/tests/test_tea06_access.py` and `test_tea06_concurrency.py` (helpers: reuse `adm02_helpers.py` and `adm04_helpers.py`); frontend `src/frontend/tests/tea06-inbox.spec.ts` (test titles start `TEA-06 ACnn`; reuse the route-mock style of `stu05-06-inbox.spec.ts` and the API helpers `adm02Api.ts`, `adm04Api.ts`, `stu0506Api.ts`). SoC LLM not involved. Existing evidence is the first pass; the test-designer confirms it against the test folders (no `src/` access) and reports any mismatch.

| AC | Existing evidence | New test (gap) |
|---|---|---|
| AC01 | `test_adm02_feedback.py::test_adm02_ac09_12_explicit_audience_atomic_delivery_read_and_no_retroactive_target` (role-parametrised delivery) | `test_tea06_teacher_inbox_lists_only_forms_addressed_to_them_by_name` (second teacher and a student with other forms see none; draft forms absent) |
| AC02 | `test_adm02_ac04_22_24_incomplete_required_draft_restores_but_submission_requires_answer` (student actor), `adm02-feedback.spec.ts` AC04_24 and AC24 (student) | API `test_tea06_teacher_submit_requires_required_answers_then_201_and_inbox_completed`; browser `TEA-06 AC02 teacher submit with a required answer missing shows the 422 copy, then submits and sees Feedback submitted. Thank you.` |
| AC03 | `test_adm02_ac22_23_25_draft_exact_whitespace_owner_only_and_new_login_restores`; `test_adm02_ac18_20_...private_review` (outsider list at line 197 includes a teacher) | `test_tea06_second_teacher_and_student_get_404_on_teachers_form_draft_response_and_submit`; `test_tea06_teacher_response_absent_from_other_teacher_payloads`; `test_tea06_admin_and_anonymous_refused_on_recipient_endpoints` (403 `forbidden` / 401) |
| AC04 | `test_adm04_ac01_05_response_recipient_is_derived_and_only_intended_inbox_receives`, `adm04-inbox.spec.ts` teacher messages (line 125) | browser `TEA-06 AC04 teacher sees From: Administrator and the sent time on each message and survey requests under Feedback requests` |
| AC05 | `test_adm04_ac09_11_recipient_read_ownership_and_no_admin_delivery_bypass`, `test_adm04_ac06_10_selected_audience_frozen_deduplicated_and_private` | `test_tea06_other_teacher_and_student_cannot_list_or_read_a_teachers_delivery` (404 `MESSAGE_UNAVAILABLE`, absent from their list); browser `TEA-06 AC05 message body with HTML renders as literal text` |
| AC06 | none for teachers (`adm02-feedback.spec.ts` AC09-10 inbox link test is student-only; corrected after verification) | browser `TEA-06 AC06 request title opens /teacher/feedback/{id} by a push and Back returns to a fresh inbox`; API `test_tea06_non_recipient_teacher_form_open_is_404_and_does_not_mark_read` |
| AC07 | `test_adm02_ac14_17_closure_keeps_submitted_and_hides_drafts_no_reopen` (actor kind not teacher-specific) | `test_tea06_teacher_closed_form_rejects_draft_and_submit_409_feedback_closed`; `test_tea06_teacher_completed_form_resubmit_409_already_submitted`; browser `TEA-06 AC07 closed request shows Closed, This form is closed. and no editable controls` |
| AC08 | `test_adm04_ac03_08_12_read_is_persistent_idempotent_and_send_replay_never_unreads`, `adm04-inbox.spec.ts:123` teacher | browser `TEA-06 AC08 new message is Unread and Mark as read makes it Read for the teacher only` |
| AC09 | `test_adm04_unread_summary_owned_components_and_read_updates` (both roles); `test_adm02_ac22_23_25...new_login_restores` (draft) | `test_tea06_read_state_and_counts_persist_across_new_login` (request read via form GET, message read via POST; fresh session shows same state); browser `TEA-06 AC09 after logout and sign-in the Read markers and badge come from the server` |
| AC10 | none | browser `TEA-06 AC10 teacher inbox exposes no email or push control` (UI scan) |
| AC11 | `test_adm04_unread_summary_*`, `adm04-redesign.spec.ts` | browser `TEA-06 AC11 badge equals requests plus messages, absent at 0, 99+ over 99, both section counts kept` |
| AC12 | `adm04-inbox.spec.ts` refresh tests (student-based) | browser `TEA-06 AC12 badge drops after opening a form and after Mark as read, with exact request counts` |
| AC13 | `adm04-inbox.spec.ts` (AC13 survey failure independent, line 60); `stu05-06-inbox.spec.ts` AC13 (student) | browser `TEA-06 AC13` three tests: survey list fails (Messages stays), message list fails (survey stays, messaging network copy), count endpoint fails (no badge text) |
| AC14 | none | browser `TEA-06 AC14 signed-in /teacher/feedback lands on /teacher/inbox with replace (Back does not return) and shows no sample form`; `TEA-06 AC14 /teacher/feedback/{id} still opens the real form`; `TEA-06 AC14 anonymous /teacher/feedback keeps the sample form` (if option A) |
| AC15 | `adm02-feedback.spec.ts` wrong-role redirect list (line 443, teacher actor); `test_adm02_all_routes_auth_roles_csrf_and_no_store` (line 284, 403 for teacher on admin routes) | browser `TEA-06 AC15 student and admin opening /teacher/inbox, /teacher/feedback and /teacher/feedback/{id} are redirected with no page requests`; API `test_tea06_student_and_admin_roles_on_teacher_data_return_404_or_403` (student is a valid recipient role, so a student gets 404 for a teacher's form; admin gets 403) |
| Concurrency | `test_adm04_ac12_concurrent_read_and_send_replays_never_erase_first_read`; `test_adm02_ac24_duplicate_submission_exactly_one_response` (student) | `test_tea06_concurrent_mark_read_one_delivery_leaves_one_read_time` and `test_tea06_concurrent_submit_one_form_leaves_one_response_and_one_409` in `test_tea06_concurrency.py`; browser `TEA-06 badge never negative when a read races a refresh` |

Security tests (also logged in `workflow/security/`): cross-user direct access to form, draft, response and delivery (second teacher, student without a recipient row, admin, anonymous); HTML in message body rendered as text; malformed UUID gets not-found. Records tests: concurrent mark-read and concurrent submit as above.
Known unreachable shared-code mismatch (spec Open question 2): no test.
Regression: the whole existing student, ADM-02 and ADM-04 suites pass unchanged; the student `/student/feedback` sample form route still renders.

## Decisions
- Teacher only, no shared-code change (decision 1); named recipients (2); `/teacher/feedback` redirect with replace (3); `From: Administrator` kept (4).
- Anonymous behaviour of the redirect: option A, chosen by the user on 2026-11-09 (spec Open question 1).
