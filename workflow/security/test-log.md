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
| 2026-10-29 | STU-02 | Concurrent save and submit | atomic | no lock; race possible | Open, non-blocking (in-memory placeholder) |
| 2026-10-29 | STU-02 | Header variants (padded, duplicate) | no cross-student access | separate students; last duplicate wins | Pass; goes away with SHR-01 |
| 2026-10-29 | STU-02 | Committed secrets; AI prompt injection | none; not applicable | none; no AI in this slice | Pass / n/a |
