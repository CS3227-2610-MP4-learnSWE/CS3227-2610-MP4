# Workflow variants

We compare ways of splitting build and verification work. The spec step is shared and excluded from the comparison: write and approve the spec and plan once per task, then give the same files to every run.

## Shared pre-step (all variants)
`spec-writer` produces `spec.md`, `plan.md` and `tasks.md`. The plan must fix the contract (endpoint paths, request/response schemas, function signatures, error codes) because the developer and test-designer work in parallel without seeing each other's output. A human approves the spec and plan.

## Variant A: split verification (default, `.claude/agents/`)
```
[approved spec + plan] -> developer || test-designer (parallel, isolated)
  -> test-designer runs the suite -> reviewer -> security-reviewer
  -> developer fixes (max 2 rounds) -> [human approves PR]
```
Agents: developer (generator), test-designer, reviewer, security-reviewer. Build phase: 4 agents; 5 with the spec-writer.

## Variant B: merged verification (`B-merged-verification/`)
```
[approved spec + plan] -> developer || test-designer (parallel, isolated)
  -> verifier (reviews diff, security checks, runs the suite)
  -> developer fixes (max 2 rounds) -> [human approves PR]
```
Agents: developer (generator), test-designer, verifier. Build phase: 3 agents. Uses `verifier.md` in place of `reviewer.md` and `security-reviewer.md`.

## Baseline: single session
One session does build and self-check, still spec-first and tests-first, with no agent split.

## Switching variant (experiment branches only)
Start from the same `master` commit. For B, delete `reviewer.md` and `security-reviewer.md` from `.claude/agents/`, copy `B-merged-verification/verifier.md` in, and update the roster in `AGENTS.md`. For the baseline, remove the agent files and tell the session to follow the spec-first and tests-first rules. Never merge a switched-variant branch; copy only the results into `workflow/experiments/`.

## What to record per run (`experiments/resource-log.md`)
Tokens (input, cached, output, reasoning) per agent and total; revision rounds; defects the verifier or reviewers found; contract mismatches between developer and test-designer; the number of handoffs; your own review time; and a quality score against the shared rubric.
