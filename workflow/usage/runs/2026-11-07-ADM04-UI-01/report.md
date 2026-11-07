# Feature-run report: 2026-11-07-ADM04-UI-01

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-07-ADM04-UI-01 | 2026-11-07-ADM04-UI-01-developer-01 | developer | gpt-6.1-sol | inherited | 0:33:50 | 36 | 11651476 | unavailable |
| feature_run_total | 2026-11-07-ADM04-UI-01 |  | TOTAL | gpt-6.1-sol |  | 0:33:50 | 36 | 11651476 | unavailable |

Scope: one main developer session, including its housekeeping; no delegated agents. Closeout snapshot uses existing tracker parsed provider records filtered to this exact request/time window, with identical inherited copies deduplicated. Earlier feature development/chat/research excluded. Cached input is included; token volume is not a bill. Pricing may be unavailable.

Tracking deviation: manifest reconstructed at closeout from the exact user-message timestamp; it was not created before work. Existing run-report renderer used after filtering because the standard CLI rejects earlier records from a reused session outside this task window. No raw logs or exports committed.
