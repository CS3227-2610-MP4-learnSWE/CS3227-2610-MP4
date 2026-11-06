# Tasks: ADM-02 Targeted feedback forms

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Resolve privacy/retention proposals, map existing shared-module/error contracts, obtain human spec/plan approval and pass speccheck; record approved start commit | orchestrator | draft contract | todo |
| 1 | Design tests for every AC01-AC21 and shared UI/security criterion without src access, prove RED and commit in isolated worktree | test-designer | 0 | todo |
| 2 | Implement persistent forms, publication/inbox, submission/snapshots, close/review and role UI; update both guides; run existing required checks and commit source | developer | 0 | todo |
| 3 | Merge source into independent test worktree, run suite and report pass/fail separating contract mismatches from logic defects; orchestrator merges tests afterwards | test-designer, orchestrator | 1, 2, 6, 7 | todo |
| 4 | Verify every criterion, source/docs quality, auth/privacy/concurrency and suite; report ranked findings without editing files | verifier | 3 | todo |
| 5 | Fix findings and verifier re-checks (max 2 revision rounds; then escalate) | developer, verifier | 4 | todo |
| 6 | Records only: concurrent-request tests for draft version, atomic publication/inbox, duplicate submission, close/submission and eligibility changes | test-designer | 0 | todo |
| 7 | Records only: cross-user same-role, cross-role and cross-course tests; response review and inaccessible/malformed IDs never leak data | test-designer | 0 | todo |
| 8 | Record security outcomes, handoffs, session log, resource report and local status; prepare reviewable PR for human approval | orchestrator | 4, 5 | todo |

Tasks 1, 2, 6 and 7 run in parallel after approval. Independent designer resets to the exact approved start commit and never reads implementation until integration. Orchestrator owns invocation tracking and report generation. No build, deployment or application tests have run during this draft stage.
