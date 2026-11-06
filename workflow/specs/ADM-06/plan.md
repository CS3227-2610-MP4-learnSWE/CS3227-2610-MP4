# Plan: ADM-06 AI usage monitoring

Status: Approved (by user in chat, 2026-11-06); source-aware compatibility amendment below records existing integration contracts.

## Data model

Add PostgreSQL `ai_service_attempts`: UUID primary key `id`; `feature` enum `STU-03|TEA-02|ADM-03`; aware UTC `started_at`; nullable aware UTC `finished_at`; `outcome` enum `pending|success|rate_limit|other_failure`; nullable signed-bigint `input_tokens`, `output_tokens`, `total_tokens` with nonnegative constraints. No request body, provider message, identity or content column. Index `(feature, started_at)`. Each explicit/transport-level retry has a new row; SDK hidden retries must be disabled in favour of the existing bounded retry loop or observed individually. Do not introduce extra attempts.

Add `ai_usage_coverage`: one row per feature, nullable `covered_since` aware UTC, boolean `enabled`, nullable `incomplete_since`. Initialise all disabled. Enable STU-03/TEA-02 only with coordinated deployment/restart of all workers and confirmation every outbound path uses the observer; persist activation time once. ADM-03 remains disabled. Activation is a documented deployment command `uv run python -m ai_usage.activate --feature STU-03 --feature TEA-02`, idempotent and incapable of moving an existing coverage start earlier or clearing a gap; do not activate automatically in a migration or infer coverage from first call. A gap is sticky and all intersecting reports unavailable until a separately reviewed recovery/backfill policy exists. Migration on a populated database does not alter existing domain rows.

Durable pre-dispatch reservation is an internal write independent of the feature transaction, so a domain rollback does not erase a dispatched attempt. If reservation fails, dispatch is forbidden. Finalisation uses its own transaction and compare-and-set; failed finalisation leaves pending. Retain attempts indefinitely in this release; no silent pruning. Reporting transaction uses PostgreSQL REPEATABLE READ; take `as_of` in that transaction and query only rows started strictly before it. Filter completed states by `finished_at` at or before cutoff; anything finished after cutoff is pending for that report. Bounded range/indexes; no per-user joins.

## API endpoints

`GET /api/admin/ai-usage?feature=all&start_date=2026-11-01&end_date=2026-11-06` accepts active admin sessions only. All three query parameters are required strings. Feature enum: `all|STU-03|TEA-02|ADM-03`. Inclusive dates, maximum 31 days; validate against server UTC date. Reject unknown/duplicate parameters; apply spec normalisation. No mutation/report export endpoint.

200 response JSON has exactly these keys:

```json
{
  "feature": "all",
  "start_date": "2026-11-01",
  "end_date": "2026-11-06",
  "timezone": "UTC",
  "as_of": "2026-11-06T12:00:00Z",
  "rows": [
    {
      "feature": "STU-03",
      "coverage_start": "2026-10-31T12:00:00Z",
      "requests": {"value": 3, "reason": null},
      "failures": {"value": 2, "reason": null},
      "rate_limit_failures": {"value": 1, "reason": null},
      "other_failures": {"value": 1, "reason": null},
      "input_tokens": {"value": null, "reason": "missing_measurement"},
      "output_tokens": {"value": null, "reason": "missing_measurement"},
      "total_tokens": {"value": null, "reason": "missing_measurement"}
    }
  ]
}
```

Example illustrates one row shape; `all` actually returns exactly three rows ordered STU-03, TEA-02, ADM-03. A specific feature returns exactly one row. Metric `value` is a nonnegative integer or null; `reason` is null iff value is available, else enum `not_enabled|incomplete_coverage|pending_attempts|missing_measurement|no_measurements`. Available sums must fit JavaScript's safe integer range; on overflow that metric uses null/`missing_measurement` rather than a rounded number. `coverage_start` is timestamp/null. No other metadata/IDs or content in response. All responses set `Cache-Control: private, no-store` and `Vary: Cookie`.

Availability precedence for each row: disabled => all metrics `not_enabled`; period start before covered_since or intersecting incomplete_since => all metrics `incomplete_coverage`; otherwise any pending row makes every metric, including requests, null/`pending_attempts`, because a crash between reservation and dispatch cannot prove an outbound call occurred. With no pending, requests = number of terminal rows. With no pending, failure counters count terminal categories (failures = rate_limit + other_failure). Zero attempts => all counts zero, all tokens `no_measurements`. For each token field independently, if any attempt lacks a valid recorded field use `missing_measurement`; otherwise sum that field. Never show a partial sum as a complete total. Valid provider usage on failed calls may be included if explicitly supplied and recorded.

Errors use existing application's shared JSON error envelope, with stable `detail.code` for this route: 401 `unauthenticated`; 403 `forbidden`; 422 `invalid_ai_usage_filters`; 429 `ai_usage_report_rate_limited`; 503 `ai_usage_unavailable`. The developer must reuse existing authentication/active-account dependency, shared session error handling and report throttling facilities; do not add a parallel auth scheme. Per-active-admin reporting throttle: at most 30 accepted report requests per rolling 60 seconds, existing shared limiter or dedicated named bucket; a rejected request has 429 and Retry-After integer seconds. Route unknown status/malformed response maps to the UI invalid-report message. Database unavailability must become safe 503, never a fake empty 200. No 404/409 in normal report operations.

Internal contract in new `ai_usage/service.py` (not public API):

```python
reserve_attempt(feature: str) -> UUID
finish_attempt(attempt_id: UUID, outcome: str, *, input_tokens: int | None = None,
               output_tokens: int | None = None, total_tokens: int | None = None) -> bool
read_usage_report(feature: str, start_date: date, end_date: date) -> dict
activate_coverage(features: list[str]) -> None
```

`reserve_attempt` server-sets started_at and pending; only supported feature enums. `finish_attempt` accepts terminal outcomes only; returns True for initial write or identical replay; False for conflicting replay/unknown ID, without overwriting. Invalid token values become null per field. Database exceptions propagate internally for safe adapter handling, never store exception text. `read_usage_report` implements exact JSON/availability rules. `activate_coverage` commits atomically for all supplied features; disabled unknown feature/ADM-03 rejected until integration is approved. Tests may directly insert fixtures via SQLAlchemy without depending on implementation model class names.

## Components and modules

New backend package `ai_usage` owns models/repository/service/report router and activation CLI; additive Alembic migration. Reuse the existing shared SoC LLM client, SQLAlchemy session/engine, admin authentication/active-account dependency, error handling and rate limiter. Bind a server-owned feature context at existing shared-client call sites; client/server-controlled data cannot override it. Never duplicate the provider HTTP transport. A narrow observer around every actual outbound attempt reserves/finalises metadata; feature validation remains outside service-call outcome classification. Once implementation can inspect source, document the exact provider usage-field mapping and reused symbol names as a plan amendment before coding; if incompatible, report a blocking contract gap instead of guessing.

New frontend `AdminAiUsage` page, typed service using existing shared client/session generation, authenticated admin router and shared shell/navigation/styles. Reuse existing table/form/alert patterns and logout confirmation. Update UserGuide and DeveloperGuide for metrics, initial unavailable periods, coordinated activation, migration, restart and outage semantics. No browser persistent storage or service-worker caching of reports.

## UI contract

Route `/admin/ai-usage`; heading level 1 "AI usage"; link "AI usage" in admin navigation. Combobox "Feature" options exactly "All features", "Student assistant (STU-03)", "Teacher generation (TEA-02)", "Feedback analysis (ADM-03)". Labelled date inputs "Start date (UTC)" and "End date (UTC)". Buttons "Apply filters" and, on recoverable report error, "Retry". Table accessible name "AI usage by feature". Column headers "Feature", "Requests", "Failures", "Rate-limit failures", "Other failures", "Input tokens", "Output tokens", "Total tokens". Row labels match feature option labels. Coverage text per row "Collection started: TIMESTAMP" or "Collection is not enabled for this feature."; use response timestamp verbatim. Unavailable cell text and reason are visible accessible plain text; no tooltip-only explanation. Counts use base-10 ungrouped numerals, no percentages.

Loading/empty messages are role status; failures role alert, with exactly the spec messages. Reason mapping: incomplete_coverage => "Coverage does not include the whole period."; not_enabled => "Collection is not enabled for this feature."; pending_attempts => "Some service calls have not finished recording."; missing_measurement => "The provider did not supply this measurement for every call."; no_measurements => "No recorded token measurements in this period." Caption and period text exactly as specified. A horizontally scrollable table has accessible region name "AI usage results"; controls remain inside narrow viewports and keyboard usable. No motion required.

- Requests per load and per retry: one GET after session resolution per route/history activation, valid Apply filters, or Retry; no development duplicate calls, polling, automatic retry or validation-error request. Pending disables action buttons. Retry captures last applied filters, not unsent edits.
- Wrong role: student/teacher route visit uses existing role-home replace redirect without report request; server 403 is exact access alert without Retry.
- Link history: push or replace: navigation link pushes; filters/Retry have no URL change; role/expiry redirects replace. No filter query parameters in page URL.
- No generic failure message: each 401/403/422/429/503/network/timeout/invalid-report state maps exactly to the spec table, not a blanket catch message.
- Refresh: default seven UTC dates, clear all prior data and one new GET after authentication.
- Back and Forward: default filters and a fresh GET on every history entry; no private stale cache.
- Expired session or logout: inherit existing Confirm logout and shared 401 handling; clear private report on actual session end, keep session/dialog on logout failure; reject superseded account/filter response generations.
- Backend down: preserve fields and show actual network error or HTTP 503 message; Retry performs one request.
- Longest wait before an error: 15-second abort per report request; exact timeout message, no automatic retry.

## AI usage

Reporting sends no prompts and consumes no SoC calls. Instrument existing application calls only; retain quotas, input/output caps, models and retry policy. Record every actual retry independently, including provider failures. Local limiter rejections do not count as provider attempts. Do not infer tokens from text length, requested caps, character counts, timing or assumed sums. Proposed source mapping is explicit numeric counters returned by SoC; unknown schema means unavailable until an approved documented mapping. Tests mock provider calls and never use live quota. Content-level failure remains ADM-01 scope.

## Test plan

Independent tests named with ADM-06/adm06; write from contract before implementation, isolated worktree at approved start commit. AC1: mocked success/retry/429/timeout and hidden-retry interception; local quota/validation rejection has no row. AC2/3: exact counts, TEA-02 note/MCQ grouping, UTC boundaries, features and 31-day filter limit. AC4: complete zero vs preactivation/gap/disabled/database outage/pending, restart persistence and metadata-write failure, and crash after reservation before dispatch makes request totals unavailable instead of counting a presumed call. AC5: adversarial credential/prompt/completion/exception strings absent from schema, DB metadata and report; non-admins cannot access aggregates. AC6: no outcome percentages in API/UI. AC7-9: independent explicit token fields including zero, absent/malformed/negative/bool/overflow and partial coverage; never derive total. AC10: unauthenticated/student/teacher/disabled/archived/expired-session API and UI guards, cross-account delayed response/cache tests. AC11: simultaneous finalisers, identical/conflicting replay, request cutoff and snapshot during concurrent completion; strict/duplicate/unknown filter inputs; migration over populated database. AC12: all existing provider call paths including retries observed, reservation failure prevents transport, finalisation failure pending, activation across restarts/unsupported features. AC13: all visible UI states, request counts under StrictMode, 15-second abort, stale filter/account response, navigation history, refresh, logout confirmation and narrow viewport/keyboard tests; report reading never invokes AI. Report throttle 30/60s gets a dedicated mocked-clock test.

Record applicable privacy/auth/input/rate-limit/concurrency security outcomes in workflow/security/test-log.md through orchestrator. Verifier re-runs suites and checks shared safeguards were retained. Backend pytest; frontend browser tests/typecheck/lint/build as configured. Do not weaken tests for contract mismatches; amend contract through human approval if needed.

## Decisions

Approved by user in chat on 2026-11-06: UTC inclusive date filters (max 31 days), feature-level combined TEA-02, three allowlisted features with ADM-03 explicitly unavailable, forward-only coverage activated after coordinated restart, durable fail-closed pre-dispatch recording, independent provider token counters only, no retention pruning and no new provider retry policy. Exact existing symbol names/provider usage mapping require source-aware integration amendment before developer/test-designer starts; spec-writer is prohibited from reading implementation. Subject/upload/scoring/feedback identity decisions are outside this metadata-only contract. Human approval of spec/plan is a required build gate, not implied by this draft.


## Source-aware compatibility amendment (2026-11-06)

Orchestrator inspected existing interfaces after approval, before implementation. Reuse `teacher_materials.models.Base`, `auth.db.engine_for`, `auth.settings.load_settings`, `auth.dependencies.current_user(role="admin")`, `auth.rate_limit.admit`, `errors.ApiError`, `practice_routes.error_response` and existing no-store middleware. Error envelope is `{"detail":{"code":"...","message":"..."}}`, not a detail string. Preserve shared auth codes `unauthenticated`/`forbidden` so existing frontend session expiry works; other report codes above remain. A SQLAlchemy failure during auth may use existing safe `service_unavailable` 503; UI maps by status.

Shared transport is `llm_client.SoclaasClient._send` with explicit retry loop and httpx (no SDK hidden retries). Observe immediately around each `_http.post` attempt. A 2xx HTTP response is service success even if subsequent `_parse` or feature validation rejects content; 429 is rate_limit, other non-2xx/transport errors other_failure. Extract usage from response JSON independently of content validation: `usage.prompt_tokens` => input_tokens, `usage.completion_tokens` => output_tokens, `usage.total_tokens` => total_tokens. Require actual nonnegative signed-64-bit integers, excluding bool. Do not change existing LlmReply constructor or infer total. Malformed JSON has unavailable tokens. No live-provider verification claimed.

Preserve `LlmClient.complete(messages, *, max_tokens, caller_id)` and dependency override identity `get_llm_client`, because existing independent fakes use that exact interface. New context manager `llm_client.usage_feature(feature: str)` uses ContextVar with token reset in finally, default STU-03; explicitly wrap companion call as STU-03 and both `teacher_notes.generation.generate_notes`/`teacher_mcqs.generation.generate_mcqs` calls as TEA-02. Do not infer attribution from caller IDs, request payloads or text. Production singleton `get_llm_client` injects database observer; standalone `SoclaasClient` gains optional keyword `observer=None` for isolated transport tests, while production must always pass durable observer. New `ai_usage.observer.DatabaseAttemptObserver` exposes `reserve(feature: str) -> UUID` and `finish(attempt_id: UUID, outcome: str, *, input_tokens=None, output_tokens=None, total_tokens=None) -> bool`, delegating to service functions. Constructor injection accepts same duck-typed interface; no-op only for standalone test clients. Reservation errors map to fixed `LlmUpstreamError` (existing safe 502 service response) without dispatch; no automatic retry on recording failure. Finalisation errors are swallowed content-free leaving pending. False finalisation must not overwrite existing data.

Frontend reuse `services/client.ts` request/session-generation APIs, `auth/RequireRole`, `AuthContext`, existing admin shell. Extend shared request options only as needed for distinct timeout classification and retain all other callers' existing defaults. Use 15 seconds for this route and map malformed JSON separately. Admin routes are composed inside `pages/Admin.tsx`; preserve demo shell behaviour but do not fetch private usage in anonymous demo mode. Demo shows existing sign-in notice rather than fabricated usage. For actual authenticated usage obey exact per-history request contract. Test designers may inspect only test fixtures; supplied names above are the implementation integration contract.


Empty-state clarification (2026-11-06, orchestrator/designer): the global "No AI service calls in this period." status appears only when every selected row has an available request count of zero. Any selected disabled/incomplete/pending row suppresses this global claim; known zero sibling rows still display zero. This applies to All features as well as individual-feature filters.
