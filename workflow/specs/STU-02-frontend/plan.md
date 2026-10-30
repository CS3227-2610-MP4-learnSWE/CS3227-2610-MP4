# Plan: STU-02-frontend Student Practice page on the real API

Status: Approved by the user in chat (30 Oct 2026), together with `spec.md`.

## Data model (frontend state)
One practice session state, kept in a provider above the student pages so it survives navigation (AC10):

| Field | Meaning |
|---|---|
| `load` | `loading`, `ready` or `error` for the set |
| `set` | `{id, title, questions[]}` from the API |
| `choices` | `{questionId: choiceId}` the student has picked (local) |
| `attemptId` | server attempt id or `null` (memory only) |
| `phase` | `editing`, `submitting` (button disabled), `submitted` |
| `results` | the results response, or `null` |
| `message` | one of the fixed page messages, or `null`; `missing` is a list of question ids |

`submitted` for the study companion is `phase === "submitted"`.

## API calls used (contract: `../STU-02/plan.md`, unchanged)
| Step | Call | Handling |
|---|---|---|
| Open page | `GET /api/practice-sets/intro-se-1` | 200 show; 404, network, timeout, bad shape: error panel with retry |
| Submit, no attempt yet | `POST /api/practice-sets/{set}/attempts` | 201 keep `attempt_id` |
| Save | `PUT /api/attempts/{id}/answers` with all picked answers | 404 `attempt_not_found`: new attempt, save again, once |
| Submit | `POST /api/attempts/{id}/submit` | 200 continue; 422 `incomplete`: use `missing`; 409: go to results; 5xx or network: retry message |
| Results | `GET /api/attempts/{id}/results` | 200 show; 404 `attempt_not_found`: new attempt, save, submit, results, once (verifier round 1); other failure: retry message |

Every request sends `X-Student-Id` and uses a 10 s timeout. Retry repeats only the step that failed, so a submit that succeeded is never repeated (a repeat would return 409, which is handled anyway).

## Components and modules
New (small, single purpose):
- `src/frontend/src/services/client.ts`: the only place that calls `fetch` for the business API: base path, header, timeout, JSON parsing, and one `ApiError` (status, code, missing). Reuses nothing duplicated; the health check in `Shell.tsx` stays as is.
- `src/frontend/src/services/practice.ts`: typed functions `getSet`, `startAttempt`, `saveAnswers`, `submitAttempt`, `getResults`, with a check that each response has the expected shape (a wrong shape counts as a failed response).
- `src/frontend/src/config.ts`: `STUDENT_ID` placeholder with a comment pointing to SHR-01.
- `src/frontend/src/practice/PracticeContext.tsx`: provider and hook holding the state above and the actions `load`, `choose`, `submit`, `startAnother`, `retry`. Mounted in `DemoProvider`'s place for practice only; the old `answers`, `answer`, `submit`, `resetPractice` and `submitted` are removed from `state.tsx` (the companion reads the new hook).
- `src/frontend/src/pages/Practice.tsx`: the page (moved out of `Student.tsx`), same layout and classes; renders from the state.
- `src/frontend/src/teacherDemo.ts`: the demo questions with answers and explanations, moved out of `data.ts`; imported only by `Teacher.tsx`.

Changed: `data.ts` (remove `questions`), `Student.tsx` (use the new page), `Teacher.tsx` (import from `teacherDemo.ts`), `StudyCompanion.tsx` (read submitted from the practice hook), `App.tsx` (provider; `React.lazy` + `Suspense` for `Teacher` and `Admin`), `state.tsx`, `docs/UserGuide.md`, `docs/DeveloperGuide.md`, `workflow/security/test-log.md`.

The backend is not changed. The Vite proxy already forwards `/api` to the backend, so no CORS change.

## AI usage
None. The hint panel stays a scripted demo and says so.

## Test plan
Playwright (`src/frontend/tests/`), practice API mocked with `page.route` through one shared helper `tests/practiceApi.ts` that also records the requests. The helper is registered in the existing `beforeEach`, so other tests that open the Practice page keep working. The old practice test is rewritten against the mocks.

| AC | Test |
|---|---|
| AC1 | Page shows the mocked title, questions, code and choices in order; changing the mock changes the page |
| AC2 | Select and change choices; counter correct; no "Correct", score or explanation text before submit, including after a mocked 500 on submit |
| AC3 | Click submit with 2 of 3 answered: no POST/PUT recorded, missing question number named, answers still selected |
| AC4 | Full flow with mocks: requests happen in order (attempt, save, submit, results); score, correct choice and explanations shown; radios disabled |
| AC5 | Mock results whose score differs from the picked answers: page shows the server's values |
| AC6 | One test each: network failure on load, 404 set, 500 on submit then retry succeeds, 422 incomplete, 409 then results, 404 attempt then new attempt and one re-save, slow response past 10 s (fake clock) |
| AC7 | After submit, "Start another attempt": empty form, no results, next submit makes a new attempt |
| AC8 | Collect all script responses for `/student/practice`: none contains the fixture explanation texts or "Correct choice"; `/teacher/review` still shows its demo answers |
| AC9 | Existing companion, teacher and admin tests pass unchanged; companion text switches after submit |
| AC10 | Answer, go to Overview and back: answers kept; after submit, back: results kept |
| AC11 | Every recorded practice request has `X-Student-Id`; `localStorage` and `sessionStorage` are empty |
| AC12 | CI green |
| AC13 | Verifier checks docs against behaviour |

If the user approves open question 3: one extra Playwright project `real-backend` with a single test (start, answer, submit, see score from the real server), run in CI in a new job that starts uvicorn first. Otherwise it is run by hand once and recorded in `logs/`.

Security cases to add to `workflow/security/test-log.md`: answer key absent from student scripts; no results request before a successful submit; server text rendered as text (a mocked question containing `<img onerror>` stays text); double click sends one submit.

## Decisions
- Attempt created on first submit; all answers saved in one PUT before submitting, not on every click: fewer requests, no ordering races, same result for the server (spec open questions 1 and the autosave exclusion).
- Attempt id in memory only (open question 2, proposed).
- Teacher demo data moves to its own file and teacher/admin load on demand: this is the only way the student scripts can be free of answers while the teacher demo still has them; the teacher demo remains placeholder data until the teacher backend exists.
- Workflow: Variant B (developer || test-designer in a worktree, then verifier, max 2 fix rounds). The test-designer works from this spec and the API contract only.

## UI wording contract (added during the build, 30 Oct 2026)
The spec did not fix page wording; both the page and the tests rely on this. It is part of the contract.
- Failures (every failure message and the load error panel) have a button named exactly "Try again".
- The missing-question message is an element with `role="alert"` that contains the unanswered question numbers; for a server 422 it uses the server's `missing` list.
- The reset button is named "Start another attempt". While the set loads, text matching /loading/i is shown.
- The score reads "N / M" or "N of M" (also "N out of M"); the counter reads "N of M answered".
- Keep the `.question-panel` class; each question panel shows, after submission, the student's choice, the correct choice, the word "correct" and the explanation; code snippets render in `pre code`.
- The label for the correct choice must not be the exact string "Correct choice" in student code (Teacher.tsx uses it); use "Correct answer".
- The 10 s timeout is `setTimeout` plus `AbortController` (not `AbortSignal.timeout`), so a fake clock controls it.
- After a second `attempt_not_found` the page shows "Try again" with exactly 2 attempt starts, 2 saves and no submit. A retry repeats only the failed step (results retry sends only results; submit retry only submit).
- The study companion keeps its text: "Hints only before whole-set submission" before submit and "Practice submitted" after.
- Folder renamed from `api/` to `services/`: the dev server serves `/src/api/...` modules, and the existing login test counts any URL containing `/api/` as a business request.
