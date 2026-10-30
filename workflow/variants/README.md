# Workflow variants

**Outcome (30 Oct 2026): Variant B was chosen** after a fair comparison (all three conditions re-run from the same commit with the same model, settings and correct agent definitions). The pre-set tie-break pointed to A, because B used one revision round, but that round fixed stale documentation that A's reviewer had rated non-blocking and left in place, so the team overrode it. B is now the only active workflow (`.claude/agents/`, `../coordination.md`); A's reviewer and security-reviewer definitions were removed. The active verifier (`.claude/agents/verifier.md`) adds a severity rule and robustness checks that the experiment's `B-merged-verification/verifier.md` did not have. See `../experiments/results/stu02-decision.md`.

We compare ways of splitting build and verification work. The spec step is shared and excluded from the comparison: write and approve the spec and plan once per task, then give the same files to every run.

## Shared pre-step (all variants)
`spec-writer` produces `spec.md`, `plan.md` and `tasks.md`. The plan must fix the contract (endpoint paths, request/response schemas, function signatures, error codes) because the developer and test-designer work in parallel without seeing each other's output. A human approves the spec and plan.

In both multi-agent variants the developer works in the run folder and the test-designer in its own git worktree, so neither sees the other's files. When the developer has committed and reported ready, the test-designer merges the run branch into its worktree and runs its suite; the orchestrator then merges the tests into the run branch. See `../coordination.md`.

## Variant A: split verification (historical experiment)
```
[approved spec + plan] -> developer (run folder) || test-designer (own worktree)
  -> test-designer runs the suite -> tests merged into the run branch
  -> reviewer -> security-reviewer
  -> developer fixes (max 2 rounds) -> [human approves PR]
```
Agents: developer (generator), test-designer, reviewer, security-reviewer. Build phase: 4 agents; 5 with the spec-writer.

## Variant B: merged verification (chosen; folder below is historical)
```
[approved spec + plan] -> developer (run folder) || test-designer (own worktree)
  -> test-designer runs the suite -> tests merged into the run branch
  -> verifier (reviews the diff, security checks, re-runs the suite)
  -> developer fixes (max 2 rounds) -> [human approves PR]
```
Agents: developer (generator), test-designer, verifier. Build phase: 3 agents. The active definition is `.claude/agents/verifier.md` (Codex roles: `AGENTS.md`); `B-merged-verification/verifier.md` is the historical experiment copy without the later strict severity rule.

## Baseline: single session (reference only)
One session does build and self-check, still spec-first and tests-first, with no agent split. It shows what multi-agent coordination costs and buys. It is not a candidate for the project workflow, because the assignment requires multi-agent SE; the choice is between A and B.

## Switching variant (experiment run branches only)
Every run branches from the same commit of `exp/stu02-setup`. For B, delete `reviewer.md` and `security-reviewer.md` from `.claude/agents/`, copy `B-merged-verification/verifier.md` in, and update the roster in `AGENTS.md`. For the baseline, remove the agent files and tell the session to follow the spec-first and tests-first rules.

## After the comparison
1. Choose A or B using the decision rule, with the human team.
2. Merge only the winning run's feature code and tests into `exp/stu02-setup` (never its agent-file changes), then into `master` by PR. The other run branches are discarded.
3. The chosen variant becomes the only active workflow: its agent files stay in `.claude/agents/`, the other variant's definitions are deleted, and `coordination.md` and `AGENTS.md` describe only the chosen one. The change goes to `master` by PR so teammates review it.
4. Keep this file and the results as the record of what was compared and why, for the reflection.

## What to record per run (`experiments/resource-log.md`)
Tokens (input, cached, output, reasoning) per agent and total; revision rounds; defects the verifier or reviewers found; contract mismatches between developer and test-designer; the number of handoffs; your own review time; and a quality score against the shared rubric.
