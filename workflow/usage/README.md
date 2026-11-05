# Agent usage archive

This folder stores one token-usage report for every multi-agent feature run. It is separate from `workflow/experiments/results/`, which stores workflow comparisons and other experiments such as the A/B/C runs.

## Record a feature run

1. The orchestrator chooses a unique feature-run ID, for example `2026-11-05-STU04-01`, and creates `runs/<feature-run-id>/`.
2. Copy `templates/invocations.csv` into that folder.
3. Add one manifest row for each agent start. Use an invocation ID of `<feature-run-id>-<role>-<sequence>`, for example `2026-11-05-STU04-01-developer-01`. The ID is unique for that invocation; a second developer start gets `...-developer-02`.
4. Record the role, requested effort, source tool/session/agent IDs, and start time. Fill the finish time when the agent returns. Use timezone-aware ISO timestamps. After the agent returns, use the local `tracker export` CSV and its timestamps to confirm the session and agent IDs; that CSV stays gitignored.
5. Generate the report from `workflow/tools/token-tracker`:

   ```powershell
   Set-Location (git rev-parse --show-toplevel)
   Set-Location workflow\tools\token-tracker
   python -m tracker run-report --manifest ..\..\..\usage\runs\2026-11-05-STU04-01\invocations.csv
   ```

6. Commit `invocations.csv` and `report.md`, then link the report from the feature's row in `workflow/experiments/resource-log.md`.

The Markdown report has one row per invocation, even when a role is started more than once, and a feature-run total row. It includes model names from local usage logs, effort from the manifest, elapsed wall-clock time, token categories and cost. A blank cost means at least one needed price was unavailable. An invocation with no matching usage records is shown with zero requests; check the source IDs if you expected model calls.

The report format is labelled `invocation-v1`. Older aggregate summaries remain unchanged in `workflow/experiments/results/`; do not infer invocation-level details for them. The tracker reads each teammate's local logs, so the teammate who ran an agent must provide the correct source IDs and contribute the run's manifest/report. Never commit provider JSONL logs or prompt/reply content.
