# Tasks: TEA-05 Learning overview

Status: Approved by the user on 2026-11-09. Open questions 1-11 resolved with the recommended answers, except 9: the greeting is fixed in this feature (AC17).

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | User approves spec and plan and answers the Open questions; orchestrator creates the run manifest and runs speccheck | orchestrator | spec + plan | todo |
| 1 | Design backend tests `test_tea05_*.py` from the plan contract (AC1-AC11, AC16): periods and boundaries, lesson and practice figures, missed ranking, access, privacy allow-list, rate limit, 503, no LLM call. No `src/` access | test-designer | 0 | todo |
| 2 | Design browser tests `tea05-overview.spec.ts` and helper `tea05Api.ts` (AC12-AC15): every UI state and exact message, request counts, history, session, timeout, 320 px, themes | test-designer | 0 | todo |
| 3 | Add only the overview mock route (one import and one call) to the existing shared specs listed in the plan; no assertion changes; report any existing assertion broken by the new request | test-designer | 0 | todo |
| 4 | Backend: additive helpers `course_student_ids`, `lesson_completion_stats` in `study_lessons/progress.py` and `submitted_in_period` in `attempt_store.py` (no existing function touched) | developer | 0 | todo |
| 5 | Backend: new package `teacher_overview/` (`schemas.py`, `service.py`, `routes.py`), register the router in `main.py`; contract as in the plan | developer | 4 | todo |
| 6 | Frontend: `services/teacherOverview.ts`, `pages/TeacherOverview.tsx`, replace the sample Overview content in `Teacher.tsx` and the greeting (AC17), scoped CSS | developer | 0 | todo |
| 7 | Docs: `docs/UserGuide.md` (teacher Overview, calculations, limits; remove "sample preview" wording for it) and `docs/DeveloperGuide.md` (TEA-05 section) | developer | 5, 6 | todo |
| 8 | Concurrent-request tests: parallel identical reads equal; roster invariants hold with a concurrent completion/enrolment writer; rate-limit isolation between teachers | test-designer | 0 | todo |
| 9 | Cross-user tests: second teacher, student, admin, anonymous, removed teacher cannot read another course's figures; no answer-key or identity leakage | test-designer | 0 | todo |
| 10 | Run the new suites plus the shared specs and `test_stu04_*`, `test_stu01_*`; report pass/fail per test, separating contract mismatches from logic bugs | test-designer | 1, 2, 3, 5, 6, 8, 9 | todo |
| 11 | Verify: acceptance criteria, security (SHR-01, SHR-05), code quality (SRP/DRY, no change to existing student-module functions), docs match product; re-run suite | verifier | 10 | todo |
| 12 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 11 | todo |
| 13 | Record security results in `workflow/security/`, resource log, usage report and handoff | orchestrator | 12 | todo |

Tasks 1-3, 4-7, 8 and 9 run in parallel after task 0 (test-designer and developer in separate worktrees). Tasks 8 and 9 are kept because the feature reads stored records.
