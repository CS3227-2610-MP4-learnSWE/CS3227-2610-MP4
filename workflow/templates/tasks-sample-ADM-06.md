# Tasks: ADM-06 AI usage monitoring (sample)

Sample only, to show the standing tasks 6 and 7 filled in for a feature that reads stored records. It is not an approved task list; the spec-writer produces the real one in `workflow/specs/ADM-06/`.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design tests for each acceptance criterion in US-ADM-06-01 and US-ADM-06-02 (no src/ access) | test-designer | spec + plan approved | todo |
| 2 | Implement per plan contract | developer | spec + plan approved | todo |
| 3 | Run suite; report pass/fail | test-designer | 1, 2, 6, 7 | todo |
| 4 | Verify: code, docs and security review; re-run suite | verifier | 3 | todo |
| 5 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 4 | todo |
| 6 | Records only: concurrent-request test. Many AI requests recorded at the same moment, mixed with reads of the usage view, give counts equal to the number of requests; no request is lost or counted twice | test-designer | spec + plan approved | todo |
| 7 | Records only: cross-user test. A student, a teacher and a signed-out caller cannot read the usage view or its counts; the view shows no credentials, request text or user identifiers | test-designer | spec + plan approved | todo |

Tasks 1, 2, 6 and 7 run in parallel.
