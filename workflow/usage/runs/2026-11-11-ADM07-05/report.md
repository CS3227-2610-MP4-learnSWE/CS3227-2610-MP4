# Feature-run report: 2026-11-11-ADM07-05

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-11-ADM07-05 | 2026-11-11-ADM07-05-orchestrator-01 | orchestrator | claude-sonnet-5-5 | inherited | 7:37:34 | 87 | 13627391 | 3.425728 |
| invocation | 2026-11-11-ADM07-05 | 2026-11-11-ADM07-05-test-designer-01 | test-designer | claude-sonnet-5-5 | inherited | 0:13:30 | 44 | 6583052 | 1.965532 |
| invocation | 2026-11-11-ADM07-05 | 2026-11-11-ADM07-05-developer-01 | developer | claude-sonnet-5-5 | inherited | 0:09:51 | 47 | 2911035 | 0.752359 |
| invocation | 2026-11-11-ADM07-05 | 2026-11-11-ADM07-05-verifier-01 | verifier | claude-opus-5-5 | inherited | 0:22:46 | 22 | 829414 | 0.792773 |
| invocation | 2026-11-11-ADM07-05 | 2026-11-11-ADM07-05-spec-writer-01 | spec-writer | claude-sonnet-5-5 | inherited | 0:00:46 | 4 | 111719 | 0.160098 |
| feature_run_total | 2026-11-11-ADM07-05 |  | TOTAL | claude-opus-5-5; claude-sonnet-5-5 |  | 7:37:34 | 204 | 24062611 | 7.096491 |
