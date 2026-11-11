# Plan: ADM-07 Analytics hub

Contract for the developer and the test-designer, who work in parallel without seeing each other. Spec: `spec.md`. Conventions are those of ADM-01 (the removed ADM-01 plan): router prefix `/api/admin/analytics`, error body `{"detail": {"code", "message"}}`, timestamps ISO 8601 UTC with `Z`, `user_id` is `varchar(64)`, `Cache-Control: no-store` from the existing `/api/admin/*` middleware, admin auth via the shared dependency, hooks use `open_session()` and never raise. Where this plan names an existing symbol it comes from the ADM-01/ADM-06 plans; the developer confirms it by reading code and reports differences in `workflow/notes.md` instead of guessing.

## Refinements after Gate E (2026-11-12)
- `PUT /api/admin/ai-usage/coverage` in `ai_usage/routes.py` (model `CoverageIn`, strict, `extra=forbid`) calls `service.activate_coverage` or the new `service.deactivate_coverage` for `service.INTEGRATED` (STU-03, TEA-02). Tests: `tests/test_adm07_coverage_toggle.py` (on/off keeps start, roles, bad bodies, CSRF) and two Playwright tests in `adm07-retained-aiusage.spec.ts`. Frontend: `setCollection` in `services/aiUsage.ts`, state derived from the report in `AiUsageSection.tsx`.
- Success-rate display: `HealthStrip.tsx` (`successPercent`, `SuccessKpi`) and `SeverityChip.tsx`; tests renamed to "Chatbot success rate" and "Generation success rate".
- Click-to-open chart cards, header icon refresh, section and subheader styles, totals cards, table borders, Quality grid: `ChartCard.tsx`, `ChatbotUsersTable.tsx`, `QualitySection.tsx`, `styles.css` (scoped `analytics-hub-*`, `analytics-quality-grid`).
- Dev seed: `dev_seed.py` and `feature_analytics/seed_dev.py` (idempotent through the marker `dev_seed_applied_at` in `analytics_meta`).

## Phases
| Phase | Backend | Frontend |
|---|---|---|
| 2 | `/health`, `/hourly`, `/daily`, `/chatbot-users` read existing tables; `/usage` gains `include_rows` | Whole hub UI; old ADM-01 page moved to `/admin/feature-analytics-legacy` |
| 4 (marked **[P4]**) | Migration for 4 tables; hook extensions; purge; backfill; one-off AI usage cleanup (separate approved command); `/hourly`, `/health` (rate-limited), `/daily` (logins, drafts started, published) switch to the new sources | none (states change from unavailable to real values) |

## Data model
No schema change in phase 2. Reads use existing tables: `analytics_chat_request` (student chatbot rows, `outcome` success|failure|pending, `duration_ms`, `received_at`), `analytics_generation_attempt` (`workflow`, `accepted_at`, `outcome`), `analytics_practice_attempt` (`attempt_ref`, `user_id`, `started_at`, `submitted_at`), `analytics_meta`.

### **[P4]** Migration `20261111_adm07_events` (`down_revision` = the single Alembic head at the start of phase 4; the developer reads `alembic heads`). Four new tables.
| Table | Columns | Constraints and indexes |
|---|---|---|
| `analytics_request_log` | `id bigserial PK`, `kind text not null` (`chatbot`\|`generation_notes`\|`generation_mcq`), `source_id bigint null` (id of the chat request or generation attempt; `null` for rate-limited generation requests that created no attempt), `occurred_at timestamptz not null` (request receipt / acceptance time), `outcome text not null default 'pending'` (`pending`\|`success`\|`failure`), `failure_category text null` (`timeout`\|`rate_limited`\|`invalid_output`\|`upstream`\|`unclassified`), `duration_ms integer null`, `created_at timestamptz not null default now()` | `CHECK ((outcome IN ('pending','success') AND failure_category IS NULL) OR (outcome='failure' AND failure_category IS NOT NULL))`; a `pending` row is never rewritten by the read path (in-progress rule below); partial unique index `(kind, source_id) WHERE source_id IS NOT NULL`; index `(occurred_at)`. No user id, no text. |
| `analytics_login_event` | `id bigserial PK`, `user_id varchar(64) not null FK users`, `role text not null` (`student`\|`teacher`), `occurred_at timestamptz not null` | `CHECK (role IN ('student','teacher'))`; index `(occurred_at)`, `(user_id, occurred_at)`. No IP, user agent or email. One row per successful student or teacher sign-in; admins are not recorded. |
| `analytics_practice_draft_started` | `practice_set_id text PK` (1 to 100 chars), `teacher_id varchar(64) not null FK users`, `started_at timestamptz not null` | index `(started_at)`. Insert-if-absent: first save of a new practice set only. Never deleted when the set is edited, published or removed. |
| `analytics_practice_published` | `practice_set_id text PK` (1 to 100 chars), `teacher_id varchar(64) not null FK users`, `published_at timestamptz not null` | index `(published_at)`. Insert-if-absent: first transition to the published state only; unpublish and republish never update, delete or add a row. |
| `analytics_meta` rows (existing table) | keys `request_log_started_at`, `login_events_started_at`, `practice_draft_started_started_at`, `practice_published_started_at`, `request_log_categories_started_at` (ISO 8601 UTC; all set to the migration time, except `request_log_started_at`, which is the later of ADM-01 `recording_started_at` and the backfill floor `migration time - 30 days`, so backfilled history counts; and the draft/published keys, which may be the earliest backfilled time). Amendment 2026-11-11 by the orchestrator after verifier round 1 (plan line contradicted the backfill); to be confirmed at Gate E | `recording_started_on` of the new metrics is the UTC date of these values |

Migration steps in order: create tables; insert meta keys; **backfill** `analytics_request_log` from rows of `analytics_chat_request` (kind `chatbot`) and `analytics_generation_attempt` (kind by workflow) with time `>= now() - interval '30 days'` and any outcome (`pending` rows are copied as `pending`; the read-time rule then expires old ones as `timeout`) (`INSERT ... ON CONFLICT DO NOTHING`; failures get `failure_category='unclassified'`; `source_id` = the source row id); if existing practice-set rows carry a first-save time and a first-publication time, backfill `analytics_practice_draft_started` and `analytics_practice_published` from them (developer check; if a time is not stored, no backfill for that table and its start key is the migration time). Downgrade drops the four tables and deletes the five meta keys. The backfill never touches source tables.

`request_log_categories_started_at` marks the date from which categories are real; before it, failures are `unclassified` (the hourly category breakdown stays available but the rate-limited tile uses the coverage rule below).

Retention (decided): `PURGE_REQUEST_LOG_DAYS = 30` and `PURGE_LOGIN_EVENT_DAYS = 400` in `feature_analytics/config.py`. Draft-started and published rows are kept (as long as attempts).

### In-progress rule (applied at read time, never written)
Constant `IN_PROGRESS_EXPIRY_S = 120` in `config.py`. Shared query helper `finished_state(outcome, received_at, now)` used by every query that counts chatbot or generation requests (`health_*`, `hourly`, `chatbot_users`; phase 2 on `analytics_chat_request`/`analytics_generation_attempt`, phase 4 on `analytics_request_log`): `success`/`failure` rows are finished as stored; a `pending` row with `now - received_at < 120 s` is **in progress** (excluded from rates, counts, percentiles and buckets, and counted in the response's `in_progress`); a `pending` row with `now - received_at >= 120 s` is a **failure with category `timeout`** (phase 2: `unclassified`, since the breakdown is unavailable) with duration 120 000 ms, counted in its received hour. `now` is one server timestamp taken at the start of the request and returned as `as_of`, so tile, charts and table of one request agree; tests fix it by monkeypatching `feature_analytics.queries.utcnow`. A late outcome hook call still updates a `pending` row (first outcome wins), so a request first shown as timeout can later show its real outcome. Generation attempts are recorded together with their outcome after the AI call, so `in_progress` for generation is 0.

### Window rule and coverage
`window_start = period_start 00:00:00 UTC`, `window_end = (period_end + 1 day) 00:00:00 UTC`; a row is in the period if `effective_start <= ts < window_end`, where `effective_start = max(window_start, <source>_started_on 00:00 UTC, retention floor for hourly data and the rate-limited tile)`. **Partial coverage (decided, replaces the ADM-01 whole-metric rule):** if `effective_start > window_start` the metric is computed over `[effective_start, window_end)` and the response carries `data_starts_on` = the UTC date of `effective_start` (else `null`); only if `effective_start >= window_end` is the metric `unavailable` with `period_before_recording` (source start) or `beyond_retention`. The source start is `recording_started_on` (existing tables, chat/generation/attempt metrics and, in phase 2, hourly), the login/draft-started/published/request-log keys (phase 4 metrics); the retention floor is `date_trunc('hour', now() - 30 days)`. Dense arrays (`buckets`, `per_day`) start at `effective_start`. This applies to `/health`, `/hourly`, `/daily`, `/chatbot-users` and, for `/usage`, `/generation` and `/quality` counts and times, to the kept endpoints (they gain the same `data_starts_on` field; the old behaviour was whole-metric unavailable and its tests are updated by the test-designer, assertions otherwise unchanged). `/api/admin/ai-usage` is unchanged and keeps its stricter rule (any part of the period before coverage, or touching a gap, is unavailable); see "AI usage cleanup" below.

### **[P4]** AI usage cleanup (one-off, destructive, human-approved; decided: delete completely, no archive)
Purpose: remove the older incomplete ADM-06 records that keep recent periods unavailable. It is **not** an Alembic revision (Alembic runs automatically on deploy); it is an explicit command in the migration phase, same pattern as `ai_usage.activate`: `uv run python -m ai_usage.cleanup --dry-run` and `uv run python -m ai_usage.cleanup --apply --approved-by <name>`. There is no `--restore` and no backup or archive table; the deletion is permanent.
- **Tables touched** (names from the ADM-06 plan; the developer confirms them in code): `ai_service_attempts` and `ai_usage_coverage`. No other table.
- **Cut-off** `C = run time (UTC) - 24 hours` (constant `AI_USAGE_STALE_PENDING_HOURS = 24` in `ai_usage/cleanup.py`). Attempts newer than `C` are never touched (they may still be in flight).
- **Deleted:** every row of `ai_service_attempts` with `outcome = 'pending'` and `started_at < C` (reservations that never finished and can never be resolved). Terminal rows (`success`, `rate_limit`, `other_failure`) are never deleted.
- **Coverage rows:** for each feature with at least one deleted row or a non-null `incomplete_since`: set `incomplete_since = NULL` and `covered_since = max(existing covered_since, the next UTC midnight after the run time)`. A coverage start is never moved earlier, `enabled` is unchanged. Periods starting before the new `covered_since` stay unavailable (the stricter ADM-06 rule is unchanged); recorded terminal rows before it stay in the table but cannot appear in a report.
- **Dry run:** changes nothing and prints, per feature: the cut-off, the number of `pending` rows that would be deleted, the oldest and newest `started_at` among them, the current and the would-be `covered_since` and `incomplete_since`. `--apply` re-computes the same numbers, prints them, and runs only if `--approved-by` is given (non-empty) and the transaction deletes exactly rows matching the criteria; it prints the deleted counts and writes one log line (counts and approver, no row content).
- **Atomic and idempotent:** one transaction; a second run finds nothing to delete and leaves coverage unchanged.
- **Approval step:** the developer implements and tests the command but never runs `--apply` on a real database; the human reviews the dry-run output (task P4-10) and runs or authorises `--apply`. Tests run it only against a test database.
- **Irreversible:** the deleted rows cannot be restored by the application. Operator-owned database backups, if any, are outside this plan and are not claimed.

Reasons added to the ADM-01 set (`period_before_recording`, `no_source`, `read_failed`; `no_practice_attempts`, `no_generation_attempts`, `no_eligible_records`, `none_graded`): unavailable `not_collected`, `beyond_retention`; not applicable `no_chat_requests`.

Metric state shape (all new endpoints): `{"state": "available"|"not_applicable"|"unavailable", "reason": null|"<code>", ...fields}`. Unavailable: all numbers `null` and arrays `[]`. Not applicable: averages, rates and percentages `null`, known counts still present.

## API endpoints
All `GET`; role admin only; query `period_start` and `period_end` (`YYYY-MM-DD`) unless stated.

### Kept, extended or new
| Endpoint | Status | Change |
|---|---|---|
| `GET /api/admin/analytics/usage` | **extended** | Adds `data_starts_on`; optional `include_rows` (`true`\|`false`, default `true`; any other value 422 `invalid_include_rows`). With `false` the `rows` arrays are `[]` and `rows_truncated` `false`; everything else identical. The hub does not call it; it stays for the old screen until phase 5. |
| `GET /api/admin/analytics/generation` | **extended** | Adds `data_starts_on` (partial coverage). **[P4]** each workflow entry gains `rate_limited` (count of limiter-refused requests from the request log) and `requests = attempts + rate_limited`; `unsuccessful = requests - successful`; `rate_percent = successful/requests`; `attempts` keeps its old meaning (accepted attempts). Phase 2: `rate_limited` is `null`, `requests = attempts`, entry `rate_limited_state: {"state":"unavailable","reason":"not_collected"}`. Zero requests: `not_applicable`/`no_generation_attempts`. |
| `GET /api/admin/analytics/quality` | **extended** | Adds `data_starts_on` (partial coverage); otherwise none (hub Quality section; includes `grades.privacy_mode`, `grades.privacy_blocked_count` and `active_run` as implemented by the ADM-01 privacy amendment) |
| `POST /api/admin/analytics/grading-runs`, `GET /api/admin/analytics/grading-runs/{run_id}` | **kept** | none |
| `GET /api/admin/ai-usage` (ADM-06) | **kept** | none; hub calls it with `feature`, `start_date`, `end_date` |
| `GET /api/admin/analytics/health` | **new (phase 2; rate-limited tile real in P4)** | below |
| `GET /api/admin/analytics/hourly` | **new (phase 2 reads union of existing tables; P4 reads `analytics_request_log`)** | below |
| `GET /api/admin/analytics/daily` | **new (phase 2: funnel and attempts per student; P4: logins, drafts started, published)** | below |
| `GET /api/admin/analytics/chatbot-users` | **new (phase 2)** | below |

### Errors (new codes; ADM-01 period codes unchanged)
| Code | Status | Message | When |
|---|---|---|---|
| `invalid_date`, `period_order`, `period_too_long` | 422 | as ADM-01 (`Enter dates as YYYY-MM-DD.`, `The start date must be on or before the end date.`, `The period can be at most 366 days.`) | period rules |
| `invalid_role` | 422 | `Choose student or teacher.` | `role` missing or other after trimming and lower-casing |
| `invalid_sort` | 422 | `Choose a valid sort column and order.` | `sort` not in `unsuccessful`,`successful`,`name`,`failure_rate`, or `order` not in `asc`,`desc` |
| `invalid_paging` | 422 | `limit must be 1 to 100 and offset must be 0 or more.` | as ADM-01 |
| `invalid_include_rows` | 422 | `include_rows must be true or false.` | `/usage` only |

Validation order: dates, order, span, role, sort and order, paging, include_rows. First failing rule wins. 401 and 403 from the shared dependency before any validation.

### `GET /api/admin/analytics/health`
200:
```json
{
  "period_start": "2026-11-05", "period_end": "2026-11-11",
  "recording_started_on": "2026-11-09", "data_starts_on": "2026-11-09", "as_of": "2026-11-11T09:30:00Z",
  "low_sample_threshold": 20,
  "chatbot_failure": {"state": "available", "reason": null, "total": 120, "failed": 9,
                      "in_progress": 1, "rate_percent": 7.5, "severity": "critical"},
  "generation_failure": {"state": "available", "reason": null, "total": 30, "failed": 1,
                         "in_progress": 0, "includes_rate_limited": false,
                         "rate_percent": 3.3, "severity": "warning"},
  "rate_limited": {"state": "unavailable", "reason": "not_collected", "since": null,
                   "count": null, "total_requests": null},
  "chatbot_response_time": {"state": "available", "reason": null,
    "all": {"count": 120, "median_ms": 2100, "p95_ms": 5400},
    "successful": {"count": 111, "median_ms": 2000, "p95_ms": 4100},
    "failed": {"count": 9, "median_ms": 120000, "p95_ms": 120000}},
  "generation_response_time": {"state": "available", "reason": null,
    "all": {"count": 30, "median_ms": 14200, "p95_ms": 31800},
    "successful": {"count": 29, "median_ms": 14000, "p95_ms": 30000},
    "failed": {"count": 1, "median_ms": 31800, "p95_ms": 31800}},
  "practice_completion": {"state": "available", "reason": null,
                          "started": 10, "submitted": 7, "percentage": 70.0}
}
```
- Top-level `data_starts_on` is the latest `data_starts_on` of the tiles (each tile object also carries its own `data_starts_on`, omitted above for brevity when `null`). All tiles use one `as_of` and the in-progress rule.
- `chatbot_failure`: `total` = finished student chat requests in the period (any activity type; success plus failure plus expired pending as `timeout`; in-progress excluded and returned in `in_progress`); `failed` = unsuccessful; `rate_percent = round_half_up(failed*100/total, 1)`; `severity` in `low_sample` (total < 20), `critical` (`failed*100 > 5*total`), `warning` (`2*total <= failed*100 <= 5*total`), `ok`; `severity` and `rate_percent` are `null` when `total = 0` (`not_applicable`/`no_chat_requests`).
- `generation_failure`: same over generation requests (both workflows). Phase 2: `analytics_generation_attempt` only, `includes_rate_limited: false`. **[P4]** (decided change to ADM-01-02): accepted attempts plus limiter-refused requests, read from the request log kinds `generation_notes`/`generation_mcq`, `includes_rate_limited: true`; zero requests is `not_applicable`/`no_generation_attempts`.
- `rate_limited`: phase 2 `unavailable`/`not_collected`. **[P4]** `count` = finished request-log rows (chatbot and generation) with `failure_category='rate_limited'` in the effective window, `total_requests` = all finished request-log rows there, `since` = date of `request_log_categories_started_at` (partial coverage from that date, `data_starts_on`); `unavailable` only when the whole period is earlier than `since` or past retention. Count 0 is `available`.
- `chatbot_response_time` and `generation_response_time` (same shape, computed separately, never mixed): over finished requests of that workflow (chatbot: `analytics_chat_request` or, in phase 4, request-log kind `chatbot`; generation: `analytics_generation_attempt` or, in phase 4, kinds `generation_notes` and `generation_mcq`) that have a non-null `duration_ms`. Three sets: `successful` (outcome success), `failed` (outcome failure, including rate-limited and other failures with a recorded duration, plus expired pending rows as timeouts at 120 000 ms) and `all` (their union, so `all.count = successful.count + failed.count`); in-progress rows and rate-limited generation rows (null duration) are in no set. Each set is `{"count", "median_ms", "p95_ms"}`: `median_ms` as ADM-01 (integer, half up); `p95_ms` nearest-rank: sort ascending, take element at 1-based position `ceil(0.95*n)`; an empty set has `count` 0 and both `null` (UI: "No requests"). The object `state` is `available`, or `unavailable` (coverage) or `read_failed` as for other metrics; an empty `all` set is `not_applicable` with reason `no_chat_requests` (chatbot) or `no_generation_attempts` (generation) and the three sets still present with count 0. Query functions: `health_chatbot_response_time(db, window)` and `health_generation_response_time(db, window)`.
- `practice_completion`: identical object to `/usage.practice_completion`.
- Each metric is computed separately; a raising query makes only that metric `unavailable`/`read_failed`. Coverage rule applies per metric.

### `GET /api/admin/analytics/hourly`
200:
```json
{
  "period_start": "...", "period_end": "...", "recording_started_on": "...",
  "data_starts_on": null, "as_of": "2026-11-11T09:30:00Z", "in_progress": 0,
  "state": "available", "reason": null, "retention_days": 30,
  "category_breakdown": {"state": "unavailable", "reason": "not_collected"},
  "totals": {"successful": 90, "failed": 6, "total": 96},
  "buckets": [
    {"hour_start": "2026-11-09T00:00:00Z", "successful": 3, "failed": 1, "total": 4,
     "failure_rate_percent": 25.0,
     "failed_by_category": {"timeout": 0, "rate_limited": 0, "invalid_output": 0, "upstream": 0, "unclassified": 1}}
  ]
}
```
- Dense: exactly one bucket per UTC hour from `effective_start` (see coverage rule) to `window_end` exclusive, ordered ascending (24 per day, at most 744), zero-filled; `failure_rate_percent = round_half_up(failed*100/total, 1)`, `null` when `total = 0`; `total = successful + failed`.
- Counts finished requests (success, failure, and pending older than 120 s as `timeout` failures; in-progress excluded and returned in top-level `in_progress`), chatbot and generation together, using the same in-progress rule and `as_of` as `/health`. Phase 2 source: `analytics_chat_request` (by `received_at`) plus `analytics_generation_attempt` (by `accepted_at`); all failures counted in `unclassified`. **[P4]** source: `analytics_request_log` by `occurred_at`, categories real; rate-limited generation requests included.
- `category_breakdown`: phase 2 `unavailable`/`not_collected` (the `failed_by_category` object is still present, all failures under `unclassified`); **[P4]** `available`. Sum of `failed_by_category` equals `failed`.
- States: `unavailable`/`period_before_recording` or `beyond_retention` only when the whole period is earlier (buckets `[]`, totals `null`); otherwise partial coverage sets `data_starts_on`; no requests in an otherwise available period stays `available` with all zeros (the UI shows its empty state when `totals.total = 0`).

### `GET /api/admin/analytics/daily`
200:
```json
{
  "period_start": "...", "period_end": "...", "recording_started_on": "...",
  "logins": {"state": "unavailable", "reason": "not_collected", "since": null,
             "per_day": [], "total_logins": null},   // available example per_day entry below
  "practice_drafts_started": {"state": "unavailable", "reason": "not_collected", "since": null,
                              "per_day": [], "total": null},
  "practice_published": {"state": "unavailable", "reason": "not_collected", "since": null,
                         "per_day": [], "total": null},
  "attempts_funnel": {"state": "available", "reason": null, "started_total": 10, "submitted_by_period_end": 7,
                      "per_day": [{"date": "2026-11-09", "started": 3, "submitted": 2}]},
  "attempts_per_student": {"state": "available", "reason": null,
    "per_day": [{"date": "2026-11-09", "active_students": 2, "median_attempts": 1.5,
                 "distribution": {"1": 1, "2": 1, "3": 0, "4": 0, "5_plus": 0}}]}
}
```
- `per_day` is dense: one entry per UTC date in the period, ascending. `logins.per_day` entries: `{"date": "2026-11-09", "student_logins": 12, "teacher_logins": 3, "total_logins": 15, "active_students": 8, "active_teachers": 2, "active_users_total": 10}` (`active_users_total` = distinct student and teacher users that day; admins are not recorded and never appear); `practice_drafts_started.per_day`: `{"date", "drafts_started"}`; `practice_published.per_day`: `{"date", "published"}`. Every metric object also carries `data_starts_on` (`null` or the first covered date); `per_day` starts at the metric's own effective start.
- `attempts_funnel`: `started` by `started_at` date, `submitted` by `submitted_at` date (UTC), from `analytics_practice_attempt`; `started_total` = attempts started in the period; `submitted_by_period_end` = of those, submitted before `window_end` (ADM-01 AC8-AC9); none started: `not_applicable`/`no_practice_attempts` with `per_day` still dense and zero except submitted counts from earlier-started attempts.
- `attempts_per_student`: per UTC day, group attempts by `started_at` date and `user_id`; `active_students` = distinct users; `median_attempts` = median of per-student counts (mean of two middle values, one decimal), `null` if `active_students = 0`; `distribution` buckets of students by count (`1`,`2`,`3`,`4`,`5_plus`); no attempt started in the period: `not_applicable`/`no_practice_attempts`.
- **[P4]** `logins`: from `analytics_login_event`, per UTC day `student_logins`/`teacher_logins` = events by `role`, `total_logins` their sum, `active_students`/`active_teachers` = distinct `user_id` per role, `active_users_total` = distinct `user_id` overall (admin events do not exist); `since` = date of `login_events_started_at`; partial coverage; none in the period: `available` with zeros. `practice_drafts_started`: from `analytics_practice_draft_started` by `started_at` UTC date (each practice set counted once, on its first save); `practice_published`: from `analytics_practice_published` by `published_at` UTC date (each set counted once, on its first publication; unpublish and republish change nothing). The two are independent series; a set can appear in both on the same day.

### `GET /api/admin/analytics/chatbot-users`
Query: `period_start`, `period_end`, `role` (`student`\|`teacher`), `sort` (default `unsuccessful`), `order` (default `desc`), `limit` (default 10, 1 to 100), `offset` (default 0). 200:
```json
{
  "period_start": "...", "period_end": "...", "recording_started_on": "...",
  "data_starts_on": null, "as_of": "2026-11-11T09:30:00Z", "in_progress": 1,
  "role": "student", "state": "available", "reason": null,
  "totals": {"successful": 120, "unsuccessful": 9},
  "all_users_total": {"state": "unavailable", "reason": "no_source", "successful": null, "unsuccessful": null},
  "sort": "unsuccessful", "order": "desc", "limit": 10, "offset": 0, "total_users": 23,
  "rows": [{"user_id": "u-3f9a1c2b", "name": "Alice Tan", "successful": 5, "unsuccessful": 4, "failure_rate_percent": 44.4}]
}
```
- Rows only for users with at least one request in the period (student rows exist; finished requests only: expired pending counts as unsuccessful, in-progress is excluded and returned as top-level `in_progress`; a user whose only requests are in progress has no row). `failure_rate_percent = round_half_up(unsuccessful*100/(successful+unsuccessful), 1)`. `name` is the display name or `null`.
- Sorting: primary column per `sort` (`name` case-insensitive, nulls last) in `order`; ties by `name` ascending (case-insensitive, nulls last) then `user_id` ascending. `failure_rate` ties are broken by `unsuccessful` descending first.
- `role=teacher`: `state: "unavailable"`, `reason: "no_source"`, `totals` `{"successful": null, "unsuccessful": null}`, `rows: []`, `total_users: null`; no table is queried. `all_users_total` is `available` only when both roles are available (so unavailable/`no_source` while no teacher chatbot exists). Partial coverage applies to `student` (`data_starts_on`; unavailable/`period_before_recording` only if the whole period is earlier).
- `totals` cover all users, not just the page.

## Components and modules
### Backend (`src/backend/feature_analytics/`, existing package)
| File | Change |
|---|---|
| `routes.py` | add the four GET routes; `/usage` gains `include_rows`; routes call `queries.<function>` through the module (so tests can replace it) |
| `schemas.py` | response models for the four endpoints |
| `health.py` (new) | `severity(failed: int, total: int, threshold: int = 20) -> str \| None` (returns `low_sample`, `critical`, `warning`, `ok`; `None` if `total == 0`), `percentile_nearest_rank(sorted_values: Sequence[int], pct: int) -> int \| None`, `round_half_up(value: float \| Decimal, places: int) -> float` |
| `queries.py` | new functions `health_chatbot(db, window)`, `health_generation(db, window)`, `health_rate_limited(db, window)`, `health_chatbot_response_time(db, window)`, `health_generation_response_time(db, window)`, `hourly(db, window)`, `daily_logins(db, window)`, `daily_practice_drafts_started(db, window)`, `daily_practice_published(db, window)`, `finished_state(outcome, received_at, now)` (in-progress rule, `health.py`), `daily_attempts_funnel(db, window)`, `daily_attempts_per_student(db, window)`, `chatbot_users(db, window, role, sort, order, limit, offset)`; existing `practice_completion` reused for `/health` (DRY) |
| `periods.py` | reuse `parse_period`; add `parse_chatbot_users_query(role, sort, order, limit, offset)` raising the feature errors |
| `config.py` | add `LOW_SAMPLE_REQUESTS=20`, `CRITICAL_PERCENT=5`, `WARNING_PERCENT=2`, `HOURLY_RETENTION_DAYS=30`, `LOGIN_RETENTION_DAYS=400`, `PURGE_INTERVAL_S=3600`, `PURGE_BATCH=5000`, `CHATBOT_USERS_DEFAULT_LIMIT=10` |
| **[P4]** `models.py` | models for the three tables |
| **[P4]** `recording.py` | hook extensions below |
| **[P4]** `retention.py` (new) | `purge_expired(now: datetime \| None = None) -> dict[str, int]` deletes request-log rows older than 30 days and login events older than 400 days in batches of `PURGE_BATCH`; called at app startup and at most once per `PURGE_INTERVAL_S` per process from the outcome hooks (monotonic check); never raises |
| **[P4]** `alembic/versions/20261111_adm07_events.py` | migration above |

### **[P4]** Hook contract (extends ADM-01 `recording.py`; same rules: keyword arguments, own `open_session()`, never raise, no content logged)
```python
FAILURE_CATEGORIES = ("timeout", "rate_limited", "invalid_output", "upstream", "unclassified")
def categorize_llm_error(exc: BaseException) -> str: ...   # mapping of spec AC34
def record_chat_request_outcome(request_id: int | None, *, success: bool,
        grading: "GradingContent | None" = None, completed_at: datetime | None = None,
        failure_category: str | None = None) -> None: ...        # extended
def record_generation_outcome(attempt_id: int | None, *, success: bool,
        grading: "GradingContent | None" = None, completed_at: datetime | None = None,
        failure_category: str | None = None) -> None: ...        # extended
def record_generation_rate_limited(*, workflow: str, occurred_at: datetime | None = None) -> None: ...   # new
def record_login(*, user_id: str, role: str, occurred_at: datetime | None = None) -> None: ...            # new
def record_practice_draft_started(*, practice_set_id: str, teacher_id: str,
        started_at: datetime | None = None) -> None: ...                                                  # new
def record_practice_published(*, practice_set_id: str, teacher_id: str,
        published_at: datetime | None = None) -> None: ...                                                # new
def purge_expired_request_log(now: datetime | None = None) -> int: ...   # thin wrapper of retention.purge_expired for the request log
```
- `record_chat_request_received` and `record_generation_accepted` also insert the `pending` request-log row (same transaction as their own row; `source_id` = the new request/attempt id). The two outcome hooks, in the same transaction that sets the outcome (first outcome only: `UPDATE ... WHERE outcome='pending'`; repeats change nothing), update that row (`outcome`, category, `duration_ms`). On `success=True` the category is ignored (stored `null`); on `success=False` a missing or unknown category is stored `unclassified`.
- `record_generation_rate_limited` inserts a request-log row only (`source_id` null, outcome `failure`, category `rate_limited`, kind from workflow: `study_notes`→`generation_notes`, `mcq_batch`→`generation_mcq`); invalid workflow returns without a write. It creates no generation attempt and no grading item.
- `record_login` accepts `role` in `student`,`teacher` only (any other role, including `admin`, is a no-op); `record_practice_draft_started` and `record_practice_published` are each `INSERT ... ON CONFLICT (practice_set_id) DO NOTHING` on the table's primary key, which is how once-per-set is enforced in the database even under concurrent calls (decided: "Published" counts once per set, on its first publish only; unpublish and republish add nothing, and the hook for a republish is a no-op because the row exists). The host call sites call `record_practice_published` on every transition to the published state, not only the first; the primary key makes the repeats harmless. No update or delete path exists for either table.
- Host call sites (developer finds exact lines; behaviour of the host routes must not change): the student companion route passes `failure_category=categorize_llm_error(exc)` in its error paths and `None` on success; the two TEA-02 routes' existing `finally` block passes the category of the exception that ended the call; their `except (LlmRateLimited, LlmBusy)` branch additionally calls `record_generation_rate_limited(workflow=...)` before re-raising (the existing "not an attempt" rule is untouched); the sign-in route calls `record_login(user_id=..., role=...)` after the session is created (not on `/me` or session bootstrap, not on failed sign-in); the teacher practice-set save route calls `record_practice_draft_started(...)` after the commit of a set's first save (calling it on every save is harmless); the publish route calls `record_practice_published(...)` after its commit on each transition to published. If creating a set already published is possible, both are called.

### Reused shared modules
Shared SoC LLM client and `usage_feature`, `auth.dependencies` admin dependency, `auth.db.open_session`, `errors.ApiError`, `queries.practice_completion`, `periods.parse_period`, `ai_usage` package (unchanged), existing grading code (unchanged).

### Frontend (`src/frontend/src`)
- `pages/AdminAnalytics.tsx` is replaced by the hub shell (header, period, section layout, wrapper that redirects anonymous visitors like `LiveAnalysis`). The previous ADM-01 page file is moved unchanged to `pages/AdminFeatureAnalyticsLegacy.tsx` and routed at `/admin/feature-analytics-legacy` (no nav link; Open question 2). `pages/AdminAiUsage.tsx` and its route stay.
- New `components/analytics/`: `PeriodSelector.tsx`, `CustomRangeDialog.tsx`, `HealthStrip.tsx`, `KpiTile.tsx`, `SeverityChip.tsx`, `HourlyCharts.tsx`, `ChartCard.tsx`, `ChartModal.tsx`, `RequestsPerHourChart.tsx`, `FailureRateChart.tsx`, `PeakHoursHeatmap.tsx`, `DailyActivity.tsx`, `DailyCard.tsx`, `ChatbotUsersTable.tsx`, `GenerationTable.tsx`, `AiUsageSection.tsx`, `QualitySection.tsx` (moves the ADM-01 quality, grading dialog and progress logic out of the old page; reuse, do not rewrite), `BlockState.tsx` (loading/failure/retry wrapper).
- New `hooks/useAnalyticsBlock.ts`: `useAnalyticsBlock<T>(key, fetcher, deps)` returns `{status: "idle"|"loading"|"success"|"error", data, error, reload}`; owns the AbortController, 15-second timeout, stale-response guard (generation counter) and error classification (`network` \| `timeout` \| `http` with status); no storage.
- New `lib/analyticsTime.ts`: `toLocalBucket(hourStartUtc: string, timeZone: string): {iso: string; weekday: number /* 0 = Monday */; hour: number; label: string}`; `buildHeatmap(buckets: HourlyBucket[], timeZone: string): HeatmapCell[]` (168 cells, `{weekday, hour, total, failed}`). New `lib/csv.ts`: `buildCsv(header: string[], rows: (string | number | null)[][]): string` (CRLF, quotes only when a cell contains `,` `"` or a newline; `null` is empty), `downloadCsv(filename: string, csv: string): void`. New `lib/period.ts`: `resolvePeriod(range: "today" | "7d" | "30d", todayUtc: string)`, `validateCustomPeriod(from, to, todayUtc)` returning one of the four messages or `null`.
- `services/featureAnalytics.ts` gains typed calls `getHealth`, `getHourly`, `getDaily`, `getChatbotUsers`; `services/aiUsage.ts` reused.
- Touched: `App.tsx` (routes), admin nav (`{path: "analytics", label: "Feature Analytics"}`; the demo `Analytics` item and the `AI usage` item are unchanged), `styles.css` (scoped `.analytics-*`), docs.
- Dependencies: none added (Open question 14).

## UI contract
Applies [the shared UI design guide](../../ui-design.md). Copy is exactly the "UI states and copy" table in `spec.md`; this section fixes roles, names, test hooks and behaviour.

Layout: page header; four sections in one column of padded panels; inside Health the KPI strip then the chart cards; reuse theme tokens `--bg --paper --ink --muted --line --blue --blue-soft --green --green-soft`, plus scoped `--analytics-critical`, `--analytics-warning` (values for light and dark that meet 4.5:1 on their backgrounds, verified by the developer). Controls are outlined with persistent labels; tables sit in `overflow-x: auto` containers with `tabindex="0"` named by the table. Mobile 320 to 390 px: header controls wrap under the title, KPI tiles 1 or 2 per row, charts stacked, no page horizontal scroll. Reduced motion: no transitions on charts or modal.

Accessible roles and names (tests use only these and the test ids below):
| Element | Role and name |
|---|---|
| Title | heading level 1 "Feature Analytics" |
| Nav link | link "Feature Analytics" (exact; distinct from link "Analytics") |
| Period select | combobox "Reporting period" (options by text) |
| Custom range | dialog "Custom range"; textboxes found by label "From date", "To date"; buttons "Apply period", "Cancel"; field errors linked by `aria-describedby`, `aria-invalid="true"` on the invalid field |
| Refresh | button "Refresh"; text "Last updated ..." (`time` element) |
| Sections | headings level 2 "Health", "Feature outcomes", "AI usage", "Quality"; regions named the same |
| KPI | group named by the six tile labels ("Chatbot success rate", "Generation success rate", "Rate-limited requests", "Chatbot response time", "Generation response time", "Practice completion"); inside each response-time group a radio group "Chatbot response time outcome" / "Generation response time outcome" with radios "All" (checked by default), "Successful", "Failed" (changing it sends no request; `data-testid="response-time-median"` and `"response-time-p95"` on the two value elements of each tile); chip text as in the spec; severity also as `data-severity="low_sample\|ok\|warning\|critical"` |
| Loading | `status` with the exact text per block ("Loading health...", "Loading hourly charts...", "Loading daily activity...", "Loading chatbot users...", "Loading generation reliability...", "Loading AI usage...", "Loading quality results...") |
| Failure | `alert` with the exact message; button "Retry health", "Retry hourly charts", "Retry daily activity", "Retry chatbot users", "Retry generation reliability", "Retry AI usage", "Retry quality results" |
| Charts | `role="img"` with the names in the spec; Expand buttons "Expand Requests per hour", "Expand Failure rate per hour", "Expand Peak hours" |
| Chart test ids | bar `data-testid="bar-{hour_start ISO UTC}"`; point `data-testid="point-{hour_start ISO UTC}"`; heatmap cell `data-testid="cell-{weekday 0-6 Monday first}-{hour 0-23}"`; reference line `data-testid="reference-5"`; tooltip `role="tooltip"` |
| Modal | dialog named by the chart title; table named "{title} data"; buttons "Download CSV", "Close" |
| Daily cards | groups by title; button "Show data table" / "Hide data table" with `aria-expanded`; tables named "{title} data" |
| Users table | tablist "Role" (tabs "Students", "Teachers"); table "Chatbot requests by user"; buttons "Sort by Name", "Sort by Successful", "Sort by Unsuccessful", "Sort by Failure rate"; `aria-sort` on the active header; buttons "Previous page", "Next page"; text "Showing {from} to {to} of {total} users" |
| Generation | table "Generation success rates" |
| AI usage | combobox "Feature"; table "AI usage by feature"; scroll region "AI usage results" |
| Quality | tablist "Assessment workflow"; tabs "Student exercises", "Teacher lesson planning"; table "Assessed responses"; buttons "Previous page", "Next page" (within Quality), "Grade ungraded responses", dialog "Grade responses with AI?" with "Start grading" and "Cancel"; button "Check progress" |

Duplicate names: "Previous page"/"Next page" occur in two blocks; tests scope them with the region ("Feature outcomes" or "Quality").

CSV contract (UTF-8, CRLF line endings, header row first, chronological order, no byte-order mark):
| Chart | Filename | Header |
|---|---|---|
| Requests per hour | `requests-per-hour_{period_start}_{period_end}.csv` | `hour_utc,hour_local,successful,failed,total,failure_rate_percent,timeout,rate_limited,invalid_output,upstream,unclassified` |
| Failure rate per hour | `failure-rate-per-hour_{period_start}_{period_end}.csv` | `hour_utc,hour_local,requests,failed,failure_rate_percent` |
| Peak hours | `peak-hours_{period_start}_{period_end}.csv` | `weekday,hour_local,requests,failed` |
`hour_utc` is the bucket start `2026-11-09T00:00:00Z`; `hour_local` is ISO with offset, for example `2026-11-09T08:00:00+08:00`; empty cell for `null`; category columns are empty while the breakdown is unavailable; `weekday` is `Monday`..`Sunday`, ordered Monday first then hour 0..23 (168 rows).

Modal behaviour: opens on click or Enter/Space on Expand; `aria-modal="true"`; initial focus on "Close"; focus trap; Esc and backdrop click close; focus returns to the opener; body scroll locked; below 600 px the dialog fills the viewport. 0 requests.

Severity chips: icon (`aria-hidden`) plus the visible words; Low sample uses the neutral muted style.

Per-screen labelled entries (`/admin/analytics`):
- Requests per load and per retry: load, period change, Refresh = 7 parallel GETs (6 when AI usage does not apply); exact URLs: `/api/admin/analytics/health`, `/hourly`, `/daily` (each with `period_start`, `period_end`), `/chatbot-users?role=student&sort=unsuccessful&order=desc&limit=10&offset=0&...`, `/generation`, `/quality?workflow=...&limit=25&offset=0&...`, `/api/admin/ai-usage?feature=all&start_date=...&end_date=...`. Retry = 1. Everything else as in the spec's entry.
- Wrong role: student or teacher redirected with history replace to `homePath(role)`, zero analytics requests; anonymous visitor to `/login` with replace, zero requests; tests assert final URL, that Back does not return, and zero requests to `/api/admin/analytics/*` and `/api/admin/ai-usage`.
- Link history: push or replace: nav link push; preset change push; applied changed custom range push; workflow tab replace; invalid-URL normalisation and redirects replace; nothing else changes the URL.
- No generic failure message: every failure uses its exact message from the spec; the network message only for a fetch rejection that is neither an abort nor the 15-second timeout.
- Refresh, Back and Forward, Expired session or logout, Backend down, Longest wait before an error: exactly as in the spec.
- Query parameters: `range`, `from`, `to`, `workflow`. If both `range` and `from`/`to` are present, `range` wins only if valid, else the custom pair if valid, else default (URL normalised with replace).

## AI usage
No new AI call. The hub reads grading and usage data produced by existing features. Grading (section 4) is unchanged: shared SoC LLM client, `usage_feature("ADM-01")`, caller id `admin-grading:<admin id>`, local privacy gate, 20 items per run, bounds 200/300/900 seconds, no retry. Hourly, daily, health and user endpoints call no AI and send no content to any AI service.

Service limits (observed 2026-11-11, not documented quotas): live tests against the project's gateway with the configured model `qwen3.6:35b` accepted `max_tokens` of 100, 2 000, 5 000, 20 000 and 100 000 (HTTP 200) and a 160 000-character prompt (26 687 prompt tokens); an 8 000-token completion ended with `finish_reason` "length"; no rate-limit or remaining-quota headers were returned; the model list reports a 131 072-token context window. Requests-per-minute and daily quotas were not tested and are unknown. A remembered 2 000 or 5 000 per-request limit was not reproduced; an unconfirmed hypothesis is that reasoning tokens consume the `max_tokens` budget (the repo's `llm_client` handles `finish_reason` "length"). The code and the existing ADM-01 and ADM-06 limits are not changed by these findings. The hub shows no limit or quota as fact; the AI usage block carries the fixed note "Service limits: Unavailable. The SoC LLM service does not report quotas or remaining limits." The Developer Guide records the findings as dated observations (task P2-12).

## Test plan
Backend: `src/backend/tests/test_adm07_*.py`, real PostgreSQL, rows inserted directly with chosen timestamps (helper from the ADM-01 tests), a fixed "now" via monkeypatching the module clock used by retention checks. Frontend: `src/frontend/tests/adm07-analytics.spec.ts` (Playwright, API mocked per URL, `timezoneId` set per test). Existing ADM-01 and ADM-06 tests stay green for the kept endpoints; ADM-01 browser tests are repointed to `/admin/feature-analytics-legacy` (task P2-5; assertions unchanged).

| AC | Test |
|---|---|
| AC1 | 401/403/200 and `no-store` on each new endpoint for anonymous, student, teacher, admin |
| AC2 | Table of invalid inputs: each code, status, message; order (bad date plus bad role gives `invalid_date`); trimming and case of `role`, `sort`, `order`; `limit` 0, 101, `offset` -1, non-integer |
| AC3 **[P4]** | Hooks with `open_session` forced to raise: no exception; host routes (companion, TEA-02, sign-in, practice-set save and publish) still return normal responses |
| AC4 | Seed unique marker text in chat/grading rows; no marker in any new response; request log and login tables have no user-text or IP columns (schema inspection) |
| AC5 | `/health` with a replaced `queries.health_*` that raises: only that metric `read_failed`; coverage rule per metric |
| AC6 | Parametrised severity: (19 of 19) low_sample; (20, 0) ok; (20, 1) warning; (20, 2) critical; (50, 1) warning at 2.0%; (51, 1) ok; (100, 5) warning; (100, 6) critical; (0, 0) null with `not_applicable`; HTTP and unit test of `health.severity` |
| AC7 | Playwright: for each severity the tile shows the chip words and icon; computed contrast of chip text and tile border in both themes meets 4.5:1 and 3:1 |
| AC8 | Chatbot and generation computed separately (a slow generation row does not move the chatbot figures); three sets per workflow: `all.count = successful.count + failed.count`; median and p95 per set (odd/even counts; p95 for n = 1, 20, 21, 100); expired pending rows in `failed` at 120 000 ms; in-progress and null-duration rows in no set; empty set has count 0 and null times; Playwright: radios All/Successful/Failed switch the displayed median and p95 with 0 requests, default All, empty set shows "No requests" (never "0"), selection survives Refresh and resets on reload |
| AC19-AC22 login split | Student and teacher logins counted separately and in total; unique active users per role and distinct total (a user logging in twice counts once); admin login creates no event; `record_login(role="admin")` is a no-op |
| AC42 **[P4]** | Test database only: `--dry-run` deletes nothing and prints counts; `--apply` without `--approved-by` refuses; apply deletes only `pending` rows older than 24 h (rows at 23 h 59 m and terminal rows survive), clears `incomplete_since`, sets `covered_since` to the next UTC midnight and never earlier; second run is a no-op; no backup or archive table exists afterwards |
| AC9 | Practice completion boundary cases (before, in and after the period; none started) |
| AC10 **[P4]** | Request-log rows with categories; count; zero is `available`; before categories start and beyond retention states; phase 2: `not_collected` |
| AC11 | Rows at window start, start minus 1 s, end minus 1 s, end; dense buckets, zero fill, rounding; chat and generation combined; pending excluded; sum of categories equals failed |
| AC12 | Period starting 31 days ago and before recording: states, empty buckets |
| AC13 | Phase 2 categories unavailable; **[P4]** available |
| AC14 | Playwright with timezones `Asia/Singapore` and `America/New_York`: tooltip text, table hour labels and heatmap cell for a known UTC bucket (for example 2026-11-09T16:00:00Z is Tuesday 00:00 in Singapore) |
| AC15 | `reference-5` present only in the failure-rate chart; hover tooltips by test id; empty hour tooltip |
| AC16 | Modal open/close by click, Esc, backdrop; initial focus; Tab and Shift+Tab loop; focus return; background inert; 0 requests |
| AC17 | Download event: filename, header line, row count, a sample row, CRLF, empty cells for null, categories empty when unavailable; 0 requests |
| AC18 | Accessible names of the three images; table content equals chart data; `prefers-reduced-motion` emulation |
| AC19-AC21 | `/daily` seeded attempts across days and users (started on day D, submitted on D+1, even and odd student counts); distribution buckets; day with none; not applicable |
| AC22-AC23 | Phase 2: `not_collected`; **[P4]** `record_login` once per call (two calls two events), role validation, no extra columns; `record_practice_draft_started` and `record_practice_published` idempotent (publish, unpublish, publish again leaves one row with the first time); coverage by own start key; partial coverage `data_starts_on` |
| AC24-AC26 | `/chatbot-users`: default order, each sort and order, ties, paging, totals over all users, users without requests absent, teacher `no_source`, `all_users_total` unavailable; existing `/usage` tests unchanged plus `include_rows=false` |
| AC27 | Existing ADM-01 (generation, quality, grading) and ADM-06 backend tests; hub Playwright checks for the carried strings and tables |
| AC28 | Playwright grading flow ported from ADM-01 (dialog, progress, completion, each failure, strict and scanner states) |
| AC29 | Request counting: exactly 7 (and 6) on load; list by URL; Retry 1; period change 7; tab, sort, page, role, feature 1; zero for modal, CSV, disclosure, unchanged period |
| AC30 | Selector options and URL results (push/replace via history length and Back); custom dialog messages, no request, focus; Refresh disabled while pending; "Last updated" text including partial failure; refresh and Back/Forward restore |
| AC31 | Student, teacher, anonymous redirects with replace and zero requests; 401 mid-session to sign-in; no analytics text after logout and Back |
| AC32 | Keyboard-only run (period, Refresh, Expand, modal, sort, tabs); 320 and 390 px overflow check; light/dark screenshots for success, empty, unavailable and failure |
| AC33-AC34 **[P4]** | Fake LLM errors through the companion and TEA-02 route tests: each exception class gives the mapped category; rate-limited generation: one request-log row, zero attempts, zero grading items |
| AC35 **[P4]** | Rows aged 29 d 23 h and 30 d 1 h: purge deletes only the latter; read ignores unpurged old rows; interval throttle |
| AC36 **[P4]** | Migration test over a populated database: backfill counts, categories `unclassified`, re-run adds nothing, source tables unchanged, downgrade |
| AC37 **[P4]** | Concurrent threads: two outcome calls for one request, two draft-started hooks and two published hooks for one set |
| AC38 | Fixed `utcnow`: pending at 119 s is in progress (excluded from tile, buckets, users table; `in_progress` count), at 120 s is a `timeout` failure in its received hour with 120 000 ms; tile, hourly totals and users totals agree for the same `as_of`; a late outcome replaces the timeout; generation `in_progress` is 0 |
| AC39 | Period starting before the source start and before the retention floor: `data_starts_on` set, arrays start there, banner text in the UI per block; whole period earlier gives `unavailable`; kept endpoints gain `data_starts_on` (ADM-01 coverage tests updated) |
| AC40 **[P4]** | `/generation` and `/health`: `requests = attempts + rate_limited`, rate over requests, rate-limited counted unsuccessful, still no attempt row; phase 2 shows `rate_limited_state` unavailable |
| AC41 | `/daily` `practice_drafts_started` and `practice_published` separately; UI shows two cards |

Security tests: cross-role access (AC1); no private content (AC4); hook isolation (AC3); input validation (AC2); concurrency (AC37). Cross-user task applies to `/chatbot-users` (admin only; non-admin 403). Log results in `workflow/security/`.

## Decisions
- Hub calls seven endpoints so each block fails, retries and tests independently; `/usage` is kept only for the old screen and is removed with it in phase 5 after its criteria move to `/health` and `/chatbot-users` tests.
- Server computes severity and rates so the UI and tests share one definition; the browser computes only local-time bucketing, heatmap aggregation and CSV text.
- Hourly request log has no user id by design; per-user tables use `analytics_chat_request`.
- Open questions in `spec.md` use the defaults stated there until the human decides.
