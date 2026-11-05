# Invocation report: 2026-11-05-ADM01-H3

Format: `invocation-v2`

Sessions: 875d00bd-3d04-433b-a389-0591c36c3c02

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H3-orchestrator-01 | orchestrator |  | 875d00bd-3d04-433b-a389-0591c36c3c02 |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T12:25:17.455Z | 2026-11-05T14:13:07.521Z | 6470.1 | 23 | 72 | 1438093 | 0 | 49483 | 5714 | 666 | 0.399025 |
| 2026-11-05-ADM01-H3-developer-01 | developer |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | ab27ca5366ca70776 | 1 | 2026-11-05-ADM01-H3-orchestrator-01 | developer | claude-haiku-5-5 | claude-haiku-5-5 | yes | 2026-11-05T12:25:34.493Z | 2026-11-05T13:15:16.177Z | 2981.7 | 101 | 202 | 11873092 | 183862 | 0 | 98898 | 45967 | 0.729301 |
| 2026-11-05-ADM01-H3-test-designer-01 | test-designer |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | a7b5ab0fc1bb3dc4d | 1 | 2026-11-05-ADM01-H3-orchestrator-01 | test-designer | claude-haiku-5-5 | claude-haiku-5-5 | yes | 2026-11-05T12:25:34.504Z | 2026-11-05T12:32:38.973Z | 424.5 | 22 | 44 | 1679520 | 153953 | 0 | 91157 | 61892 | 0.210781 |
| 2026-11-05-ADM01-H3-test-designer-02 | test-designer |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | a7b5ab0fc1bb3dc4d | 2 | 2026-11-05-ADM01-H3-orchestrator-01 | test-designer | claude-haiku-5-5 | claude-haiku-5-5 | yes | 2026-11-05T13:15:31.543Z | 2026-11-05T13:34:33.086Z | 1141.5 | 23 | 50 | 3571200 | 347879 | 0 | 17047 | 4526 | 0.438627 |
| 2026-11-05-ADM01-H3-verifier-01 | verifier |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | a789a62d714fc3b38 | 1 | 2026-11-05-ADM01-H3-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T13:34:50.338Z | 2026-11-05T13:53:34.108Z | 1123.8 | 18 | 38 | 471347 | 39182 | 0 | 8270 | 1306 | 0.455731 |
| 2026-11-05-ADM01-H3-test-designer-03 | test-designer |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | a7b5ab0fc1bb3dc4d | 3 | 2026-11-05-ADM01-H3-orchestrator-01 | test-designer | claude-haiku-5-5 | claude-haiku-5-5 | yes | 2026-11-05T13:49:23.956Z | 2026-11-05T13:49:46.413Z | 22.5 | 3 | 8 | 375136 | 189548 | 0 | 2689 | 315 | 0.143951 |
| 2026-11-05-ADM01-H3-developer-02 | developer |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | ab27ca5366ca70776 | 2 | 2026-11-05-ADM01-H3-orchestrator-01 | developer | claude-haiku-5-5 | claude-haiku-5-5 | yes | 2026-11-05T13:53:44.490Z | 2026-11-05T13:57:08.896Z | 204.4 | 9 | 20 | 1538503 | 191385 | 0 | 6884 | 1443 | 0.213761 |
| 2026-11-05-ADM01-H3-test-designer-04 | test-designer |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | a7b5ab0fc1bb3dc4d | 4 | 2026-11-05-ADM01-H3-orchestrator-01 | test-designer | claude-haiku-5-5 | claude-haiku-5-5 | yes | 2026-11-05T13:53:44.610Z | 2026-11-05T13:54:32.928Z | 48.3 | 6 | 16 | 1160882 | 7058 | 0 | 5458 | 2253 | 0.076108 |
| 2026-11-05-ADM01-H3-verifier-02 | verifier |  | 875d00bd-3d04-433b-a389-0591c36c3c02 | a789a62d714fc3b38 | 2 | 2026-11-05-ADM01-H3-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T13:57:19.262Z | 2026-11-05T14:12:54.294Z | 935.0 | 5 | 14 | 171091 | 52272 | 0 | 2663 | 41 | 0.348894 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-haiku-5-5; claude-opus-5-5; claude-sonnet-5-5 | claude-haiku-5-5; claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-05T12:25:17.455Z | 2026-11-05T14:13:07.521Z | 6470.1 | 210 | 464 | 22278864 | 1165139 | 49483 | 238780 | 118409 | 3.016179 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H3-orchestrator-01 | 0.1166 | 0.9667 | 0 | 6 | 11749 | 45616 | 77612 | 64680.3 |
| 2026-11-05-ADM01-H3-developer-01 | 0.4648 | 0.9847 | 0 | 0 | 0 | 11218 | 183864 | 119377.8 |
| 2026-11-05-ADM01-H3-test-designer-01 | 0.6790 | 0.9160 | 0 | 0 | 0 | 11657 | 153955 | 83341.7 |
| 2026-11-05-ADM01-H3-test-designer-02 | 0.2655 | 0.9112 | 1 | 1 | 167715 | 157970 | 185619 | 170396.9 |
| 2026-11-05-ADM01-H3-verifier-01 | 0.1579 | 0.9232 | 0 | 0 | 0 | 10947 | 39184 | 28364.8 |
| 2026-11-05-ADM01-H3-test-designer-03 | 0.1171 | 0.6643 | 0 | 0 | 0 | 187102 | 189550 | 188230.7 |
| 2026-11-05-ADM01-H3-developer-02 | 0.2096 | 0.8894 | 0 | 0 | 0 | 187441 | 196282 | 192212.0 |
| 2026-11-05-ADM01-H3-test-designer-04 | 0.4128 | 0.9939 | 0 | 0 | 0 | 190683 | 196610 | 194659.3 |
| 2026-11-05-ADM01-H3-verifier-02 | 0.0154 | 0.7659 | 1 | 1 | 45959 | 42219 | 46304 | 44675.4 |
| TOTAL | 0.4959 | 0.9483 | 2 | 8 | 225423 |  | 196610 | 111876.0 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H3-orchestrator-01 | 11 | 0 | Agent=3; Bash=4; SendMessage=4 | 0 | 0 | 0 | 5 | 6467.2 | 35.3 | 11 | unavailable |
| 2026-11-05-ADM01-H3-developer-01 | 101 | 2 | Bash=73; Edit=13; Grep=2; SubagentHandback=1; TaskStop=1; Write=11 | 0 | 0 | 0 | 0 | 2975.9 | 2299.8 | 101 | unavailable |
| 2026-11-05-ADM01-H3-test-designer-01 | 39 | 1 | Bash=4; Edit=3; Glob=1; Grep=7; Read=19; SubagentHandback=1; Write=4 | 19 | 15 | 4 | 0 | 420.4 | 28.4 | 39 | unavailable |
| 2026-11-05-ADM01-H3-test-designer-02 | 28 | 3 | Bash=15; Edit=9; Monitor=1; Read=2; SubagentHandback=1 | 2 | 2 | 0 | 0 | 1135.1 | 339.9 | 28 | 15.4 |
| 2026-11-05-ADM01-H3-verifier-01 | 19 | 0 | Bash=17; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 1121.6 | 900.6 | 19 | 17.3 |
| 2026-11-05-ADM01-H3-test-designer-03 | 2 | 0 | Bash=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 15.6 | 2.5 | 2 | 890.9 |
| 2026-11-05-ADM01-H3-developer-02 | 9 | 0 | Bash=8; SubagentHandback=1 | 0 | 0 | 0 | 0 | 198.5 | 160.7 | 9 | 10.4 |
| 2026-11-05-ADM01-H3-test-designer-04 | 5 | 0 | Bash=3; Edit=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 32.6 | 13.1 | 5 | 10.5 |
| 2026-11-05-ADM01-H3-verifier-02 | 5 | 0 | Bash=4; SubagentHandback=1 | 0 | 0 | 0 | 0 | 932.9 | 63.5 | 5 | 10.4 |
| TOTAL | 219 | 6 | Agent=3; Bash=129; Edit=26; Glob=1; Grep=9; Monitor=1; Read=22; SendMessage=4; SubagentHandback=8; TaskStop=1; Write=15 | 22 | 18 | 4 | 5 |  | 3843.8 | 219 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H3-orchestrator-01 | 0.000144 | 0.143809 | 0.000000 | 0.197932 | 0.057140 | 0.399025 |
| 2026-11-05-ADM01-H3-developer-01 | 0.000072 | 0.492825 | 0.065169 | 0.000000 | 0.171235 | 0.729301 |
| 2026-11-05-ADM01-H3-test-designer-01 | 0.000011 | 0.060340 | 0.053402 | 0.000000 | 0.097028 | 0.210781 |
| 2026-11-05-ADM01-H3-test-designer-02 | 0.000025 | 0.178560 | 0.217424 | 0.000000 | 0.042618 | 0.438627 |
| 2026-11-05-ADM01-H3-verifier-01 | 0.000152 | 0.094269 | 0.195910 | 0.000000 | 0.165400 | 0.455731 |
| 2026-11-05-ADM01-H3-test-designer-03 | 0.000004 | 0.018757 | 0.118468 | 0.000000 | 0.006723 | 0.143951 |
| 2026-11-05-ADM01-H3-developer-02 | 0.000010 | 0.076925 | 0.119616 | 0.000000 | 0.017210 | 0.213761 |
| 2026-11-05-ADM01-H3-test-designer-04 | 0.000008 | 0.058044 | 0.004411 | 0.000000 | 0.013645 | 0.076108 |
| 2026-11-05-ADM01-H3-verifier-02 | 0.000056 | 0.034218 | 0.261360 | 0.000000 | 0.053260 | 0.348894 |
| TOTAL | 0.000482 | 1.157748 | 1.035759 | 0.197932 | 0.624258 | 3.016179 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H3-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-developer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-test-designer-03 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-developer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-test-designer-04 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H3-verifier-02 |  |  |  |  |  |  |  |
