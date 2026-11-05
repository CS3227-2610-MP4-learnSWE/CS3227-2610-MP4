# Tasks: TRK-02 Per-invocation usage reports

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Write tests for manifest validation, repeated invocations, attribution, Markdown and totals | test-designer | approved spec + plan | done |
| 2 | Implement manifest parsing and feature-run report rendering | developer | approved spec + plan; tests | done |
| 3 | Add `run-report` CLI command and preserve current commands | developer | 1, 2 | done |
| 4 | Update usage archive and workflow instructions | developer | 2, 3 | done |
| 5 | Run tracker tests and manually inspect a generated synthetic report | developer | 1-4 | done |
