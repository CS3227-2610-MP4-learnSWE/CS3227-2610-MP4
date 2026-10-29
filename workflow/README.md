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
| `deployment.md` | Deployment (CD) options and open hosting decisions. |
| `../.github/workflows/ci.yml` | Continuous integration; plan in `specs/CI-01/plan.md`. |

## Default agent roster, Variant A (`.claude/agents/`)

| Agent | Model | Job |
|---|---|---|
| `spec-writer` | sonnet | Feature ID to spec, plan (with contract), tasks. Shared pre-step. |
| `developer` | sonnet | Generator: implements from the spec; fixes defects. |
| `test-designer` | sonnet | Independent tests from the spec; runs the suite at verification. |
| `reviewer` | sonnet | Read-only review against spec and docs. |
| `security-reviewer` | opus | Adversarial tests and security checklist. |

Variant B replaces `reviewer` and `security-reviewer` with one `verifier` (`variants/B-merged-verification/`).

`AGENTS.md` at the repo root holds the same rules and role definitions for Codex. Edit all three places together (`CLAUDE.md`, `.claude/agents/`, `AGENTS.md`).

The human team members approve each spec/plan and each PR. Nothing is committed directly to `master`.
