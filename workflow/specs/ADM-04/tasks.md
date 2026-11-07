# Tasks: ADM-04 Feedback follow-up

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Resolve source-aware inbox/auth/routes/error integration; human approves final spec and plan; pass speccheck; commit approved start contract | orchestrator | draft | done |
| 1 | Independently design AC01-13 HTTP/browser and adversarial tests in isolated worktree reset to approved start commit; commit RED evidence | test-designer | 0 | done |
| 2 | Implement additive durable message/preview migration, authenticated service/router, atomic idempotent inbox delivery, admin compose/review and recipient rendering; update guides; existing checks; commit source | developer | 0 | done |
| 3 | Merge source into independent test worktree; run backend/browser suites and report contract mismatches separately; orchestrator merges tests | test-designer | 1, 2, 6, 7 | done |
| 4 | Read-only acceptance/test coverage, code/docs/security review; rerun suites; report ranked defects | verifier | 3 | done |
| 5 | Fix reported defects and recheck (maximum two revision rounds) | developer, verifier | 4 | done |
| 6 | Concurrent send/replay/read-state/rollback/restart and audience/account mutation tests prove one consistent durable all-or-nothing result | test-designer | 0 | done |
| 7 | Cross-user/role/course ownership and raw-feedback privacy tests for sender/preview/inbox; no other-recipient exposure | test-designer | 0 | done |
| 8 | Record security outcomes, notes/status/session summary and resource use; generate and link complete invocation report; prepare PR for human review | orchestrator | 4, 5 | done |

Tasks 1, 2, 6 and 7 run in parallel with developer and test-designer isolated. Records are read and written, so concurrency and cross-user tasks are mandatory. Do not implement before approval or weaken independent tests.

UI follow-up (user request2026-11-07): developer completed visual/notification amendment, regression-first metadata and layout checks, scoped design, full622browser/121focused backend verification, guides/spec and tracked closeout. No new delegated feature run.
