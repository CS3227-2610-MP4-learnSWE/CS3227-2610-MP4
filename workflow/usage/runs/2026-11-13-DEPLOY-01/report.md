# Feature-run report: 2026-11-13-DEPLOY-01

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-orchestrator-01 | orchestrator |  | unavailable | 0:03:59 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-spec-writer-01 | spec-writer |  | unavailable | 0:03:59 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-orchestrator-02 | orchestrator |  | unavailable | 6:24:34 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-test-designer-01 | test-designer |  | unavailable | 0:09:08 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-developer-01 | developer |  | unavailable | 6:24:34 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-test-designer-02 | test-designer |  | unavailable | 0:07:14 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-verifier-01 | verifier |  | high | 6:10:46 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-test-designer-03 | test-designer |  | unavailable | 6:08:12 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-orchestrator-03 | orchestrator |  | unavailable | 0:09:50 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-developer-02 | developer |  | unavailable | 0:02:39 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-verifier-02 | verifier |  | high | 0:09:50 | 0 | unavailable | unavailable |
| invocation | 2026-11-13-DEPLOY-01 | 2026-11-13-DEPLOY-01-developer-03 | developer |  | unavailable | 0:07:11 | 0 | unavailable | unavailable |
| feature_run_total | 2026-11-13-DEPLOY-01 |  | TOTAL |  |  | 6:39:46 | 0 | unavailable | unavailable |

No usage records matched these invocations; verify the source IDs or confirm that they made no model calls: 2026-11-13-DEPLOY-01-orchestrator-01, 2026-11-13-DEPLOY-01-spec-writer-01, 2026-11-13-DEPLOY-01-orchestrator-02, 2026-11-13-DEPLOY-01-test-designer-01, 2026-11-13-DEPLOY-01-developer-01, 2026-11-13-DEPLOY-01-test-designer-02, 2026-11-13-DEPLOY-01-verifier-01, 2026-11-13-DEPLOY-01-test-designer-03, 2026-11-13-DEPLOY-01-orchestrator-03, 2026-11-13-DEPLOY-01-developer-02, 2026-11-13-DEPLOY-01-verifier-02, 2026-11-13-DEPLOY-01-developer-03.

Checkpoint status: code review and local validation complete; awaiting latest CI, teammate review/merge and live provisioning. Not a completed deployment.

Attribution limitation: provider session IDs were resolved from local session_meta. Normal run-report rejects earlier parent-session usage outside the workflow interval; nested subagent metadata also limits attribution. Report generated against an empty temporary export source rather than invent totals. Zero observed requests means unavailable attribution, not zero actual usage. All interrupted/recovered finish timestamps are observation bounds, not exact return times. Model metadata: parent gpt-6.1-sol; verifier gpt-6-astra/high. Other requested effort unavailable. No raw provider logs or credentials committed.
