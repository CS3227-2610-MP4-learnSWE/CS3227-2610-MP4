# Invocation report: 2026-11-09-ADM01-A2

Format: `invocation-v2`

Sessions: bacb5410-87a0-471b-8397-c366b23e7a26

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-A2-orchestrator-01 | orchestrator |  | bacb5410-87a0-471b-8397-c366b23e7a26 |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T14:00:29.274Z | 2026-11-09T14:52:39.370Z | 3130.1 | 19 | 52 | 1541377 | 0 | 47847 | 4464 | 245 | 0.390270 |
| 2026-11-09-ADM01-A2-developer-01 | developer |  | bacb5410-87a0-471b-8397-c366b23e7a26 | ae0fb70bb4657a2be | 1 | 2026-11-09-ADM01-A2-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T14:00:55.376Z | 2026-11-09T14:23:21.100Z | 1345.7 | 36 | 72 | 1973394 | 72511 | 0 | 24186 | 3319 | 0.620621 |
| 2026-11-09-ADM01-A2-test-designer-01 | test-designer |  | bacb5410-87a0-471b-8397-c366b23e7a26 | a6e92fc8ccf37bab9 | 1 | 2026-11-09-ADM01-A2-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T14:00:55.388Z | 2026-11-09T14:04:13.020Z | 197.6 | 12 | 24 | 447306 | 64659 | 0 | 23295 | 2099 | 0.439376 |
| 2026-11-09-ADM01-A2-test-designer-02 | test-designer |  | bacb5410-87a0-471b-8397-c366b23e7a26 | a6e92fc8ccf37bab9 | 2 | 2026-11-09-ADM01-A2-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T14:23:30.778Z | 2026-11-09T14:40:06.618Z | 995.8 | 25 | 52 | 1757942 | 73693 | 0 | 6607 | 623 | 0.426201 |
| 2026-11-09-ADM01-A2-verifier-01 | verifier |  | bacb5410-87a0-471b-8397-c366b23e7a26 | a2d64c22568078e47 | 1 | 2026-11-09-ADM01-A2-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-09T14:40:25.423Z | 2026-11-09T14:45:48.312Z | 322.9 | 10 | 20 | 230690 | 31749 | 0 | 6914 | 1854 | 0.343243 |
| 2026-11-09-ADM01-A2-developer-02 | developer |  | bacb5410-87a0-471b-8397-c366b23e7a26 | ae0fb70bb4657a2be | 2 | 2026-11-09-ADM01-A2-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T14:45:55.519Z | 2026-11-09T14:48:36.263Z | 160.7 | 7 | 16 | 452952 | 77449 | 0 | 3291 | 150 | 0.271860 |
| 2026-11-09-ADM01-A2-verifier-02 | verifier |  | bacb5410-87a0-471b-8397-c366b23e7a26 | a2d64c22568078e47 | 2 | 2026-11-09-ADM01-A2-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-09T14:48:45.222Z | 2026-11-09T14:52:13.661Z | 208.4 | 4 | 10 | 143441 | 7346 | 0 | 2344 | 40 | 0.112338 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-09T14:00:29.274Z | 2026-11-09T14:52:39.370Z | 3130.1 | 113 | 246 | 6547102 | 327407 | 47847 | 71101 | 8330 | 2.603908 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-A2-orchestrator-01 | 0.0549 | 0.9699 | 0 | 3 | 6264 | 71336 | 93715 | 83646.1 |
| 2026-11-09-ADM01-A2-developer-01 | 0.1372 | 0.9645 | 0 | 0 | 0 | 11296 | 72513 | 56832.7 |
| 2026-11-09-ADM01-A2-test-designer-01 | 0.0901 | 0.8737 | 0 | 0 | 0 | 11732 | 64661 | 42665.8 |
| 2026-11-09-ADM01-A2-test-designer-02 | 0.0943 | 0.9597 | 0 | 0 | 0 | 66473 | 78590 | 73267.5 |
| 2026-11-09-ADM01-A2-verifier-01 | 0.2682 | 0.8790 | 0 | 0 | 0 | 11009 | 31751 | 26245.9 |
| 2026-11-09-ADM01-A2-developer-02 | 0.0456 | 0.8540 | 0 | 0 | 0 | 73952 | 77451 | 75773.9 |
| 2026-11-09-ADM01-A2-verifier-02 | 0.0171 | 0.9512 | 0 | 0 | 0 | 35580 | 39097 | 37699.2 |
| TOTAL | 0.1172 | 0.9458 | 0 | 3 | 6264 |  | 93715 | 61262.0 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-A2-orchestrator-01 | 12 | 0 | Agent=3; Bash=6; SendMessage=3 | 0 | 0 | 0 | 2 | 3114.7 | 33.6 | 12 | unavailable |
| 2026-11-09-ADM01-A2-developer-01 | 53 | 3 | Bash=31; Edit=7; Read=5; SubagentHandback=1; Write=9 | 5 | 5 | 0 | 0 | 1332.2 | 1211.3 | 53 | unavailable |
| 2026-11-09-ADM01-A2-test-designer-01 | 23 | 1 | Bash=4; Edit=1; Grep=3; Read=11; SubagentHandback=1; Write=3 | 11 | 10 | 1 | 0 | 189.0 | 31.7 | 23 | unavailable |
| 2026-11-09-ADM01-A2-test-designer-02 | 28 | 5 | Bash=17; Edit=1; Grep=1; Monitor=1; Read=7; SubagentHandback=1 | 7 | 5 | 2 | 0 | 991.3 | 904.2 | 28 | 9.7 |
| 2026-11-09-ADM01-A2-verifier-01 | 10 | 1 | Bash=9; SubagentHandback=1 | 0 | 0 | 0 | 0 | 319.2 | 244.8 | 10 | 18.8 |
| 2026-11-09-ADM01-A2-developer-02 | 6 | 0 | Bash=5; SubagentHandback=1 | 0 | 0 | 0 | 0 | 158.0 | 125.7 | 6 | 7.2 |
| 2026-11-09-ADM01-A2-verifier-02 | 4 | 0 | Bash=3; SubagentHandback=1 | 0 | 0 | 0 | 0 | 204.8 | 182.6 | 4 | 9.0 |
| TOTAL | 136 | 10 | Agent=3; Bash=75; Edit=9; Grep=4; Monitor=1; Read=23; SendMessage=3; SubagentHandback=6; Write=12 | 23 | 20 | 3 | 2 |  | 2733.9 | 136 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-A2-orchestrator-01 | 0.000104 | 0.154138 | 0.000000 | 0.191388 | 0.044640 | 0.390270 |
| 2026-11-09-ADM01-A2-developer-01 | 0.000144 | 0.197339 | 0.181278 | 0.000000 | 0.241860 | 0.620621 |
| 2026-11-09-ADM01-A2-test-designer-01 | 0.000048 | 0.044731 | 0.161648 | 0.000000 | 0.232950 | 0.439376 |
| 2026-11-09-ADM01-A2-test-designer-02 | 0.000104 | 0.175794 | 0.184232 | 0.000000 | 0.066070 | 0.426201 |
| 2026-11-09-ADM01-A2-verifier-01 | 0.000080 | 0.046138 | 0.158745 | 0.000000 | 0.138280 | 0.343243 |
| 2026-11-09-ADM01-A2-developer-02 | 0.000032 | 0.045295 | 0.193622 | 0.000000 | 0.032910 | 0.271860 |
| 2026-11-09-ADM01-A2-verifier-02 | 0.000040 | 0.028688 | 0.036730 | 0.000000 | 0.046880 | 0.112338 |
| TOTAL | 0.000552 | 0.692123 | 0.916255 | 0.191388 | 0.803590 | 2.603908 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-A2-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-A2-developer-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-A2-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-A2-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-A2-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-A2-developer-02 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-A2-verifier-02 |  |  |  |  |  |  |  |
