# Spec: STU-02-frontend Student Practice page on the real API

Status: Approved by the user in chat (30 Oct 2026), including the proposed answers to the three open questions. Second slice of STU-02: the backend slice (`../STU-02/`) is merged; this slice connects the student Practice page to it.

## Goal
A student does a practice set on the real server: the questions come from the API, the answers are saved and submitted through the API, and the score, correct answers and explanations appear only after the server accepts the whole-set submission (US-STU-02-01, US-STU-02-02).

## Behaviour
- Opening `/student/practice` loads the set `intro-se-1` from `GET /api/practice-sets/intro-se-1` (title, questions in order, code snippets, choices) and shows it with the existing look. While loading, a loading state is shown.
- The student picks one choice per question and may change any choice. The side panel shows "N of M answered", with M taken from the set.
- Nothing about correctness is shown before submission. The "Get a hint" panel stays a scripted demo (no AI).
- Pressing "Submit practice set":
  - If a question has no choice yet, nothing is sent; the page names the unanswered questions by number.
  - Otherwise the page makes the attempt on the server if it has none, saves all the answers, submits, then reads the results. It shows the score from the server, and for each question the student's choice, the correct choice, whether it was right and the explanation.
- After submission the choices are locked. "Start another attempt" clears the page; the next attempt is made on the server when the student next submits.
- Errors never lose the student's answers (see AC6).
- Leaving the Practice page and coming back keeps the answers or results for the rest of the browser session, as today. A page reload starts fresh.

## Acceptance criteria
- [ ] AC1: The Practice page shows the set title and questions (text, code or none, choices) exactly as returned by the API, in the API's order. No question text, choice, answer or explanation is hard-coded in student code.
- [ ] AC2: A student can select and change one choice per question; "N of M answered" is correct. No correctness, score or explanation appears before submission, including after a failed submission.
- [ ] AC3: Submitting with unanswered questions sends no request that changes server state, shows which questions (by number) are missing, and keeps every chosen answer.
- [ ] AC4: Submitting a complete set shows the score, and per question the student's choice, the correct choice and the explanation, all taken from the server's results response. The choices become read-only.
- [ ] AC5: The page never computes correctness or score itself. If the server's score and per-question results disagree with what the page would guess, the server's values are shown.
- [ ] AC6: Failures are shown in plain words with a way to retry and no lost answers:
  - backend unreachable, timeout (10 s), HTTP 5xx or a response of the wrong shape: a message, answers kept, "Try again" that repeats the failed step;
  - set not found (404 `set_not_found`) or the set cannot be loaded: an error panel with "Try again", no questions shown;
  - 422 `incomplete` from the server: the same missing-question message as AC3, using the server's `missing` list;
  - 409 `already_submitted` (for example a second tab submitted first): the page loads the results instead of showing an error;
  - 404 `attempt_not_found` (for example the server restarted): the page makes a new attempt, saves the same answers and continues once; if that fails it shows the error from the first bullet.
  Raw response bodies, stack traces and status codes are not shown.
- [ ] AC7: "Start another attempt" returns to an empty form with no old results visible and no old attempt reused.
- [ ] AC8: Student pages contain no answer key. The demo question data that holds answers and explanations moves to a file used only by the teacher pages, and the teacher and admin pages are loaded on demand, so the scripts the browser downloads for `/student/practice` contain none of the fixture's explanation texts or "correct answer" fields.
- [ ] AC9: The study companion widget still works on the Practice page and still reflects submitted or not submitted; the teacher and admin pages (including the teacher's review and practice-set screens) work and look as before; the other student pages are unchanged.
- [ ] AC10: Answers and results survive navigating to another student page and back during the session.
- [ ] AC11: Every practice request sends `X-Student-Id` from one configuration constant (placeholder until SHR-01). The id is not read from or written to browser storage, and no login, token or credential is added.
- [ ] AC12: `npm run typecheck`, `npm run lint`, `npm run format:check` and `npm test` pass, and the CI workflow passes. The Playwright tests do not need a running backend (they mock the practice API), and at least one test per criterion above exists.
- [ ] AC13: `docs/UserGuide.md` and `docs/DeveloperGuide.md` describe the new behaviour; the "Demo scoring runs in your browser" note on the page is removed or corrected.

## Out of scope
Real login (SHR-01), database persistence, resuming an attempt after a reload, choosing between several sets (only `intro-se-1`), autosave while answering, teacher publishing, the real AI companion (STU-03), progress on the dashboard (STU-04), changes to the backend.

## Security and safeguards
- The server alone decides what is released; the page only shows what the results endpoint returns, and requests results only after a successful submit (or a 409 on submit).
- Correct answers and explanations are never in student code or in any response before submission (AC8, AC2).
- Two requests for the same attempt at once: the button is disabled while a submit is running so a double click sends one flow; if two tabs race, the server's lock decides and the loser handles 409 (AC6).
- Identifiers from the server (attempt id, question id, choice id) are used as opaque strings; path parts are URL-encoded; server text is rendered as text, never as HTML.
- The student id is a fixed placeholder, trimmed by the server. Nothing from the browser is trusted by the server beyond that header, which SHR-01 replaces.
- Error messages shown come from fixed page text, not from raw server bodies.

## Open questions (answered: all three as proposed)
1. Create the attempt when the page opens, or when the student first submits? Proposed: on first submit, so abandoned visits leave no empty attempts on the server.
2. Keep the attempt id only in memory (reload = fresh start, proposed) or in `sessionStorage` so a reload could resume? The Developer Guide currently says nothing is stored in the browser.
3. Add a real-backend end-to-end test to CI (start uvicorn, run one Playwright test), so a contract change on either side fails CI? Proposed: yes, one test.
