# Tasks: STU-01 Study materials

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Approve spec and plan (decisions recorded); tell the TEA-03 owner about `publish_lesson` | human (orchestrator asks) | spec + plan drafted | in progress |
| 1 | Design backend tests `test_stu01_*` for AC1 to AC12 and AC15 from the plan contract (isolated PostgreSQL schema, SHR-01 helpers, SQL-inserted lessons) | test-designer | 0 | todo |
| 2 | Design mocked Playwright tests and helper `tests/lessonsApi.ts` for AC13, AC14 (every row of the spec's UI table, timeouts with a fake clock, 390 px and 1440 px, light and dark); rewrite the two sample-lesson tests in `app.spec.ts` (AC16) | test-designer | 0 | todo |
| 3 | Migration `20261104_stu01_lessons` and models in `study_lessons/models.py`; register models for Alembic | developer | 0 | todo |
| 4 | `study_lessons/access.py`, `progress.py`, `schemas.py`, `routes.py`; include the router in `main.py`; `no-store` header on study responses | developer | 3 | todo |
| 5 | `study_lessons/publish.py` (`publish_lesson`) with a unit test brief for the test-designer, and `study_lessons/seed.py` and the README/CI run step (`uv run python -m study_lessons.seed` after the teacher seed) | developer | 3 | todo |
| 6 | Frontend: `services/lessons.ts`, `services/lessonMessages.ts`, `pages/Materials.tsx`, `pages/Lesson.tsx`; update `Student.tsx` (Overview stat, remove sample cards), `SignInNotice.tsx`, `state.tsx`, `data.ts`, `StudyCompanion.tsx` label | developer | 4 | todo |
| 7 | Update `docs/UserGuide.md` (only what works, state that lessons appear after a teacher publishes or after the dev seed), `docs/DeveloperGuide.md` (progress helpers for STU-04, `get_visible_lesson` for STU-03), `docs/SharedDataContract.md` (two tables, endpoints), `workflow/security/test-log.md`, `workflow/STATUS.md` | developer | 4, 6 | todo |
| 8 | Run backend suite, mocked Playwright, typecheck, lint, format check; report pass/fail per test, separating contract mismatches from logic bugs | test-designer | 1, 2, 4, 5, 6, 9, 10 | todo |
| 9 | Concurrent-request test: simultaneous PUTs on the same student and lesson leave one row and one consistent state; none returns 500; two students racing do not interfere | test-designer | 0 | todo |
| 10 | Cross-user test: a second student in the same course, a student in another course, and a teacher and admin cannot read or change the first student's completion; draft ids and withdrawn lessons are not readable | test-designer | 0 | todo |
| 11 | Verify: code, docs and security review (SHR-01, SHR-05; no answer data in lessons); re-run the suites | verifier | 8 | todo |
| 12 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 11 | todo |
| 13 | Optional, if approved: one real-backend Playwright test (sign in, open seeded lesson, mark complete, reload) and the CI seed step | developer, test-designer | 6 | todo |

Tasks 1, 2, 3 (then 4, 5, 6), 9 and 10 run in parallel after task 0. The test-designer works only from `spec.md` and `plan.md` in its own worktree.
