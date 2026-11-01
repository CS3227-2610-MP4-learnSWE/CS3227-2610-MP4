# Tasks: TEA-01 Manage learning materials

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Build independent TEA-01 API/security tests for AC1–AC9 and browser tests for the Materials page contract; use an isolated PostgreSQL schema/private temp directory for API tests, import only backend `app`, and mock the browser's business API | test-designer | approved spec + plan | verified locally |
| 2 | Add PostgreSQL/SQLAlchemy models, Alembic migration, configuration, and explicit idempotent seed with the fixed IDs and memberships; document migration/seed invocation | developer | approved spec + plan | verified locally |
| 3 | Add gated demo teacher identity and server-side course/material/topic access checks with exact error envelopes | developer | 2 | verified locally |
| 4 | Add streamed private PDF/UTF-8 upload validation, generated storage keys, and file/metadata failure cleanup | developer | 2, 3 | verified locally |
| 5 | Add six teacher API routes, DTOs, listing/filter/assignment/download behavior, and PostgreSQL 16 CI service configuration | developer | 2–4 | verified locally |
| 6 | Replace the Materials preview with working controls/dialog/actions/error states, connect the shared API client without changing practice calls, and update guides only for working behavior | developer | 5 | verified locally |
| 7 | Run existing backend/frontend suites and report developer readiness; merge developer changes into test-designer worktree, then run independent tests and report pass/fail by case | developer, test-designer | 1, 6 | verified locally |
| 8 | Verify acceptance coverage, code/docs consistency, access controls, upload cleanup and concurrent operations; re-run full suite and record security cases | verifier | 7 | verified locally |
| 9 | Fix blocking defects and re-check, at most two revision rounds; hand off merge-ready result to human team | developer, verifier | 8 | verified locally |

Tasks 1 and 2–5 run in parallel in separate worktrees. The developer does not inspect or edit the independent tests before the test-designer's verification merge. Stage only owned paths; no agent commits directly to `master`.

Verified locally at source commit `673ca24` after one correction round: backend76/browser74, type/lint/format/build, independent verifier PASS. Human PR publication/merge remains pending; no deployment or production authentication claim. See `logs/TEA01Session.md` for the documented parent-developer substitution after a subagent spend-cap error.
