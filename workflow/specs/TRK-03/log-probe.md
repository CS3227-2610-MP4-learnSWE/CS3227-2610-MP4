# TRK-03 log probe

Read-only inspection of Claude Code session logs on 2026-11-05, to fix what the TRK-03 spec may rely on. Field names and counts only; no prompt or reply text is quoted. The Claude Code log format is not a documented, stable interface, so every field below is "observed", not "guaranteed" (see the spec's known limits).

## Sample

- One session under `~/.claude/projects/<repo folder>/` has a `subagents/` folder: `18c5e2f6-090d-4bc9-9483-50edca41322b` (2026-10-30, branch `orchestration/optimize-orchestration-2`). It is the only such session for this repository on this machine; other sessions have no subagents. The probe is therefore one session, 8 subagent files, 221 main-session assistant lines and 111 subagent assistant lines (per-line counts, before the tracker's de-duplication).
- Layout: `<session>.jsonl` (main) and `<session>/subagents/agent-<agentId>.jsonl` with a sibling `agent-<agentId>.meta.json`.

## Line types (main session, 900 lines)

`user` 121, `assistant` 221, `attachment` 38, `system` 16, `queue-operation` 58, `last-prompt` 55, `custom-title` 56, `agent-name` 54, `relocated` 55, `atis-latch` 55, `api-request` 102, `api-request-blob` 51, `api-request-shape` 2, `file-history-snapshot` 10, `file-history-delta` 2, `cost-state` 3, `mode` 1. Subagent files hold only `user`, `assistant`, `attachment`, `api-request`, `api-request-blob`, `api-request-shape`.

## Fields the tracker can use

| Need | Where it is | Observed |
|---|---|---|
| Timestamps | top-level `timestamp` on `user`, `assistant`, `attachment`, `system`, `api-request` lines | present on 560 of 900 main lines; `api-request-blob`, `queue-operation` and some others have none |
| Token usage | `message.usage`: `input_tokens`, `cache_creation_input_tokens`, `cache_read_input_tokens`, `output_tokens`, `output_tokens_details`, `cache_creation` (`ephemeral_5m_input_tokens`, `ephemeral_1h_input_tokens`), `server_tool_use`, `service_tier`, `inference_geo`, `iterations`, `speed`, `fallback_credit` | on all 221 main and 98 subagent assistant lines |
| Observed model | `message.model` | on every assistant line |
| Requested model | top-level `requestedModel` on the same assistant line; `.meta.json` has `model` as an alias (`sonnet`, `opus`) | equal to `message.model` on all 332 lines here; a mismatch was not observed |
| Effort | top-level `effort` and `perTurnEffort` on assistant lines | present, `low` throughout |
| Stop reason | `message.stop_reason`: `tool_use` 199, `end_turn` 22 (main) | present on assistant lines |
| Thinking | content block `thinking`; top-level `thinkingDurationMs`, `thinkingDisplay` on some lines; `output_tokens_details.thinking_tokens` (already used by the tracker) | 83 thinking blocks in main |
| Tool calls | assistant `message.content[]` block `type: tool_use` with `id`, `name`, `input` | 130 in main (Bash 79, Agent 8, Write 2, SendMessage 2, others) |
| Tool results | user `message.content[]` block `type: tool_result` with `tool_use_id` and `is_error`; top-level `sourceToolAssistantUUID`, `toolUseResult` | 133 results in main, 2 with `is_error` |
| File reads | `tool_use` named `Read` with `input.file_path` (path only needed); `Grep` and `Glob` have `pattern` and `path` | `Read` 26 in total across 3 subagents (2, 9 and 15); none in the main session |
| Human message vs tool result | user line whose `content` is a string (human or injected) versus a list with `tool_result` | 19 string-content user lines in main; 7 carry `isMeta: true` |
| Cost cross-check | `cost-state` lines: `totalCostUSD`, `totalAPIDuration`, `totalAPIDurationWithoutRetries`, `totalToolDuration`, `totalDuration`, `startTime`, `modelUsage`, `hasUnknownModelCost` | 3 lines in main only |
| Git branch and cwd | top-level `gitBranch`, `cwd` | on `user`/`assistant` lines |

## Subagents

- `.meta.json` keys: `agentType`, `description`, `finished`, `model`, `requestNonInteractive`, `requestShape`, `spawnDepth`, `toolUseId`. Here `agentType` was `general-purpose` for all 8 (the agent types were not registered in that session), so role names depend on the session's agent registry.
- `toolUseId` equals the `id` of an `Agent` `tool_use` block in the main session for all 8 subagents. That is the link from a subagent file to the orchestrator call (and its `subagent_type`, `model` and `isolation` inputs) that started it.
- Subagent lines carry `agentId`, `isSidechain: true`, `sessionId` (the parent session ID) and `attributionAgent`. Subagent usage rows therefore have a non-blank `agentId`.
- The `Agent` tool result in the main session has `toolUseResult` keys `agentId`, `status`, `isAsync`, `resolvedModel`, `outputFile`, `canContinueAgent`.
- Every subagent ends each prompt with a `SubagentHandback` `tool_use`.

## Main-session usage rows and blank agent id

All 221 main-session assistant lines have no `agentId` (blank), so the existing tracker labels them `main`. Subagent lines never have a blank `agentId` (0 of 111). A main-session row is therefore recognisable as `agent_id == ""`.

## Resumed subagents

Two `SendMessage` calls (and `toolUseResult` keys `resumedAgentId`, `revivedAgentId`) appear in the main session. A resume does not add a new file. It appends to the same `agent-<id>.jsonl`. Boundaries seen in the subagent that handed back twice:

1. First prompt: a non-meta string user line (`isMeta` absent), followed by one `isMeta` string user line (injected context).
2. After `SubagentHandback` `tool_use` and its `tool_result`, the next prompt is an `isMeta: true` string user line with a new `promptId`.

So a prompt boundary is: the first non-meta string user line, and every string user line that follows a `SubagentHandback` result. `promptId` alone is not usable: it also changes between tool-result turns (4 or 5 distinct values in files with one non-meta prompt). All 8 subagent files have exactly one non-meta string user line. One file has two `SubagentHandback` calls and so two prompts by this rule (the only observed resume); the other seven have one prompt.

## Duplicate logging

Each content block of one assistant message is logged as a separate line with the same `message.id` (111 of 160 ids appear more than once, at most 7 times). The tracker already keeps the line with the largest `output_tokens`. A tool-call count must count each `tool_use` `id` once.

## Worktree-isolated subagents

Not observed. No log in this project has a `cwd` containing `worktree`, and no `isolation` input was used in the sampled `Agent` calls. The spec must therefore state that where a worktree-isolated subagent's log lands is unverified, and handle the case that its file is absent or under another project folder (the tool already scans all of `projects/`).

## Tool timing

In the one subagent file sampled for this (27 pairs), a `tool_use` line and its `tool_result` line both have timestamps for 19 pairs; for the other 8 one side has none. Tool time is derived from the pair when both exist and is otherwise "unavailable" for that call.

## Gaps for the spec

- Not available in the sample: worktree log location, a model mismatch, a Codex equivalent of any metric, `isolation` input. These are written as "unavailable" or "not observed", never estimated.
- The format is undocumented and can change; metrics parse defensively and report "unavailable" when a field is missing.
