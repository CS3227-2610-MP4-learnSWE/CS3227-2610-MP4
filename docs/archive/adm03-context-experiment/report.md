# Feature-run report: 2026-11-07-ADM03-01

**Experiment closed on9Nov2026; adoption rejected.** The19-invocation table below is frozen. ADM-03 remains incomplete/U63blocking. Conclusion (kept on branch test/adm03-u63-2026-11-09) explains the ADM-04 comparison; future repair/closure-maintenance usage is not added to this feature snapshot.

Format: `invocation-v1`

Elapsed values are wall-clock durations. The run total is latest finish minus earliest start, so parallel agent time is not added twice.

Token usage = uncached input + cache reads + cache writes + output. Reasoning is already included in output and is not added again. Unmatched usage and incomplete totals are unavailable, not zero.

| Record | Feature run ID | Invocation ID | Role | Model(s) | Effort | Elapsed | Requests | Token usage | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-orchestrator-01 | orchestrator | gpt-6.1-sol | low | 1 day, 2:22:35 | 329 | 63241788 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-spec-writer-01 | spec-writer | gpt-6.1-sol | medium | 0:05:52 | 11 | 405376 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-developer-01 | developer | gpt-6.1-sol | medium | 0:01:55 | 9 | 405034 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-01 | test-designer | gpt-6.1-sol | medium | 0:10:49 | 27 | 1979146 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-spec-writer-02 | spec-writer | gpt-6.1-sol | medium | 0:02:01 | 8 | 324019 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-developer-02 | developer | gpt-6.1-sol | medium | 0:40:44 | 107 | 13696361 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-02 | test-designer | gpt-6.1-sol | medium | 0:08:40 | 43 | 3606744 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-verifier-01 | verifier | gpt-6-astra | high | 8:38:09 | 16 | 1127820 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-verifier-02 | verifier | gpt-6-astra | high | 0:11:09 | 36 | 3370868 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-developer-03 | developer | gpt-6.1-sol | medium | 0:25:57 | 86 | 8967466 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-03 | test-designer | gpt-6.1-sol | medium | 0:07:07 | 33 | 2382383 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-04 | test-designer | gpt-6.1-sol | medium | 0:25:37 | 105 | 9631541 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-verifier-03 | verifier | gpt-6-astra | high | 5:39:04 | 50 | 5345519 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-verifier-04 | verifier | gpt-6-astra | high | 0:05:42 | 14 | 950380 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-developer-04 | developer | gpt-6.1-sol | medium | 0:24:51 | 72 | 5782263 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-05 | test-designer | gpt-6.1-sol | medium | 0:05:59 | 21 | 1339950 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-06 | test-designer | gpt-6.1-sol | medium | 0:10:58 | 26 | 1477311 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-test-designer-07 | test-designer | gpt-6.1-sol | medium | 0:10:26 | 34 | 1883741 | unavailable |
| invocation | 2026-11-07-ADM03-01 | 2026-11-07-ADM03-01-verifier-05 | verifier | gpt-6-astra | high | 0:13:46 | 36 | 3755158 | unavailable |
| feature_run_total | 2026-11-07-ADM03-01 |  | TOTAL | gpt-6-astra; gpt-6.1-sol |  | 1 day, 2:22:35 | 1063 | 129672868 | unavailable |

Status at experiment end: user stopped the handoff and declined an extra round; feature NOT complete. Both allowed correction rounds used. Independent focused7/backend1612/browser817 allPASS, but final strongest probe1FAIL confirms U63: transient non-timeout cleanup failure returns terminal502 while durable request stays pending and immediate replay409. No third source correction, PR, push or deployment performed. Proposal in workflow/specs/ADM-03/extra-round-proposal.md; approval pending.

All19actualinvocations+total inspected, single Token usage column. Three provider-limit interruptions retained; exact interrupted returns bounded in manifest/notes, whole window includes user/idle time, not active inference. Placeholder for unlaunched verifier05 was removed before actual launch, no fake zero use. Pricing/context metrics unavailable. Observed snapshot excludes later reporting/final-message tail and does not establish completed-feature usage or billed cost. Workflow-policy implementation excluded; frozen historical cohort unchanged.
