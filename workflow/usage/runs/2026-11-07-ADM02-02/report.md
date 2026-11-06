# Feature-run report: 2026-11-07-ADM02-02

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-developer-01 | developer |  | inherited | 0:25:24 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-test-designer-01 | test-designer |  | inherited | 0:11:57 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-test-designer-02 | test-designer |  | inherited | 0:22:47 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-developer-02 | developer |  | inherited | 0:01:13 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-verifier-01 | verifier |  | high | 0:09:37 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-developer-03 | developer |  | inherited | 0:06:23 | 0 | unavailable | unavailable |
| invocation | 2026-11-07-ADM02-02 | 2026-11-07-ADM02-02-verifier-02 | verifier |  | high | 0:13:47 | 0 | unavailable | unavailable |
| feature_run_total | 2026-11-07-ADM02-02 |  | TOTAL |  |  | 0:57:35 | 0 | unavailable | unavailable |

No usage records matched these invocations; verify the source IDs or confirm that they made no model calls: 2026-11-07-ADM02-02-developer-01, 2026-11-07-ADM02-02-test-designer-01, 2026-11-07-ADM02-02-test-designer-02, 2026-11-07-ADM02-02-developer-02, 2026-11-07-ADM02-02-verifier-01, 2026-11-07-ADM02-02-developer-03, 2026-11-07-ADM02-02-verifier-02.

## Recovery limitations

Actual tokens/cost are unavailable, not zero. Metadata-only recovery evidence is in recovery-metadata.json. Current Codex parser cannot safely attribute nested subagent metadata and repeated parent-session metadata. No raw prompts/replies were copied. Interrupted designer-02/verifier-02 return times use last-observed log bounds, not exact returns. This historic seven-invocation manifest omits orchestrator and browser follow-up usage. TRK-03 richer v2 remains Claude-only.
