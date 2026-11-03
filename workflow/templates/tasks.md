# Tasks: <FEATURE-ID> <name>

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design tests for each acceptance criterion (no src/ access) | test-designer | spec + plan approved | todo |
| 2 | Implement per plan contract | developer | spec + plan approved | todo |
| 3 | Run suite; report pass/fail | test-designer | 1, 2, 6, 7 | todo |
| 4 | Verify: code, docs and security review; re-run suite | verifier | 3 | todo |
| 5 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 4 | todo |
| 6 | Records only: concurrent-request test. Two or more simultaneous requests on the same record (create, update, submit) leave one consistent result; none is lost or applied twice | test-designer | spec + plan approved | todo |
| 7 | Records only: cross-user test. A second user of the same and of another role, and a user of another course, cannot read or change the first user's records | test-designer | spec + plan approved | todo |

Tasks 1, 2, 6 and 7 run in parallel. Keep tasks 6 and 7 for any feature that reads or writes stored records; delete them, with a note in the spec, if it does not.
