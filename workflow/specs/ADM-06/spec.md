# Spec: ADM-06 AI usage monitoring

Status: Approved (by user in chat, 2026-11-06)

## Goal
Allow admins to inspect AI service-call attempts, failures and recorded resource measurements by feature and period without exposing private request content.

## Behaviour
The admin navigation link "AI usage" opens `/admin/ai-usage`. Filters select All features, Student assistant (STU-03), Teacher generation (TEA-02), or Feedback analysis (ADM-03), plus inclusive UTC start/end calendar dates. Default dates are today and six days earlier. One row per selected feature reports requests, failures, rate-limit failures, other failures, input tokens, output tokens and total tokens. All features always returns all three rows, including unsupported/not-yet-instrumented features with unavailable values. TEA-02 combines note and MCQ generation. Do not show outcome percentages.

A request means an actual outbound SoC provider attempt, including every provider retry, attributed to the UTC reservation instant immediately before dispatch. The reservation-to-dispatch gap is handled conservatively as unavailable rather than claiming an observed call. Local validation, authentication and quota rejection do not dispatch a service call and are excluded. Provider 429 failures count as rate-limit failures; all other unsuccessful transports/provider responses count as other failures. A provider response that later fails feature-content validation is still a successful service call. This distinction must be documented beside the report.

Persist metadata before dispatch, then finish that same attempt once. An interrupted pending reservation cannot prove dispatch; it makes request, failure and resource totals unavailable until resolved. A completed reservation confirms an actual outbound attempt. Coverage begins only when all running call paths for a feature are instrumented. Earlier history is not reconstructed. Coverage gaps or a period starting before coverage make all affected metrics unavailable; recorded rows are never presented as complete historical totals. A complete covered period with no calls shows zero counts and unavailable token measurements. Display coverage timestamps and an explanation for each unavailable metric. This may mean initial calendar-day reports are unavailable until a full covered UTC day exists; no backfill is implied.

## Acceptance criteria
The first nine criteria copy the ADM-06 user-story acceptance criteria; operational details below make them testable.

- [ ] AC1 **Request unit:** Count each AI service-call attempt as one request, including a retry as a separate attempt.
- [ ] AC2 **Breakdown:** For the selected feature and reporting period, show the total request count and failure count.
- [ ] AC3 **Failure category:** Identify rate-limit failures separately from other failures.
- [ ] AC4 **Zero activity and unavailable data:** If the data is available and no requests occurred in the selected period, show zero requests and failures. If the data source is unavailable or incomplete, label the affected counts unavailable rather than showing zero.
- [ ] AC5 **Privacy restriction:** Do not display credentials, private prompts, or private response content.
- [ ] AC6 **Scope boundary:** This story reports operational counts and failure categories, not generation success percentages (ADM-01-02) or resource measurements (ADM-06-02).
- [ ] AC7 **Measurement context:** Each available token or other resource measurement identifies the AI feature and reporting period it describes.
- [ ] AC8 **Unavailable values:** If a measurement is unavailable, label it unavailable; do not show an estimate as if it were an observed value.
- [ ] AC9 **Scope boundary:** Show recorded measurements only. Forecasts, inferred measurements, and private request content are outside this story.
- [ ] AC10 Only authenticated active admins can read the report; student/teacher/disabled/archived/expired sessions are rejected server-side, including direct API requests.
- [ ] AC11 Validate feature/date inputs; at most 31 inclusive UTC days, no future end date, start no later than end. Use one consistent database snapshot and an `as_of` cutoff so concurrent completion cannot mix incompatible totals. Preserve records over restart; replaying finalisation cannot double-count.
- [ ] AC12 Every configured SoC call path for STU-03 and TEA-02 uses the shared observer. ADM-03 remains explicitly uninstrumented until its own feature integrates. Recording failures never expose provider messages/content; if reservation cannot be persisted, make no outbound call and use the existing feature's safe service-unavailable response. Failed finalisation leaves pending state, not fabricated success/failure.
- [ ] AC13 Accessible responsive UI provides exact loading, empty, unavailable and recoverable failure states; stale results are cleared on a new request, navigation/logout or account change. Ignore late responses from superseded filters or sessions. No live AI calls are made by the reporting endpoint.

## UI states and copy

| Screen or action | Control (button, tab, link, field) and its exact label | Loading | Success | Empty | Each failure that can happen (wrong input, 401, 403, 404, 409, 422, 429, network, timeout) and the exact message | After a failed action (what stays, what is retried) |
|---|---|---|---|---|---|---|
| Open report | link "AI usage"; heading "AI usage" | status "Loading AI usage…" | table "AI usage by feature"; caption "Service-call attempts, including retries. Dates are UTC. Local quota rejections are excluded." | Covered row: zero counts, token cells "Unavailable"; all selected covered rows empty: status "No AI service calls in this period." | 401: "Your session has expired. Sign in again."; 403: "You do not have access to AI usage."; 429: "Too many report requests. Try again shortly."; 503: "AI usage data is temporarily unavailable. Try again."; network: "Could not reach the server. Check your connection and retry."; timeout: "AI usage request timed out. Try again."; unexpected status/malformed response: "The server returned an invalid AI usage report. Try again."; 404/409 not produced by this API and use the unexpected-response message | Keep filters, clear report; button "Retry" retries same applied filters. 401 uses shared expiry handling and sign-in redirect; 403 retains access error without report/retry |
| Apply filters | combobox "Feature"; date fields "Start date (UTC)", "End date (UTC)"; button "Apply filters" | same status; Apply filters and Retry disabled while pending; fields remain editable | selected feature rows; applied period visible as "Period: YYYY-MM-DD to YYYY-MM-DD (UTC)" | same covered empty state | 422/local invalid: "Choose a valid feature and a UTC date range of at most 31 days ending today or earlier." | role alert shows exact error; retain entered fields; no report shown; local invalid makes no request; valid resubmission uses Apply filters |
| Unavailable metric | no extra control | not applicable | numeric value only when complete | "Unavailable" | Inline reasons: "Coverage does not include the whole period."; "Collection is not enabled for this feature."; "Some service calls have not finished recording."; "The provider did not supply this measurement for every call."; "No recorded token measurements in this period." | Available sibling metrics remain; no automatic retry or fabricated zero |

- Requests per load and per retry: one report GET per history-entry activation after authentication resolves, including development StrictMode; one per valid Apply filters or Retry; zero on invalid input or wrong-role navigation. No polling or automatic retries. Shared session bootstrap requests are separate.
- Wrong role: authenticated student/teacher visiting the route is redirected with replace to their existing role home and sends no report GET. Direct API requests return 403. A mid-session server 403 shows the specified alert.
- Link history: push or replace: AI usage navigation pushes; normal cross-page links push. Apply filters and Retry do not change the URL. Wrong-role and expired-session redirects replace. Filter state is in memory per mounted page, not URL/session storage.
- Refresh: shared session bootstrap then one GET with default filters. Clear old report immediately; never restore private report from browser storage or HTTP cache.
- Back and Forward: each route/history-entry activation resets default filters and sends one GET, including returning to an already mounted page; no old report flashes. Wrong-role/session guards run first.
- Expired session or logout: use shared authenticated shell, existing Confirm logout flow and session-generation protections. Successful logout/expiry clears report and filters; failed logout keeps the existing session/dialog. Browser Back cannot reveal cached report. A newly signed-in account cannot receive a former account's pending result.
- Backend down: show the network alert only on actual network failure, preserve filters and offer Retry. A known database/service outage gives the separate 503 alert.
- Longest wait before an error: each report request is aborted after 15 seconds and shows the timeout alert; no automatic retries. Old aborted requests cannot overwrite a newer result.
- No generic failure message: use the exact messages above; never substitute a network message for an HTTP/validation failure.

## Out of scope
ADM-01 feature-outcome rates, individual-user/session breakdowns, transcripts, per-call drill-down, cost estimates, forecasting, inferred tokenisation, exports, retention deletion UI, new retry policies/quotas/models, instrumentation of future ADM-03 functionality, and live-provider verification. Other resource dimensions beyond directly supplied input/output/total token counters are deferred.

## Security and AI safeguards
Only admins read aggregate metadata. Store and return no user/course/feedback/chat identifiers, credentials, provider URLs, model-supplied strings, prompts, completions, exception messages or stack traces. Feature and outcome are server-owned enums; provider token fields are untrusted and accepted only as finite nonnegative JSON integers within signed 64-bit range (booleans excluded). Do not derive total tokens by adding input/output; each measurement stands independently. Do not modify access checks, quotas, limits, retry bounds, authorised retrieval or answer-release rules in existing call paths. No monitoring payload is sent to an LLM. Use private no-store HTTP responses and safe text rendering.

- Concurrent requests (same time): unique attempt IDs; atomic creation; finalise by compare-and-set from pending to one terminal state, idempotent repeat with identical data, conflicting repeat rejected. Different retries always receive different IDs. Concurrent readers use a repeatable-read database snapshot/cutoff; pending-at-cutoff yields unavailable request, failure and resource totals. Concurrent finalisation cannot remove or duplicate requests. Coverage timestamps are durable and cannot reset on process restart.
- Normalisation: strip surrounding ASCII whitespace from feature/date query values, then require exact case-sensitive enums and strict real `YYYY-MM-DD` dates; reject unknown/repeated query keys and controls. Internally use aware UTC timestamps; start inclusive, end exclusive at midnight after inclusive end_date, capped at `as_of` for today. Never accept client-supplied attribution on application AI endpoints.

## Open questions
- Approved by user in chat on 2026-11-06: UTC calendar-day reporting (maximum 31 days), feature-level grouping (combined TEA-02 note/MCQ calls), and deployment-forward coverage with no historical backfill. These defaults are approved.
- Exact SoC quotas, model configuration and resource measurements are unresolved in UserStories. Proposal: retain existing quotas/model/retries, accept only explicit provider input/output/total token counters through a documented mapping verified during implementation; absent/unrecognised counters remain unavailable. No external provider lookup/live call is authorised by this spec. Contract mapping changes require a plan amendment before source changes.
- Initial subject/learner level, upload types/limits, attempt scoring and feedback anonymity/retention do not affect this aggregate-content-free feature; those decisions remain with their owning features. Existing account/course policy is inherited. No new retention policy or silent data deletion is introduced.


Empty-state clarification (2026-11-06, orchestrator/designer): the global "No AI service calls in this period." status appears only when every selected row has an available request count of zero. Any selected disabled/incomplete/pending row suppresses this global claim; known zero sibling rows still display zero. This applies to All features as well as individual-feature filters.


### User-approved readability follow-up (2026-11-06)

Inset report content by24px (16px on mobile). Period/description/caption text is16px; table headers and reasons at least14px, metric text15px. Wrap long cell text within fixed columns; keep caption text within the visible report width while the table scrolls. Preserve all existing labels, request counts and behavior. User explicitly requested padding, larger fonts and wrapping; existing responsive tests gain geometry/readability assertions before CSS changes.
