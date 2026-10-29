# Handoff notes

Newest entry first. Use `templates/handoff.md`.

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
