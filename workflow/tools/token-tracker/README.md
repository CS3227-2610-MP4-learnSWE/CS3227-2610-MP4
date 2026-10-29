# Token tracker

Reads the local session logs of Claude Code and Codex and reports token use and cost per agent type and model, so workflow variants can be compared. Python 3.12+, standard library only. Not product code; it is independent of learnSWE and can be copied elsewhere.

## Run (from this folder)

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\workflow\tools\token-tracker"
python -m tracker report --cwd-contains CS3227-2610-MP4
```

Per-run summary for an experiment branch, saved for committing:

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\workflow\tools\token-tracker"
python -m tracker report --branch exp/stu02-A --out ..\..\experiments\results\stu02-A.csv
```

Row-level CSV of every request (rewritten from scratch each time, never appended):

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\workflow\tools\token-tracker"
python -m tracker export --cwd-contains CS3227-2610-MP4
```

Options on both commands: `--claude-dir` (default `~/.claude`), `--codex-dir` (default `~/.codex`), `--prices` (default `prices.json` here), `--cwd-contains TEXT`, `--since ISO-DATE`. `report` also takes `--branch` and `--out`; `export` takes `--out` (default `usage.csv`).

## What it reads

- Claude Code: `~/.claude/projects/**/*.jsonl`, including subagents in `<session>/subagents/agent-*.jsonl`. The agent type comes from the sibling `.meta.json`. Messages logged several times are counted once (largest `output_tokens`).
- Codex: `~/.codex/sessions/**/rollout-*.jsonl`. One row per `token_count` event whose cumulative total changed. Input is stored as uncached input (input minus cached input).

## Privacy

Only numbers, ids, model names, branch names and folder paths are written. No prompts or replies. `usage*.csv` here is gitignored because it holds your whole usage history. Commit only per-run summaries under `workflow/experiments/results/`. Each teammate runs the tool on their own machine.

## Cost

`prices.json` is empty on purpose: fill in `input`, `cache_read`, `cache_write_5m`, `cache_write_1h` and `output` (USD per million tokens) for each model from the provider's official pricing, and record `as_of` and `source`. A model or token type without a price gives a blank cost, never a guess. `reasoning_tokens` is a subset of `output_tokens` and is not priced separately.

## Known limits

- Codex input is assumed to include cached input (the usual convention); not checked against billing.
- The branch comes from each log line, so a session that switches branch is split only where the log records it.
- Results should be compared with the usage shown in the Claude and Codex apps before being trusted.

## Tests

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\workflow\tools\token-tracker"
python -m unittest discover -s tests
```

Tests build synthetic logs in temporary folders; no real logs are in the repo. The spec, plan and tasks are in `workflow/specs/TRK-01/`.
