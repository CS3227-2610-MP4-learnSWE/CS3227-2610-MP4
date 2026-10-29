# Spec: STU-02 Practice attempt API (server-side core)

Status: Approved by the user in chat (29 Oct 2026). Slice of STU-02 covering US-STU-02-01 and US-STU-02-02 on the server. Shared input for the workflow comparison; every variant builds exactly this.

## Goal
A student starts an attempt on a practice set, answers and revises single-answer MCQs, submits the whole set once, and only then can see the score, correct answers and explanations. The server alone decides what is released.

## Scope
Backend only, in `src/backend/`, with an in-memory store behind a clean interface. The student is identified by the `X-Student-Id` request header, a stand-in for real authentication (SHR-01) that will be replaced later. No database, AI, teacher publishing or frontend changes.

## Fixture (the only practice set)
Set `intro-se-1`, title "Software engineering basics", three questions in this order. Choice ids are `a`, `b`, `c`; exactly one is correct. Key version `v1`.

| Question | Text | Code | Choices | Correct | Explanation |
|---|---|---|---|---|---|
| `q1` | What should a well-designed function have? | none | a: A single, focused responsibility; b: As many responsibilities as possible; c: No descriptive name | `a` | One focused responsibility makes a function easier to understand, test and change. |
| `q2` | Why do we keep automated tests alongside our code? | none | a: To make the repository larger; b: To catch regressions when code changes; c: To avoid ever reviewing code | `b` | Tests protect expected behaviour and can catch regressions introduced by later changes. |
| `q3` | What does this Python code print? | `values = [1, 2, 3]` newline `print(len(values))` | a: 2; b: 4; c: 3 | `c` | len returns the number of items. The list contains three items. |

## Acceptance criteria
- [ ] AC1: Reading a set returns its id, title and the questions in order, each with id, text, code (or null) and choices (id, text). No correct answer, explanation or key version appears in this response.
- [ ] AC2: A student can start an attempt on a set; it begins `in_progress` with no answers. Starting requires the student header and an existing set.
- [ ] AC3: A student can save and revise answers (question id to choice id) any number of times before submission. Unknown questions and choices not belonging to the question are rejected.
- [ ] AC4: Submitting with any question unanswered is rejected, lists the missing question ids in set order, keeps the attempt `in_progress`, preserves the saved answers, and unlocks nothing.
- [ ] AC5: Submitting a complete attempt succeeds once, marks it `submitted`, and returns the score as correct and total. The score is computed by the server from the saved answers; anything the client sends is ignored.
- [ ] AC6: After submission, answers can no longer be changed and the attempt cannot be submitted again.
- [ ] AC7: Results are available only for a submitted attempt, and contain: the student's answers, the score, the key version, and for each question the selected choice, the correct choice, whether it was correct and the explanation.
- [ ] AC8: For an unsubmitted attempt, no response from any endpoint contains a correct choice or explanation text, including error responses.
- [ ] AC9: A student cannot read, change, submit or see results of another student's attempt, and cannot tell whether such an attempt exists.
- [ ] AC10: Each attempt is independent; a student may start several attempts on the same set.
- [ ] AC11: The existing health endpoints keep working.

## Out of scope
Real authentication, persistence, teacher-authored sets, publishing, the AI assistant, per-question feedback, frontend changes, and any code execution.

## Security and safeguards
- Answer key and explanations stay in server-side data only and are read solely when building results for a submitted attempt.
- Ownership is checked on every attempt endpoint before any other behaviour.
- Scores are never taken from the client.
- Error bodies must not echo the answer key.

## Open questions
None. The header-based identity is a deliberate placeholder.
