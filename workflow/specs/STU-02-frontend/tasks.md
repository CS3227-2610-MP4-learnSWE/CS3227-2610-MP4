# Tasks: STU-02-frontend Student Practice page on the real API

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design Playwright tests for AC1-AC12 with the shared API mock helper (no `src/` access) | test-designer | spec + plan approved | done |
| 2 | Implement per plan: API client, practice state, page, teacher demo data split, lazy teacher/admin, companion link | developer | spec + plan approved | done |
| 3 | Update docs: UserGuide, DeveloperGuide, security test log, notes | developer | 2 | done |
| 4 | Run typecheck, lint, format check and the Playwright suite; report pass/fail | test-designer | 1, 2 | done |
| 5 | Verify: code, docs and security review; re-run suite | verifier | 4 | done |
| 6 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 5 | done |
| 7 | Approved real-backend end-to-end test and CI job | developer | 2 | done |

Tasks 1 and 2 run in parallel.

## Completion record (30 Oct 2026)
All seven tasks were delivered in merged PR 5 (`4a9b541`). Variant B used two fix rounds; verifier PASS at `d1f8392` recorded 62 mocked tests twice, 60 backend tests and one real-backend test. The later single-session colour fix brought the mocked suite to 65 and was not independently verified. Dark-mode colours still need an eye check. These are historical results, not tests re-run during the docs update; GitHub CI status was not independently checked here. Real login, persistence and AI remain out of scope.
