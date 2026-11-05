# Invocation report: 2026-11-05-ADM01-A

Format: `invocation-v2`

Sessions: c4975c87-0699-46f6-bcd9-5bfadb160b6d

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-A-orchestrator-01 | orchestrator |  | c4975c87-0699-46f6-bcd9-5bfadb160b6d |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T11:07:37.900Z | 2026-11-05T11:15:25.668Z | 467.8 | 11 | 30 | 580433 | 0 | 37391 | 4280 | 445 | 0.250467 |
| 2026-11-05-ADM01-A-developer-01 | developer |  | c4975c87-0699-46f6-bcd9-5bfadb160b6d | add3dd28c19553c7f | 1 | 2026-11-05-ADM01-A-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T11:07:55.114Z | 2026-11-05T11:11:18.750Z | 203.6 | 17 | 34 | 762693 | 68153 | 0 | 17180 | 1199 | 0.418520 |
| 2026-11-05-ADM01-A-test-designer-01 | test-designer |  | c4975c87-0699-46f6-bcd9-5bfadb160b6d | af013de0604154c0c | 1 | 2026-11-05-ADM01-A-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T11:07:55.137Z | 2026-11-05T11:11:59.231Z | 244.1 | 10 | 20 | 376951 | 74356 | 0 | 30203 | 6779 | 0.525655 |
| 2026-11-05-ADM01-A-test-designer-02 | test-designer |  | c4975c87-0699-46f6-bcd9-5bfadb160b6d | af013de0604154c0c | 2 | 2026-11-05-ADM01-A-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T11:12:06.660Z | 2026-11-05T11:13:27.840Z | 81.2 | 11 | 24 | 884783 | 10365 | 0 | 4428 | 571 | 0.158719 |
| 2026-11-05-ADM01-A-verifier-01 | verifier |  | c4975c87-0699-46f6-bcd9-5bfadb160b6d | aac61ae03b26b64d4 | 1 | 2026-11-05-ADM01-A-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T11:13:42.091Z | 2026-11-05T11:15:10.727Z | 88.6 | 7 | 14 | 147474 | 35109 | 0 | 6614 | 2272 | 0.337376 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-05T11:07:37.900Z | 2026-11-05T11:15:25.668Z | 467.8 | 56 | 122 | 2752334 | 187983 | 37391 | 62705 | 11266 | 1.690737 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-A-orchestrator-01 | 0.1040 | 0.9394 | 0 | 0 | 0 | 45631 | 65520 | 56168.5 |
| 2026-11-05-ADM01-A-developer-01 | 0.0698 | 0.9179 | 0 | 0 | 0 | 11245 | 68155 | 48875.3 |
| 2026-11-05-ADM01-A-test-designer-01 | 0.2244 | 0.8352 | 0 | 0 | 0 | 11683 | 74358 | 45132.7 |
| 2026-11-05-ADM01-A-test-designer-02 | 0.1290 | 0.9884 | 0 | 0 | 0 | 77215 | 84723 | 81379.3 |
| 2026-11-05-ADM01-A-verifier-01 | 0.3435 | 0.8076 | 0 | 0 | 0 | 10978 | 35111 | 26085.3 |
| TOTAL | 0.1797 | 0.9243 | 0 | 0 | 0 |  | 84723 | 53175.5 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-A-orchestrator-01 | 7 | 0 | Agent=3; Bash=3; SendMessage=1 | 0 | 0 | 0 | 0 | 465.0 | 19.1 | 7 | unavailable |
| 2026-11-05-ADM01-A-developer-01 | 46 | 0 | Bash=7; Edit=10; Glob=2; Grep=2; Read=16; SubagentHandback=1; Write=8 | 16 | 16 | 0 | 0 | 199.5 | 169.6 | 46 | unavailable |
| 2026-11-05-ADM01-A-test-designer-01 | 21 | 2 | Bash=3; Grep=3; Read=13; SubagentHandback=1; Write=1 | 13 | 12 | 1 | 0 | 237.2 | 6.3 | 21 | unavailable |
| 2026-11-05-ADM01-A-test-designer-02 | 17 | 3 | Bash=14; Edit=2; SubagentHandback=1 | 0 | 0 | 0 | 0 | 77.0 | 43.5 | 17 | 7.4 |
| 2026-11-05-ADM01-A-verifier-01 | 7 | 0 | Bash=6; SubagentHandback=1 | 0 | 0 | 0 | 0 | 85.4 | 12.7 | 7 | 14.3 |
| TOTAL | 98 | 5 | Agent=3; Bash=33; Edit=12; Glob=2; Grep=5; Read=29; SendMessage=1; SubagentHandback=4; Write=9 | 29 | 28 | 1 | 0 |  | 251.2 | 98 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-A-orchestrator-01 | 0.000060 | 0.058043 | 0.000000 | 0.149564 | 0.042800 | 0.250467 |
| 2026-11-05-ADM01-A-developer-01 | 0.000068 | 0.076269 | 0.170383 | 0.000000 | 0.171800 | 0.418520 |
| 2026-11-05-ADM01-A-test-designer-01 | 0.000040 | 0.037695 | 0.185890 | 0.000000 | 0.302030 | 0.525655 |
| 2026-11-05-ADM01-A-test-designer-02 | 0.000048 | 0.088478 | 0.025912 | 0.000000 | 0.044280 | 0.158719 |
| 2026-11-05-ADM01-A-verifier-01 | 0.000056 | 0.029495 | 0.175545 | 0.000000 | 0.132280 | 0.337376 |
| TOTAL | 0.000272 | 0.289981 | 0.557730 | 0.149564 | 0.693190 | 1.690737 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-A-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-A-developer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-A-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-A-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-A-verifier-01 |  |  |  |  |  |  |  |
