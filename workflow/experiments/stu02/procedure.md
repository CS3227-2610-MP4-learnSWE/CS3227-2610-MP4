# STU-02 workflow comparison: procedure

Question: which workflow gives the best result per cost for the same feature? Claude only. One run per condition; this is anecdotal evidence, not a statistical result.

This folder is kept off the run branches. The runs must not see the grader or the rubric.

## Conditions
| Run | Branch | Agents and models |
|---|---|---|
| A, split verification | `exp/stu02-A` | developer (sonnet) and test-designer (sonnet) in parallel, then reviewer (sonnet) and security-reviewer (opus) |
| B, merged verification | `exp/stu02-B` | developer (sonnet) and test-designer (sonnet) in parallel, then verifier (opus) |
| baseline | `exp/stu02-baseline` | one session (sonnet), spec-first and tests-first, no agent split |

The orchestrating session uses sonnet in A and B and its tokens count toward the run. Revision loops: at most 2 rounds.

## Setup (before any run)
1. Merge `exp/stu02-setup` (spec, plan, tasks, prices) to `master` by PR. Every run branches from that merge commit.
2. The grader branch `exp/stu02-grader` stays local and unpushed until all three runs are graded.
3. Each run is a fresh session, in its own git worktree, started from the same commit. One session is one run, so the tracker can attribute usage by branch.

## Running one condition
1. Create the branch from the setup commit: `git switch -c exp/stu02-<X> <setup-commit>` (or a worktree on it).
2. For B: delete `.claude/agents/reviewer.md` and `.claude/agents/security-reviewer.md`, copy in `workflow/variants/B-merged-verification/verifier.md`, and update the roster in `AGENTS.md`. For the baseline: delete the agent files and tell the session to follow the spec-first, tests-first rules itself.
3. Give the session this prompt, and nothing else about the experiment: "Implement the STU-02 practice attempt API as specified in workflow/specs/STU-02. Follow the workflow in CLAUDE.md." Variant A and B sessions use the coordination in `workflow/coordination.md`.
4. Do not help beyond the 2 revision rounds. Note every point where you had to step in.
5. When the run says it is done, commit its work on the run branch. Record your review time in minutes (time you spend reading and fixing the result, excluding waiting).
6. Run order: A, then B, then baseline. Note any learning effect.

## Grading one run (after it is committed)
From the repo root:

```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4"
python workflow/experiments/stu02/grade_run.py exp/stu02-A --label A
```

This applies the hidden grader to a temporary checkout of the run branch (the branch is not changed) and writes `workflow/experiments/results/stu02-A-grade.json`. Repeat for `B` and `baseline`.

Then record the hand-measured facts for each run in `workflow/experiments/results/stu02-<label>-notes.json`:

```json
{"revision_rounds": 1, "review_minutes": 25, "quality_score": 4}
```

`quality_score` is your 1 to 5 rating of the code against the criteria below.

## The comparison to record
```powershell
cd "C:\Users\yikbi\NUS\CS3227\MP4\CS3227-2610-MP4"
python workflow/experiments/stu02/compare.py
```

Prints one table with, for A, B and baseline: grader score (passed, total, percent), the run's own test results, requests, input, cache-read, cache-write, output and reasoning tokens, total tokens, cost in USD, cost per passing grader test, revision rounds, review minutes and quality score. It also writes `stu02-comparison.csv` and `stu02-comparison.md` under `workflow/experiments/results/` for pasting into the reflection and slides.

Token usage is read from the local Claude logs by branch name. Cost uses `workflow/tools/token-tracker/prices.json` (API-equivalent list prices).

## Rubric
Quality is judged on three things, in this order:
1. **Grader score** (primary): percent of the hidden suite passed. Covers correctness, validation, ownership and answer leakage.
2. **Code quality** (1 to 5, rated by a team member against written criteria, not knowing which condition made it if practical): single-responsibility modules as the plan describes; no duplicated header or ownership checks; clear names; the store behind an interface; no dead code; tests readable and named per criterion.
3. **Process facts:** revision rounds used, defects found by reviewers, contract mismatches between developer and test-designer, and the number of times a human had to step in.

## Decision rule (fixed before running)
1. A run qualifies only if it passes at least 90% of the grader suite and has no answer-leakage or ownership failure.
2. Among qualifying runs, the cheapest in USD wins.
3. If qualifying runs are within about 15% of each other in cost, prefer the one with fewer revision rounds and less review time.
4. If quality differs a lot but cost does not, say so and consider a second run before deciding.

## Limits to state in the write-up
One run per condition. Absolute totals are not checked against the apps. The author of the grader is an AI that also takes part in the runs, so a human should read the grader first. Order effects: later runs may benefit from a spec that has been read before.
