# Security test log

| Date | Feature | Case | Expected | Actual | Fix / status |
|---|---|---|---|---|---|
| 2026-10-29 | STU-02 | Attempt endpoint without `X-Student-Id`, or whitespace-only | 401 `missing_student` | 401 | Pass |
| 2026-10-29 | STU-02 | Other student reads/saves/submits/gets results of an attempt | 404 `attempt_not_found`, identical to a nonexistent id | 404, same body | Pass |
| 2026-10-29 | STU-02 | Malformed PUT body for another student's or a nonexistent attempt | indistinguishable | same 422 for both | Pass (non-blocking: 422 precedes 404) |
| 2026-10-29 | STU-02 | Read set / in-progress save / 422 invalid choice / incomplete submit / results before submit | no correct choice, explanation or key version | none present | Pass |
| 2026-10-29 | STU-02 | Incomplete submit with client `score` in query/body | 422 `incomplete`, client score ignored | 422, missing in set order | Pass |
| 2026-10-29 | STU-02 | `/openapi.json`, `/docs` | schema only, no fixture answers | field names only, no key values | Pass |
| 2026-10-29 | STU-02 | Attempt id guessability; path traversal and NUL ids | opaque id; 404 | 22-char urlsafe token; 404 | Pass |
| 2026-10-29 | STU-02 | Concurrent save and submit | atomic | per-attempt lock added | Fixed (tests/test_stu02_fixes.py) |
| 2026-10-29 | STU-02 | Header variants (padded, duplicate) | no cross-student access | separate students; last duplicate wins | Pass; goes away with SHR-01 |
| 2026-10-29 | STU-02 | Committed secrets; AI prompt injection | none; not applicable | none; no AI in this slice | Pass / n/a |
| 2026-10-30 | STU-02-frontend | Student scripts for `/student/practice` searched for fixture explanations | none present; teacher data only in the lazy Teacher chunk | explanation texts only in the Teacher chunk; student chunks hold the field name `correct_choice` only | Pass (built bundle checked) |
| 2026-10-30 | STU-02-frontend | Results request before successful submit | none sent | results requested only after submit 200 or 409 (code path) | Pass: tests/practice.spec.ts "security results are requested only after a successful submit" |
| 2026-10-30 | STU-02-frontend | Server text (question, choice, explanation) rendered | shown as text, not HTML | React text nodes only, no `dangerouslySetInnerHTML` | Pass: tests/practice.spec.ts "security server text is rendered as text, never as HTML" |
| 2026-10-30 | STU-02-frontend | Double click on Submit | one submit flow | button disabled and a `busy` guard | Pass: tests/practice.spec.ts "a double click on Submit sends one flow" and "the submit button is disabled while a submit is running" |
