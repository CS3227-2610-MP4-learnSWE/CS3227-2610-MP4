# Agent usage archive

This folder stores one token-usage report for every multi-agent feature run. It is separate from `workflow/experiments/results/`, which stores workflow comparisons and other experiments such as the A/B/C runs.

## Automatic feature-run tracking

The orchestrator performs these steps; the human user does not need to create the files or run the report command during a normal feature run.

1. **When a feature ID is selected for a multi-agent run, before the spec-writer starts:** the orchestrator chooses a unique feature-run ID (for example, `2026-11-05-STU04-01`), creates `runs/<feature-run-id>/`, and copies `templates/invocations.csv` there.
2. **Before each agent starts:** the orchestrator adds a row with a unique invocation ID (`<feature-run-id>-<role>-<sequence>`), role, requested effort, provider tool and timezone-aware start time. Every retry or revision round is a new row.
3. **When each agent returns:** the orchestrator fills the finish time, provider tool and exact provider session ID, and agent ID when available. For Codex, take the ID from `session_meta.payload.id`; set `agent_id` to that same ID for a Codex subagent and leave it blank for the main session. The tool, source IDs and timestamps let the report attribute repeated invocations. Never put `unavailable` in the session ID field. If an agent ran on another teammate's machine, that teammate's local usage data must be collected before the shared report is complete.
4. **When the feature run ends or is stopped:** the orchestrator runs `python -m tracker run-report --manifest <manifest>`, commits `invocations.csv` and `report.md`, and links the report from the feature's row in `workflow/experiments/resource-log.md`. The report includes Claude and Codex token counts by invocation. Stopped runs are marked incomplete. If any session ID or usage record cannot be matched, say attribution is unavailable in the resource log; do not claim zero usage.

The repo has no background provider hook that observes agent launches. These are mandatory orchestrator lifecycle triggers, so report creation is automatic within the workflow. The following command is for testing or recovery, not a routine user step:

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker run-report --manifest ..\..\usage\runs\2026-11-05-STU04-01\invocations.csv
```

macOS/Linux equivalent:

```sh
cd "$(git rev-parse --show-toplevel)"
cd workflow/tools/token-tracker
python3 -m tracker run-report --manifest ../../usage/runs/2026-11-05-STU04-01/invocations.csv
```

The Markdown report has one row per invocation, even when a role is started more than once, and a feature-run total row. It includes model names from local usage logs, effort from the manifest, elapsed wall-clock time, token categories and cost. A blank cost means at least one needed price was unavailable. An invocation with no matching usage records is shown with zero requests; treat this as measured zero only after confirming its source IDs and local logs are complete.

## Rebuilding invocations from logs (`invocation-v2`)

When per-invocation detail is needed (cache behaviour, tool and file-read counts, time split, orchestrator spend) or no hand-written manifest exists, `invocations-from-logs` rebuilds the invocations from Claude Code session logs. It does not replace the orchestrator's manifest for routine runs; it is for analysis and recovery.

```powershell
Set-Location (git rev-parse --show-toplevel)
Set-Location workflow\tools\token-tracker
python -m tracker invocations-from-logs --run-id 2026-11-05-ADM01-01 SESSION_ID [SESSION_ID ...]
```

It writes `report-v2.md` (format `invocation-v2`) and `metrics-v2.csv` into `runs/<run-id>/`, next to any `invocations.csv` and `report.md` of the same run. It produces one `orchestrator` row per session and one row per subagent prompt, with the role from the agent type the log records, the agent type the orchestrator requested, and an optional label from a metadata sidecar (`--meta`) that can also carry arm, phase, revision round, trigger, start and end commit and an agent-definition hash. This detailed reconstruction currently covers Claude Code only. Use the routine `run-report` manifest path above for both Claude and Codex invocation token totals.

Unavailable data is written `unavailable`, never estimated. Costs are tracker list-price estimates, not billed. Outputs hold numbers, IDs, model names, roles, timestamps, folder paths and the paths of files read; never prompts, replies or file contents, and raw logs are never committed. Known limits: the Claude Code log format is undocumented and may change; where a worktree-isolated subagent's log is stored is unverified; Codex `run-report` includes token totals but not Claude-specific tool, file-read, context or detailed timing metrics; the Haiku 5.5 price tier rule is an assumption; wall-clock gaps are not dependencies. Options, metric rules and the sidecar format are in `workflow/tools/token-tracker/README.md`.

The report format is labelled `invocation-v1`. Older aggregate summaries remain unchanged in `workflow/experiments/results/`; do not infer invocation-level details for them. The tracker reads each teammate's local logs; when agents run on different machines, usage data must be collected from those machines before the shared report is complete. The tracker does not merge reports from multiple machines automatically. Never commit provider JSONL logs or prompt/reply content.
