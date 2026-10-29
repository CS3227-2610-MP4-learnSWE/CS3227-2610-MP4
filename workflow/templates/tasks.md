# Tasks: <FEATURE-ID> <name>

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design tests for each acceptance criterion (no src/ access) | test-designer | spec + plan approved | todo |
| 2 | Implement per plan contract | developer | spec + plan approved | todo |
| 3 | Run suite; report pass/fail | test-designer | 1, 2 | todo |
| 4 | Review and docs check | reviewer | 3 | todo |
| 5 | Security checks and adversarial tests | security-reviewer | 3 | todo |
| 6 | Fix defects (max 2 rounds) | developer | 3-5 | todo |

Tasks 1 and 2 run in parallel; tasks 4 and 5 may run in parallel.
