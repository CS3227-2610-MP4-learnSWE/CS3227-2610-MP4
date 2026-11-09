# Invocation report: 2026-11-10-ADM01-H5

Format: `invocation-v2`

Sessions: 010420ab-1702-4fc9-8d00-d6e04b2e7744

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-10-ADM01-H5-orchestrator-01 | orchestrator |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T17:30:13.736Z | 2026-11-09T19:14:36.088Z | 6262.4 | 36 | 98 | 3244951 | 0 | 54676 | 8430 | 1328 | 0.627695 |
| 2026-11-10-ADM01-H5-developer-01 | developer |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 | a7571df561f7f2cba | 1 | 2026-11-10-ADM01-H5-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T17:30:33.367Z | 2026-11-09T17:43:07.049Z | 753.7 | 21 | 42 | 817182 | 51910 | 0 | 16829 | 1272 | 0.379867 |
| 2026-11-10-ADM01-H5-test-designer-01 | test-designer |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 | a6fcf5715364d1b65 | 1 | 2026-11-10-ADM01-H5-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T17:30:33.380Z | 2026-11-09T17:35:37.714Z | 304.3 | 11 | 22 | 363645 | 52525 | 0 | 19430 | 1592 | 0.362021 |
| 2026-11-10-ADM01-H5-developer-02 | developer |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 | a7571df561f7f2cba | 2 | 2026-11-10-ADM01-H5-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T18:01:49.468Z | 2026-11-09T18:45:34.368Z | 2624.9 | 8 | 24 | 340052 | 114965 | 0 | 2009 | 110 | 0.341556 |
| 2026-11-10-ADM01-H5-test-designer-02 | test-designer |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 | a6fcf5715364d1b65 | 2 | 2026-11-10-ADM01-H5-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-09T18:14:28.393Z | 2026-11-09T18:14:44.180Z | 15.8 | 2 | 6 | 59282 | 60260 | 0 | 969 | 0 | 0.166280 |
| 2026-11-10-ADM01-H5-verifier-01 | verifier |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 | a17660ae3d270fd6e | 1 | 2026-11-10-ADM01-H5-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-09T18:43:24.637Z | 2026-11-09T18:44:25.957Z | 61.3 | 5 | 10 | 87210 | 27763 | 0 | 3109 | 354 | 0.218477 |
| 2026-11-10-ADM01-H5-verifier-02 | verifier |  | 010420ab-1702-4fc9-8d00-d6e04b2e7744 | a17660ae3d270fd6e | 2 | 2026-11-10-ADM01-H5-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-09T18:45:41.973Z | 2026-11-09T18:46:15.415Z | 33.4 | 2 | 6 | 57658 | 2920 | 0 | 903 | 0 | 0.044216 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-09T17:30:13.736Z | 2026-11-09T19:14:36.088Z | 6262.4 | 85 | 208 | 4969980 | 310343 | 54676 | 51679 | 4656 | 2.140112 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-10-ADM01-H5-orchestrator-01 | 0.1575 | 0.9834 | 0 | 5 | 4032 | 71605 | 110025 | 91659.0 |
| 2026-11-10-ADM01-H5-developer-01 | 0.0756 | 0.9402 | 0 | 0 | 0 | 11384 | 51912 | 41387.3 |
| 2026-11-10-ADM01-H5-test-designer-01 | 0.0819 | 0.8737 | 0 | 0 | 0 | 11917 | 57633 | 37835.6 |
| 2026-11-10-ADM01-H5-developer-02 | 0.0548 | 0.7473 | 1 | 1 | 57030 | 54100 | 58364 | 56880.1 |
| 2026-11-10-ADM01-H5-test-designer-02 | 0.0000 | 0.4959 | 0 | 0 | 0 | 59286 | 60262 | 59774.0 |
| 2026-11-10-ADM01-H5-verifier-01 | 0.1139 | 0.7585 | 0 | 0 | 0 | 11224 | 27765 | 22996.6 |
| 2026-11-10-ADM01-H5-verifier-02 | 0.0000 | 0.9517 | 0 | 0 | 0 | 29899 | 30685 | 30292.0 |
| TOTAL | 0.0901 | 0.9315 | 1 | 6 | 61062 |  | 110025 | 62767.1 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-10-ADM01-H5-orchestrator-01 | 26 | 0 | Agent=3; Bash=16; SendMessage=3; ToolSearch=1; mcp__ccd_turn__update_plan=1; mcp__ccd_turn__wrap_up=2 | 0 | 0 | 0 | 6 | 6255.1 | 81.1 | 26 | unavailable |
| 2026-11-10-ADM01-H5-developer-01 | 30 | 3 | Bash=18; Read=3; SubagentHandback=1; Write=8 | 3 | 3 | 0 | 0 | 749.6 | 647.9 | 30 | unavailable |
| 2026-11-10-ADM01-H5-test-designer-01 | 20 | 5 | Bash=8; Grep=1; Read=9; SubagentHandback=1; Write=1 | 9 | 9 | 0 | 0 | 297.0 | 20.2 | 20 | unavailable |
| 2026-11-10-ADM01-H5-developer-02 | 5 | 0 | Bash=3; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 2619.4 | 35.2 | 5 | 1122.4 |
| 2026-11-10-ADM01-H5-test-designer-02 | 3 | 0 | Bash=1; Edit=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 8.0 | 7.5 | 3 | 1881.3 |
| 2026-11-10-ADM01-H5-verifier-01 | 5 | 0 | Bash=4; SubagentHandback=1 | 0 | 0 | 0 | 0 | 58.9 | 28.9 | 5 | 1720.5 |
| 2026-11-10-ADM01-H5-verifier-02 | 2 | 0 | Bash=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 30.4 | 24.4 | 2 | 7.6 |
| TOTAL | 91 | 8 | Agent=3; Bash=51; Edit=1; Grep=1; Read=13; SendMessage=3; SubagentHandback=6; ToolSearch=1; Write=9; mcp__ccd_turn__update_plan=1; mcp__ccd_turn__wrap_up=2 | 13 | 12 | 1 | 6 |  | 845.2 | 91 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-10-ADM01-H5-orchestrator-01 | 0.000196 | 0.324495 | 0.000000 | 0.218704 | 0.084300 | 0.627695 |
| 2026-11-10-ADM01-H5-developer-01 | 0.000084 | 0.081718 | 0.129775 | 0.000000 | 0.168290 | 0.379867 |
| 2026-11-10-ADM01-H5-test-designer-01 | 0.000044 | 0.036365 | 0.131313 | 0.000000 | 0.194300 | 0.362021 |
| 2026-11-10-ADM01-H5-developer-02 | 0.000048 | 0.034005 | 0.287413 | 0.000000 | 0.020090 | 0.341556 |
| 2026-11-10-ADM01-H5-test-designer-02 | 0.000012 | 0.005928 | 0.150650 | 0.000000 | 0.009690 | 0.166280 |
| 2026-11-10-ADM01-H5-verifier-01 | 0.000040 | 0.017442 | 0.138815 | 0.000000 | 0.062180 | 0.218477 |
| 2026-11-10-ADM01-H5-verifier-02 | 0.000024 | 0.011532 | 0.014600 | 0.000000 | 0.018060 | 0.044216 |
| TOTAL | 0.000448 | 0.511485 | 0.852565 | 0.218704 | 0.556910 | 2.140112 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-10-ADM01-H5-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-10-ADM01-H5-developer-01 |  |  |  |  |  |  |  |
| 2026-11-10-ADM01-H5-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-10-ADM01-H5-developer-02 |  |  |  |  |  |  |  |
| 2026-11-10-ADM01-H5-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-10-ADM01-H5-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-10-ADM01-H5-verifier-02 |  |  |  |  |  |  |  |
