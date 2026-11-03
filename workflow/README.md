# Workflow index

Everything about how this project is built. The default agent definitions live in `.claude/agents/` because Claude Code loads them from there; everything else is here.

| Path | Purpose |
|---|---|
| `coordination.md` | Coordination pattern: generator-verifier with an independent test designer; triggers, isolation, handoffs, revision caps, conflict resolution, verification. |
| `variants/` | Workflow variants under comparison (A split verification, B merged verification, single-session baseline) and how to switch between them. |
| `STATUS.md` | One row per feature: stage, branch, PR, open items. |
| `notes.md` | Live handoff log between agents/sessions. Newest 10 entries, newest first. |
| `notes-archive.md` | Older handoff entries, moved unchanged from `notes.md`. |
| `templates/` | `spec.md`, `plan.md`, `tasks.md`, `handoff.md` templates, and a filled sample tasks file (`tasks-sample-ADM-06.md`). |
| `specs/<feature-id>/` | Per-feature spec, plan and tasks (spec-driven development). |
| `experiments/context-engineering.md` | Context-engineering experiments and results. |
| `experiments/resource-log.md` | Per-task model, token, revision-round and retry records. |
| `experiments/results/` | Committed per-run usage summaries produced by the token tracker. |
| `tools/token-tracker/` | Token usage tracker for Claude Code and Codex logs; see its README. |
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

After any notable task or experiment run, run the token tracker on your own machine for the branch the work was done on, save the summary under `experiments/results/`, and add one row to `experiments/resource-log.md`.
Only summaries are committed; the row-level `usage.csv` stays local.
A feature is not closed until its row exists in `experiments/resource-log.md`; every handoff states whether the tracker was run, total tokens, cost and retries (`templates/handoff.md`).
Full steps, options and limits: [`tools/token-tracker/README.md`](tools/token-tracker/README.md#use-in-the-workflow).
