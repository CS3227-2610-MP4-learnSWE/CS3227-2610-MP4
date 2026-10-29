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

## Clarifying the comparison

The user asked how "Variant A and B" related to the "5 vs 3" agents they had agreed. The AI explained that A is the 5-agent workflow (counting the shared spec-writer) and B the 3-agent one (build phase only), and that it had added a single-session baseline as a third run, which the user had accepted without that being made explicit. The user agreed to keep three runs and asked to be kept in the loop on every addition or change. Agreed plan: runs branch from `exp/stu02-setup` directly; the baseline is a reference only because the assignment requires multi-agent SE; after the comparison only the winning run's feature code and tests are merged, and the chosen variant becomes the team's only workflow, with the record of the comparison kept.

## Pilot run

The user asked what an endpoint was and why a pilot was needed; the AI explained the pilot as a cheap rehearsal of the process (building two of the six STU-02 endpoints), whose code is thrown away. The user approved a two-endpoint pilot of Variant A, run in a separate fresh Sonnet session started from the agreed start commit. The AI then checked the result itself rather than relying on the session's report: tests passed, the relevant hidden acceptance checks passed, and the tracker attributed all five agents to the run by session, for 1.46 USD in total (the Opus security reviewer cost about as much as the orchestrator). The pilot exposed five process problems: the test-designer's worktree lacked the spec, a reviewer instruction contradicted itself, an agent staged another agent's file, an unverifiable lint trigger, and the security reviewer's logging. The user approved all five fixes, which were applied to the agent definitions, `coordination.md` and `AGENTS.md`.

## The three runs

With the user's standing approval for the remaining experiment steps, the AI started Runs A, B and the baseline in fresh Sonnet sessions, graded each with the hidden suite and measured each by session. All three passed 18/18; costs were 2.76, 1.56 and 0.52 USD. Run A's security reviewer stalled and was resumed after the user approved a nudge. While Run B ran, the AI found that subagent definitions load from the main project folder, which held older agent files, so Runs A and B used older instructions; the user chose to accept and document this rather than re-run, and the baseline was started with the main folder on its own branch. The user also decided not to measure review minutes or a human quality score. By the decision rule B wins; the findings note that A's dedicated security review fixed a race that B left open.

## Reviews and decision

At the user's request an independent subagent reviewed the A and B backends blind, as a frontend developer would: behaviour and contract were identical, and it preferred A narrowly (typed status values, trimmed student id) while B's messages were slightly clearer. The user asked how to try both; the AI explained that the runs built only the backend, so the frontend is unchanged, and gave commands to run both servers and use each one's `/docs` page with a step-by-step test list. The user then chose Variant B. Asked why B's flaws were not caught, the AI explained that B's verifier did notice the race and the untrimmed id but rated them non-blocking, because the AI-written spec did not require concurrency safety or id normalisation and the verifier had no severity rule; this is recorded as the main quality cost of merging the reviewers, with proposed compensations.

## Reflection, presentation and merge

The user asked for the comparison and the reasons for choosing B in the reflection, a visual for a presentation and a PowerPoint deck, and then for B's changes to be made and pushed with the decision. The AI wrote the A vs B section of `docs/Reflections.md`, rendered a comparison image (cost by role and a scorecard) with a colour-blind-checked palette, and built an eight-slide editable deck with native charts and speaker notes, checked by rendering every slide through PowerPoint; both were saved to the user's presentation folder. It then applied only Run B's feature code, kept the hidden grader as permanent tests, fixed the race and the id trimming with tests that failed first, and made Variant B the only workflow with a stricter verifier. The tracker showed that this coordinating session cost far more than the runs it coordinated, mostly after its switch to Opus.

## Fair comparison and the change to Variant A

The user questioned the evidence: why every run scored the same, why A's wall time included a stall, and why A had been re-run with different instructions. The AI explained that the original runs had accidentally loaded older agent definitions and that the re-run of A used the correct ones. The user then asked for all three conditions to be re-run with the workflow as the only difference, for an independent reviewer to set the edge cases, and for all earlier tests to be repeated, and pre-approved applying the decision rule. The app required a message from the user to start each run session. In the fair runs all three scored 18/18 on the hidden grader, 107/115 on the independent edge cases and 62/62 on planted bugs; A cost 1.36, B 1.46 and the baseline 0.45 USD. The rule picked A (within the cost band, no revision round). Every run shipped the save/submit race, which both reviewers rated non-blocking; the merged code fixes it and the security-reviewer now has a severity rule. The reflection concludes that on this small, precise feature multi-agent coordination bought little over a single session.

## Choosing B over the rule's tie-break

Asked to explain the choice of A, the AI showed that the rule had decided on a thin margin. Asked whether B cost more because of its docs revision, it measured that round at about 0.21 USD, the whole cost difference, and found that A's reviewer had seen the same stale developer guide and let it ship. The user chose B for the long run. PR 3 was switched to the fair B run's code with the race and id fixes, the workflow files went back to B, and the override and its reasoning were recorded in the decision record, the reflection and the presentation.

## Not done

The frontend integration, documenting error responses in OpenAPI, and cleaning up the run branches are not done yet. Absolute token totals are not checked against the apps. This summary was written by the AI and should be checked by a team member.
