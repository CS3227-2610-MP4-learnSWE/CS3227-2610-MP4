# 2026-11-03 — Phase D: code duplication (behaviour unchanged) — isaac

Model: Claude Sonnet 5.5. Each refactor is on its own local branch cut from `master` (6d65273), so each can be its own PR. Nothing was pushed and no PR was opened. R4 and R5 are investigations; their record is on `chore/workflow-cleanup-and-refactor`.

## Test setup

- The backend suite skips 156 database tests unless `TEA01_TEST_DATABASE_URL` is set. I started a throwaway `postgres:16` container on 127.0.0.1:55432 (not the project's Postgres on 5433), set `TEA01_TEST_DATABASE_URL=postgresql+psycopg://postgres:test@127.0.0.1:55432/postgres`, and stopped the container afterwards. Each test run creates and drops its own schema.
- Baseline on `master`: 483 passed (matches the 483 in `workflow/notes.md`). A first run showed 2 teardown errors from pytest's own temp-folder cleanup on Windows (`PermissionError` on `pytest-of-isaac`); using `--basetemp` in the scratchpad removed them, so they are environmental, not product failures.
- Ruff `--select F,E9` (unused imports, syntax) on the changed files: clean. The backend has no configured linter; this was a one-off check.
- Frontend checks were not run: no frontend file changed in any refactor.

## Commits

| Task | Branch | Commit message | Change | Tests |
|---|---|---|---|---|
| R1 | `refactor/r1-teacher-access` | `refactor(teacher): put teacher access checks in one module (R1)` (60b0645) | New `src/backend/teacher_access.py` holds `teacher_session`, `owned_material`, `parse_uuid` (were private in `teacher_materials/routes.py`). New `src/backend/timestamps.py` holds `utc_timestamp` (the old `_timestamp`, which the MCQ and notes routers also imported privately). `demo_identity.py` gets `require_demo_enabled()`: the development-only gate, now defined once and called once in `teacher_session`; the copy inside `require_teacher` is removed. The three routers import the public names. | 483 passed before and after. `grep "from teacher_materials.routes import _"` finds nothing. The gate string appears once outside tests. The 403/401/404 identity and access tests pass unchanged. |
| R2 | `refactor/r2-normalise-newlines` | `refactor(teacher): one newline-and-trim helper (R2)` (60a2468) | `text_validation.normalise_newlines_and_trim`, used by `teacher_mcqs/generation.py`, `teacher_notes/generation.py` (its private `_normalise` removed) and `teacher_notes/routes.py`. | New `tests/test_text_validation.py` (5 CRLF, lone CR and trim cases) was written first and failed at import (RED), then passed. Full suite 488 passed (483 + 5). One definition of the chain remains. |
| R3 | `refactor/r3-student-identity` | `refactor(student): move the student header check to student_identity (R3)` (b023bcf) | New `src/backend/student_identity.py` with `require_student` and a note that SHR-01 replaces it; `practice_routes.py` and `companion_routes.py` import it. `companion_routes` no longer imports from `practice_routes`. | 483 passed before and after; the 7 existing header and student-id tests (including trimming) also run alone and pass. |
| R4 | chore branch | `docs: record R4 and R5 duplication checks (no code change)` (798cd52) | Investigation only. The teacher routers already share one mapping (`teacher_notes/generation._llm_error`, imported by `teacher_mcqs/generation.py`). The companion's `_map_error` uses different codes and student-facing wording that tests assert, so merging it would change error codes, which is out of scope. Recorded in `workflow/notes.md`. | n/a (no code change) |
| R5 | chore branch | same commit as R4 | Investigation only. No service builds its own fetch, timeout or error handling: `companion.ts` and `practice.ts` use `request`; the three teacher services use `requestTeacher`; `teacherGeneration.ts` only maps error codes to text. The overlap is inside `client.ts` (`request` vs `requestTeacher`), plus one health fetch in `components/Shell.tsx`. Recorded in `workflow/notes.md`; the oldest notes entry moved to the archive to keep 10. | n/a (no code change) |

## Things to know before opening the PRs

- R1 touched the same three route files as R2 and R3 touches `companion_routes.py`/`practice_routes.py`; R1 and R2 edit different lines of `teacher_notes/routes.py`, so they should merge without conflict, but I did not test the merge of all three together.
- R1 went slightly beyond the task text: `_timestamp` also had to move, otherwise the MCQ and notes routers would still import a private name from `routes.py`.
- Each PR description should list its test run from the table above. Nothing was run on GitHub CI.

## Open decisions for the user

1. Merge `request` and `requestTeacher` in `client.ts` (R5 finding)? Not done because the task only asked to investigate.
2. Make `_llm_error` public or move it to `llm_errors.py` (R4 finding)? Not done for the same reason.

## Follow-ups (same day, after the user approved both open decisions)

| Branch | Commit | Change | Tests |
|---|---|---|---|
| `refactor/r4-llm-errors` | `refactor(teacher): move the generation error mapping to llm_errors (R4 follow-up)` | New `src/backend/llm_errors.py` with `generation_error` (the former `teacher_notes.generation._llm_error`); notes and MCQ generation import it. Codes and messages unchanged. The companion mapping is untouched. | Backend 483 passed. |
| `refactor/r5-client-transport` | `refactor(frontend): share one transport core in client.ts (R5 follow-up)` | `request` and `requestTeacher` call a private `send()` and `errorFrom()`; signatures unchanged. One small side effect: teacher errors now also carry `missing` if the server sends it (none does). | `npm run typecheck`, `npm run lint`, `npm test` (mocked suite): 155 passed. The first run failed everywhere because Playwright's Chromium was not installed on this machine; after `npx playwright install chromium` it passed. The real-backend test was not run. |
