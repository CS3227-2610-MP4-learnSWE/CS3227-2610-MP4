# Agent usage archive

This folder stores one token-usage report for every multi-agent feature run. It is separate from `workflow/experiments/results/`, which stores workflow comparisons and other experiments such as the A/B/C runs.

## Automatic feature-run tracking

The orchestrator performs these steps; the human user does not need to create the files or run the report command during a normal feature run.

1. **When a feature ID is selected for a multi-agent run, before the spec-writer starts:** the orchestrator chooses a unique feature-run ID (for example, `2026-11-05-STU04-01`), creates `runs/<feature-run-id>/`, and copies `templates/invocations.csv` there.
2. **Before each agent starts:** the orchestrator adds a row with a unique invocation ID (`<feature-run-id>-<role>-<sequence>`), role, requested effort, provider tool and timezone-aware start time. Every retry or revision round is a new row.
3. **When each agent returns:** the orchestrator fills the finish time, provider tool and session ID, and agent ID when available. The report tool requires the session ID and uses timestamps to distinguish repeated invocations in the same session. Model and token counts come from local provider usage logs. If an agent ran on another teammate's machine, that teammate's usage data must be collected before the shared report is complete.
4. **When the feature run ends or is stopped:** the orchestrator generates the report, commits `invocations.csv` and `report.md`, and links the report from the feature's row in `workflow/experiments/resource-log.md`. Stopped runs are marked incomplete.

The repo has no background provider hook that observes agent launches. These are mandatory orchestrator lifecycle triggers, so report creation is automatic within the workflow. The following command is for testing or recovery, not a routine user step:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker run-report --manifest ..\..\..\usage\runs\2026-11-05-STU04-01\invocations.csv
```

macOS/Linux equivalent:

```sh
cd "$(git rev-parse --show-toplevel)"
cd workflow/tools/token-tracker
python3 -m tracker run-report --manifest ../../../usage/runs/2026-11-05-STU04-01/invocations.csv
```

The Markdown report has one row per invocation, even when a role is started more than once, and a feature-run total row. It includes model names from local usage logs, effort from the manifest, elapsed wall-clock time, token categories and cost. A blank cost means at least one needed price was unavailable. An invocation with no matching usage records is shown with zero requests; check the source IDs if you expected model calls.

The report format is labelled `invocation-v1`. Older aggregate summaries remain unchanged in `workflow/experiments/results/`; do not infer invocation-level details for them. The tracker reads each teammate's local logs; when agents run on different machines, usage data must be collected from those machines before the shared report is complete. The tracker does not merge reports from multiple machines automatically. Never commit provider JSONL logs or prompt/reply content.
