# Token tracker and experiment setup summary — 29 October 2026

## User direction

After PR 1 (workflow scaffolding) was merged, the user asked for a token-usage tracker usable both in this project and personally, then for an experiment comparing the workflow variants on one real student feature. Decisions taken with the user: Claude only for the first comparison (the cheaper workflow will later be applied to Codex); the same feature built once per condition so all runs share criteria; one run per condition, repeating only if results are close; each variant uses the models already chosen for its agents, so costs reflect real use; tracker output stays local (gitignored) and only per-run summaries are committed; the grading suite is hidden from the runs to avoid over-fitting to the tests. The user also asked that docs and logs always be kept up to date.

## Token tracker (PR 2, merged)

Built spec-first and tests-first in a single session: `workflow/specs/TRK-01/`, failing tests committed before the code, 25 unit tests. It reads Claude Code logs (including subagent files and their agent types) and Codex rollouts, writes an idempotent row-level CSV and per-branch summaries, and prices requests from `prices.json`. Checks on real data: subagent logs live in `<session>/subagents/agent-*.jsonl` with an agent-type `.meta.json`, and the parent log does not repeat them; repeated log lines for one message carry identical usage (60 of 60 cases), so counting each message once is correct. Prices for Sonnet 5.5 and Opus 5.5 were taken from Anthropic's pricing page and dated.

## Experiment setup

A shared spec, plan and task list for the server-side core of STU-02 (practice attempts with answer release only after whole-set submission) were written and approved by the user. The plan fixes an exact HTTP contract so a developer and an independent test designer can work in parallel. Supporting tooling (an acceptance suite, grading and comparison scripts, and an HTML report) was prepared on a separate local branch and is withheld from run branches until the runs finish; it was checked against a throwaway reference implementation and deliberate bugs. The HTML report was previewed only with invented placeholder numbers, which were labelled as such and never committed; no experiment run has happened yet.

## Review after a model switch

The user switched the session from Sonnet 5.5 to Opus 5.5 and asked for a review of earlier work. Gaps found: parallel agents would share one working tree, so isolation was only an instruction; grading used the main checkout's environment, which could fail a run that adds a dependency; Variant B and baseline runs would read Variant A's coordination text; the plan did not state the attempt-id length that a test checked; the spec still said "Draft"; and notes, logs and the resource log had fallen behind. The small fixes were applied, and each run now gets a prompt naming its variant. For isolation, the AI recommended and the user chose giving the test-designer its own git worktree: the developer and test-designer cannot see each other's files, the test-designer merges the developer's committed work into its worktree to run the suite, and the orchestrator then merges the tests into the run branch. Because a worktree subagent logs a different branch, usage is attributed to a run by session rather than by branch.

The switch itself cost 2.69 USD over 5 requests, mostly from rewriting the prompt cache at Opus prices, which is recorded in the resource log as a context-engineering observation.

## Not done

No pilot or experiment run, so the agent definitions remain untested. Absolute token totals are not checked against the apps. This summary was written by the AI and should be checked by a team member.
