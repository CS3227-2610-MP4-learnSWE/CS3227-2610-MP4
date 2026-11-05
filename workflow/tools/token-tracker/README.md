# Token tracker

Reads local Claude Code and Codex session logs and reports token use and cost. The existing aggregate report groups by agent type and model; `run-report` produces a per-invocation Markdown report for one feature run. Python 3.12+, standard library only. Not product code; it is independent of learnSWE and can be copied elsewhere.

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

`prices.json` is empty on purpose: fill in `input`, `cache_read`, `cache_write_5m`, `cache_write_1h` and `output` (USD per million tokens) for each model from the provider's official pricing, and record `as_of` and `source`. A model or token type without a price gives a blank cost, never a guess. `reasoning_tokens` is a subset of `output_tokens` and is not priced separately.

## Known limits

- Codex input is assumed to include cached input (the usual convention); not checked against billing.
- The branch comes from each log line, so a session that switches branch is split only where the log records it.
- Results should be compared with the usage shown in the Claude and Codex apps before being trusted.

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

Tests build synthetic logs in temporary folders; no real logs are in the repo. The original tracker spec is in `workflow/specs/TRK-01/`; invocation reports are specified in `workflow/specs/TRK-02/`.
