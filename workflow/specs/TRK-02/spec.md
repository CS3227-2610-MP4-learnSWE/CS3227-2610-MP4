# Spec: TRK-02 Per-invocation usage reports

Status: Approved by user in chat (2026-11-05): per-feature-run Markdown report with unique invocation rows, model, effort and elapsed time.

## Goal
Record token usage for every multi-agent feature run, with a distinct row for each agent invocation, including repeated invocations of the same role. Keep existing aggregate tracker reports available for historical comparisons.

## Behaviour
- A feature run has a stable `feature_run_id` and a manifest at `workflow/usage/runs/<feature_run_id>/invocations.csv`.
- Each agent start is recorded once in the manifest with a globally unique `invocation_id`, role, effort setting, source tool, source session ID, source agent ID, and start and finish timestamps.
- Invocation IDs follow `<feature_run_id>-<role>-<sequence>` (for example `2026-11-05-STU04-01-developer-01`); every new start gets a new sequence value for that role.
- The manifest uses columns in this order: `feature_run_id, invocation_id, role, effort, tool, session_id, agent_id, started_at, finished_at`.
- `invocation_id` is the unique primary key. `feature_run_id` groups invocations into one build run. No separate attempt-number field is used.
- A new `run-report` command reads the manifest and local Claude Code and Codex usage logs, matches usage rows by tool/session/agent IDs, and uses timestamps to disambiguate a reused source ID.
- It writes one Markdown report at `workflow/usage/runs/<feature_run_id>/report.md`, with one row per invocation and a feature-run total. Invocation rows show role, model(s) observed in usage logs, configured effort, elapsed wall time, request count, token categories and cost.
- The report identifies its format as `invocation-v1`. Existing `export` and `report` commands and their output remain unchanged.
- Unmatched or multiply matched usage rows for a manifest source are reported as attribution errors; the command exits non-zero instead of silently assigning or double-counting them.
- An invocation with no matching usage rows is retained with zero requests and a note asking the reader to verify its source IDs or confirm it made no model calls.
- The manifest and Markdown report contain usage metadata only, never prompt/reply text. Local raw usage exports remain gitignored.

## Acceptance criteria
- [ ] AC1: Two invocations with the same feature run and role receive separate rows when their invocation IDs differ.
- [ ] AC2: Each manifest row requires a unique `<feature_run_id>-<role>-<numeric-sequence>` invocation ID, a non-empty role/effort/source session ID, tool `claude` or `codex`, and timezone-aware ISO timestamps where `finished_at` is not earlier than `started_at`.
- [ ] AC3: Usage rows are assigned to the invocation with matching tool, session ID and agent ID, and timestamp within its start/end interval.
- [ ] AC4: A usage row matching zero or multiple invocations for a referenced source is reported as an attribution error and does not produce a successful report.
- [ ] AC5: The report includes model(s) observed in usage rows, configured effort, elapsed wall-clock duration, request count, input/cache-read/cache-write/output/reasoning token sums and cost per invocation.
- [ ] AC6: The feature-run token/request totals equal the sum of invocation rows; run elapsed time is latest finish minus earliest start (not the sum of parallel invocations); if any contributing cost is unknown, total cost is blank.
- [ ] AC7: Markdown output is deterministic, includes `invocation-v1`, escapes table delimiters/newlines, and contains no prompt/reply text.
- [ ] AC8: Re-running the command with identical manifest/logs produces byte-identical output.
- [ ] AC9: Existing `export` and aggregate `report` behavior remains unchanged.
- [ ] AC10: A report is written only under the manifest's matching run folder, unless the caller explicitly supplies another output path.
- [ ] AC11: An invocation with no matched usage rows remains visible with zero requests and a note to verify its source IDs or confirm it made no model calls.

## UI states and copy
No screen: this is a local command-line tool.

## Out of scope
- Starting or branching agent workflows automatically.
- Live token monitoring.
- Backfilling invocation IDs for old aggregate reports.
- Uploading or centrally collecting raw provider logs from teammates.
- HTML dashboards or external dependencies.

## Security and AI safeguards
This tool reads local metadata and emits aggregate usage data. It does not call an LLM or process prompt/reply content into reports.
- Concurrent requests (same time): not applicable: report generation is a local, deterministic read of completed log files.
- Normalisation: source IDs are compared exactly; timestamps are parsed as timezone-aware ISO values and normalised to UTC before range checks.

## Open questions
None for the agreed minimal implementation.
