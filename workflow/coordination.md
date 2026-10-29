# Coordination pattern

Generator-verifier with an independent test designer and one merged verifier (Variant B). Chosen on 29 Oct 2026 after comparing it with split verification (Variant A); see `experiments/results/stu02-decision.md` and `variants/README.md`.

```
feature ID -> spec-writer -> [human approves spec + plan/contract]
  -> developer (generator, run folder) || test-designer (own worktree)
  -> test-designer merges the run branch into its worktree and runs the suite
  -> orchestrator merges the tests into the run branch
  -> verifier (code, docs and security review; re-runs the suite)
  -> developer fixes (max 2 rounds) -> [human approves PR]
```

The orchestrator is the session that runs the workflow: it starts the agents, passes messages between them, does the merges and writes `notes.md`.

## Triggers
- spec-writer: a feature is chosen from `docs/FeatureList.md`.
- developer and test-designer: spec and plan marked Approved. Before starting them, the orchestrator records the start commit (`git rev-parse HEAD` on the run branch). They start together; the test-designer is started with worktree isolation and given the start commit, which it resets its worktree to first, because a new worktree may be cut from a different branch.
- verification: the developer has committed its work and reports ready (existing tests pass, plus typecheck and lint where configured), and the test-designer has committed its tests on its worktree branch.
- merge of tests: the test-designer has reported its suite results.
- verifier: the tests are merged into the run branch. Read-only. It re-checks after each fix round.

## Isolation
Enforced by separate folders, not only by instruction. The developer works in the run's folder on the run branch. The test-designer works in its own git worktree on its own branch, from the spec, plan contract and threat model only, so neither can see the other's files. At verification the test-designer merges the run branch into its worktree and runs its tests; only then does the orchestrator merge the test branch into the run branch. The plan's contract (paths, schemas, signatures, error codes) is the only shared interface; a mismatch is reported as a contract defect, not patched by editing a test.

## Context management
Each agent reads only the files named in its definition plus the feature's folder under `specs/`. Claude Code loads agent definitions from the main project folder, not from a worktree: before starting a feature session, check out a branch with the current `.claude/agents/` in the main folder and confirm the registered agent types. State passes through files, never assumed memory: `spec.md`, `plan.md`, `tasks.md`, and a handoff entry in `notes.md`.

## Handoff
Every agent ends with a handoff using `templates/handoff.md` (done, next, open questions, files touched, rough resource use). Only the developer and the orchestrator write `notes.md`. The test-designer and verifier put their handoff at the end of their report and the orchestrator records it, so read-only agents stay read-only and `notes.md` never conflicts at merge. Security cases go only into the existing `security/test-log.md`.

Every agent stages files by path when committing, never `git add -A` or `git add .`, so it cannot pick up another agent's files.

## Revision loop and caps
Verification failures return to the developer as a ranked defect list. At most 2 revision rounds; after that the human team decides. Round counts are logged in `experiments/resource-log.md`.

## Resource sharing
The run folder belongs to the developer, the only agent that writes `src/` outside tests. The test-designer writes only test files, in its own worktree. The verifier is read-only. No two agents write in the same folder at the same time. The SoC LLM quota is shared: tests use mocks, and no agent runs live calls against it without approval.

## Conflict resolution
A disagreement between agents goes in `notes.md` as blocking or non-blocking. Blocking findings go to the developer. Contract disputes go back to the spec-writer to amend `plan.md`. Unresolved cases go to the human team and the decision is recorded in `plan.md`.

## Verifying the pattern is followed
Per feature, check from git history and notes: spec approved before code; tests committed before or independently of the implementation; one handoff entry per agent stage; revision rounds within the cap; a security log entry for AI features. Record deviations, idle or blocked agents and retries in `experiments/resource-log.md`; they feed `docs/Reflections.md`.

## When not to use multi-agent
Small fixes, docs edits and one-file changes go directly to a single session. Record the decision so the cost-benefit analysis has data.
