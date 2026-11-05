# Invocation report: 2026-11-05-ADM01-H1

Format: `invocation-v2`

Sessions: 8700f4e3-0f55-49b9-951b-ff55b343bb65

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H1-orchestrator-01 | orchestrator |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T15:20:32.525Z | 2026-11-05T16:33:05.254Z | 4352.7 | 27 | 74 | 1700042 | 0 | 55345 | 7642 | 975 | 0.467952 |
| 2026-11-05-ADM01-H1-developer-01 | developer |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | a74df3eabc00e1d3a | 1 | 2026-11-05-ADM01-H1-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T15:20:53.223Z | 2026-11-05T15:22:59.718Z | 126.5 | 14 | 28 | 491866 | 51738 | 0 | 11511 | 928 | 0.293698 |
| 2026-11-05-ADM01-H1-test-designer-01 | test-designer |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | ad6efdb63d9b860ff | 1 | 2026-11-05-ADM01-H1-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T15:20:53.235Z | 2026-11-05T15:24:27.883Z | 214.6 | 15 | 30 | 583697 | 60585 | 0 | 27994 | 3951 | 0.489832 |
| 2026-11-05-ADM01-H1-test-designer-02 | test-designer |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | ad6efdb63d9b860ff | 2 | 2026-11-05-ADM01-H1-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T15:24:37.056Z | 2026-11-05T15:29:59.918Z | 322.9 | 11 | 24 | 779100 | 9263 | 0 | 2672 | 96 | 0.127835 |
| 2026-11-05-ADM01-H1-test-designer-03 | test-designer |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | ad6efdb63d9b860ff | 3 | 2026-11-05-ADM01-H1-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T15:30:20.399Z | 2026-11-05T16:00:25.689Z | 1805.3 | 13 | 30 | 954570 | 85747 | 0 | 4473 | 987 | 0.354614 |
| 2026-11-05-ADM01-H1-verifier-01 | verifier |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | af4bea516b9bde759 | 1 | 2026-11-05-ADM01-H1-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T16:00:42.336Z | 2026-11-05T16:02:56.545Z | 134.2 | 6 | 12 | 103740 | 34322 | 0 | 5054 | 1383 | 0.293486 |
| 2026-11-05-ADM01-H1-developer-02 | developer |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | a74df3eabc00e1d3a | 2 | 2026-11-05-ADM01-H1-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T16:03:07.159Z | 2026-11-05T16:04:12.510Z | 65.4 | 4 | 8 | 168876 | 51354 | 0 | 1737 | 61 | 0.162659 |
| 2026-11-05-ADM01-H1-test-designer-04 | test-designer |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | ad6efdb63d9b860ff | 4 | 2026-11-05-ADM01-H1-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T16:03:07.303Z | 2026-11-05T16:04:07.049Z | 59.7 | 5 | 12 | 435247 | 6006 | 0 | 1308 | 166 | 0.071644 |
| 2026-11-05-ADM01-H1-verifier-02 | verifier |  | 8700f4e3-0f55-49b9-951b-ff55b343bb65 | af4bea516b9bde759 | 2 | 2026-11-05-ADM01-H1-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T16:04:21.065Z | 2026-11-05T16:32:38.952Z | 1697.9 | 5 | 14 | 155789 | 51520 | 0 | 2411 | 115 | 0.337034 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-05T15:20:32.525Z | 2026-11-05T16:33:05.254Z | 4352.7 | 100 | 232 | 5372927 | 350535 | 55345 | 64802 | 8662 | 2.598754 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H1-orchestrator-01 | 0.1276 | 0.9684 | 0 | 3 | 4957 | 45788 | 83474 | 65017.1 |
| 2026-11-05-ADM01-H1-developer-01 | 0.0806 | 0.9048 | 0 | 0 | 0 | 11502 | 51740 | 38830.9 |
| 2026-11-05-ADM01-H1-test-designer-01 | 0.1411 | 0.9059 | 0 | 0 | 0 | 11901 | 65482 | 42954.1 |
| 2026-11-05-ADM01-H1-test-designer-02 | 0.0359 | 0.9882 | 0 | 0 | 0 | 68338 | 74745 | 71671.5 |
| 2026-11-05-ADM01-H1-test-designer-03 | 0.2207 | 0.9175 | 1 | 1 | 77256 | 75991 | 83934 | 80026.7 |
| 2026-11-05-ADM01-H1-verifier-01 | 0.2736 | 0.7513 | 0 | 0 | 0 | 11377 | 34324 | 23012.3 |
| 2026-11-05-ADM01-H1-developer-02 | 0.0351 | 0.7668 | 0 | 0 | 0 | 53433 | 56251 | 55059.5 |
| 2026-11-05-ADM01-H1-test-designer-04 | 0.1269 | 0.9864 | 0 | 0 | 0 | 85601 | 89940 | 88253.0 |
| 2026-11-05-ADM01-H1-verifier-02 | 0.0477 | 0.7514 | 1 | 1 | 42503 | 37559 | 43739 | 41464.6 |
| TOTAL | 0.1337 | 0.9297 | 2 | 5 | 124716 |  | 89940 | 57790.4 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H1-orchestrator-01 | 17 | 0 | Agent=3; Bash=8; PowerShell=1; SendMessage=5 | 0 | 0 | 0 | 2 | 4349.7 | 48.2 | 17 | unavailable |
| 2026-11-05-ADM01-H1-developer-01 | 16 | 0 | Bash=12; Read=3; SubagentHandback=1 | 3 | 3 | 0 | 0 | 122.0 | 29.0 | 16 | unavailable |
| 2026-11-05-ADM01-H1-test-designer-01 | 22 | 1 | Bash=11; Edit=5; Read=4; SubagentHandback=1; Write=1 | 4 | 4 | 0 | 0 | 207.3 | 48.8 | 22 | unavailable |
| 2026-11-05-ADM01-H1-test-designer-02 | 13 | 5 | Bash=8; Grep=1; Monitor=1; Read=2; SubagentHandback=1 | 2 | 1 | 1 | 0 | 316.4 | 277.9 | 13 | 9.2 |
| 2026-11-05-ADM01-H1-test-designer-03 | 12 | 0 | Bash=10; Edit=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 1801.1 | 79.5 | 12 | 20.5 |
| 2026-11-05-ADM01-H1-verifier-01 | 7 | 0 | Bash=5; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 131.9 | 86.0 | 7 | 16.6 |
| 2026-11-05-ADM01-H1-developer-02 | 4 | 0 | Bash=3; SubagentHandback=1 | 0 | 0 | 0 | 0 | 61.1 | 50.3 | 4 | 10.6 |
| 2026-11-05-ADM01-H1-test-designer-04 | 5 | 0 | Bash=3; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 56.4 | 47.5 | 5 | 10.8 |
| 2026-11-05-ADM01-H1-verifier-02 | 4 | 0 | Bash=3; SubagentHandback=1 | 0 | 0 | 0 | 0 | 1695.9 | 3.4 | 4 | 8.6 |
| TOTAL | 100 | 6 | Agent=3; Bash=63; Edit=6; Grep=1; Monitor=1; PowerShell=1; Read=11; SendMessage=5; SubagentHandback=8; Write=1 | 11 | 10 | 1 | 2 |  | 670.6 | 100 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H1-orchestrator-01 | 0.000148 | 0.170004 | 0.000000 | 0.221380 | 0.076420 | 0.467952 |
| 2026-11-05-ADM01-H1-developer-01 | 0.000056 | 0.049187 | 0.129345 | 0.000000 | 0.115110 | 0.293698 |
| 2026-11-05-ADM01-H1-test-designer-01 | 0.000060 | 0.058370 | 0.151463 | 0.000000 | 0.279940 | 0.489832 |
| 2026-11-05-ADM01-H1-test-designer-02 | 0.000048 | 0.077910 | 0.023158 | 0.000000 | 0.026720 | 0.127835 |
| 2026-11-05-ADM01-H1-test-designer-03 | 0.000060 | 0.095457 | 0.214367 | 0.000000 | 0.044730 | 0.354614 |
| 2026-11-05-ADM01-H1-verifier-01 | 0.000048 | 0.020748 | 0.171610 | 0.000000 | 0.101080 | 0.293486 |
| 2026-11-05-ADM01-H1-developer-02 | 0.000016 | 0.016888 | 0.128385 | 0.000000 | 0.017370 | 0.162659 |
| 2026-11-05-ADM01-H1-test-designer-04 | 0.000024 | 0.043525 | 0.015015 | 0.000000 | 0.013080 | 0.071644 |
| 2026-11-05-ADM01-H1-verifier-02 | 0.000056 | 0.031158 | 0.257600 | 0.000000 | 0.048220 | 0.337034 |
| TOTAL | 0.000516 | 0.563246 | 1.090942 | 0.221380 | 0.722670 | 2.598754 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H1-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-developer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-test-designer-03 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-developer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-test-designer-04 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H1-verifier-02 |  |  |  |  |  |  |  |
