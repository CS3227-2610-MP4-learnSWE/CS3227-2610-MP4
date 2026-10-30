# Tasks: TEA-01 Manage learning materials

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Build independent TEA-01 API/security tests for AC1–AC9 and browser tests for the Materials page contract; use an isolated PostgreSQL schema/private temp directory for API tests, import only backend `app`, and mock the browser's business API | test-designer | approved spec + plan | todo |
| 2 | Add PostgreSQL/SQLAlchemy models, Alembic migration, configuration, and explicit idempotent seed with the fixed IDs and memberships; document migration/seed invocation | developer | approved spec + plan | todo |
| 3 | Add gated demo teacher identity and server-side course/material/topic access checks with exact error envelopes | developer | 2 | todo |
| 4 | Add streamed private PDF/UTF-8 upload validation, generated storage keys, and file/metadata failure cleanup | developer | 2, 3 | todo |
| 5 | Add six teacher API routes, DTOs, listing/filter/assignment/download behavior, and PostgreSQL 16 CI service configuration | developer | 2–4 | todo |
| 6 | Replace the Materials preview with working controls/dialog/actions/error states, connect the shared API client without changing practice calls, and update guides only for working behavior | developer | 5 | todo |
| 7 | Run existing backend/frontend suites and report developer readiness; merge developer changes into test-designer worktree, then run independent tests and report pass/fail by case | developer, test-designer | 1, 6 | todo |
| 8 | Verify acceptance coverage, code/docs consistency, access controls, upload cleanup and concurrent operations; re-run full suite and record security cases | verifier | 7 | todo |
| 9 | Fix blocking defects and re-check, at most two revision rounds; hand off merge-ready result to human team | developer, verifier | 8 | todo |

Tasks 1 and 2–5 run in parallel in separate worktrees. The developer does not inspect or edit the independent tests before the test-designer's verification merge. Stage only owned paths; no agent commits directly to `master`.
