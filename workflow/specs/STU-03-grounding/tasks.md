# Tasks: STU-03-grounding Study companion grounded in published lessons

Variant B. Nothing starts until the user approves `spec.md` and `plan.md` and answers the open questions. The orchestrator creates the usage run manifest before the first agent starts (`workflow/coordination.md`). Tasks 1, 2, 6 and 7 run in parallel with the build; the test-designer sees only the spec and the plan contract, not `src/`.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Review `spec.md` and `plan.md`, answer open questions 1 to 8, approve (human) | user | draft | todo |
| 1 | Backend tests: AC1 to AC8, AC10 to AC20, AC23 (route and logic, fake LLM, lesson rows), unit tests for `lesson_match` and `find_leak(check_text=False)`; update only old-shape assertions in existing STU-03 tests and list them | test-designer | 0 | todo |
| 2 | Frontend tests: AC5, AC21, AC22 (Playwright with the `companionApi.ts` mock extended with `sources`; no backend) | test-designer | 0 | todo |
| 3 | Implement `lesson_provider.py`, `lesson_match.py`, the additive `check_text` option in `leak_check.py`, and the config constants | developer | 0 | todo |
| 4 | Implement schema, prompt, service (`select_mode`, `finish_lesson_reply`, lesson context) and route changes; update `companion_help.py` | developer | 3 | todo |
| 5 | Implement the frontend: service types and shape check, `StudyCompanion.tsx` lesson id, sources line, failure text, scoped CSS | developer | 0 | todo |
| 6 | Records: concurrent-request test. 30 simultaneous lesson-page requests from one student admit exactly 20 per minute with no other error; a lesson withdrawn during the model call yields 404 and no reply text | test-designer | 0 | todo |
| 7 | Records: cross-user test. A student who is not a member, a student of another course, a teacher and an admin cannot read lesson context through the companion; ids cannot be probed (identical 404) | test-designer | 0 | todo |
| 8 | Run backend suite (`uv run pytest -q`) and frontend checks (`npm run typecheck`, `lint`, `format:check`, `test`); report pass/fail per test, contract mismatch versus logic bug; no live calls | test-designer | 1, 2, 3, 4, 5, 6, 7 | todo |
| 9 | Docs: `docs/UserGuide.md`, `docs/DeveloperGuide.md`, `docs/FeatureList.md` (STU-03 last bullet), `docs/UserStories.md` (US-STU-03-05 last bullet), the pointer in `workflow/specs/STU-03/spec.md`, `workflow/security/test-log.md`, `workflow/STATUS.md`; help text matches the guide | developer | 4, 5 | todo |
| 10 | Verify: code, docs and security review (access through `study_lessons/access.py`, uniform 404, post-call recheck, no key or explanation in Lesson context, pasted-question precedence, marker handling, sources limited to id and title, leak check scope, no connection held across the model call, rendered titles as text); re-run suites; confirm no live call in tests or CI | verifier | 8, 9 | todo |
| 11 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 10 | todo |
| 12 | Manual live check by the user with approval and a local ignored `.env` (AC29); record results in `workflow/security/test-log.md` and `logs/`; any threshold, stopword or cap change is a separate approved change | user | 11 | todo |
| 13 | Closeout: run report (`python -m tracker run-report`), link it from `workflow/experiments/resource-log.md` and `workflow/notes.md`, session summary in `logs/`, retro; open a PR into `master` only after asking the user | orchestrator | 11 | todo |

Tasks 1, 2, 3, 5, 6 and 7 can start together once task 0 is done; task 4 waits for task 3. Tasks 6 and 7 are kept because the feature reads stored records (lessons, memberships).
