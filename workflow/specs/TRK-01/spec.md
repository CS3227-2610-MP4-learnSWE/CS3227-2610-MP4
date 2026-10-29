# Spec: TRK-01 Token usage tracker

Status: Approved by the user in chat (29 Oct 2026): CSV design, gitignored local output, committed per-run summaries, Claude first, Codex included.

## Goal
Measure token use and cost per agent, model and branch from the local session logs of Claude Code and Codex, so workflow variants can be compared on cost per accepted outcome. Process tool, not product code. Standard library only.

## Behaviour
- `export` re-reads local logs and rewrites a row-level `usage.csv` from scratch (idempotent; never appends).
- `report` summarises rows (filtered by branch, working-directory text, start date) grouped by agent type and model, with totals and cost, printed as a table and optionally written to a summary CSV.
- Reads Claude Code logs (`~/.claude/projects/**/*.jsonl`, including `<session>/subagents/agent-*.jsonl` with their `.meta.json`) and Codex logs (`~/.codex/sessions/**/rollout-*.jsonl`).
- Cost uses a user-supplied `prices.json` (USD per million tokens). A model with no price gets a blank cost, never a guess.

## Acceptance criteria
- [ ] AC1: Claude assistant messages that appear several times in a log produce exactly one row, taking the largest `output_tokens`.
- [ ] AC2: Subagent files are included; rows carry `is_subagent=true`, the `agentId`, and `agent_type` from the `.meta.json`; main-session rows have `agent_type=main`.
- [ ] AC3: Cache creation is split into 5-minute and 1-hour tokens when the log gives the breakdown; otherwise all go to 5-minute.
- [ ] AC4: Lines without usage, synthetic-model messages and malformed JSON lines are skipped without error.
- [ ] AC5: Codex `token_count` events become rows from `last_token_usage`; an event whose cumulative total is unchanged is skipped; uncached input = input - cached input; model comes from the latest `turn_context`; a session with `parent_thread_id` is a subagent.
- [ ] AC6: Cost is computed from `prices.json` for known models and blank for unknown models.
- [ ] AC7: Running `export` twice produces byte-identical CSV, and no prompt or reply text appears in any output.
- [ ] AC8: `report` filters by branch and groups by agent type and model; totals equal the sum of the filtered rows.
- [ ] AC9: `--cwd-contains` limits rows to sessions whose working directory contains the text.

## Out of scope
A GUI; live monitoring; other tools' logs; estimating prices; merging CSVs from several machines (each person runs it locally and commits summaries).

## Security and privacy
Only numbers, ids, model names, branch names and paths are exported. Never message content. Local `usage*.csv` files are gitignored. No network access.

## Known limits
`reasoning_tokens` is a subset of `output_tokens` for both tools and may be 0 where the log does not report it. Codex input is assumed to include cached input (OpenAI convention); unverified against live billing. Branch comes from each log line, so a session that switches branch is split correctly only where the log records it.
