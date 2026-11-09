# Tasks: ADM-03 AI feedback analysis

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design tests for AC1 to AC38 (including delete, dialog and race tests) from the plan contract (no src/ access): pure-function, API and frontend tests, with map and reduce mocks, statistics-without-AI tests and the message registry tests | test-designer | spec + plan approved | todo |
| 2 | Backend: migration for feedback_analyses (down_revision 20261107_adm04_messaging, single Alembic head, no retention), models, constants | developer | spec + plan approved | todo |
| 3 | Backend: pure aggregate functions using each response's own form_snapshot and the plan's cross-version grouping rule | developer | 2 | todo |
| 4 | Backend: pure entry builder (normalise, de-duplicate, cap, sample, batch), map and reduce prompt builders, strict reply validators with rule names | developer | 2 | todo |
| 5 | Backend: failure registry (exact messages, step, details, reference ids) and shared-client error mapping | developer | 2 | todo |
| 6 | Backend: service (select_all snapshot, synchronous statistics in the create request, idempotency, one running AI step per admin, sweep, paginated history), background job with conditional progress writes, six routes including DELETE (own rows only, 409 while running, uniform 404, conditional job writes) and response-count (ADM-02 untouched), shared ADM-02-04 lookup, usage label feedback_analysis | developer | 3, 4, 5 | todo |
| 7 | Frontend: api client, selection page with Select all, result page with immediate charts, AI section states and polling hook, evidence page, history with Load more analyses, DeleteAnalysisDialog (alertdialog, focus handling, list consistency), message builders, routes, link from AdminFeedback, scoped styles, exact copy and accessible names | developer | 6 | todo |
| 8 | Update docs/DeveloperGuide.md and docs/UserGuide.md for the feature | developer | 7 | todo |
| 9 | Concurrent-request test: same request_id twice and two different submits at once by one admin leave one consistent result; late job write cannot revive an interrupted analysis | test-designer | spec + plan approved | todo |
| 10 | Cross-user test: another admin, student, teacher and disabled admin cannot read or delete analyses or evidence | test-designer | spec + plan approved | todo |
| 11 | Adversarial tests: prompt injection in responses, replies with foreign labels, oversize and malformed map and reduce replies, no identity in prompts, no raw answers in the reduce call, no choice or scale answers in any call | test-designer | spec + plan approved | todo |
| 12 | Run suite; report pass/fail | test-designer | 1, 7, 9, 10, 11 | todo |
| 13 | Verify: code, docs and security review; re-run suite | verifier | 12 | todo |
| 14 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 13 | todo |
| 15 | Amendment 2026-11-09 (user): design tests AC39 to AC50 (response delete API, uniform 404, concurrency with delete, submit and draft save, resubmission, effects on stored and running analyses, registry messages, delete dialog) from the plan contract | test-designer | amendment | todo |
| 16 | Amendment: backend DELETE response route in feedback.py plus store function (one transaction: row delete and recipient completion revert, lock order as submit), failure registry entries `feedback_response_not_found`, `ai_responses_deleted` and delete internal_error step; replace the batch-count-mismatch guard in the job with the missing-responses check; ADM-02 existing endpoints unchanged | developer | amendment | todo |
| 17 | Amendment: frontend "Delete response" button and DeleteResponseDialog on the response detail view (shared confirm-dialog component with the analysis dialog), success status and focus on the response list, exact copy | developer | 16 | todo |
| 18 | Amendment: update docs/DeveloperGuide.md and docs/UserGuide.md (response delete, resubmission rule, analyses kept indefinitely, running-analysis failure) | developer | 17 | todo |
| 19 | Amendment: run suite including AC39 to AC50 and re-run ADM-02 and earlier ADM-03 tests; report pass/fail | test-designer | 15, 17 | todo |
| 20 | Amendment: verify security (admin-only, uniform 404, concurrency with submit and job, no side effects), docs and tests; fix rounds as in task 14 | verifier, developer | 19 | todo |

Tasks 1, 2 to 8, 9, 10 and 11 run in parallel (developer tasks in order). Tasks 9 and 10 stay because the feature stores records.
