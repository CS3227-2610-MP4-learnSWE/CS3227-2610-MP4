# Invocation report: 2026-11-09-ADM01-H4

Format: `invocation-v2`

Sessions: 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-H4-orchestrator-01 | orchestrator |  | 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93 |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T16:20:13.072Z | 2026-11-09T17:19:33.918Z | 3560.8 | 25 | 72 | 2112280 | 0 | 53810 | 5691 | 705 | 0.483522 |
| 2026-11-09-ADM01-H4-developer-01 | developer |  | 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93 | ac680b9957436b57b | 1 | 2026-11-09-ADM01-H4-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T16:20:37.103Z | 2026-11-09T16:34:42.208Z | 845.1 | 24 | 48 | 1012216 | 53655 | 0 | 17383 | 1206 | 0.409285 |
| 2026-11-09-ADM01-H4-test-designer-01 | test-designer |  | 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93 | ad0a60102a75c97a3 | 1 | 2026-11-09-ADM01-H4-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T16:20:37.114Z | 2026-11-09T16:23:29.102Z | 172.0 | 11 | 22 | 289687 | 59992 | 0 | 24715 | 1317 | 0.426143 |
| 2026-11-09-ADM01-H4-developer-02 | developer |  | 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93 | ac680b9957436b57b | 2 | 2026-11-09-ADM01-H4-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T16:37:23.767Z | 2026-11-09T17:07:09.200Z | 1785.4 | 10 | 28 | 528393 | 67117 | 0 | 4255 | 469 | 0.263238 |
| 2026-11-09-ADM01-H4-verifier-01 | verifier |  | 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93 | aae068d18d6065c06 | 1 | 2026-11-09-ADM01-H4-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-09T17:02:07.638Z | 2026-11-09T17:05:11.976Z | 184.3 | 7 | 14 | 117511 | 26908 | 0 | 4496 | 612 | 0.248018 |
| 2026-11-09-ADM01-H4-test-designer-02 | test-designer |  | 3f6b7a3c-0822-4eb4-a2fd-2e63d6768c93 | ad0a60102a75c97a3 | 2 | 2026-11-09-ADM01-H4-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T17:18:21.258Z | 2026-11-09T17:19:01.816Z | 40.6 | 7 | 16 | 389272 | 67423 | 0 | 2832 | 574 | 0.235837 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-09T16:20:13.072Z | 2026-11-09T17:19:33.918Z | 3560.8 | 84 | 200 | 4449359 | 275095 | 53810 | 59372 | 4883 | 2.066043 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-H4-orchestrator-01 | 0.1239 | 0.9751 | 0 | 3 | 3462 | 71436 | 99680 | 86646.5 |
| 2026-11-09-ADM01-H4-developer-01 | 0.0694 | 0.9496 | 0 | 0 | 0 | 11128 | 53657 | 44413.3 |
| 2026-11-09-ADM01-H4-test-designer-01 | 0.0533 | 0.8284 | 0 | 0 | 0 | 11524 | 59994 | 31791.0 |
| 2026-11-09-ADM01-H4-developer-02 | 0.1102 | 0.8873 | 1 | 1 | 58310 | 55297 | 62874 | 59553.8 |
| 2026-11-09-ADM01-H4-verifier-01 | 0.1361 | 0.8136 | 0 | 0 | 0 | 10970 | 26910 | 20633.3 |
| 2026-11-09-ADM01-H4-test-designer-02 | 0.2027 | 0.8523 | 0 | 0 | 0 | 62256 | 67425 | 65244.4 |
| TOTAL | 0.0822 | 0.9311 | 1 | 4 | 61772 |  | 99680 | 56886.5 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-H4-orchestrator-01 | 14 | 0 | Agent=3; Bash=8; SendMessage=2; mcp__ccd_turn__wrap_up=1 | 0 | 0 | 0 | 4 | 3552.6 | 35.6 | 14 | unavailable |
| 2026-11-09-ADM01-H4-developer-01 | 32 | 3 | Bash=21; Read=2; SubagentHandback=1; Write=8 | 2 | 1 | 1 | 0 | 839.6 | 769.8 | 32 | unavailable |
| 2026-11-09-ADM01-H4-test-designer-01 | 12 | 1 | Bash=9; Read=1; SubagentHandback=1; Write=1 | 1 | 1 | 0 | 0 | 166.7 | 15.0 | 12 | unavailable |
| 2026-11-09-ADM01-H4-developer-02 | 7 | 0 | Bash=5; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 1780.2 | 72.1 | 7 | 161.6 |
| 2026-11-09-ADM01-H4-verifier-01 | 7 | 0 | Bash=6; SubagentHandback=1 | 0 | 0 | 0 | 0 | 181.4 | 140.1 | 7 | 1645.4 |
| 2026-11-09-ADM01-H4-test-designer-02 | 8 | 0 | Bash=6; Edit=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 35.9 | 15.7 | 8 | 672.1 |
| TOTAL | 80 | 4 | Agent=3; Bash=55; Edit=1; Read=4; SendMessage=2; SubagentHandback=5; Write=9; mcp__ccd_turn__wrap_up=1 | 4 | 2 | 2 | 4 |  | 1048.4 | 80 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-H4-orchestrator-01 | 0.000144 | 0.211228 | 0.000000 | 0.215240 | 0.056910 | 0.483522 |
| 2026-11-09-ADM01-H4-developer-01 | 0.000096 | 0.101222 | 0.134137 | 0.000000 | 0.173830 | 0.409285 |
| 2026-11-09-ADM01-H4-test-designer-01 | 0.000044 | 0.028969 | 0.149980 | 0.000000 | 0.247150 | 0.426143 |
| 2026-11-09-ADM01-H4-developer-02 | 0.000056 | 0.052839 | 0.167792 | 0.000000 | 0.042550 | 0.263238 |
| 2026-11-09-ADM01-H4-verifier-01 | 0.000056 | 0.023502 | 0.134540 | 0.000000 | 0.089920 | 0.248018 |
| 2026-11-09-ADM01-H4-test-designer-02 | 0.000032 | 0.038927 | 0.168557 | 0.000000 | 0.028320 | 0.235837 |
| TOTAL | 0.000428 | 0.456687 | 0.755007 | 0.215240 | 0.638680 | 2.066043 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-09-ADM01-H4-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-H4-developer-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-H4-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-H4-developer-02 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-H4-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-09-ADM01-H4-test-designer-02 |  |  |  |  |  |  |  |
