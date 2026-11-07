# Spec: STU-05-06 Student feedback and inbox (verification slice)

Status: Draft (awaiting user approval). Sender label: option A chosen by the user on 2026-11-07, built after PR 31 merges. Labels checked against PR 31 code on 2026-11-07.

## Goal
From the user stories: a student completes open feedback forms intended for them (US-STU-05-01) and reads admin follow-up in an in-app inbox, opens survey requests and tracks unread items (US-STU-06-01 to 06-03). ADM-02 and ADM-04 (PR 31) already build almost all of it; this slice proves every STU-05/STU-06 criterion against that behaviour, adds student-focused tests for the gaps, and closes the sender gap.

## Behaviour
No new student screen, route, table or endpoint. The student side is delivered by:
- ADM-02: `/student/inbox` (survey requests), `/student/feedback/{form_id}` (form, draft, submit); contract in `workflow/specs/ADM-02/plan.md` (endpoints GET `/api/feedback/inbox`, GET `/api/feedback/forms/{form_id}`, PUT `.../draft`, POST `.../responses`; error dictionary E01-E08, V10-V11, C04-C06).
- ADM-04 (PR 31, `workflow/specs/ADM-04/` on branch `origin/feat/adm04-feedback-follow-up`): a separate `Messages` section on the same inbox page, GET `/api/messaging/inbox`, POST `/api/messaging/inbox/{delivery_id}/read`, and a combined sidebar badge from GET `/api/messaging/unread-count` returning `{unread_count, unread_messages, unread_requests}` (hook `useInboxUnread`, badge in `Shell.tsx`).

This slice adds: (a) a criterion-by-criterion verification matrix (plan.md, Test plan); (b) tests named `stu05_` / `stu06_` only where the matrix finds a gap; (c) one small frontend change (option A, chosen by the user): each message shows `From: Administrator` and its sent time, made in `MessagesInbox.tsx` after PR 31 merges; (d) accuracy fixes to `docs/UserGuide.md` and `docs/DeveloperGuide.md` for the student inbox and feedback sections; (e) a first-run browser failure record.

Resolved decisions (recorded, not re-opened): feedback is identified, so admins see the respondent name, per the ADM-02 privacy copy `Once submitted, your name and feedback are visible to administrators. Your unfinished draft is private.`; no retention or deletion this release (ADM-02 decision).

The combined badge already exists in PR 31: it shows survey unread plus message unread on the sidebar `Inbox` link, with the two section counts kept on the page. This slice specifies no badge code; it tests the badge.

## Acceptance criteria
Copied from `docs/UserStories.md`; IDs added for test mapping.

- [ ] AC01 (US-STU-05-01) I can find forms targeted to me or my student group. Slice reading: forms targeted to me by name appear in my inbox as survey requests; student-group targeting does not exist (see Out of scope and Open questions).
- [ ] AC02 (US-STU-05-01) Required fields are validated and submission is confirmed.
- [ ] AC03 (US-STU-05-01) The saved response belongs to the correct form and is unavailable to other students.
- [ ] AC04 (US-STU-06-01) My in-app inbox contains admin survey requests, feedback responses and announcements addressed to me or an audience I belong to, with sender and sent time.
- [ ] AC05 (US-STU-06-01) Messages intended for other users or groups remain inaccessible.
- [ ] AC06 (US-STU-06-02) Opening a request leads to the associated form, subject to audience checks.
- [ ] AC07 (US-STU-06-02) Closed or unavailable forms show a clear status and reject submissions.
- [ ] AC08 (US-STU-06-03) New messages are unread, and opening a message marks it read for my account.
- [ ] AC09 (US-STU-06-03) Read status persists after signing in again, and the unread count matches unread messages I can access.
- [ ] AC10 (US-STU-06-03) Email and push delivery are outside the MVP.
- [ ] AC11 (slice) The sidebar badge on the student `Inbox` link equals survey unread plus message unread (the `unread_count` of the count endpoint), the page keeps the two section counts, and the badge is absent at zero.
- [ ] AC12 (slice) The badge drops after the student opens a survey request's form and after the student marks a message read.
- [ ] AC14 (slice) After PR 31 merges, student pages send one extra `GET /api/messaging/unread-count` from the shell badge. The existing STU-02 picker request-count test (`stu02ps-picker.spec.ts`, AC15 "one GET /api/practice-sets on load and nothing else") must still express its intent (the picker itself sends exactly one GET `/api/practice-sets`) and no longer fail because of the shell's count request. Only that assertion changes; no picker behaviour changes.
- [ ] AC13 (slice) A failure of one count source does not hide the other section's count or list, and no failure shows a generic message.

## UI states and copy
Names are taken from the ADM-02 code on this branch and the PR 31 code (checked 2026-11-07).

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen (wrong input, 401, 403, 404, 409, 422, 429, network, timeout) and the exact message | After a failed action (what stays, what is retried) |
|---|---|---|---|---|---|---|
| Sidebar badge | status text on the `Inbox` nav link, accessible name `{n} unread inbox items` | Badge absent until the first count arrives | Number `n`, shown as `99+` above 99 | Absent when the count is 0 | 401: `Your session has expired. Sign in again.` (existing sign-in flow); network, timeout, 429, 503: the badge keeps its last known value, or is absent if none, and no message is shown for the badge itself | The last known badge stays; the next scheduled refresh retries; nothing blocks the page |
| Survey requests section | heading `Feedback requests`; status `Unread requests: {count}`; link per form title | `Loading feedback requests...` | Rows `Unread` or `Read` with `Not started`, `Draft`, `Completed` or `Closed` | `No feedback requests yet.` | ADM-02 dictionary E01-E08 (for example network: `Cannot connect to the server. Check your connection and try again.`) | Prior rows stay; button `Retry` repeats the one failed read |
| Messages section | heading `Messages`; status `{count} unread messages`; each message shows subject, body, sent time and sender (option A) | `Loading messages…` | Messages newest first, `Unread` or `Read` marker | `No messages yet.` | 401 `Your session has expired. Sign in again.`; 404 `This message is unavailable.`; 429 `Too many messaging requests. Wait a minute and try again.`; 503 `Messaging is temporarily unavailable. Try again.`; 500 `Messaging encountered an error. Try again.`; network `Could not reach the server. Check your connection and try again.`; timeout `The request timed out. Try again. If you were sending, retry this review to check delivery.`; a failure here must not hide the survey section | Survey section and its count stay; the Messages section offers its own button `Retry messages` (list) and the message keeps its `Mark as read` button after a failed read |
| Sender and sent time (option A) | text on each message: `From: Administrator` and the sent time | not applicable: part of the message row | `From: Administrator` shown on every message | not applicable: only shown with a message | not applicable: static label | not applicable: static label |
| Open a survey request | link with the form title | `Loading feedback form...` | Form with its questions, button `Submit feedback` | not applicable: a request always has a form | ADM-02 dictionary: E03 `This feedback form or response is not available.`, C04 `This form is closed.` | Stays on the page with the message; no editable answers for a closed form |
| Closed or completed form | text `This form is closed.` or `Completed` with `You have already submitted feedback.`; link `Back to inbox` | `Loading feedback form...` | Status text, submit disabled, no answers fetched | not applicable: terminal state | Direct POST on a closed form: C04 `This form is closed.`; after completion: C05 `You have already submitted feedback.` | Nothing is submitted; no editable controls |
| Mark a message read | button `Mark as read` on an unread message (shown only while unread; messages show their full text, nothing expands) | button disabled while the request runs | Marker changes to `Read`; badge and `{count} unread messages` drop by one | not applicable: action on an existing row | 404 `This message is unavailable.` for another student's delivery; other failures as in the Messages row, shown as an alert on that message | Message stays `Unread`; count unchanged; user can press `Mark as read` again |

- Requests per load and per retry: The student inbox page sends one GET `/api/feedback/inbox` and one GET `/api/messaging/inbox` on load, and one of each repeated only for the section whose `Retry` is pressed; the shell badge sends one GET `/api/messaging/unread-count` on mount of the signed-in shell. The badge also refreshes on window focus or visibility change (throttled to one per 5 seconds), every 60 seconds, immediately from the counts the two sections publish, and once, forced and not throttled, after a survey form loads. Opening a form sends the one form GET that marks the request read, then one forced count refresh (not throttled); marking a message read sends one POST and no extra list read. Development effect replay must not double these. No other polling is added by this slice.
- Wrong role: A teacher or admin visiting a student inbox or form URL is redirected to their own area with no inbox, form or count request for that page; direct API calls return 403 as in ADM-02. Teachers have their own badge on their own shell and are not part of this slice's tests.
- Link history: push or replace: Sidebar `Inbox` link, form title links and `Back to inbox` push a history entry. Retry, pagination, marking a message read and badge refreshes do not change the URL. Redirects for wrong role and expired session replace.
- Refresh: The inbox reloads from the server with the counts above; read state and badge come from the server, so they match what the student last saw; unsaved form answers follow ADM-02 (server draft only).
- Back and Forward: Returning to the inbox issues a fresh read of both sections and the badge shows the current server count; a form opened earlier shows its current state (open, completed or closed), never cached answers.
- Expired session or logout: The badge timers and requests stop, the badge disappears with the shell, and the student sees the sign-in screen; a 401 on any inbox read shows `Your session has expired. Sign in again.`; after signing in again the badge shows the server count, which preserves earlier reads.
- Backend down: The page shows the section-specific network message with `Retry`; the badge keeps its last value and silently retries at the next refresh; recovery is pressing `Retry` or waiting for the next refresh.
- Longest wait before an error: 15 seconds for feedback requests, as in ADM-02 (E05 `The request timed out. Check the current form before trying again.`); the messaging requests also use 15 seconds (timeout copy in the Messages row).
- No generic failure message: Every failure uses its dictionary message or the section-specific message above; the words for a network failure appear only for a real transport failure (known inconsistency: the survey section says `Cannot connect to the server. Check your connection and try again.` and the Messages section says `Could not reach the server. Check your connection and try again.`; both are kept, tests assert each as is); the badge never shows an error text.

## Out of scope
Student-group targeting (forms target named recipients, so AC01 "or my student group" is met only by named targeting); a merged chronological list of requests and messages; a deep link from a message to a form; search or filter of the inbox; email and push delivery; new student routes, tables or backend endpoints; any admin or teacher change; changes to ADM-02 or ADM-04 behaviour beyond the sender label; the PR 31 search-debounce test failure (`adm04-messaging.spec.ts:163`) belongs to the ADM-04 owner.

## Security and AI safeguards
No SoC LLM call is made or changed; feedback and messages never enter AI context. Access is enforced on the server by ADM-02 and ADM-04: a student can read only their own inbox rows, their own form and draft, and mark only their own delivery read; another student's form, response or delivery returns the same not-found error as a missing one (ADM-02 E03). Rendering is plain text; message bodies are never inserted as HTML. The slice adds no endpoint, so no new access rule; the new tests must prove the existing ones by direct request as a second student.

- Concurrent requests (same time): Two simultaneous mark-read requests for one delivery leave one read time and both succeed or one is a harmless repeat; two simultaneous submissions of one form leave one response and one C05 (ADM-02); a badge refresh racing a mark-read shows either the old or the new count, never a negative or stale-after-refresh value.
- Normalisation: Delivery, form and response identifiers are parsed as canonical UUIDs and a malformed one returns not found, as in ADM-02; account IDs are exact opaque strings and are never taken from the client.

## Open questions
1. Sender gap (resolved 2026-11-07, user chose A). The ADM-04 inbox item has no sender, but US-STU-06-01 requires sender and sent time. A fixed `From: Administrator` label is added in `MessagesInbox.tsx` after PR 31 merges (no conflict with the ADM-04 owner's file); no backend change. A fixed label does not distinguish between admins; accepted. Options B (sender field in ADM-04's backend) and C (known deviation) were not chosen.
2. Group targeting (user view: recommended acceptance, pending final confirmation). Forms target named recipients only (ADM-02), so "or my student group" is met by named targeting. Record as a known limit in `docs/UserGuide.md`.
3. Badge failure behaviour (checked against PR 31): a failed count read is ignored and the badge keeps its last value, or is absent if it never loaded. Opening a form forces an immediate refresh, with no throttle delay.
4. "One source fails" (checked): the count comes from one aggregated endpoint, so the tests fail the survey list read or the message list read while the other section still shows.
5. Labels (checked): see the Messages row. Still to confirm during test design: that a 403 on the student inbox redirects to the student's own area, because PR 31's `forbidden` text is the admin-only `Only admins can send messages.`.
6. Decisions list: "Whether feedback is identified or anonymous, with retention and deletion" is resolved as identified, none this release (ADM-02 decision). Initial subject, upload formats, repeat-attempt scoring, SoC quotas and ADM-05 course decisions do not affect this slice.
