# Tasks: ADM-02 Targeted feedback forms

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Resolve privacy/retention proposals, map existing shared-module/error contracts, obtain human spec/plan approval and pass speccheck; record approved start commit | orchestrator | draft contract | done |
| 1 | Design tests for every AC01-AC25 (including user-requested respondent drafts) and shared UI/security criterion without src access, prove RED and commit in isolated worktree | test-designer | 0 | done |
| 2 | Implement persistent forms, publication/inbox, private respondent draft autosave/resume, atomic submission/completion/snapshots, close/review and role UI; update both guides; run existing required checks and commit source | developer | 0 | done |
| 3 | Merge source into independent test worktree, run suite and report pass/fail separating contract mismatches from logic defects; orchestrator merges tests afterwards | test-designer, orchestrator | 1, 2, 6, 7 | in progress |
| 4 | Verify every criterion, source/docs quality, auth/privacy/concurrency and suite; report ranked findings without editing files | verifier | 3 | in progress |
| 5 | Fix findings and verifier re-checks (max 2 revision rounds; then escalate) | developer, verifier | 4 | in progress |
| 6 | Records only: concurrent-request tests for admin and recipient draft versions, atomic publication/inbox, two-tab saves, delayed save after submit, draft-save/close, duplicate submission, close/submission and eligibility changes | test-designer | 0 | done |
| 7 | Records only: cross-user same-role, cross-role and cross-course tests; unfinished drafts are owner-only (including denial to admins), submitted review is admin-only, inaccessible/malformed IDs never leak data | test-designer | 0 | done |
| 8 | Record security outcomes, handoffs, session log, resource report and local status; prepare reviewable PR for human approval | orchestrator | 4, 5 | in progress |

Tasks 1, 2, 6 and 7 run in parallel after approval. Independent designer resets to the exact approved start commit and never reads implementation until integration. Orchestrator owns invocation tracking and report generation. Approval received 2026-11-07; build begins from the orchestrator-recorded approved commit.
