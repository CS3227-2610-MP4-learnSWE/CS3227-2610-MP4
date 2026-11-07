# Feature-run report: 2026-11-07-ADMIN-UI-01

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-07-ADMIN-UI-01 | 2026-11-07-ADMIN-UI-01-developer-01 | developer | gpt-6.1-sol | inherited | 0:16:06 | 46 | unavailable | unavailable |
| feature_run_total | 2026-11-07-ADMIN-UI-01 |  | TOTAL | gpt-6.1-sol |  | 0:16:06 | 46 | unavailable | unavailable |

Scope: one main developer invocation, no delegated agents. Manifest recorded after initial read-only discovery and before spec/test/source changes. This is a closeout snapshot of observed provider events inside the recorded time window; final reporting tail is not included.

The standard run-report CLI was executed but rejected earlier requests from this reused source session outside the invocation window. The existing tracker parser/pricing/renderer generated this report after exact source/time filtering and identical-row deduplication. No raw logs or row exports committed; no measured cost is inferred when pricing is unavailable.

Observed provider subtotal within the recorded snapshot: 46 requests and 7,109,961 tokens including cache reads. Complete invocation/run token totals are unavailable because the final reporting tail is outside that snapshot; no zero-use or complete-cost claim.
