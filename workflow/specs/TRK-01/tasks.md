# Tasks: TRK-01 Token usage tracker

Built in a single session (spec-first, tests-first); this is not an experiment run.

| # | Task | Owner | Depends on | Status |
|---|---|---|---|---|
| 1 | Write failing unittest suites for AC1-AC9 | session | spec | todo |
| 2 | Implement model, claude_logs, codex_logs | session | 1 | todo |
| 3 | Implement pricing, export, report, CLI | session | 2 | todo |
| 4 | Run on real local logs; compare totals with the Claude app's own usage view | user + session | 3 | todo |
| 5 | Fill `prices.json` from official pricing, with date | user | 3 | todo |
| 6 | README for the tool; gitignore local CSVs; link from developer guide | session | 3 | todo |
