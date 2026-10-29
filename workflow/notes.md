# Handoff notes

Newest entry first. Use `templates/handoff.md`.

## 2026-10-29: decision for Variant B
- Decision (user): Variant B (merged verification, 3 agents) becomes the team workflow, to be confirmed with the team in the switch PR. Reason: same hidden-grader score as A at 43% lower cost (1.56 vs 2.76 USD), no stall, re-verified after its fix round. A blind API usability review found A and B behaviourally identical; it preferred A narrowly.
- Known cost of B: its verifier saw the save/submit race and the untrimmed student id but rated them non-blocking, because the spec did not require concurrency safety or id normalisation and the verifier has no severity rule for criteria broken under concurrent requests. A's dedicated security-reviewer had insisted on the race fix.
- Next (each needs the user's go-ahead): fix B's race and trimming, then merge B's feature code by PR; make B the only workflow (delete A's reviewer definitions, update `coordination.md` and `AGENTS.md`) with a verifier severity rule and concurrency/normalisation in the spec template; fix the shared OpenAPI gaps; write the frontend integration spec; clean up run branches and worktrees.
- Records: `experiments/results/stu02-decision.md` and the rest of the results on the local branch `exp/stu02-grader`.

## 2026-10-29: STU-02 workflow comparison runs (A, B, baseline)
- Done: three runs of the full STU-02 feature from start commit `70ab114`, each in a fresh sonnet session, graded with the hidden acceptance suite and measured by session with the tracker. All three pass 18/18. Cost: A (5 agents) 2.76 USD, B (3 agents) 1.56 USD, baseline (single session, reference only) 0.52 USD. Revision rounds: A 1, B 1, baseline 0. Interventions: A 1 (security-reviewer stalled for 1 h 40 min, nudged at the user's request), B 0, baseline 0.
- Findings: by the decision rule B wins (43% cheaper than A, same grader score). A's security-reviewer found and fixed a save/submit race that B's verifier rated non-blocking and left open; the grader has no concurrency test. Opus verification was the largest single cost in both multi-agent runs.
- Setup flaw (accepted by the user, documented): subagent definitions load from the main project folder, which held older agent files during Runs A and B; B's verifier ran as a general-purpose agent. The baseline was started with the main folder on its own branch.
- Results and charts: on the local branch `exp/stu02-grader` under `workflow/experiments/results/`.
- Next: the user and team choose A or B; then merge the winning run's feature code by PR and make the chosen variant the only workflow.

## 2026-10-29: Variant A pilot (two endpoints) and process fixes
- Done: pilot of Variant A on STU-02 endpoints 1-2 (AC1, AC2, AC11) in a fresh sonnet session, branch `claude/stu02-pilot-ab66d7` (discarded, not merged). Checked independently: 59 tests pass (1 strict xfail for an unbounded student-id length), the 5 relevant hidden acceptance checks pass, and the tracker attributed all 5 agents to the run by session (11 of 66 requests came from the test-designer's worktree branch and would have been missed by branch alone). Cost 1.46 USD: orchestrator 0.57, security-reviewer (opus) 0.54, developer 0.14, test-designer 0.14, reviewer 0.08. One revision round.
- Process problems found and fixed (user approved all five): (1) the test-designer's worktree was cut from `master`, which lacks the spec, so it read the spec from the run branch; it now resets its worktree to the start commit the orchestrator gives it. (2) The reviewer's definition said read-only and also "write to notes.md"; all read-only agents now return their handoff in their report. (3) The developer committed another agent's file with `git add -A`; all agents stage by path. (4) "Lint green" could not be checked because the backend has no linter; now "where configured". (5) The security-reviewer created a new log file; it now appends to `security/test-log.md` and marks non-applicable checks. Updated: `.claude/agents/*`, `variants/B-merged-verification/verifier.md`, `coordination.md`, `AGENTS.md`.
- Decision: no student-id length or attempt limit added to the spec (user did not ask; header identity is a placeholder until SHR-01).
- Next: the three real runs (A, B, baseline) from the new start commit, each in a fresh sonnet session.

## 2026-10-29: session on STU-02 experiment setup
- Done: STU-02 practice attempt API spec, plan (fixed HTTP contract) and tasks in `specs/STU-02/`, approved by the user; price table filled; "Measuring token usage" section in `README.md`; resource-log columns aligned with the tracker. A hidden acceptance suite and the comparison tooling exist on a local branch and are withheld from run branches until all runs finish.
- Decisions: same feature built once per condition (A, B, baseline), one run each, Claude only; the spec is shared and excluded from the comparison; each run gets a fresh session on its own branch; usage is attributed by session so subagents in their own worktrees still count.
- Decision (user, 29 Oct): the test-designer runs in its own git worktree, so isolation is enforced by separate folders. At verification it merges the run branch into its worktree and runs the suite; the orchestrator then merges the tests into the run branch. Only agents in the run folder edit `notes.md`; the test-designer reports its handoff to the orchestrator. Updated: `coordination.md`, `variants/README.md`, `.claude/agents/test-designer.md`, `.claude/agents/developer.md`, `AGENTS.md`.
- Decision (user, 29 Oct): the comparison is Variant A (5 agents: spec-writer, developer, test-designer, reviewer, security-reviewer) against Variant B (3 build agents: developer, test-designer, verifier), plus a single-session baseline as a reference only, since the assignment requires multi-agent SE. Runs branch from `exp/stu02-setup` without merging it first. Afterwards only the winning run's feature code and tests are merged (never its agent-file changes), the chosen variant becomes the only active workflow, and the variant record is kept for the reflection. See `variants/README.md`.
- Next: a small pilot run of Variant A to check the worktree flow and usage attribution, then the three runs, each in a fresh sonnet session.
- Open: subagent attribution not yet seen on a real run in this repo; agent definitions never run; absolute totals unchecked against the apps.
- Resource use: see `experiments/resource-log.md`.

## 2026-10-29: session on TRK-01 token tracker
- Done: tracker in `tools/token-tracker/` (spec, failing tests first, then code; 25 tests), merged by PR 2. Verified on real logs that repeated Claude log lines for one message carry the same usage, so each message is counted once.
- Next: fill prices (done in the setup session).
- Open: Codex input/cached convention unchecked against billing.

## 2026-10-28: scaffolding (session)
- Done: CLAUDE.md, AGENTS.md, agent definitions, coordination pattern, variants A and B, templates, reflection skeleton, checklist.
- Design decisions: generator-verifier with an independent test-designer running in parallel and isolated from `src/`; the spec step is shared and excluded from the comparison; revision loop capped at 2 rounds; changes go to `master` by PR only; experiments run on separate branches cut from the same `master` commit and are not merged.
- Next: build the token tracker (separate from learnSWE, with a copy under `workflow/tools/`), define the experiment task candidates and rubric, assign team members and roles, write the first spec.
- Open: SoC LLM access and quota; deployment target; subject and learner level; the Codex `AGENTS.md` pickup is untested; where the Codex model name is logged.
