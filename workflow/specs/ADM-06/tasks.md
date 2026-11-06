# Tasks: ADM-06 AI usage monitoring

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Review proposed defaults, resolve source-aware shared-symbol/provider-field mapping and approve spec/plan; pass speccheck and record run start commit | orchestrator, human | draft | todo |
| 2 | Independently write ADM-06 acceptance/adversarial tests from contract in reset isolated worktree; commit tests by path | test-designer | 1 | todo |
| 3 | Implement persistent metadata/coverage migration, observer on every shared-client attempt and bounded admin report; update both guides; commit source after existing checks | developer | 1 | todo |
| 4 | Implement accessible admin UI and exact history/session/error behaviour as part of same development handoff | developer | 1 | todo |
| 5 | Merge implementation into test worktree; run backend/frontend suites and report each failure without weakening assertions; orchestrator merges tests | test-designer, orchestrator | 2, 3, 4, 8, 9 | todo |
| 6 | Verify code/docs/auth/privacy/availability/atomicity; rerun suites and report ranked defects read-only | verifier | 5 | todo |
| 7 | Fix and recheck defects, at most two rounds; escalate further blockers | developer, verifier | 6 | todo |
| 8 | Concurrent-request tests: separate attempts/retries, atomic finalisation/replay, reservation/finalisation outages and consistent report cutoff | test-designer | 1 | todo |
| 9 | Cross-user/role tests: non-admin/disabled sessions denied, admin global aggregate allowed without identities, no previous-session report leakage | test-designer | 1 | todo |
| 10 | Record security/session/resource evidence; generate run usage report; human reviews PR into master | orchestrator, human | 6, 7 | todo |

Tasks 2, 3, 4, 8 and 9 run in parallel in the prescribed developer/test-designer worktree separation; tasks 3/4 are owned by the same developer. No application code until task 1 approval gate. No live AI calls.
