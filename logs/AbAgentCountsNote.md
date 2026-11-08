# A vs B agent counts note: 2026-11-08

## Request and scope
While preparing the final presentation the user asked how many agents Workflow A and B really had and whether the spec-writer was included. The repo labelled them inconsistently ("A 5 agents", "B 3 agents"; Reflections listed the spec-writer in A).

## What happened
Checked `workflow/experiments/stu02/fair/README.md` (cost by agent), `workflow/variants/README.md` and `docs/Reflections.md`. The runs had: A = orchestrator, developer, test-designer, reviewer, security-reviewer; B = orchestrator, developer, test-designer, verifier. The spec-writer was a shared pre-step, not part of the runs. So the "5 vs 3" labels counted the orchestrator for A only. The user chose to state the counts like for like and update the repo.

Edited one place: `docs/Reflections.md` (the variant bullets and a "How the agents are counted" paragraph). Added a handoff entry to `workflow/notes.md`. Left the historical records, the resource log, the results files, the comparison image and the variants README unchanged on purpose.

## Verification and what is not verified
Counts checked against the cost-by-agent lines in the fair-comparison README. Documentation only; no tests run. Not pushed, no PR. The comparison image and older records still say "5 agents / 3 agents"; the note explains why.
