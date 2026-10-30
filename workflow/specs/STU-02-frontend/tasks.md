# Tasks: STU-02-frontend Student Practice page on the real API

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design Playwright tests for AC1-AC12 with the shared API mock helper (no `src/` access) | test-designer | spec + plan approved | todo |
| 2 | Implement per plan: API client, practice state, page, teacher demo data split, lazy teacher/admin, companion link | developer | spec + plan approved | todo |
| 3 | Update docs: UserGuide, DeveloperGuide, security test log, notes | developer | 2 | todo |
| 4 | Run typecheck, lint, format check and the Playwright suite; report pass/fail | test-designer | 1, 2 | todo |
| 5 | Verify: code, docs and security review; re-run suite | verifier | 4 | todo |
| 6 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 5 | todo |
| 7 | (If approved) real-backend end-to-end test and CI job | developer | 2 | todo |

Tasks 1 and 2 run in parallel.
