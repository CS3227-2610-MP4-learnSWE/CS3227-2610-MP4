# Workflow index

Everything about how this project is built. The default agent definitions live in `.claude/agents/` because Claude Code loads them from there; everything else is here.

| Path | Purpose |
|---|---|
| `coordination.md` | Coordination pattern: generator-verifier with an independent test designer; triggers, isolation, handoffs, revision caps, conflict resolution, verification. |
| `variants/` | Workflow variants under comparison (A split verification, B merged verification, single-session baseline) and how to switch between them. |
| `notes.md` | Live handoff log between agents/sessions. Newest entry first. |
| `templates/` | `spec.md`, `plan.md`, `tasks.md`, `handoff.md` templates. |
| `specs/<feature-id>/` | Per-feature spec, plan and tasks (spec-driven development). |
| `experiments/context-engineering.md` | Context-engineering experiments and results. |
| `experiments/resource-log.md` | Per-task model, token, revision-round and retry records. |
| `experiments/results/` | Committed per-run usage summaries produced by the token tracker. |
| `tools/token-tracker/` | Token usage tracker for Claude Code and Codex logs; see its README. |
| `security/threat-model.md` | AI and development-process threats and controls. |
| `security/test-log.md` | Security test cases, outcomes and fixes. |
| `checklist.md` | Submission and setup checklist with owners. |
| `AppShellPlan.md` | Execution record of the first app-shell phase. |

## Agent roster, Variant B (`.claude/agents/`)

| Agent | Model | Job |
|---|---|---|
| `spec-writer` | sonnet | Feature ID to spec, plan (with contract), tasks. Shared pre-step. |
| `developer` | sonnet | Generator: implements from the spec; fixes defects. |
| `test-designer` | sonnet | Independent tests from the spec; runs the suite at verification. |
| `verifier` | opus | Read-only code, docs and security review in one pass; re-runs the suite; severity rule for concurrency and normalisation. |

This is Variant B (merged verification), chosen after the STU-02 comparison (`experiments/results/stu02-decision.md`). Variant A's separate reviewer and security-reviewer were removed; their comparison record stays in `variants/` and `experiments/`.

`AGENTS.md` at the repo root holds the same rules and role definitions for Codex. Edit all three places together (`CLAUDE.md`, `.claude/agents/`, `AGENTS.md`).

The human team members approve each spec/plan and each PR. Nothing is committed directly to `master`.

## Measuring token usage

The token tracker (`tools/token-tracker/`) reads your own local Claude Code and Codex logs, so each teammate runs it on their own machine. Use it after any notable task or experiment run, on the branch the work was done on.

1. See where the tokens and cost went (branch names are matched against the git branch recorded in the logs):

   ```powershell
   cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\workflow\tools\token-tracker"
   python -m tracker report --branch <branch-name>
   ```

2. For an experiment run or any result worth keeping, save the summary and commit that file:

   ```powershell
   cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4\workflow\tools\token-tracker"
   python -m tracker report --branch <branch-name> --out ..\..\experiments\results\<name>.csv
   ```

3. Add one row to `experiments/resource-log.md` (task, agent, model, the numbers from the summary, retries and a note).

Only summaries under `experiments/results/` are committed. The row-level `usage.csv` holds your whole usage history, is gitignored, and stays on your machine. Cost is API list price (see the tool's README for limits and for keeping `prices.json` current). The numbers have not been checked against the Claude or Codex apps, so quote them as measured by the tracker, not as billed.
