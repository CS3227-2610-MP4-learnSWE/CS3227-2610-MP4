# Plan: TRK-02 Per-invocation usage reports

## Data model
- Input manifest CSV columns: `feature_run_id, invocation_id, role, effort, tool, session_id, agent_id, started_at, finished_at`.
- `invocation_id` is unique across manifests; `feature_run_id` is the grouping key and directory name.
- One invocation can use multiple models; report `model(s)` as a sorted, semicolon-separated list and aggregate the per-model costs already computed on each `UsageRow`.
- Keep existing `UsageRow` and aggregate summary schemas unchanged.
- Report columns: `record, feature_run_id, invocation_id, role, model(s), effort, elapsed, requests, input, cache_read, cache_write_5m, cache_write_1h, output, reasoning, cost_usd`. Invocation rows use `record=invocation`; the final row uses `record=feature_run_total` and blank `invocation_id`.

## API endpoints
Not applicable: local CLI tool.

## Components and modules
- New `tracker/run_report.py`: read/validate the per-run manifest, attribute `UsageRow` objects, aggregate invocation totals, render and write Markdown.
- `tracker/cli.py`: add `run-report --manifest PATH [--claude-dir PATH] [--codex-dir PATH] [--prices PATH] [--out PATH]`; default output is `report.md` next to the manifest.
- Reuse `export.collect_rows`, `UsageRow`, `pricing.load_prices`, and existing parser functions. Leave `report.summarise` unchanged.
- New `tests/test_run_report.py`: synthetic manifest and provider logs.
- Update token-tracker README, workflow README, coordination, handoff template and resource-log guidance.
- New `workflow/usage/README.md`: explain the archive, manifest creation and report regeneration.

## UI contract
No screen: local CLI. Success prints the report path and invocation count. Invalid manifest or attribution errors print a specific error to stderr, exit non-zero, and do not overwrite a prior successful report.

## AI usage
None. Uses local provider logs only; no live model calls.

## Test plan
- Validate valid/invalid manifests, unique IDs and timestamps.
- Test repeated role invocations in one feature run, attribution by source identifiers and time ranges, model/effort display, duration, all token sums, cost handling, total-row equality, Markdown escaping and deterministic bytes.
- Test unmatched and ambiguous attribution fails without replacing an existing report.
- Run the complete existing tracker unittest suite to prove the legacy commands remain unchanged.

## Decisions
- Use Markdown for the committed per-run report; keep raw row-level CSV local and ignored.
- Do not change the existing experiment-results directory or historical files.
- The orchestrator records each invocation in its run manifest; tracker IDs from local logs are matching metadata and need not be shown in the report table.
