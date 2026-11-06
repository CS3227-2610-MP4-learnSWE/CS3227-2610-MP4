# Tasks: ADM-05 User and access management

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Independent endpoint, adversarial and UI tests from approved contract, commit before source visibility | test-designer | approved spec and plan | done |
| 2 | Add migration and server lifecycle, fixed-role creation, course and membership endpoints; extend shared auth and AI recheck | developer | approved spec and plan | done |
| 3 | Run independent suites after merging developer branch into isolated worktree; report contract mismatches separately | test-designer | 1, 2, 6, 7 | done |
| 4 | Read-only acceptance, security, quality and guide verification; rerun suites | verifier | 3 and tests merged by orchestrator | done |
| 5 | Fix ranked findings, maximum two correction rounds, then escalate | developer, verifier | 4 | done |
| 6 | Concurrent requests on same record: last-admin race, archive/grant race, repeated email creation and opposite membership operations | test-designer | approved spec and plan | done |
| 7 | Cross-user test: anonymous/student/teacher cannot administer; course revocation blocks teacher/student and AI context access | test-designer | approved spec and plan | done |
| 8 | Build accessible account/course screens using shared cookie client and exact state contract; update guides and test-only password example | developer | 2 | done |
| 9 | Record security outcomes, feature status, handoffs, session log and usage report; local commits only | orchestrator | verification | done |

Tasks 1, 2, 6 and 7 run in parallel in separate worktrees. No live LLM or deployment. User has requested local commit and testing instructions; do not push or open a remote PR.

## User-requested maintenance follow-up (2026-11-06)

- [x] Amend UI contract for green toast, cleared form retaining role, modal details and visible logout.
- [x] Commit RED UI regressions and independent cookie-jar login tests before source.
- [x] Implement scoped UI fixes; preserve failure state and nested confirmations.
- [x] Verify desktop/mobile layout and real form-created student/teacher login in fresh isolated browser contexts.
- [x] Update guides/handoff/resource/security evidence; user confirms login working.
