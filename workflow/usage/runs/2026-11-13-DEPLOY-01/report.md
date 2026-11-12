# Feature-run report: 2026-11-13-DEPLOY-01

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-orchestrator-01 | orchestrator |  | unavailable | 0:03:59 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-spec-writer-01 | spec-writer |  | unavailable | 0:03:59 | 0 | unavailable | unavailable |
| feature_run_total | 2026-11-13-DEPLOY-01 |  | TOTAL |  |  | 0:03:59 | 0 | unavailable | unavailable |

No usage records matched these invocations; verify the source IDs or confirm that they made no model calls: 2026-11-13-DEPLOY-01-orchestrator-01, 2026-11-13-DEPLOY-01-spec-writer-01.

Attribution limitation: source session IDs were resolved from local session_meta. The normal exporter rejected usage from earlier in the same parent session as outside this invocation interval; host/log timestamp alignment is also unverified. Report regenerated against an empty temporary export source to preserve the invocation table without inventing totals. Zero observed requests means unavailable attribution, not zero actual use. Model identifier observed in parent metadata: gpt-6.1-sol; requested effort unavailable. Finish timestamps are closeout observation bounds, not exact sampled return times. Run is awaiting spec/plan approval and hosting account access, not complete.
