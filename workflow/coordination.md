# Coordination pattern

Generator-verifier with an independent test designer. The default (Variant A) is below; see `variants/README.md` for Variant B and the baseline.

```
feature ID -> spec-writer -> [human approves spec + plan/contract]
  -> developer (generator) || test-designer (parallel, isolated)
  -> test-designer runs the suite -> reviewer -> security-reviewer
  -> developer fixes (max 2 rounds) -> [human approves PR]
```

## Triggers
- spec-writer: a feature is chosen from `docs/FeatureList.md`.
- developer and test-designer: spec and plan marked Approved. They start together.
- verification: the developer reports ready (typecheck, lint green) and the tests are committed.
- reviewer and security-reviewer: the suite has been run. Read-only; they may run in parallel.

## Isolation
The test-designer works only from the spec, plan contract and threat model, and does not read `src/` until verification. The developer builds from the spec and does not read the tests until it has reported ready. The plan's contract (paths, schemas, signatures, error codes) is the only shared interface; a mismatch is reported as a contract defect, not patched by editing a test.

## Context management
Each agent reads only the files named in its definition plus the feature's folder under `specs/`. State passes through files, never assumed memory: `spec.md`, `plan.md`, `tasks.md`, and a handoff entry in `notes.md`.

## Handoff
Every agent ends by prepending an entry to `notes.md` using `templates/handoff.md` (done, next, open questions, files touched, rough resource use).

## Revision loop and caps
Verification failures return to the developer as a ranked defect list. At most 2 revision rounds; after that the human team decides. Round counts are logged in `experiments/resource-log.md`.

## Resource sharing
One working tree per feature branch; only the developer writes `src/`. The test-designer writes only test files; reviewers are read-only. The SoC LLM quota is shared: tests use mocks, and no agent runs live calls against it without approval.

## Conflict resolution
A disagreement between agents goes in `notes.md` as blocking or non-blocking. Blocking findings go to the developer. Contract disputes go back to the spec-writer to amend `plan.md`. Unresolved cases go to the human team and the decision is recorded in `plan.md`.

## Verifying the pattern is followed
Per feature, check from git history and notes: spec approved before code; tests committed before or independently of the implementation; one handoff entry per agent stage; revision rounds within the cap; a security log entry for AI features. Record deviations, idle or blocked agents and retries in `experiments/resource-log.md`; they feed `docs/Reflections.md`.

## When not to use multi-agent
Small fixes, docs edits and one-file changes go directly to a single session. Record the decision so the cost-benefit analysis has data.
