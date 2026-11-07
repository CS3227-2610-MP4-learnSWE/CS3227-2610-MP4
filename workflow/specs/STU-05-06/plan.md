# Plan: STU-05-06 Student feedback and inbox (verification slice)

Dependency: the build starts from a branch containing PR 31 (`origin/feat/adm04-feedback-follow-up`, ADM-04). The orchestrator merges that branch into this one for the build, and the STU pull request stays stacked on PR 31 until PR 31 merges. `FeedbackInbox.tsx` and `Shell.tsx` are shared with ADM-04, so no work in them starts earlier.

## Data model
No change. No new table, column or migration. Reused: `feedback_recipients.read_at` and `feedback_responses` (ADM-02, `workflow/specs/ADM-02/plan.md`, Data model) and the ADM-04 delivery rows with `read_at` per recipient (`workflow/specs/ADM-04/plan.md`, Data model).

## API endpoints
No new endpoint. The slice relies on these existing contracts, which are not copied here:
- ADM-02 plan, API endpoints: GET `/api/feedback/inbox`, GET `/api/feedback/forms/{form_id}`, PUT `/api/feedback/forms/{form_id}/draft`, POST `/api/feedback/forms/{form_id}/responses`, error dictionary E01-E08, V10, V11, C04-C06.
- ADM-04 plan (PR 31): GET `/api/messaging/inbox` (item `{id, kind, subject, body, sent_at, read_at}`), POST `/api/messaging/inbox/{delivery_id}/read`, GET `/api/messaging/unread-count` returning `{unread_count, unread_messages, unread_requests}`. Roles and error codes as in that plan.

Mismatch found: the message item has no sender, but US-STU-06-01 needs one (spec, Open question 1). Option A needs no endpoint change.

## Components and modules
Reused unchanged: `src/frontend/src/pages/FeedbackInbox.tsx`, `RecipientFeedback.tsx`, `Inbox.tsx`, `services/feedbackApi.ts`, `components/MessagesInbox.tsx`, `hooks/useInboxUnread.ts` (events `publishInboxCount`, `refreshInboxUnread`), `components/Shell.tsx` badge; backend routes, store and the shared auth, rate-limit and error modules.

Possible change (only if the user approves option A): `components/MessagesInbox.tsx`, render the text `From: Administrator` beside the sent time in each message row. One component, no new module, no data change. The existing sent-time rendering stays as is.

New files: tests only (names below), written by the test-designer; docs: `docs/UserGuide.md` and `docs/DeveloperGuide.md` student inbox and feedback sections corrected to match the product (the developer does this; no claim for anything that is not delivered).

## UI contract
Accessible names the tests use (all except the sender line are existing ADM-02 or PR 31 names):
- Sidebar: link named `Inbox`; its badge is a `status` whose accessible name is `{n} unread inbox items`, shown as `99+` above 99, absent at 0.
- Page: heading level 1 `Feedback requests`; status `Unread requests: {count}`; links named by form title; texts `Unread` or `Read` and `Not started`, `Draft`, `Completed`, `Closed`; button `Retry`; buttons `Next page`, `Previous page`; empty text `No feedback requests yet.`; loading `Loading feedback requests...`.
- Messages: heading `Messages`; status `{count} unread messages`; each message shows `From: Administrator` (option A) and the sent time. Names for the loading text, empty text, error copy and the mark-read control are to be confirmed from PR 31 by the orchestrator and written here before the test-designer starts (spec, Open question 5).
- Form: heading is the form title; button `Submit feedback`; success `Feedback submitted. Thank you.`; closed `This form is closed.`; completed `You have already submitted feedback.`; link `Back to inbox`.

- Requests per load and per retry: Inbox page load sends one GET `/api/feedback/inbox` and one GET `/api/messaging/inbox`; the shell sends one GET `/api/messaging/unread-count` on mount. `Retry` in a section repeats only that section's read once. Opening a form sends one form GET, followed by one forced count refresh (not throttled; the 5-second throttle applies only to focus and visibility refreshes). Marking a message read sends one POST and no list re-read. The existing focus, visibility and 60-second refreshes of the badge are kept; this slice adds no polling. Tests assert counts for the inbox page and for one retry, using StrictMode-style double effects.
- Wrong role: A teacher or admin on a student inbox or form URL is redirected to their own area with replace; no inbox, form or count request for that page is sent. Direct student APIs return 403 for other roles.
- Link history: push or replace: `Inbox` link, form title links and `Back to inbox` push; Retry, pagination, mark-read and badge refreshes leave the URL; wrong-role and session-expiry redirects replace.
- No generic failure message: every failure uses the ADM-02 dictionary copy or the PR 31 section message; a network message appears only for a real transport failure; the badge shows no text on failure and keeps its last value.

## AI usage
Not applicable: no SoC LLM call is added or changed; inbox and feedback content never enter AI context.

## Test plan
Tests only, by the independent test-designer from this spec and the ADM-02 and ADM-04 plans; backend names `test_stu05_...` / `test_stu06_...`, frontend names start `STU-05` / `STU-06`; SoC LLM not involved. First pass: the matrix below says what exists; the developer's PR 31 and ADM-02 tests are cited by file once the test-designer can see the test folders.

| Criterion | Existing evidence (to confirm in test folders) | Gap test to write (student view) |
|---|---|---|
| AC01 | ADM-02 publish and inbox delivery tests (`test_adm02_...`) | `stu05` student sees only requests addressed to them; named targeting only |
| AC02 | ADM-02 V10 and required-field tests, submit confirmation | `stu05` student submits with a required answer missing and sees V10 copy, then submits and sees `Feedback submitted. Thank you.` |
| AC03 | ADM-02 cross-user E03 tests | `stu05` second student requests first student's form, draft and response by direct URL and gets E03; response not in the second student's payloads |
| AC04 | ADM-04 inbox tests (no sender in the item) | `stu06` each message row shows `From: Administrator` and the sent time (option A); survey requests listed under `Feedback requests`; gap until option A is built |
| AC05 | ADM-04 recipient-only tests | `stu06` second student reads or marks the first student's delivery by direct request and gets not found; not in list |
| AC06 | ADM-02 form-open tests | `stu06` clicking a request title opens `/student/feedback/{form_id}` form; non-recipient gets E03 |
| AC07 | ADM-02 C04 tests | `stu06` closed form shows `This form is closed.`, no editable answers, direct POST returns C04; completed form shows C05 |
| AC08 | ADM-04 mark-read tests | `stu06` new message is `Unread`, becomes `Read` after opening, for that student only |
| AC09 | ADM-04 unread-count tests | `stu06` after logout and sign-in the message and the request stay read and counts match |
| AC10 | none | `stu06` no email or push control or endpoint is exposed (UI scan only) |
| AC11 | ADM-04 badge test (to confirm) | `stu06` badge equals survey unread plus message unread, absent at 0, `99+` over 99 |
| AC12 | ADM-04 refresh test (to confirm) | `stu06` badge drops by one after opening a form and after reading a message |
| AC13 | none | `stu06` survey list read fails: message section and its count still show; message read fails: survey section still shows; count endpoint fails: page unaffected, badge keeps last value; copy exact |

Security tests (also in `workflow/security/`): cross-student direct access to form, draft, response and delivery; wrong-role access to student inbox endpoints (403); unauthenticated 401 on each; a message body containing HTML renders as text.
Records tests (Tasks 6 and 7 of the template apply): concurrent mark-read and concurrent submit on one record, cross-user test with another student, another role and a student with no recipient row.

## Decisions
- Identified feedback and no retention or deletion this release (ADM-02 decision).
- Thin slice approved by the user: no new student UI, routes or tables.
- The badge, its count endpoint and its refresh rules are ADM-04 (PR 31) behaviour and are only tested here.
- Sender label: option A recommended, awaiting the user's decision (spec, Open question 1).
