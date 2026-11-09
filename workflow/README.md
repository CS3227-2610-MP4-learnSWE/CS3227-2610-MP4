# Workflow index

Everything about how this project is built. The default agent definitions live in `.claude/agents/` because Claude Code loads them from there; everything else is here.

| Path | Purpose |
|---|---|
| `coordination.md` | Coordination pattern: generator-verifier with an independent test designer; triggers, isolation, handoffs, revision caps, conflict resolution, verification. |
| `ui-design.md` | Shared, user-approved UI principles for future screen specs and redesigns: hierarchy, outlined inputs, colours, responsive layouts, accessible notifications and visual checks. |
| `variants/` | Workflow variants under comparison (A split verification, B merged verification, single-session baseline) and how to switch between them. |
| `STATUS.md` | One row per feature: stage, branch, PR, open items. |
| `notes.md` | Live handoff log between agents/sessions. Newest 10 entries, newest first. |
| `notes-archive.md` | Older handoff entries, moved unchanged from `notes.md`. |
| `templates/` | `spec.md`, `plan.md`, `tasks.md`, `handoff.md` templates, and a filled sample tasks file (`tasks-sample-ADM-06.md`). |
| `templates/retro.md` | One retro per feature when it closes: revision rounds, who found each defect, tokens and cost, RED-before-GREEN evidence, steps outside the pipeline. |
| `specs/<feature-id>/` | Per-feature spec, plan and tasks (spec-driven development). |
| `experiments/context-engineering.md` | Context-engineering experiments and results. |
| `experiments/resource-log.md` | Per-task model, token, revision-round and retry records. |
| `experiments/results/` | Committed per-run usage summaries produced by the token tracker. |
| `usage/runs/` | Per-feature-run invocation manifests and Markdown token reports; distinct from workflow comparison experiments. |
| `tools/token-tracker/` | Token usage tracker for Claude Code and Codex logs; see its README. |
| `tools/speccheck/` | Spec checker: required sections and labelled items in `spec.md`, `plan.md`, `tasks.md`; run before the build phase; see its README. |
| `tools/phase2/` | Phase 2 runner for backend suites: merge the run branch into the test worktree, run pytest, write a report; no agent. See its README and `experiments/results/adm01-phase2-script.md`. |
| `security/threat-model.md` | AI and development-process threats and controls. |
| `security/test-log.md` | Security test cases, outcomes and fixes. |
| `checklist.md` | Submission and setup checklist with owners. |
| `AppShellPlan.md` | Execution record of the first app-shell phase. |
| `deployment.md` | Deployment (CD) options and open hosting decisions. |
| `../.github/workflows/ci.yml` | Continuous integration; plan in `specs/CI-01/plan.md`. |

## Agent roster, Variant B (`.claude/agents/`)

| Agent | Model | Job |
|---|---|---|
| `spec-writer` | sonnet | Feature ID to spec, plan (with contract), tasks. Shared pre-step. |
| `developer` | sonnet | Generator: implements from the spec; fixes defects. |
| `test-designer` | sonnet | Independent tests from the spec; runs the suite at verification. |
| `verifier` | opus | Read-only code, docs and security review in one pass; re-runs the suite; severity rule for concurrency and normalisation. |

This is Variant B (merged verification), chosen after a fair comparison in which A, B and a single-session baseline ran from the same commit with the same model and settings (`experiments/results/stu02-decision.md`). Variant A's separate reviewer and security-reviewer were removed; their record stays in `variants/` and `experiments/`.

`AGENTS.md` at the repo root is the single source of the shared rules and holds the role definitions; Codex reads it and `CLAUDE.md` imports it. Role text is also in `.claude/agents/`; edit both places together.

The human team members approve each spec/plan and each PR. Nothing is committed directly to `master`.

## Measuring token usage

The orchestrator starts tracking when a feature is selected for a multi-agent run, records each agent start and return (including retries), and generates/links the report when the run closes. The human user does not do this manually. Keep A/B/C workflow comparisons and other experiments under `experiments/results/`.
Each teammate runs the tracker on their own machine because it reads local tool logs. Commit only the manifest and aggregate Markdown report; the row-level `usage.csv` stays local.
A feature is not closed until its usage report is linked from `experiments/resource-log.md`; every handoff states the invocation ID, model, effort, elapsed time and report path (`templates/handoff.md`).
Full steps, options and limits: [`tools/token-tracker/README.md`](tools/token-tracker/README.md#use-in-the-workflow).

Every explicit workflow invocation must close with a generated and linked report.md usage table, including incomplete runs. See coordination.md and usage/README.md closeout checks. Standard report.md has one Token usage column; unavailable attribution must be explicit.
