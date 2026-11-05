# Tasks: STU-04 Progress dashboard

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Approve spec and plan; answer the open questions (topic mapping, course scoping, Overview stat definitions) | human (orchestrator asks) | spec + plan drafted | todo |
| 1 | Design backend tests `test_stu04_*` for AC1 to AC12, AC17 and AC18 from the plan contract (isolated PostgreSQL schema, SHR-01 helpers, STU-02 endpoints to create attempts, SQL-inserted lessons and topics, synthetic sets for unit tests of `build_progress`) | test-designer | 0 | todo |
| 2 | Design mocked Playwright tests and helper `tests/progressApi.ts` for AC13 to AC16 (every row of the spec's UI tables, request counts, timeouts with a fake clock, wrong role, link targets, 390 px and 1440 px, light and dark); rewrite the existing tests tied to the Overview sample stats and its `/api/study/courses` call (AC19) | test-designer | 0 | todo |
| 3 | Migration `20261105_stu04_practice_attempt` and `attempt_models.py`; seed topic row in `teacher_materials/seed.py` | developer | 0 | todo |
| 4 | `attempt_store.py` database store (`lock` as a context manager yielding a locked, fresh attempt; `submitted_summaries`), `practice_data.topic_id` and fixture mapping, `practice_logic.correct_question_ids`, `practice_routes.py` changes; existing STU-02 behaviour unchanged | developer | 3 | todo |
| 5 | `progress_rules.py`, `progress_schemas.py`, `progress_service.py`, `progress_routes.py`; `study_lessons.progress.member_courses` and `list_courses` reuse; include the router in `main.py`; `no-store` for `/api/progress` | developer | 4 | todo |
| 6 | Frontend: `services/readOnce.ts` (moved out of `lessons.ts`), `services/progress.ts`, `services/progressMessages.ts`, `pages/Progress.tsx`; `Student.tsx` (route, Overview stats and link, remove sample figures and chart), `data.ts` (nav item, remove `weeklyActivity`), `ui.tsx` (`Stat` role group) | developer | 5 | todo |
| 7 | Concurrent-request test: simultaneous submits of one attempt (one 200, the rest 409, counted once), simultaneous answer saves, simultaneous progress reads during a submit; two students racing do not interfere | test-designer | 0 | todo |
| 8 | Cross-user test: a second student on the same set and course, a student in another course, and a teacher and admin cannot read or change the first student's attempts or see their figures; query/header user ids ignored | test-designer | 0 | todo |
| 9 | Update `docs/UserGuide.md` (Progress page, weak-topic rule, repeat-attempt rule, only what works), `docs/DeveloperGuide.md` (store interface and `lock` contract, progress helpers, rule constants), `docs/SharedDataContract.md` (table, endpoint), `workflow/security/test-log.md`, `workflow/STATUS.md` | developer | 5, 6 | todo |
| 10 | Run backend suite, mocked Playwright, typecheck, lint, format check; report pass/fail per test, separating contract mismatches from logic bugs | test-designer | 1, 2, 4, 5, 6, 7, 8 | todo |
| 11 | Verify: code, docs and security review (SHR-01, SHR-02, SHR-05; no answer data in the progress body; row locking; aggregate query); re-run the suites | verifier | 10 | todo |
| 12 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 11 | todo |

Tasks 1, 2, 3 (then 4, 5, 6), 7 and 8 run in parallel after task 0. The test-designer works only from `spec.md` and `plan.md` in its own worktree. Tasks 7 and 8 stay because the feature reads and writes stored records.
