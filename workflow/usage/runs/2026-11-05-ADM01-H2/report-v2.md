# Invocation report: 2026-11-05-ADM01-H2

Format: `invocation-v2`

Sessions: 658082de-c459-4ddc-8dcf-f835ea10dd08

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H2-orchestrator-01 | orchestrator |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T17:41:02.535Z | 2026-11-05T18:46:24.523Z | 3922.0 | 26 | 70 | 1674961 | 0 | 57258 | 9021 | 1080 | 0.486878 |
| 2026-11-05-ADM01-H2-developer-01 | developer |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | a9bbe896c05152a10 | 1 | 2026-11-05-ADM01-H2-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T17:41:16.871Z | 2026-11-05T17:43:06.906Z | 110.0 | 12 | 24 | 377680 | 49939 | 0 | 14677 | 592 | 0.309434 |
| 2026-11-05-ADM01-H2-test-designer-01 | test-designer |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | aec33cb7b5481aeb2 | 1 | 2026-11-05-ADM01-H2-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T17:41:16.881Z | 2026-11-05T17:44:57.342Z | 220.5 | 16 | 32 | 707734 | 70258 | 0 | 32723 | 7508 | 0.573712 |
| 2026-11-05-ADM01-H2-test-designer-02 | test-designer |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | aec33cb7b5481aeb2 | 2 | 2026-11-05-ADM01-H2-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T17:45:03.676Z | 2026-11-05T17:46:09.025Z | 65.3 | 10 | 22 | 827200 | 13496 | 0 | 5398 | 768 | 0.170484 |
| 2026-11-05-ADM01-H2-verifier-01 | verifier |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | aa114bd2dc838c944 | 1 | 2026-11-05-ADM01-H2-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T18:12:59.474Z | 2026-11-05T18:15:42.017Z | 162.5 | 8 | 16 | 149369 | 32795 | 0 | 7092 | 1508 | 0.335753 |
| 2026-11-05-ADM01-H2-developer-02 | developer |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | a9bbe896c05152a10 | 2 | 2026-11-05-ADM01-H2-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T18:15:50.626Z | 2026-11-05T18:16:05.661Z | 15.0 | 3 | 6 | 103401 | 52711 | 0 | 1312 | 0 | 0.155250 |
| 2026-11-05-ADM01-H2-test-designer-03 | test-designer |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | aec33cb7b5481aeb2 | 3 | 2026-11-05-ADM01-H2-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-05T18:15:50.786Z | 2026-11-05T18:16:16.976Z | 26.2 | 4 | 10 | 276214 | 94206 | 0 | 2410 | 304 | 0.287256 |
| 2026-11-05-ADM01-H2-verifier-02 | verifier |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | ae090552332850e5c | 1 | 2026-11-05-ADM01-H2-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T18:17:19.220Z | 2026-11-05T18:46:10.740Z | 1731.5 | 11 | 24 | 161752 | 33928 | 0 | 4073 | 209 | 0.283546 |
| 2026-11-05-ADM01-H2-verifier-03 | verifier |  | 658082de-c459-4ddc-8dcf-f835ea10dd08 | ae090552332850e5c | 2 | 2026-11-05-ADM01-H2-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-05T18:46:10.761Z | 2026-11-05T18:46:12.406Z | 1.6 | 1 | 4 | 20116 | 2077 | 0 | 84 | 15 | 0.016104 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-05T17:41:02.535Z | 2026-11-05T18:46:24.523Z | 3922.0 | 91 | 208 | 4298427 | 349410 | 57258 | 76790 | 11984 | 2.618417 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H2-orchestrator-01 | 0.1197 | 0.9669 | 0 | 3 | 3252 | 45720 | 85387 | 66626.5 |
| 2026-11-05-ADM01-H2-developer-01 | 0.0403 | 0.8832 | 0 | 0 | 0 | 11355 | 49941 | 35636.9 |
| 2026-11-05-ADM01-H2-test-designer-01 | 0.2294 | 0.9097 | 0 | 0 | 0 | 11765 | 75155 | 48626.5 |
| 2026-11-05-ADM01-H2-test-designer-02 | 0.1423 | 0.9839 | 0 | 0 | 0 | 78483 | 88651 | 84071.8 |
| 2026-11-05-ADM01-H2-verifier-01 | 0.2126 | 0.8199 | 0 | 0 | 0 | 12268 | 32797 | 22772.5 |
| 2026-11-05-ADM01-H2-developer-02 | 0.0000 | 0.6623 | 0 | 0 | 0 | 51547 | 52713 | 52039.3 |
| 2026-11-05-ADM01-H2-test-designer-03 | 0.1261 | 0.7457 | 0 | 0 | 0 | 90174 | 94208 | 92607.5 |
| 2026-11-05-ADM01-H2-verifier-02 | 0.0513 | 0.8265 | 1 | 1 | 19742 | 11440 | 20118 | 17791.3 |
| 2026-11-05-ADM01-H2-verifier-03 | 0.1786 | 0.9062 | 0 | 0 | 0 | 22197 | 22197 | 22197.0 |
| TOTAL | 0.1561 | 0.9135 | 1 | 4 | 22994 |  | 94208 | 51706.6 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H2-orchestrator-01 | 18 | 0 | Agent=4; Bash=11; SendMessage=3 | 0 | 0 | 0 | 3 | 3920.1 | 665.1 | 18 | unavailable |
| 2026-11-05-ADM01-H2-developer-01 | 20 | 1 | Bash=11; SubagentHandback=1; Write=8 | 0 | 0 | 0 | 0 | 108.2 | 151.5 | 20 | unavailable |
| 2026-11-05-ADM01-H2-test-designer-01 | 29 | 2 | Bash=3; Edit=2; Grep=3; Read=14; SubagentHandback=1; Write=6 | 14 | 11 | 3 | 0 | 217.7 | 21.5 | 29 | unavailable |
| 2026-11-05-ADM01-H2-test-designer-02 | 12 | 3 | Bash=9; Read=1; SubagentHandback=1; Write=1 | 1 | 1 | 0 | 0 | 62.4 | 30.1 | 12 | 6.3 |
| 2026-11-05-ADM01-H2-verifier-01 | 8 | 0 | Bash=7; SubagentHandback=1 | 0 | 0 | 0 | 0 | 159.5 | 94.1 | 8 | 1610.4 |
| 2026-11-05-ADM01-H2-developer-02 | 3 | 0 | Bash=2; SubagentHandback=1 | 0 | 0 | 0 | 0 | 11.3 | 3.7 | 3 | 8.6 |
| 2026-11-05-ADM01-H2-test-designer-03 | 7 | 0 | Bash=1; Edit=3; Grep=1; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 21.1 | 13.3 | 7 | 8.8 |
| 2026-11-05-ADM01-H2-verifier-02 | 12 | 2 | Bash=6; Grep=2; Read=3; SubagentHandback=1 | 3 | 3 | 0 | 0 | 1726.1 | 186.3 | 12 | 62.2 |
| 2026-11-05-ADM01-H2-verifier-03 | 0 | 0 | none | 0 | 0 | 0 | 0 | 0.0 | 0.0 | 0 | 0.0 |
| TOTAL | 109 | 8 | Agent=4; Bash=50; Edit=5; Grep=6; Read=19; SendMessage=3; SubagentHandback=7; Write=15 | 19 | 16 | 3 | 3 |  | 1165.6 | 109 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H2-orchestrator-01 | 0.000140 | 0.167496 | 0.000000 | 0.229032 | 0.090210 | 0.486878 |
| 2026-11-05-ADM01-H2-developer-01 | 0.000048 | 0.037768 | 0.124848 | 0.000000 | 0.146770 | 0.309434 |
| 2026-11-05-ADM01-H2-test-designer-01 | 0.000064 | 0.070773 | 0.175645 | 0.000000 | 0.327230 | 0.573712 |
| 2026-11-05-ADM01-H2-test-designer-02 | 0.000044 | 0.082720 | 0.033740 | 0.000000 | 0.053980 | 0.170484 |
| 2026-11-05-ADM01-H2-verifier-01 | 0.000064 | 0.029874 | 0.163975 | 0.000000 | 0.141840 | 0.335753 |
| 2026-11-05-ADM01-H2-developer-02 | 0.000012 | 0.010340 | 0.131777 | 0.000000 | 0.013120 | 0.155250 |
| 2026-11-05-ADM01-H2-test-designer-03 | 0.000020 | 0.027621 | 0.235515 | 0.000000 | 0.024100 | 0.287256 |
| 2026-11-05-ADM01-H2-verifier-02 | 0.000096 | 0.032350 | 0.169640 | 0.000000 | 0.081460 | 0.283546 |
| 2026-11-05-ADM01-H2-verifier-03 | 0.000016 | 0.004023 | 0.010385 | 0.000000 | 0.001680 | 0.016104 |
| TOTAL | 0.000504 | 0.462966 | 1.045525 | 0.229032 | 0.880390 | 2.618417 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-05-ADM01-H2-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-developer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-developer-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-test-designer-03 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-verifier-02 |  |  |  |  |  |  |  |
| 2026-11-05-ADM01-H2-verifier-03 |  |  |  |  |  |  |  |
