# Spec: ADM-04 Feedback follow-up

Status: Approved by user in chat, 2026-11-07.

## Goal
Admins compose, review and confirm private feedback responses and targeted announcements. Delivery uses student and teacher in-app inboxes.

## Behaviour
An admin follows `Respond to feedback` from a submitted feedback response or opens `Announcements` in admin navigation. The response composer shows the server-derived respondent and never allows changing that recipient. Announcements select one role, `Students` or `Teachers`, then `All active users` or `Selected users`. Selected-user search and pagination never change an already selected ID silently.

Both composers require a subject and message. `Review message` creates a server-side immutable preview showing exact text, recipient names, role and count. `Edit message` returns to the populated composer and invalidates its current preview. `Confirm send` atomically creates unread inbox messages for the reviewed recipients. A repeated confirmation of the same preview returns its original successful receipt without creating duplicates, including after a timeout or process restart. A new preview is an intentional new message. A sent message cannot be edited or recalled. No recipient can see another recipient's identity, recipient list or raw feedback. Existing student/teacher inboxes retain their survey section and add a separate paginated `Messages` section for these deliveries. No raw response is copied automatically into a message.

## Acceptance criteria
- [ ] AC01 **Recipient scope:** I can address a response to the individual who submitted the selected feedback; the recipient is shown before sending.
- [ ] AC02 **Message review:** I can review the message content before confirming the send action.
- [ ] AC03 **Delivery:** After sending, the message appears as unread in that recipient's in-app inbox.
- [ ] AC04 **Privacy restriction:** The message does not include or expose other respondents' private responses.
- [ ] AC05 **Scope boundary:** This is a one-to-one follow-up, not a group announcement; group announcements are covered by ADM-04-02. Email and push delivery are outside the MVP.
- [ ] AC06 **Audience review:** Before sending, I can review whether the selected audience is students or teachers.
- [ ] AC07 **Message review:** I can review the announcement content before confirming the send action.
- [ ] AC08 **Delivery:** The announcement appears as unread in the in-app inbox of each intended recipient.
- [ ] AC09 **Access restriction:** Only intended recipients can access the announcement, including through direct requests.
- [ ] AC10 **Scope boundary:** An announcement is a shared message to an audience, not a response to an individual submission (ADM-04-01). Email and push delivery are outside the MVP.
- [ ] AC11 Unauthenticated and wrong-role requests fail on the server. Disabled/archived users cannot send or receive new deliveries. Recipient direct reads enforce ownership, with no audience or raw-feedback disclosure.
- [ ] AC12 Review and send are distinct actions; the server sends only an immutable preview owned by the current admin. Expired, altered or stale audiences cannot be sent without a fresh review. Replays and concurrent sends create at most one delivery per intended recipient.
- [ ] AC13 Fields, recipient counts, preview lifetime and quotas are bounded. Text renders literally, with accessible mobile/desktop forms, bounded loading and specific recoverable errors. No live AI requests occur.

- [ ] AC14 Active student/teacher navigation displays an owner-only unread inbox total, refreshes while visible, updates after reads, hides zero and clears on session changes without fetching message bodies.
- [ ] AC15 Inbox/composition/review have distinct section headings and editable outlined inputs, a separate recipient-search panel, clear read/category/date treatments and accessible light/dark mobile layouts.

## UI states and copy
### Approved visual and notification amendment (2026-11-07)
User requested this redesign in chat. This amendment overrides the earlier separate-counter/no-navigation-badge presentation; existing delivery, privacy and review contracts remain in force.

- Inbox has page heading `Inbox`, description `Feedback requests, announcements and replies, all in one place.`, and distinct `Feedback requests` and `Messages` section headings. Padded request rows show title, Read/Unread and lifecycle chips; message cards separate category/unread indicator, subject, plain-text body, readable local date/time (semantic time with original ISO datetime), and a trailing outlined `Mark as read` action. Existing section status/error copy remains unchanged.
- Compose has separate `Message details` and `Recipients` panels. Desktop places the message editor beside a bounded recipient picker; mobile stacks the two. Recipient search is at the top of its own panel, outside the message form. Persistent outlined labels, contrasting input surfaces and visible focus distinguish editable Subject/Message/Search from headings. Subject/body supporting copy states their limits. All-active selection says `All active students selected` or `All active teachers selected`; filtered totals are labelled `{count} matching recipients`, never selected audience size. Explicit selection retains `{count} selected`.
- Review visually separates audience summary from message preview; receipt has a clear success treatment. Light/dark use restrained blue primary/focus/unread accents, neutral surfaces, readable secondary text, visible dividers and keyboard focus. Long names, IDs and bodies wrap; minimum viewport 320px; no horizontal page overflow. These styles are scoped to ADM-04/inbox, rather than changing unrelated pages.
- Sidebar Inbox shows a rounded count badge for unread messages plus unread survey requests, hidden at zero and capped visually at `99+`. Accessible link name remains `Inbox`; badge status announces the exact count. Identical behavior in mobile navigation. No sample count for authenticated users, no previous-account count after logout/switch.
- Requests per load and per retry: metadata-only `GET /api/messaging/unread-count` once per authenticated student/teacher shell mount (deduplicated under StrictMode), every 60 seconds while visible, and on focus/visibility return with a 5-second minimum spacing. It is not repeated for ordinary route navigation. Successful list loads publish their section count locally; successful message read updates the badge locally without another GET. Opening a feedback form requests one count refresh after its successful read. In-flight refreshes coalesce; a mutation invalidation during a pending count read schedules one follow-up. No calls for anonymous/admin shells. Background failures keep the last known count; an initially unavailable count remains hidden, not an invented zero. No intrusive background alert or retry loop; next scheduled/focus refresh recovers. Existing inbox list requests and explicit retries remain unchanged.

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen (wrong input, 401, 403, 404, 409, 422, 429, network, timeout) and the exact message | After a failed action (what stays, what is retried) |
|---|---|---|---|---|---|---|
| Response composer | link `Respond to feedback`; textbox `Subject`; textbox `Message`; button `Review message` | `Loading recipient…` | heading `Respond to feedback`; `Recipient: {name} ({role})` | not applicable | mapped errors below | Failed load: `Retry`; failed preview: retain fields and recipient, retry only preview |
| Announcement composer | link `Announcements`; radio `Students`; radio `Teachers`; radio `All active users`; radio `Selected users`; textbox `Search recipients`; checkbox `{name} ({id})`; buttons `Previous page`, `Next page`, `Review message`; textboxes `Subject`, `Message` | `Loading recipients…` | heading `New announcement`; explicit selection `{count} selected`; all-active `All active students selected` or `All active teachers selected` | `No eligible recipients.`; search: `No matching recipients.` | mapped errors below | Keep text and selected IDs; failed list can retry same page; changing role clears selected IDs and current preview |
| Review | heading `Review message`; button `Edit message`; button `Confirm send`; `Recipients: {count}`; names displayed as list `Recipients` | `Preparing review…`; sending: `Sending message…` | subject and complete message, selected role and complete recipient list | not applicable | mapped errors below | Retain preview for retry unless invalid/expired/stale; stale preview returns to populated composer with selections retained for correction |
| Receipt | heading `Message sent`; status `Sent to {count} recipient(s).`; link `Back to feedback` for response or button `New announcement` | not applicable | immutable receipt summary | not applicable | not applicable | not applicable |

Message inbox adds a separate `Messages` heading, status `Loading messages…`, empty `No messages yet.`, buttons `Load more messages`, `Retry messages` and `Mark as read`, and status `{count} unread messages`. Message articles use the subject as accessible name and show literal full text, type, timestamp and Read/Unread. Exactly one messages GET on inbox mount, one per load-more/retry, one read POST per click; existing survey requests and labels remain unchanged. Read failures preserve unread state. Inbox refresh/history refetch owned messages once and never resends admin messages.

Error copy (role `alert`, exactly these messages):
- Empty/too long subject: `Enter a subject between 1 and 120 characters.`
- Empty/too long body: `Enter a message between 1 and 5000 characters.`
- No selection/too many: `Select between 1 and 500 recipients.`
- 401: `Your session has expired. Sign in again.` (clear private state and replace navigation to login.)
- 403: `Only admins can send messages.` (clear private state and replace to own role area.)
- 404 response/recipient: `This feedback recipient is unavailable.`
- 404 inbox message: `This message is unavailable.`
- 404 preview: `This message review is unavailable. Review the message again.`
- 409 recipient change: `The audience has changed. Review the recipients again before sending.`
- 409 expired preview: `This review has expired. Review the message again.`
- 422 invalid request other than field errors: `Check the message and audience, then review again.`
- 429: `Too many messaging requests. Wait a minute and try again.`
- 403 CSRF: `Your security session has expired. Refresh the page and try again.` (retain fields; no automatic retry.)
- 413: `The message request is too large. Shorten it and try again.`
- 500: `Messaging encountered an error. Try again.`
- 503: `Messaging is temporarily unavailable. Try again.`
- Network: `Could not reach the server. Check your connection and try again.`
- Timeout: `The request timed out. Try again. If you were sending, retry this review to check delivery.`

- Requests per load and per retry: a review query replaces composer loading with exactly one preview GET; otherwise response composer exactly one recipient GET; announcement exactly one first-page recipients GET (default Students, All active users). Each list search/page/role change triggers exactly one GET, search debounced 300 ms; no hidden count call. Selected-users selection and typing text send no request. Review exactly one preview POST; confirm exactly one send POST. Retry repeats exactly the failed request, never automatic retries. StrictMode must not duplicate load requests.
- Wrong role: redirect to own role home using replace, no ADM-04 API request; anonymous users replace to login. Server still enforces roles.
- Link history: push or replace: entry links push composer URLs; review adds `?review={preview_id}` by replace; edit removes that query by replace; receipt retains it; Back to feedback pushes original response URL; New announcement resets local state at same URL. Login/role redirects replace.
- Refresh: missing/expired recovered review shows its exact alert and button `Start a new message`; this clears the review query by replace and loads the empty composer once. Editing a recovered valid review restores subject/body, audience mode and selected IDs; one eligibility GET follows, with no preview creation or send. After preview creation, use its receipt directly without another GET. A composer without a review query reloads empty fields and refetches recipients. A review query loads the durable preview or sent receipt with one GET, never automatically sends. No unsent content is stored in browser storage. Successful delivery persists in inbox; after uncertain send, refresh restores the same preview/receipt and retry uses that same ID.
- Back and Forward: navigation remounts an empty composer without a review query or restores that exact durable preview/receipt with a review query; one corresponding GET, no automatic send. Abort requests and ignore stale completions when route/account changes.
- Expired session or logout: clear composer, selections, preview and receipt immediately; never show previous-account content or accept a stale response after another login.
- Backend down: show exact network or 503 copy and `Retry`; preserve current local text while account remains the same.
- Longest wait before an error: 15 seconds per request, including send; abort and show timeout copy. No uncontrolled retry.
- No generic failure message: all failures map to the exact copy above; network copy is reserved for network failure.

## Out of scope
Email, push, AI composition, raw-feedback sharing, attachments, rich text/Markdown, scheduling, conversations/replies, recipient editing of sent messages, recall/deletion and an admin sent-history browser. Do not add feedback analysis or change existing survey/draft workflows.

## Security and AI safeguards
Use existing server auth/session and durable inbox ownership controls. Every operation rechecks active-admin status; recipient data are admin-only. Messages contain only admin-authored plain text. Raw feedback, other recipients and unpublished learning/answer records are never fetched into message payloads or recipient responses. Render HTML and prompt-injection strings literally. There is no AI or answer retrieval in this feature. Human-authored messages cannot be semantically guaranteed free of copied private information; the control is no automatic private-data inclusion plus admin review, not a claimed content classifier.

Preview expires after 15 minutes. Request bodies are limited to 128 KiB. Recipient inbox list/read operations share 60 requests/minute/account; preview recovery reads share the admin recipient-read quota. Maximum 500 recipients; all-active audiences exceeding that limit must use Selected users. Limits: 20 recipient reads/minute/admin, 10 preview requests/minute/admin, 5 first-time sends/minute/admin; idempotent successful replay is exempt from send quota after active-admin/ownership checks. No sensitive message contents in telemetry/logs. Persist message/previews under the existing retention policy until a future approved deletion feature; no automatic expiry/deletion of deliveries.

- Concurrent requests (same time): durable unique preview send and message-recipient constraints plus a transaction ensure one logical message and one unread inbox delivery per intended user. Fan-out is all-or-nothing. Active-recipient checks and send serialize with account deactivation/archive; a deactivation completed before send validation cannot receive delivery. Never reset a read delivery to unread on replay. Different fresh previews are distinct sends. Preview creation itself has no delivery side effect.
- Normalisation: trim subject/body outer whitespace; normalise CRLF to LF; lengths are Unicode code points after normalisation. Reject NUL and control characters other than tab/newline in body; subject is single line. Account IDs are opaque case-sensitive strings (1-64 characters, without surrounding whitespace), never UUID-coerced or lowercased. Form/response/preview/message/delivery UUIDs are canonicalised and compared structurally; reject malformed IDs. Deduplicate recipient IDs before limits; sorted exact account IDs determine audience identity. Search is trimmed, case-insensitive, bounded to 100 characters; roles are exact enums.

## Open questions
All ADM-04 policy proposals below were approved by the user in chat on 2026-11-07; no blocking open question remains.
1. Approve proposed audience policy: one role, either all active accounts or explicit selected users, global admin scope (no implicit course filter), maximum 500 recipients. The stories do not fix audience granularity.
2. Approve preview lifetime, request quotas, text limits and intentional repeat follow-ups using fresh previews.
3. Identified feedback is required for a one-to-one response. Approve reuse of the approved ADM-02 identified-response policy and existing retention policy; anonymous or archived/missing respondents are unavailable. No new anonymity or deletion policy is introduced.
4. Subject/learner level, upload formats and practice scoring decisions do not affect ADM-04. SoC settings are not applicable because no AI calls occur.
5. Integration facts supplied by orchestrator: preserve survey inbox API unchanged, add a separate Messages section, reuse active-role/CSRF checks and the shared error envelope; no source was read by spec-writer.
