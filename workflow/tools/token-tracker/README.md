# Token tracker

Reads local Claude Code and Codex session logs and reports token use and cost. The existing aggregate report groups by agent type and model; `run-report` produces a per-invocation Markdown report for one feature run from a hand-written manifest; `invocations-from-logs` rebuilds the invocations from Claude Code logs and adds cache, tool, file-read and time metrics. Python 3.12+, standard library only. Not product code; it is independent of learnSWE and can be copied elsewhere.

## Run (from this folder)

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker report --cwd-contains CS3227-2610-MP4
```

macOS/Linux:

```sh
cd "$(git rev-parse --show-toplevel)"
cd workflow/tools/token-tracker
python3 -m tracker report --cwd-contains CS3227-2610-MP4
```

Per-run summary for an experiment branch, saved for committing:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker report --branch exp/stu02-A --out ..\..\experiments\results\stu02-A.csv
```

Row-level CSV of every request (rewritten from scratch each time, never appended):

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker export --cwd-contains CS3227-2610-MP4
```

Generate one report for all agent invocations in a feature run (the manifest and report live together):

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker run-report --manifest ..\..\..\usage\runs\2026-11-05-STU04-01\invocations.csv
```

The command writes `report.md` next to the manifest. Supply `--out PATH` to choose another location. A manifest has one row per agent start and these columns in order: `feature_run_id, invocation_id, role, effort, tool, session_id, agent_id, started_at, finished_at`. Use a globally unique `feature_run_id`; build each `invocation_id` as `<feature_run_id>-<role>-<sequence>`. Record start and finish timestamps with a timezone. `tool` is `claude` or `codex`; the source session/agent IDs connect local usage records to the invocation. Model names come from usage records; effort is recorded in the manifest.

`export` and `report` options: `--claude-dir` (default `~/.claude`), `--codex-dir` (default `~/.codex`), `--prices` (default `prices.json` here), `--cwd-contains TEXT`, `--since ISO-DATE`. `report` also takes `--branch` and `--out`; `export` takes `--out` (default `usage.csv`). `run-report` takes `--manifest`, the provider-directory and price options, and optional `--out`.

## Invocations and metrics from logs (`invocations-from-logs`)

Rebuilds invocations from Claude Code session logs without a manifest, and writes an `invocation-v2` Markdown report and a metrics CSV:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker invocations-from-logs --run-id 2026-11-05-ADM01-01 SESSION_ID [SESSION_ID ...]
```

macOS/Linux: `python3 -m tracker invocations-from-logs --run-id 2026-11-05-ADM01-01 SESSION_ID`.

Options: `--run-id` (required; starts with a letter or digit, then letters, digits, `.`, `_`, `-`), `--meta PATH` (optional sidecar, below), `--claude-dir`, `--codex-dir` (only passed to the shared row reader; Codex rows are discarded), `--prices`, `--out-md` (default `workflow/usage/runs/<run-id>/report-v2.md`) and `--out-csv` (default `workflow/usage/runs/<run-id>/metrics-v2.csv`). Outputs are written only after every check passes; an existing file is overwritten only then. Exit codes: 0 success, 1 cross-check mismatch, 2 any input or usage error. Every error line starts `error: ` and names the input that caused it (option and value, argument position, sidecar line number, path). Warnings (`warning: ...`, for example a subagent without a usable `meta.json`) go to stderr and do not change the exit code.

**How invocations are cut.** A session ID names `<claude-dir>/projects/<project folder>/<session>.jsonl` (the main session) and `.../<session>/subagents/agent-<id>.jsonl` with a sibling `.meta.json`. The main session becomes one `orchestrator` invocation per session, so orchestrator spend is visible. Each subagent file gives one invocation per prompt: a prompt starts at the first non-meta string user line and at each string user line that follows a `SubagentHandback` result, so a resumed subagent splits per new prompt. Invocation IDs are `<run-id>-<role>-<NN>`, numbered per role by start time, then session, agent and prompt. Adding an earlier invocation can renumber later ones, so write the sidecar after you have the IDs.

**Reading the role columns.** `role` is the agent type Claude Code logged. `requested_agent_type` is the `subagent_type` named in the orchestrator's `Agent` call that launched it (found through the `.meta.json` `toolUseId`; `unavailable` if none matches or the text is not a short plain name). `role_label` is a free label you put in the sidecar; it is display only and never changes an ID. When the logged type is generic (`general-purpose`) or `unknown`, use the requested type and the label to tell stages apart.

**Metrics** (each derived from the logs or `unavailable`; a blank cell means not applicable):

| Column(s) | Rule |
|---|---|
| `requested_model`, `observed_models`, `model_match` | `requestedModel` against `message.model` per request |
| `cost_input` ... `cost_output`, `cost_usd` | tokens times list price per type, tier chosen per request; a model or tier without a price gives `unavailable` |
| `reasoning_share` | thinking tokens / output tokens, over requests that report thinking tokens |
| `cache_hit_ratio` | cache read / (input + cache read + cache writes) |
| `zero_cache_read_after_first` | requests after the first with zero cache read |
| `cache_writes_after_gap`, `cache_write_tokens_after_gap` | requests that write cache more than 300 seconds after the previous request |
| `context_first`, `context_max`, `context_mean` | prompt size per request (input + cache read + cache writes) |
| `tool_calls`, `tool_calls_by_name`, `failed_tool_calls` | distinct `tool_use` IDs; calls whose result has `is_error` |
| `files_read`, `files_distinct`, `files_repeated`, `repeated_paths` | `Read` calls only; paths normalised (`/`, `.`/`..` collapsed, lowercase drive letter); paths only, never contents |
| `elapsed_s`, `active_s` | first to last log line; first to last request |
| `tool_time_s`, `tool_calls_timed` | sum of tool_use to tool_result times for calls with both timestamps (includes test commands; parallel calls overlap) |
| `wait_before_start_s` | start minus the latest finish among other invocations that finished before it; a wall-clock gap, not a dependency |
| `human_messages` | non-meta user messages after the prompt that opens the invocation |

**Output rows.** One row per invocation, then `run_total` (elapsed is latest finish minus earliest start, not a sum) and `unattributed`. Unattributed usage is usage in the listed sessions that no invocation claims (for example a log of the session stored outside the folder layout). It is not an error and totals still reconcile. Its `likely_agent (inferred guess)` names the invocation of the same session whose time window contains the row (`rule: window`, shortest window wins), else the nearest by time (`rule: nearest`), else `unavailable (rule: none)`. It is an inference, labelled as one, and is never added to any invocation's numbers.

**Cross-check.** Before writing, the per-invocation rows plus unattributed rows must equal what `report` sees for the same sessions. A mismatch exits 1 and writes nothing; the message names the sessions, each quantity that differs with both values and the difference, and the likely cause.

**Metadata sidecar (`--meta`).** UTF-8 CSV with exactly this header: `invocation_id,role_label,arm,phase,revision_round,trigger,start_commit,end_commit,agent_definition_hash`. One row per invocation (not every invocation needs one). `trigger` is blank or one of `first`, `retry`, `revision`, `resume`; `revision_round` is blank or a non-negative integer; an unknown or duplicate ID or a malformed row is an error. Rows carry these cells when given and blank cells otherwise. Typical flow: run once to get the IDs, write the sidecar, run again.

**Privacy.** Outputs hold only numbers, IDs, model names, roles, timestamps, folder paths and the paths of files read. No prompt, reply, tool result or file content is read into an output; the only tool input echoed is the `Read` file path and the short `subagent_type` name.

## Use in the workflow

For every multi-agent feature run, the orchestrator starts tracking when the feature is selected, records every agent launch/return (including retries), and generates the report when the run ends or is stopped. The human user does not do this manually. Each teammate runs the tracker on their own machine only when their local logs are needed, because the tracker reads local session logs. Routine feature-run records go under `workflow/usage/runs/<feature-run-id>/`; workflow comparison experiments such as A/B/C stay under `workflow/experiments/results/`. This is an orchestrator lifecycle requirement, not a background provider hook.

1. On feature selection, the orchestrator creates the run folder and manifest before starting the spec-writer.
2. On each launch, it adds a unique invocation row; on return, it fills `finished_at`, `tool`, the required `session_id`, and `agent_id` when available.
3. On run close, it runs `run-report`, commits the manifest and `report.md`, and links the report in `workflow/experiments/resource-log.md`.
4. Use `report --branch <branch-name>` for the existing aggregate view or manually run `run-report` only for testing/recovery.

New per-run reports use format `invocation-v1`. Existing aggregate reports under `workflow/experiments/results/` remain unchanged and are historical/experiment records. The row-level `usage.csv` holds local usage history and is gitignored. Commit invocation manifests and Markdown run reports, not provider logs or prompts/replies. Quote numbers as measured by the tracker, not as billed (see Cost and Known limits).

## What it reads

- Claude Code: `~/.claude/projects/**/*.jsonl`, including subagents in `<session>/subagents/agent-*.jsonl`. The agent type comes from the sibling `.meta.json`. Messages logged several times are counted once (largest `output_tokens`).
- Codex: `~/.codex/sessions/**/rollout-*.jsonl`. One row per `token_count` event whose cumulative total changed. Input is stored as uncached input (input minus cached input).

## Privacy

Only numbers, IDs, model names, roles, effort settings, timestamps, branch names and folder paths are written. No prompts or replies. `usage*.csv` here is gitignored because it holds your whole usage history. Each teammate runs the tool on their own machine and contributes the run manifest/report to the shared branch.

## Cost

`prices.json` holds `input`, `cache_read`, `cache_write_5m`, `cache_write_1h` and `output` (USD per million tokens) per model, with `as_of` and `source`. These are tracker list-price estimates, not billed. A model or token type without a price gives a blank cost (`unavailable` in the v2 outputs), never a guess. `reasoning_tokens` is a subset of `output_tokens` and is not priced separately.

An entry may instead hold `tiers`, a list of price rows chosen per request by prompt size (input + cache read + cache writes): the first row whose `max_prompt_tokens` is at least the prompt size is used, and a last row without `max_prompt_tokens` catches the rest. `claude-haiku-5-5` uses this (up to and including 100,000 tokens, then above; as of 2026-11-05, from the provider pricing page). An entry with `"match_variants": true` also prices model IDs that extend its key after a character other than a letter or digit, so `claude-haiku-5-5-20261105` and `claude-haiku-5-5[1m]` are priced as Haiku 5.5, while `claude-haiku-5-50` and `anthropic.claude-haiku-5-5` are not. Sonnet 5.5 and Opus 5.5 are exact-match, flat entries.

## Known limits

- Codex input is assumed to include cached input (the usual convention); not checked against billing.
- The branch comes from each log line, so a session that switches branch is split only where the log records it.
- Results should be compared with the usage shown in the Claude and Codex apps before being trusted.
- `invocations-from-logs` reads the Claude Code log format, which is undocumented and may change. Its fields were observed in one probe session (`workflow/specs/TRK-03/log-probe.md`); a missing field gives `unavailable`.
- Where a worktree-isolated subagent's log is stored is unverified. A log of a listed session outside the folder layout is shown as unattributed usage, with a labelled guess, not attached to an invocation.
- Codex logs get no new metrics; a session found only in Codex logs counts as "no logs".
- The Haiku tier rule (prompt size above 100,000 tokens uses the second row) is an unverified assumption. Only IDs that extend `claude-haiku-5-5` after a non-alphanumeric character are priced as Haiku; provider-prefixed IDs are not.
- Wall-clock gaps (`wait_before_start_s`) are not dependencies. Orchestrator elapsed time includes idle time between human turns, and its tool time includes waiting for subagents. `human_messages` may include injected messages that are not marked meta. Repeated reads ignore offsets and limits. Roles depend on the session's agent registry (unregistered agents log as `general-purpose`).
- Costs are tracker list-price estimates, not billed.

## Tests

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m unittest discover -s tests
```

macOS/Linux:

```sh
cd "$(git rev-parse --show-toplevel)"
cd workflow/tools/token-tracker
python3 -m unittest discover -s tests
```

Tests build synthetic logs in temporary folders; no real logs are in the repo. The original tracker spec is in `workflow/specs/TRK-01/`; invocation reports are specified in `workflow/specs/TRK-02/`; log-derived invocations and metrics in `workflow/specs/TRK-03/`.
