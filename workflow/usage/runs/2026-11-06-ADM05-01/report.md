# Feature-run report: 2026-11-06-ADM05-01

Format: `invocation-v1`

**Attribution limitation:** Child provider-session IDs are unavailable; their inherited environment ID is the parent session, not an independent source. Child rows below are unavailable, not zero use. The numeric total is only the matched parent-log subtotal, not complete feature-run usage. The parent window includes earlier ADM-05 advice/requirements discussion, using the earliest observed log timestamp because the tracker rejects same-session rows outside the manifest window. Prices/cost are unavailable. The interrupted first developer interval includes interruption/idle time.


Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-spec-writer-1 | spec-writer | unavailable | inherited | 0:03:24 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-developer-1 | developer | unavailable | inherited | 0:05:18 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-test-designer-1 | test-designer | unavailable | inherited | 0:08:40 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-spec-writer-2 | spec-writer | unavailable | inherited | 0:01:13 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-developer-2 | developer | unavailable | inherited | 0:11:16 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-orchestrator-1 | orchestrator | gpt-6.1-sol | inherited | 0:56:52 | 543 | 598671 | 59384448 | 0 | 0 | 137384 | 27251 | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-test-designer-2 | test-designer | unavailable | inherited | 0:17:05 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-developer-3 | developer | unavailable | inherited | 0:01:51 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-spec-writer-3 | spec-writer | unavailable | inherited | 0:01:31 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-developer-4 | developer | unavailable | inherited | 0:02:04 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-verifier-1 | verifier | unavailable | high | 0:10:39 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| invocation | 2026-11-06-ADM05-01 | 2026-11-06-ADM05-01-developer-5 | developer | unavailable | inherited | 0:01:39 | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable | unavailable |
| feature_run_total | 2026-11-06-ADM05-01 |  | MATCHED LOG SUBTOTAL (incomplete) | gpt-6.1-sol |  | 0:56:52 | 543 | 598671 | 59384448 | 0 | 0 | 137384 | 27251 | unavailable |

No usage records matched these invocations; verify the source IDs or confirm that they made no model calls: 2026-11-06-ADM05-01-spec-writer-1, 2026-11-06-ADM05-01-developer-1, 2026-11-06-ADM05-01-test-designer-1, 2026-11-06-ADM05-01-spec-writer-2, 2026-11-06-ADM05-01-developer-2, 2026-11-06-ADM05-01-test-designer-2, 2026-11-06-ADM05-01-developer-3, 2026-11-06-ADM05-01-spec-writer-3, 2026-11-06-ADM05-01-developer-4, 2026-11-06-ADM05-01-verifier-1, 2026-11-06-ADM05-01-developer-5.

The tracker generated this report; unavailable-source cells and the subtotal label were annotated during closeout to avoid treating unmatched logs as zero usage. Requested verifier model: gpt-6-astra, high; its actual token attribution is unavailable.
