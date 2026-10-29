# Tasks: <FEATURE-ID> <name>

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design tests for each acceptance criterion (no src/ access) | test-designer | spec + plan approved | todo |
| 2 | Implement per plan contract | developer | spec + plan approved | todo |
| 3 | Run suite; report pass/fail | test-designer | 1, 2 | todo |
| 4 | Verify: code, docs and security review; re-run suite | verifier | 3 | todo |
| 5 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 4 | todo |

Tasks 1 and 2 run in parallel.
