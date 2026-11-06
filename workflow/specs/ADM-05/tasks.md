# Tasks: ADM-05 User and access management

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Independent endpoint, adversarial and UI tests from approved contract, commit before source visibility | test-designer | approved spec and plan | todo |
| 2 | Add migration and server lifecycle, fixed-role creation, course and membership endpoints; extend shared auth and AI recheck | developer | approved spec and plan | todo |
| 3 | Run independent suites after merging developer branch into isolated worktree; report contract mismatches separately | test-designer | 1, 2, 6, 7 | todo |
| 4 | Read-only acceptance, security, quality and guide verification; rerun suites | verifier | 3 and tests merged by orchestrator | todo |
| 5 | Fix ranked findings, maximum two correction rounds, then escalate | developer, verifier | 4 | todo |
| 6 | Concurrent requests on same record: last-admin race, archive/grant race, repeated email creation and opposite membership operations | test-designer | approved spec and plan | todo |
| 7 | Cross-user test: anonymous/student/teacher cannot administer; course revocation blocks teacher/student and AI context access | test-designer | approved spec and plan | todo |
| 8 | Build accessible account/course screens using shared cookie client and exact state contract; update guides and test-only password example | developer | 2 | todo |
| 9 | Record security outcomes, feature status, handoffs, session log and usage report; local commits only | orchestrator | verification | todo |

Tasks 1, 2, 6 and 7 run in parallel in separate worktrees. No live LLM or deployment. User has requested local commit and testing instructions; do not push or open a remote PR.
