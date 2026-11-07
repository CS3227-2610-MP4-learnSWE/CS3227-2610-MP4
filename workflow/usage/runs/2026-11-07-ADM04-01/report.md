# Feature-run report: 2026-11-07-ADM04-01

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-orchestrator-01 | orchestrator | gpt-6.1-sol | inherited | 13:16:05 | unavailable | unavailable | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-spec-writer-01 | spec-writer | gpt-6.1-sol | inherited | 0:04:42 | 12 | 497316 | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-developer-01 | developer | gpt-6.1-sol | inherited | 0:18:09 | 100 | 11487602 | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-test-designer-01 | test-designer | gpt-6.1-sol | inherited | 0:12:28 | 78 | 8094631 | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-test-designer-02 | test-designer | gpt-6.1-sol | inherited | 7:45:58 | 33 | 6075065 | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-developer-02 | developer | gpt-6.1-sol | inherited | 0:00:59 | 6 | 1090790 | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-verifier-01 | verifier | gpt-6-astra | high | 7:40:41 | 9 | 411649 | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-test-designer-03 | test-designer |  | inherited | 5:04:29 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM04-01 | 2026-11-07-ADM04-01-verifier-02 | verifier | gpt-6-astra | high | 0:16:32 | 54 | 5178621 | unavailable |
| feature_run_total | 2026-11-07-ADM04-01 |  | TOTAL | gpt-6-astra; gpt-6.1-sol |  | 13:16:05 | unavailable | unavailable | unavailable |

No usage records matched these invocations; verify the source IDs or confirm that they made no model calls: 2026-11-07-ADM04-01-test-designer-03.

Attribution limitation: inherited metadata in forked Codex logs prevents reliable isolated parent totals; parent requests/tokens/cost and whole-run totals are explicitly unavailable. Child rows retain matched observed provider records. No guessed or zero-use totals.

Interruption bounds: designer-02 and verifier-01 finish times use the recovery upper bound, not exact returns; lower/upper bounds are in logs/Adm04Implementation.md. Their elapsed values and main wall time include the interruption, not continuous model work.

Status: completed locally; draft PR31 opened, remote CI/team review pending.
