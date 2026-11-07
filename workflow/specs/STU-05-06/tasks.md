# Tasks: STU-05-06 Student feedback and inbox (verification slice)

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | Merge PR 31 branch into this branch; confirm the PR 31 labels listed in spec Open question 5 and write them into plan.md | orchestrator | spec + plan approved, sender decision | done |
| 1 | Design tests (stu05_/stu06_) for the gaps in the plan's matrix; confirm the existing evidence column from test folders (no src/ access) | test-designer | 0 | done |
| 2 | Add `From: Administrator` beside the sent time in `MessagesInbox.tsx` (only if option A approved) | developer | 0 | done |
| 3 | Correct the student inbox and feedback sections of `docs/UserGuide.md` and `docs/DeveloperGuide.md` to match the product | developer | 0 | done |
| 4 | Run suite; report pass/fail per test | test-designer | 1, 2, 6, 7, 10 | done |
| 5 | Verify: code, docs and security review; re-run suite | verifier | 4 | done |
| 6 | Concurrent-request test: simultaneous mark-read on one delivery and simultaneous submit of one form leave one consistent result | test-designer | spec + plan approved | done |
| 7 | Cross-user test: a second student, a teacher and a student without a recipient row cannot read or change the first student's form, response, draft or delivery | test-designer | spec + plan approved | done |
| 8 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 5 | done |
| 10 | Update the one assertion in `stu02ps-picker.spec.ts` (AC14): count only picker requests, ignore the shell's `/api/messaging/unread-count`; confirm it fails before the change on a branch with PR 31 and passes after | test-designer (a test file, so not the developer; the edit is the one assertion named in AC14) | 0 | done upstream (master 09a77ce); our edit dropped at merge |
| 9 | Record the first-run browser failures, security results and resource log, and close the run report | orchestrator | 8 | todo |

Student form presentation (AC15-AC18, added 2026-11-07):

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 11 | Orchestrator runs speccheck on the amended spec and plan; user confirms the open questions 7-9 | orchestrator | spec amendment | todo |
| 12 | Write browser tests first for AC15-AC18 (`stu05_`/`stu06_` names in the plan's test plan), mocking the 422 `invalid_feedback_answers` response; confirm they fail on the current code | test-designer | 11 | todo |
| 13 | Change `FeedbackQuestion.tsx` (single prompt, aria-labelledby, tag, no floating label, scale endpoints, marker props), `RecipientFeedback.tsx` (shared blank predicate, `attempted` state, stable focus lookup, completed/closed layout), and scoped rules in `styles.css`; update the student form sections of `docs/UserGuide.md` and `docs/DeveloperGuide.md`; run existing tests, typecheck and lint | developer | 11 | todo |
| 14 | Run the suite including unchanged `adm02-feedback.spec.ts` and `stu05-06-inbox.spec.ts`; report pass/fail per test | test-designer | 12, 13 | todo |
| 15 | Verify: criteria AC15-AC18, scoping (admin screens unchanged), accessible names, no extra requests, desktop/mobile/light/dark evidence; docs match | verifier | 14 | todo |
| 16 | Record handoff, resource log, security log note (no change), usage report | orchestrator | 15 | todo |

Tasks 1, 2, 3, 6, 7 and 10 run in parallel after task 0. If the user rejects option A, task 2 is dropped and task 3 records the sender gap as a known deviation.
