# Tasks: ADM-07 Analytics hub

Phases follow `workflow/specs/CONSOL-01/migration-plan.md`. Phase 3 (Feedback hub, ADM-08) is a separate feature. Each phase ends at a human gate; tasks of a later phase start only after its gate. Items marked phase 4 are the new event collection.

## Phase 1: specs (this run)
| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| P1-1 | Write spec, plan, tasks; add US-ADM-07-xx and feature entry; mark old ADM-01/ADM-06 text superseded | spec-writer | migration plan approved | done |
| P1-2 | Review specs and answer the open questions | human | P1-1 | todo (Gate B) |

## Phase 2: UI and endpoints on existing data (Gate C: try it in the browser)
| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| P2-1 | Backend tests (incl. AC38 in-progress rule and AC39 partial coverage): `/health`, `/hourly`, `/daily`, `/chatbot-users`, `/usage?include_rows`, validation and auth (AC1, AC2, AC4-AC9, AC11-AC13, AC19-AC21, AC23-AC26); no `src/` access | test-designer | Gate B | done (Gate C passed 2026-11-11) |
| P2-2 | Frontend Playwright tests for the hub: header and period, six KPI tiles (response-time tiles per workflow with All/Successful/Failed selector) and severity, logins split by role, charts, modal, CSV, timezones, daily cards, users table, carried generation/AI usage/Quality/grading states, request counts, history, roles, 401, backend down, timeout, mobile, themes (AC7, AC14-AC18, AC27-AC32) | test-designer | Gate B | done (Gate C passed 2026-11-11) |
| P2-3 | Concurrent-request and cross-user tests for the new read endpoints (non-admin of every role gets 403; two simultaneous Refresh-style loads return consistent data) | test-designer | Gate B | done (Gate C passed 2026-11-11) |
| P2-4 | Backend: `health.py` (severity, percentile, in-progress rule), new queries, partial coverage (`data_starts_on`, also on the kept endpoints), schemas, four routes, `include_rows`, config constants | developer | Gate B | done (Gate C passed 2026-11-11) |
| P2-5 | Update existing ADM-01 coverage tests for partial coverage (test-designer, reasons recorded). Frontend: move the old ADM-01 page to `/admin/feature-analytics-legacy`; test-designer repoints the ADM-01 browser tests to that path (assertions unchanged) | developer, test-designer | Gate B | done (Gate C passed 2026-11-11) |
| P2-6 | Frontend: `useAnalyticsBlock`, `lib/period.ts`, `lib/analyticsTime.ts`, `lib/csv.ts`, services | developer | P2-4 contract | done (Gate C passed 2026-11-11) |
| P2-7 | Frontend: header, period selector, custom range dialog, Refresh and last updated | developer | P2-6 | done (Gate C passed 2026-11-11) |
| P2-8 | Frontend: Health strip, KPI tiles, severity chips | developer | P2-6 | done (Gate C passed 2026-11-11) |
| P2-9 | Frontend: hourly charts, expand modal, CSV | developer | P2-6 | done (Gate C passed 2026-11-11) |
| P2-10 | Frontend: daily cards, chatbot users table, generation table | developer | P2-6 | done (Gate C passed 2026-11-11) |
| P2-11 | Frontend: AI usage section (reuse `services/aiUsage.ts`) and Quality section (extract from the old page, reuse not rewrite) | developer | P2-6 | done (Gate C passed 2026-11-11) |
| P2-12 | Nav link "Feature Analytics", routes, scoped styles, docs (`UserGuide.md` only for what works: unavailable states are described as such) and `DeveloperGuide.md` (including the dated SoC LLM limit observations of 2026-11-11, labelled as observed, not documented quotas, with the unconfirmed reasoning-token hypothesis) | developer | P2-7 to P2-11 | done (Gate C passed 2026-11-11) |
| P2-13 | Run backend and frontend suites, typecheck, lint; report per test, contract mismatch versus logic bug | test-designer | P2-1 to P2-3, P2-4 to P2-12 | done (Gate C passed 2026-11-11) |
| P2-14 | Verify: spec coverage, SHR-01/02/05 on every new endpoint, privacy (no content), chart accessibility, docs accuracy; re-run suite | verifier | P2-13 | done (Gate C passed 2026-11-11) |
| P2-15 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | P2-14 | done (Gate C passed 2026-11-11) |
| P2-16 | Orchestrator: usage report, notes, human tries the hub (Gate C) | orchestrator | P2-15 | done (Gate C passed 2026-11-11) |

## Phase 4: new event collection (Gate E: check real data)
| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| P4-1 | Backend tests (phase 4): migration, backfill, hook extensions, category mapping, rate-limited generation logged without an attempt, login (student and teacher only; admin no-op), draft-started and published hooks (published once per set across unpublish/republish), in-progress 120 s rule, rate-limited generation counted in reports, partial coverage, purge and retention, hourly/health/daily switching from `not_collected` to real values (AC3, AC10, AC13, AC22, AC23, AC33-AC37) | test-designer | Gate C | todo |
| P4-2 | Concurrency tests (outcome applied once, one log row per request, draft-started and published idempotent per set) and privacy schema inspection (no user id/text/IP in new tables) | test-designer | Gate C | todo |
| P4-3 | Developer check: does an existing practice-set table carry a first-save time and a first-publication time to backfill, and where are the save and publish transitions? Do attempt start/submit timestamps already cover the funnel (Open question 9)? Record in `workflow/notes.md` | developer | Gate C | todo |
| P4-4 | Migration `20261111_adm07_events` with backfill and downgrade | developer | P4-3 | todo |
| P4-5 | Models, `retention.py`, hook extensions, `categorize_llm_error` | developer | P4-4 | todo |
| P4-6 | Wire host call sites (companion, TEA-02 routes, sign-in, practice-set save and publish) without changing responses; hourly/health/daily queries read the new tables | developer | P4-5 | todo |
| P4-7 | Update `DeveloperGuide.md` and `UserGuide.md` (what is collected, retention 30 days, privacy) | developer | P4-6 | todo |
| P4-8 | Run suites; frontend regression that unavailable states now show real values | test-designer | P4-1, P4-2, P4-6 | todo |
| P4-10a | Tests for the AI usage cleanup command (AC42) against a test database only | test-designer | Gate C | todo |
| P4-10b | Implement `ai_usage.cleanup` (`--dry-run`, `--apply --approved-by`; deletes `pending` attempts older than 24 h in `ai_service_attempts`, resets `ai_usage_coverage` per plan; permanent, no archive, no restore). The developer never runs `--apply` on a real database | developer | P4-10a | todo |
| P4-10c | **Human approval gate:** run `--dry-run` on the target database, review the per-feature row counts and coverage changes, then approve (or run) `--apply` with `--approved-by`. Irreversible | human | P4-10b, Gate E | todo |
| P4-9 | Verify (SHR-01/02/05, hook isolation, retention, no content in new tables); fix rounds | verifier, developer | P4-8 | todo |

## Phase 5: delete old (Gate F: review the deletion list first)
| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| P5-1 | Copy final ADM-01 (with privacy amendment) and ADM-06 acceptance criteria into `workflow/specs/ADM-07/retained-criteria.md` before any deletion | spec-writer | Gate E | todo |
| P5-2 | Deletion list: legacy page, `AdminAiUsage` page and nav link, `/usage` row logic if unused, old specs; move or keep every test that covers retained backend behaviour (never weaken) | developer, verifier | P5-1 | todo |

## Phase 6: docs and closeout
| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| P6-1 | Final docs pass, usage report, `logs/` summary, PR into `master` | orchestrator | Gate F | todo |

Within phase 2 and phase 4, the test-designer tasks and the developer tasks run in parallel (separate worktrees). Concurrency and cross-user tasks are kept because the feature reads and writes stored records.
