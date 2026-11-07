# Invocation report: 2026-11-06-STU02PS-01

Format: `invocation-v2`

Sessions: 62d8daea-6c3d-4036-8996-ec5e64384cbd

Costs are tracker list-price estimates, not billed. `unavailable` means the logs do not contain the data; no metric is estimated. The only inference is `likely_agent (inferred guess)` on the unattributed line, which is a guess and is never added to any invocation. A blank cell means not applicable. Elapsed values are wall-clock durations; the run total is latest finish minus earliest start. Wait before start is a wall-clock gap, not proof that one stage depended on another. Role is the agent type logged by Claude Code; Requested agent type is the type named in the launching Agent call; Role label is the label from the metadata file and never changes an invocation ID. Claude Code logs only; Codex sessions are not included.

## Invocations

| Invocation ID | Role | Role label | Session ID | Agent ID | Prompt | Launched by | Requested agent type | Requested model | Observed model(s) | Model match | Started | Finished | Elapsed (s) | Requests | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Reasoning | Cost (USD) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-06-STU02PS-01-orchestrator-01 | orchestrator |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd |  |  |  |  | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T06:36:41.587Z | 2026-11-06T13:49:07.754Z | 25946.2 | 169 | 448 | 32065537 | 0 | 347617 | 94181 | 17083 | 5.539728 |
| 2026-11-06-STU02PS-01-spec-writer-01 | spec-writer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a2e5aeea2ff3adbe3 | 1 | 2026-11-06-STU02PS-01-orchestrator-01 | spec-writer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T06:37:48.422Z | 2026-11-06T06:48:36.654Z | 648.2 | 34 | 68 | 4155128 | 221780 | 0 | 78392 | 34405 | 1.754019 |
| 2026-11-06-STU02PS-01-spec-writer-02 | spec-writer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a2e5aeea2ff3adbe3 | 2 | 2026-11-06-STU02PS-01-orchestrator-01 | spec-writer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T06:57:56.573Z | 2026-11-06T07:00:00.495Z | 123.9 | 6 | 14 | 1161005 | 242853 | 0 | 14726 | 2503 | 0.870521 |
| 2026-11-06-STU02PS-01-spec-writer-03 | spec-writer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a2e5aeea2ff3adbe3 | 3 | 2026-11-06-STU02PS-01-orchestrator-01 | spec-writer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T07:07:34.763Z | 2026-11-06T07:11:06.052Z | 211.3 | 13 | 28 | 3131299 | 277602 | 0 | 19114 | 2618 | 1.198331 |
| 2026-11-06-STU02PS-01-test-designer-01 | test-designer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a9d8473d20fa65e66 | 1 | 2026-11-06-STU02PS-01-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T07:12:31.063Z | 2026-11-06T07:27:59.601Z | 928.5 | 60 | 120 | 7762115 | 220363 | 0 | 101859 | 20148 | 2.345949 |
| 2026-11-06-STU02PS-01-developer-01 | developer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | ad9ebf1fab0926d24 | 1 | 2026-11-06-STU02PS-01-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T07:12:31.076Z | 2026-11-06T08:29:08.488Z | 4597.4 | 76 | 152 | 9457031 | 168344 | 0 | 49623 | 6723 | 1.863097 |
| 2026-11-06-STU02PS-01-developer-02 | developer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | ad9ebf1fab0926d24 | 2 | 2026-11-06-STU02PS-01-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T08:31:48.769Z | 2026-11-06T09:24:51.798Z | 3183.0 | 22 | 48 | 3824110 | 195875 | 0 | 11214 | 2913 | 0.984335 |
| 2026-11-06-STU02PS-01-test-designer-02 | test-designer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a9d8473d20fa65e66 | 2 | 2026-11-06-STU02PS-01-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T09:08:58.912Z | 2026-11-06T09:13:00.830Z | 241.9 | 10 | 22 | 2093308 | 237356 | 0 | 5101 | 554 | 0.853775 |
| 2026-11-06-STU02PS-01-test-designer-03 | test-designer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a9d8473d20fa65e66 | 3 | 2026-11-06-STU02PS-01-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T10:08:08.468Z | 2026-11-06T10:13:48.943Z | 340.5 | 10 | 22 | 2198320 | 248282 | 0 | 3799 | 220 | 0.878571 |
| 2026-11-06-STU02PS-01-verifier-01 | verifier |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | acdaea6d7fa35b62b | 1 | 2026-11-06-STU02PS-01-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-06T10:14:06.137Z | 2026-11-06T10:48:16.242Z | 2050.1 | 44 | 92 | 4385061 | 420740 | 0 | 31078 | 13975 | 3.602640 |
| 2026-11-06-STU02PS-01-developer-03 | developer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | ad9ebf1fab0926d24 | 3 | 2026-11-06-STU02PS-01-orchestrator-01 | developer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T10:48:45.656Z | 2026-11-06T11:19:31.616Z | 1846.0 | 26 | 54 | 5165024 | 217542 | 0 | 13287 | 2257 | 1.193335 |
| 2026-11-06-STU02PS-01-test-designer-04 | test-designer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a9d8473d20fa65e66 | 4 | 2026-11-06-STU02PS-01-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T10:48:48.061Z | 2026-11-06T10:58:05.333Z | 557.3 | 8 | 18 | 1776293 | 257049 | 0 | 4688 | 480 | 0.867168 |
| 2026-11-06-STU02PS-01-test-designer-05 | test-designer |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | a9d8473d20fa65e66 | 5 | 2026-11-06-STU02PS-01-orchestrator-01 | test-designer | claude-sonnet-5-5 | claude-sonnet-5-5 | yes | 2026-11-06T10:59:52.458Z | 2026-11-06T12:47:56.428Z | 6484.0 | 17 | 42 | 4271949 | 275386 | 0 | 8637 | 941 | 1.202114 |
| 2026-11-06-STU02PS-01-verifier-02 | verifier |  | 62d8daea-6c3d-4036-8996-ec5e64384cbd | acdaea6d7fa35b62b | 2 | 2026-11-06-STU02PS-01-orchestrator-01 | verifier | claude-opus-5-5 | claude-opus-5-5 | yes | 2026-11-06T11:21:06.937Z | 2026-11-06T12:20:13.420Z | 3546.5 | 28 | 68 | 4220523 | 522213 | 0 | 12981 | 2270 | 3.715062 |
| TOTAL | TOTAL |  |  |  |  |  |  | claude-opus-5-5; claude-sonnet-5-5 | claude-opus-5-5; claude-sonnet-5-5 | yes | 2026-11-06T06:36:41.587Z | 2026-11-06T13:49:07.754Z | 25946.2 | 523 | 1196 | 85666703 | 3505385 | 347617 | 448680 | 107090 | 26.868644 |

Unattributed usage (rows in the listed sessions that no invocation claims): requests=0, input=0, cache_read=0, cache_write_5m=0, cache_write_1h=0, output=0, reasoning=0, cost_usd=0.000000; likely_agent (inferred guess, not measured): none

## Cache and context

| Invocation ID | Reasoning share | Cache hit ratio | Zero cache read after first | Cache writes after gap | Cache write tokens after gap | First context | Max context | Mean context |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-06-STU02PS-01-orchestrator-01 | 0.1814 | 0.9893 | 0 | 18 | 123852 | 73730 | 307942 | 191796.5 |
| 2026-11-06-STU02PS-01-spec-writer-01 | 0.4389 | 0.9493 | 0 | 0 | 0 | 11817 | 221782 | 128734.6 |
| 2026-11-06-STU02PS-01-spec-writer-02 | 0.1700 | 0.8270 | 0 | 0 | 0 | 224979 | 242855 | 233978.7 |
| 2026-11-06-STU02PS-01-spec-writer-03 | 0.1370 | 0.9186 | 0 | 0 | 0 | 244672 | 277604 | 262225.3 |
| 2026-11-06-STU02PS-01-test-designer-01 | 0.1978 | 0.9724 | 0 | 0 | 0 | 12395 | 225260 | 133043.3 |
| 2026-11-06-STU02PS-01-developer-01 | 0.1355 | 0.9825 | 0 | 0 | 0 | 12194 | 168346 | 126651.7 |
| 2026-11-06-STU02PS-01-developer-02 | 0.2598 | 0.9513 | 1 | 1 | 172404 | 171543 | 192682 | 182728.8 |
| 2026-11-06-STU02PS-01-test-designer-02 | 0.1086 | 0.8982 | 0 | 0 | 0 | 228806 | 237358 | 233068.6 |
| 2026-11-06-STU02PS-01-test-designer-03 | 0.0579 | 0.8985 | 0 | 0 | 0 | 239119 | 248284 | 244662.4 |
| 2026-11-06-STU02PS-01-verifier-01 | 0.4497 | 0.9124 | 2 | 2 | 274954 | 13126 | 146927 | 109224.8 |
| 2026-11-06-STU02PS-01-developer-03 | 0.1699 | 0.9596 | 0 | 0 | 0 | 195140 | 217544 | 207023.8 |
| 2026-11-06-STU02PS-01-test-designer-04 | 0.1024 | 0.8736 | 0 | 0 | 0 | 249896 | 257051 | 254170.0 |
| 2026-11-06-STU02PS-01-test-designer-05 | 0.1089 | 0.9394 | 1 | 1 | 259342 | 258571 | 273870 | 267492.8 |
| 2026-11-06-STU02PS-01-verifier-02 | 0.1749 | 0.8899 | 2 | 3 | 343583 | 152331 | 180029 | 169385.9 |
| TOTAL | 0.2387 | 0.9569 | 6 | 25 | 1174135 |  | 307942 | 171168.1 |

## Tools, files and time

| Invocation ID | Tool calls | Failed tool calls | Tool calls by name | Files read | Distinct files | Repeated reads | Human messages | Active (s) | Tool time (s) | Tool calls timed | Wait before start (s) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-06-STU02PS-01-orchestrator-01 | 142 | 4 | Agent=4; Bash=97; Edit=1; Glob=1; Grep=2; PowerShell=4; Read=2; SendMessage=9; TaskStop=2; ToolSearch=4; Write=6; mcp__ccd_host__request_keep_awake=1; mcp__ccd_host__sync_with_base_branch=1; mcp__ccd_pr__get_status=1; mcp__ccd_session_mgmt__set_remote_control=1; mcp__ccd_turn__update_plan=1; mcp__ccd_turn__wrap_up=5 | 2 | 2 | 0 | 18 | 25937.8 | 1101.4 | 141 | unavailable |
| 2026-11-06-STU02PS-01-spec-writer-01 | 91 | 0 | Edit=1; Glob=10; Grep=24; Read=52; SubagentHandback=1; Write=3 | 52 | 51 | 1 | 0 | 642.4 | 16.4 | 91 | unavailable |
| 2026-11-06-STU02PS-01-spec-writer-02 | 28 | 0 | Edit=25; Grep=2; SubagentHandback=1 | 0 | 0 | 0 | 0 | 110.8 | 219.7 | 28 | 559.9 |
| 2026-11-06-STU02PS-01-spec-writer-03 | 53 | 0 | Edit=37; Grep=6; Read=9; SubagentHandback=1 | 9 | 2 | 7 | 0 | 198.4 | 299.3 | 53 | 454.3 |
| 2026-11-06-STU02PS-01-test-designer-01 | 64 | 3 | Bash=49; Read=4; SubagentHandback=1; Write=10 | 4 | 4 | 0 | 0 | 915.1 | 109.6 | 64 | 85.0 |
| 2026-11-06-STU02PS-01-developer-01 | 79 | 4 | Bash=73; Read=3; SubagentHandback=1; Write=2 | 3 | 3 | 0 | 0 | 4592.1 | 4052.2 | 79 | 85.0 |
| 2026-11-06-STU02PS-01-developer-02 | 21 | 0 | Bash=20; SubagentHandback=1 | 0 | 0 | 0 | 0 | 3179.9 | 816.8 | 21 | 160.3 |
| 2026-11-06-STU02PS-01-test-designer-02 | 10 | 1 | Bash=8; Read=1; SubagentHandback=1 | 1 | 1 | 0 | 0 | 238.7 | 199.2 | 10 | 2390.4 |
| 2026-11-06-STU02PS-01-test-designer-03 | 11 | 3 | Bash=9; Monitor=1; SubagentHandback=1 | 0 | 0 | 0 | 0 | 324.2 | 315.0 | 11 | 2596.7 |
| 2026-11-06-STU02PS-01-verifier-01 | 47 | 1 | Bash=28; Grep=8; Read=10; SubagentHandback=1 | 10 | 8 | 2 | 0 | 2045.7 | 217.3 | 47 | 17.2 |
| 2026-11-06-STU02PS-01-developer-03 | 26 | 0 | Bash=25; SubagentHandback=1 | 0 | 0 | 0 | 0 | 1834.9 | 1656.4 | 26 | 29.4 |
| 2026-11-06-STU02PS-01-test-designer-04 | 9 | 1 | Bash=7; SubagentHandback=1; TaskStop=1 | 0 | 0 | 0 | 0 | 543.1 | 490.2 | 9 | 31.8 |
| 2026-11-06-STU02PS-01-test-designer-05 | 13 | 1 | Bash=10; Read=2; SubagentHandback=1 | 2 | 2 | 0 | 0 | 6476.7 | 242.3 | 13 | 107.1 |
| 2026-11-06-STU02PS-01-verifier-02 | 24 | 0 | Bash=20; Read=3; SubagentHandback=1 | 3 | 3 | 0 | 0 | 3541.7 | 699.4 | 24 | 95.3 |
| TOTAL | 618 | 18 | Agent=4; Bash=346; Edit=64; Glob=11; Grep=42; Monitor=1; PowerShell=4; Read=86; SendMessage=9; SubagentHandback=13; TaskStop=3; ToolSearch=4; Write=21; mcp__ccd_host__request_keep_awake=1; mcp__ccd_host__sync_with_base_branch=1; mcp__ccd_pr__get_status=1; mcp__ccd_session_mgmt__set_remote_control=1; mcp__ccd_turn__update_plan=1; mcp__ccd_turn__wrap_up=5 | 86 | 69 | 17 | 18 |  | 10435.4 | 617 |  |

## Cost by token type (USD)

| Invocation ID | Input | Cache read | Cache write (5m) | Cache write (1h) | Output | Total |
| --- | --- | --- | --- | --- | --- | --- |
| 2026-11-06-STU02PS-01-orchestrator-01 | 0.000896 | 3.206554 | 0.000000 | 1.390468 | 0.941810 | 5.539728 |
| 2026-11-06-STU02PS-01-spec-writer-01 | 0.000136 | 0.415513 | 0.554450 | 0.000000 | 0.783920 | 1.754019 |
| 2026-11-06-STU02PS-01-spec-writer-02 | 0.000028 | 0.116101 | 0.607133 | 0.000000 | 0.147260 | 0.870521 |
| 2026-11-06-STU02PS-01-spec-writer-03 | 0.000056 | 0.313130 | 0.694005 | 0.000000 | 0.191140 | 1.198331 |
| 2026-11-06-STU02PS-01-test-designer-01 | 0.000240 | 0.776212 | 0.550908 | 0.000000 | 1.018590 | 2.345949 |
| 2026-11-06-STU02PS-01-developer-01 | 0.000304 | 0.945703 | 0.420860 | 0.000000 | 0.496230 | 1.863097 |
| 2026-11-06-STU02PS-01-developer-02 | 0.000096 | 0.382411 | 0.489688 | 0.000000 | 0.112140 | 0.984335 |
| 2026-11-06-STU02PS-01-test-designer-02 | 0.000044 | 0.209331 | 0.593390 | 0.000000 | 0.051010 | 0.853775 |
| 2026-11-06-STU02PS-01-test-designer-03 | 0.000044 | 0.219832 | 0.620705 | 0.000000 | 0.037990 | 0.878571 |
| 2026-11-06-STU02PS-01-verifier-01 | 0.000368 | 0.877012 | 2.103700 | 0.000000 | 0.621560 | 3.602640 |
| 2026-11-06-STU02PS-01-developer-03 | 0.000108 | 0.516502 | 0.543855 | 0.000000 | 0.132870 | 1.193335 |
| 2026-11-06-STU02PS-01-test-designer-04 | 0.000036 | 0.177629 | 0.642623 | 0.000000 | 0.046880 | 0.867168 |
| 2026-11-06-STU02PS-01-test-designer-05 | 0.000084 | 0.427195 | 0.688465 | 0.000000 | 0.086370 | 1.202114 |
| 2026-11-06-STU02PS-01-verifier-02 | 0.000272 | 0.844105 | 2.611065 | 0.000000 | 0.259620 | 3.715062 |
| TOTAL | 0.002712 | 9.427229 | 11.120845 | 1.390468 | 4.927390 | 26.868644 |

## Metadata

| Invocation ID | Arm | Phase | Revision round | Trigger | Start commit | End commit | Agent definition hash |
| --- | --- | --- | --- | --- | --- | --- | --- |
| 2026-11-06-STU02PS-01-orchestrator-01 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-spec-writer-01 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-spec-writer-02 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-spec-writer-03 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-test-designer-01 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-developer-01 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-developer-02 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-test-designer-02 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-test-designer-03 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-verifier-01 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-developer-03 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-test-designer-04 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-test-designer-05 |  |  |  |  |  |  |  |
| 2026-11-06-STU02PS-01-verifier-02 |  |  |  |  |  |  |  |
