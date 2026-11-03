# Tasks: SHR-01 Authentication and authorisation

Status: Draft revision 2. Task 1 gates everything else. Tasks 2 and 3 run in parallel from the approved spec and plan. Work on branch `feat/shr01-auth-spec` successors, PR into `master`; never push to `master`. No live model calls.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Human review and approval of spec.md and plan.md; resolve the remaining open questions 4, 6 and 7 (4 may wait until hosting is chosen; 6 and 7 before deployment) | human, orchestrator | spec-writer output | todo |
| 2 | Write independent backend tests from spec and plan (auth endpoints, `current_user`, course access, seed, rate limits, CSRF, cookie flags, migration, security cases SEC-AUTH-01..14 including demo-header cases); migrate STU-02/STU-03 test helpers and tests from `X-Student-Id` to session login without weakening assertions | test-designer | 1 | todo |
| 3 | Backend: migration `20261103_shr01_auth`, `User` columns, `auth/` package (settings, passwords, models, db, sessions, rate_limit, csrf, dependencies, routes, seed), `sliding_window.py` extraction, `main.py` wiring and CORS | developer | 1 | todo |
| 4 | Backend: migrate `practice_routes.require_student` to `current_user(role="student")`, protect `read_set`, verify `companion_routes.py`; no change to answer-release logic | developer | 3 | todo |
| 5 | Write frontend/Playwright tests: login and signup UI, route guard (including flag-off unit tests and demo-mode coexistence, AC25), logout, storage inspection, 401 handling (authenticated vs demo); update only the student practice/companion e2e specs to sign in first; do NOT edit `teacher-*.spec.ts`; `RequireRole`, `AuthContext`, `client.ts` unit tests | test-designer | 1 | todo |
| 6 | Frontend: `services/auth.ts`, `auth/AuthContext.tsx`, `auth/RequireRole.tsx`, `auth/demoAccess.ts`, `client.ts` (credentials, CSRF, 401 callback, drop `X-Student-Id`; `requestTeacher` unchanged), `config.ts`, `Login.tsx` (add real form, keep and relabel the demo buttons), `App.tsx`, `Shell.tsx` (logout and real name when authenticated, "Demo (not signed in)" and role switcher kept in demo mode), sign-in notice on practice/companion 401 in demo mode; teacher pages and routes untouched; accessible and responsive per SHR-04 | developer | 3 | todo |
| 7 | Docs and config: `.env.example` (backend), `docs/SharedDataContract.md`, `docs/DeveloperGuide.md` (how to use `current_user` and `require_course_member`, seed command, env vars, teacher/admin migration handoff), `docs/UserGuide.md` (only working features), CI env if needed | developer | 3, 4, 6 | todo |
| 8 | Integrate, run full backend and frontend suites (`uv run pytest -q`, `npm run typecheck`, `npm run lint`, `npm test`, Playwright), report pass/fail | test-designer | 2, 3, 4, 5, 6 | todo |
| 9 | Log SEC-AUTH-01..14 outcomes in `workflow/security/test-log.md`; update `threat-model.md` (session theft, CSRF, enumeration, brute force, role escalation) | test-designer, verifier | 8 | todo |
| 10 | Verify: read-only code, docs and security review; re-run suites; check no secrets committed, demo identity and demo UI paths untouched, teacher specs and routes unmodified (git diff shows none), historical migrations untouched, UserGuide claims accurate (demo described as a sample-data shortcut only) | verifier | 8 | todo |
| 11 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 10 | todo |
| 12 | HANDOFF note for teammates: migrate teacher routes, `requestTeacher` and `teacher-*.spec.ts` (sign in first) to `current_user(role="teacher")`; build admin routes with `current_user(role="admin")`; afterwards retire the demo gate and, as a separate change, the demo buttons/switcher/anonymous path (or keep them for demonstration) | orchestrator | 11 | todo |
| 13 | Record handoff in `workflow/notes.md`, resource-log row, `logs/` session summary; open PR for teammate review (do not merge) | orchestrator | 11 | todo |

Notes:

- Task 2 must not read `src/`; it uses only the plan's contract, the env variable table and the fixture list in spec.md.
- Task 4 touches only identity plumbing in `practice_routes.py`; any change to scoring, answer release or companion context logic is out of scope and a defect.
- Do not edit `teacher_materials/demo_identity.py` or its gate in any task of this feature.
- Do not remove or alter the demo access (buttons, switcher, anonymous demo path); only relabel it and add the demo-mode notice as specified. Do not edit teacher routes, teacher pages' data flow or `teacher-*.spec.ts`; they must pass unchanged.
