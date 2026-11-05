# 2026-11-05 — ADM-01 workflow experiment planning and TRK-03 — isaac

Branch: `master` (no repository files were changed except this log). Model: Claude Sonnet 5.5; the reasoning setting is not exposed in the thread metadata, so it is not recorded. Planning only: no code, specs, branches or tests were created or run. The thread-start timestamp was not exposed, so the entry is dated by day only.

## Conversation

### Conversation history

``````markdown
**User:** Below are some of the reflections for me to improve:

Muti-Agent SE

How to design and implement the coordination pattern for multiple agents?
How to verify that the coordination patterns are properly followed in terms of triggering, context management, resource sharing and hands-off)?
Were any agents idle, overloaded, or blocked while waiting for others?
Did retries, repeated analysis, or unnecessary tool calls consume resources?
How to resolve conflicts / disagreements between agents (if any)?
Did the benefits of multi-agent coordination outweigh the costs?
When should multi-agent coordination be used and when not?
Context Engineering and Resource-aware Use

How to engineer the system prompt and the skills for the agents?
When should information be supplied upfront, and when should the agent retrieve it as needed?
How does the organization of the context affect the agent's ability to find and follow important instructions?
What should be recorded in notes.md or a handoff document so another agent can continue efficiently?
When has adding more context made an agent less effective? What signals revealed the problem?
How to choose / configurate the model based on the tasks and the resource constraints?
What should be done to reduce the cache miss? How much did it help to reduce the actual token usage?
What is the percentage of tokens used in the internal reasoning for a specific task? How could persisted reasoning help?
What other approaches have you experimented to monitor and reduce token usage?
Which types of tasks consume the most tokens in your workflow? Did you manage to reduce the usage for such tasks?

My question:
My biggest problem right now is that the existing multiagent workflow is taking too long and too much tokens per feature (eg ADM-01) that I want to develop.
1. Which reflection question should I attempt to answer?

I want to be able to develop the feature and test implementations. I am thinking of an agent or skill creating 2 branches for the same feature I want to develop, eg ADM-01, and for each branch, it compares the base workflow with an improved workflow, then using the token tracker and time elapsed per agent, compare the results. Critique this idea to sharpen it or to propose a better idea to achieve the same goal

**Assistant (Claude Sonnet 5.5):** # Which reflection question to answer

**Primary: "Which types of tasks consume the most tokens in your workflow? Did you manage to reduce the usage for such tasks?"** This is your actual problem, and the experiment produces its evidence: a per-role token breakdown, a change, and a measured reduction.

**Secondary: "Did the benefits of multi-agent coordination outweigh the costs? When should it be used and when not?"** This falls out for free if you add a single-agent control arm (below).

The cache-miss question and the "more context made the agent worse" question can then be answered from the same data. Don't try to cover the whole list. Depth on two or three questions will read better than a shallow pass over all of them.

# Critique of the two-branch idea

The idea is sound, but as stated it has five weaknesses.

1. **One run per arm is an anecdote.** LLM runs of the same workflow can easily vary by 30–50% in tokens and wall time. If "improved" beats "base" by 20% on one run, you can't tell whether that's a real effect. You can't afford many repeats on a full feature, so do two things:
   - Run the baseline twice, or run a smaller feature several times, to estimate the noise.
   - Report improvements only when they clearly exceed that noise.

2. **"Improved workflow" bundles many changes.** If you change prompts, model tiers, context loading and handoffs at once, you can't say which one helped. Pick two or three specific hypotheses and make each a separate toggle, for example:
   - H1: don't re-read the whole `docs/` set, and read only the relevant user-story section.
   - H2: verifier runs once, with stricter scoping.
   - H3: the developer and test-designer use a cheaper model.

3. **Cheaper is not better unless quality is held constant.** Define quality before you run anything:
   - Freeze one acceptance test suite for ADM-01, written once and not by either arm, and run it against both branches.
   - Also record verifier defects found, revision rounds, and whether the PR would be mergeable.
   - A lean workflow that ships a security bug is a loss. This matters here because your rules make server-side auth blocking.

4. **Confounds.**
   - **Cache warmth:** if arm B runs second, it may inherit warm cache or a warm mental model from your own edits. Randomise the order, or compare cost-weighted tokens: cache-read, cache-write, fresh input and output priced separately, not a raw token sum.
   - **Shared spec phase:** both arms would regenerate spec and plan, adding variance. Freeze the approved spec and plan from one run, and A/B only the build phase (developer, test-designer, verifier). That is where most tokens go, and it halves the cost of the experiment.

5. **An agent or skill shouldn't do the measuring.** An LLM-based tracker costs tokens and is non-deterministic. Write a small script instead (see the fourth point below). A skill is fine only as a thin launcher that sets up the worktrees and calls the script.

# A sharper design

**Step 0: Profile the baseline once, before any A/B.** Most savings usually come from a few obvious sources:
- repeated file reads
- the verifier re-deriving context
- revision rounds
- oversized `workflow/notes.md` or docs loaded upfront
- idle waiting between the developer and test-designer

Fix the top two or three offenders, and only then run the comparison. Profiling is cheap, and it may give you most of the win without a full A/B.

**Step 1: Three arms on the frozen spec, in separate worktrees.**
- **A:** the current multi-agent workflow (baseline).
- **B:** the multi-agent workflow with your targeted changes.
- **C:** a single agent that does implementation, tests and self-review in one pass. This is the control that answers "when should multi-agent be used, and when not?"

Name the branches `experiment/adm01-a`, `-b` and `-c`. Never merge them. Only the winner, or a re-run of it, goes through the normal PR into `master`, so the "never commit to master / `master` must be gradeable" rule still holds.

**Step 2: Collect metrics with a script.** Claude Code writes per-session and per-subagent transcripts as JSONL under `~/.claude/projects/...`. They contain `usage` fields (input, output, cache-read, cache-creation) and timestamps. Parse them into one CSV row per agent:
- role
- tokens by type
- tool-call count
- repeated reads of the same file
- wall time
- active time (from the timestamps)
- idle or blocked time, which is the wall time minus the active time

This also answers the idle, overloaded and blocked question directly. If thinking tokens are not itemised in the transcripts, report that limit rather than guessing. That is the honest answer to "what percentage is internal reasoning".

**Step 3: Score quality.**
- frozen acceptance suite pass rate
- verifier blocking and non-blocking findings
- number of revision rounds
- whether `UserGuide.md` and `DeveloperGuide.md` match the product

**Step 4: Record and decide.** Log everything in `workflow/experiments/resource-log.md`, as your rules already require. Then write a one-paragraph conclusion per hypothesis: kept, dropped, or inconclusive. "Inconclusive within noise" is a legitimate result and still counts as a reflection.

# Cost control

A full A/B/C on ADM-01 is roughly three times your current cost. To limit that:
- Freeze the spec so the spec phase is not repeated.
- Run the profile (Step 0) first.
- If budget is tight, run A once and B twice, and skip C unless B shows multi-agent overhead is the dominant cost.

I can draft the transcript-parsing script, or the `workflow/experiments/` template and the frozen acceptance-test plan for ADM-01, if you'd like. Say which and I'll start there.

**User:** 1. Let's stick to the primary and secondary questions you chose.
2. I don't need to estimate the noise, I just need the percentage difference as a comparision
3. I want to test all 3 of the hypothesis separately, since they are all valid factors.
4. How can I define the quality clearly? since I already have a verifier agent as part of the workflow. does the developer get access to the entire quality checklist before developing?
5. How can I ensure confounders are minimised or eliminated?

Propose a simple workflow whereby I can test all the hypothesis with as little added complexity. State the step by step changes and evaluation clearly in succinct sequential order. This should be an umabiguous proposal that is simple to implement

**Assistant (Claude Sonnet 5.5):** # Proposal: one-variable-at-a-time test of the build phase on ADM-01

Arms A, H1, H2, H3 and C all run on the same frozen spec and are graded by the same fixed standard.

## Answers to your four points

**2. Percent difference only.** Report each arm as % change vs A in cost-weighted tokens and wall time. A single run per arm is fine, but one caveat belongs in your write-up. An LLM run is not repeatable, so a small difference (about 10% or less) shouldn't be called a finding.

**3. Hypotheses, each as its own arm.** Each arm changes one thing from baseline A, and only the agent config files differ between arms.

| Arm | The one change from A |
|---|---|
| **A** | None (current workflow) |
| **H1: context** | Each role gets an explicit file allowlist (spec, plan, relevant user-story section, own role file). No other docs are read unless the role reports a gap. |
| **H2: verifier** | The verifier gets a fixed checklist upfront (the spec's acceptance criteria plus SHR-01/02/05) and runs one full pass. Re-checks cover only the findings it raised. |
| **H3: model tier** | Developer and test-designer `model:` is set to Haiku 5.5 (was Sonnet 5.5). Spec-writer and verifier are unchanged. |
| **C: single agent** | One agent does code, tests and self-review in one session, with no subagents. This is the control for your secondary question. |

**4. Defining quality.** Quality is judged by a standard that is the same for every arm and sits outside the arms. That matters for H2, because the arm's own verifier is itself being changed. Each arm is graded on three measures:
- **Q1:** pass rate on the frozen acceptance suite.
- **Q2:** the number of blocking findings from the grader. The grader is the baseline verifier prompt, run once, read-only, on the final diff, in a separate session.
- **Q3:** the number of non-blocking findings. It is reported only and does not gate.

An arm **passes** only if Q1 is 100% and Q2 is 0 within the 2 revision rounds you already allow. A failed arm still gets its cost reported, but it is not counted as a win.

*Does the developer see the checklist?* The developer sees the spec and plan, including the acceptance criteria and the security requirements. That is the checklist content, and it is already in the developer's inputs. The developer does not see the frozen test suite or the grader output. Seeing those would make the arm overfit to the grader, and your rules already keep tests away from the developer.

**5. Minimising confounders.** The following are held constant across all arms:
- All arms start from the same commit with the same frozen spec and plan.
- Same models except where the arm says otherwise.
- Same start prompt, and the same 2-round revision cap.
- Each arm gets a fresh session, its own worktree, and a reset `workflow/notes.md`.
- No human edits during a run. Log any intervention and treat that arm as tainted.
- All runs happen on the same machine within one day, in randomised order.
- Token weights separate cache-read from other tokens, so cache warmth does not distort the totals.
- The frozen tests are kept out of every arm's repo.
- The spec phase is excluded, because it is shared.

What you cannot control is model randomness and API latency. Time is the noisier metric, so use tokens as the primary one.

## Step-by-step

**Phase 0: setup (once)**
1. Branch `exp/adm01-setup` from `master`. Run spec-writer for ADM-01 and have a teammate approve `spec.md`, `plan.md` and `tasks.md`. Commit them and tag the commit `adm01-start`.
2. Run the test-designer once on that spec and review its tests for contract correctness. Save them to a separate branch, `exp/adm01-frozen-tests`. Never merge this into any arm.
3. Write `workflow/experiments/measure.py`. It reads each session's transcript (the main session plus its subagents) and writes one CSV row per agent with these columns:
   - role
   - fresh-input, output, cache-write and cache-read tokens
   - repeated file-read count
   - wall time
   - active time
   - idle time (wall time minus active time)

   Cost-weighted tokens = 1×fresh input + 5×output + 1.25×cache-write + 0.1×cache-read. Use the current price ratios if they differ.

**Phase 1: build the arms (from tag `adm01-start`)**

4. Create branches `exp/adm01-a`, `-h1`, `-h2`, `-h3` and `-c`. Make the single change per the table above. Put it in `.claude/agents/*.md` and the matching text in `AGENTS.md`, as `CLAUDE.md` requires. Arm A has no change. Arm C adds a one-page single-agent instruction file.
5. Run each arm in a fresh session in randomised order, using the same prompt: "Run the build phase for ADM-01 per the workflow." Note the session IDs and any intervention.

**Phase 2: grade (outside the arms)**

6. For each finished arm, copy in the frozen tests and run them. Record Q1.
7. In a new session, run the baseline verifier prompt once on each arm's final diff. Record Q2 and Q3. This session's cost is excluded from the arm's totals.
8. Run `measure.py` on each arm's sessions.

**Phase 3: compare and decide**

9. Fill one table in `workflow/experiments/resource-log.md`, with one row per arm:

   | Arm | Pass? | Weighted tokens (% vs A) | Wall time (% vs A) | Idle time | Revision rounds | Q1 | Q2 | Q3 |
   |---|---|---|---|---|---|---|---|---|

10. Decision rule:
    - **Adopt** a hypothesis if the arm passes and its weighted tokens are at least 10% lower than A.
    - **Drop** it if it fails the quality gate or the saving is under 10%.
    - **Merge** the adopted changes into one workflow, and run a confirmation pass on a different feature only if you have budget.
11. Answer the reflection questions from the table:
    - **Primary:** the per-role token breakdown from A shows which task type costs most, and the adopted arms show the reduction.
    - **Secondary:** compare C with A. If C passes at substantially lower cost, the multi-agent overhead is not justified for a feature of this size. If C fails quality, multi-agent verification earns its cost.

I can build `measure.py` and the five branch configs next. Tell me which you want first.

**User:** ADM-01 is feature analytics based on teh UserStories.md, not set up. Please ensure your plan follows the actual codebase and its specs/docs

Do not write to workflow/experiments since this was used previously to determine workflow B. You can write it as workflow/experiments/adm01

workflow/experiments/resource-log.md does not show the breakdown per agent invocation. It combines token usage  of repeated calls to developer sub agent. I just developed a new feat that tracks per invocation. However that was basic details. What other details should be tracked by that too? I want it to be more detailed for these experiments

I want you to give a proper proposal for another new agent to read and execute the plan, asking me for my approval where needed, like in approving the spec, and also showing me how to review the results once done and the reflection based on it
I should be able to copy and paste this to another agent

**Assistant (Claude Sonnet 5.5):** I'll check the actual codebase before revising the plan.

**Assistant (Claude Sonnet 5.5):** Checking a few last details of the codebase (the earlier orchestration-optimization folder and the admin and event hooks ADM-01 would build on), then I'll write the plan.

**Assistant (Claude Sonnet 5.5):** Written for: a fresh Claude Code session that executes the experiment, with you approving at the gates. I changed nothing in the repo. I only read it.

**What I corrected after reading the codebase**
- **ADM-01 has no spec.** There is no spec folder, no analytics or event code, and `STATUS.md` says "not started". The plan therefore starts by writing and approving a spec, which is shared by all arms and excluded from the comparison.
- **Slice.** I scoped the experiment to the backend (event recording and an admin report API). Five full-stack runs would cost too much. The winning arm's code becomes the ADM-01 PR, and the report page is built afterwards with the adopted workflow. You can change this at the first gate.
- **Folders.** Everything goes under `workflow/experiments/adm01/`. Nothing in `resource-log.md`, `results/`, `stu02/` or `workflow/usage/` is touched. One conflict is flagged in the plan: the project rule says a feature isn't closed until it has a `resource-log.md` row. The plan asks you before adding one.
- **Haiku has no price in `prices.json`**, which only lists Sonnet and Opus. Without a price, the H3 cost would be blank, so the plan asks you for the price at the first gate.
- **Agent definitions load from the session's project root.** This is the pitfall that spoiled the first STU-02 comparison, so each arm gets its own worktree folder and you open that folder as the project.
- **The arm sessions don't keep a usage manifest.** The coordinator rebuilds invocations from the logs afterwards. That keeps bookkeeping tokens out of the arms and treats them all equally.
- **Existing `cmp-wt` worktrees and `exp/cmp-*` branches belong to an earlier comparison.** The plan says not to touch them.

**What else the per-invocation tracker should record.** TRK-02 gives you tokens by type, cost, model, effort and elapsed time. For these experiments it should also record:
- **Cause and context:** the arm, phase, revision round, why the agent was started (first run, retry, revision or resume), and a hash of the agent definition file. The definition hash catches the wrong-definitions confound.
- **Cache behaviour:** the cache hit ratio, the number of requests with zero cache read, and the context size at the first and largest request. Cache writes were 13.5 of the 30.24 USD in SHR-01, so this answers the cache-miss question.
- **Context use:** tool calls by name, failed tool calls, and total versus distinct files read, with the paths. This is the direct evidence for H1.
- **Time split:** active time, tool time (mostly test runs), and the gap before the agent started after the previous stage. This answers the idle and blocked question.
- **Orchestrator share:** the main session as its own rows. It was the second-largest cost in SHR-01 (9.61 USD) and STU-01 (3.71 USD).
- **Output size and churn:** files changed, lines added or removed, commits, and test-suite runs with pass or fail. This shows whether a cheaper arm simply did less.
- **Human involvement:** human messages and approval waits beyond the first prompt.

I kept these out of the tracker itself. A script in the experiment folder derives them, and good ones can be promoted to a later spec-first TRK-03.

**Two things I could not verify**
- The exact fields in the Claude log JSONL. The plan's first step is a probe, and any metric the logs can't support is reported "unavailable", never estimated.
- Whether `model: haiku` is the right alias in the agent file.

The block below is the pasteable plan.

````markdown
# ADM-01 workflow experiment: execution plan

You are the **experiment coordinator**. Work in one role at a time and say which. You prepare, measure, grade and report. You do **not** run the arms; the human (USER) runs each arm in a fresh session. Use AskUserQuestion at every gate and stop until answered. Never skip a gate.

## 0. Rules for you
- Write only under `workflow/experiments/adm01/`, plus the branches/tags/worktrees below and the ADM-01 spec files in `workflow/specs/ADM-01/`. Do **not** edit anything else under `workflow/experiments/` (`resource-log.md`, `results/`, `stu02/`, `multiagent-orchestration-optimization-2/`, `stu03-caps/`), `workflow/usage/`, `workflow/tools/`, `docs/` or `src/` without a gate approval. Do not touch `exp/cmp-*` or `..\cmp-wt\`.
- Never commit to `master`. Stage by path only (never `git add -A` / `.`). The USER's uncommitted `.gitignore` change and untracked `logs/isaac/transcript.md` are not yours: never stage them.
- Never push, open a PR or delete branches without approval. Never commit secrets or raw provider logs/prompts.
- Do not edit `workflow/tools/token-tracker`. Import its parsers if useful.
- PowerShell 5.1: no `&&`, one command per line, start each with `Set-Location (git rev-parse --show-toplevel)`.
- The main folder must stay on the branch named in each phase, with the baseline `.claude/agents/` (they equal master's), until the experiment ends.
- Report outcomes faithfully. Unavailable data is "unavailable", never estimated. Quote costs as "tracker list-price estimates, not billed".

Read first: `AGENTS.md`, `workflow/README.md`, `workflow/coordination.md`, `workflow/variants/README.md`, `workflow/experiments/results/stu02-decision.md`, `workflow/experiments/stu02/procedure.md` (pattern only), `workflow/experiments/stu02/grade_run.py` (pattern only; copy, do not edit), `workflow/tools/token-tracker/README.md`, `workflow/tools/speccheck/README.md`, `docs/FeatureList.md`, the ADM-01 section and "Shared acceptance criteria"/"Decisions to resolve" of `docs/UserStories.md`, `workflow/STATUS.md`, top of `workflow/notes.md`.

## 1. Question and arms
Goal: cut tokens and time per feature without losing quality. Reflection questions answered:
- **Primary:** which task types consume the most tokens, and did we reduce them?
- **Secondary:** did multi-agent benefits outweigh costs, and when should it be used?

Five runs of the ADM-01 **build phase** (developer, test-designer, verifier, fixes) on one frozen spec/plan. Each arm changes one thing from A.

| Arm | Change from A (allowed diff only in these files) |
|---|---|
| A | None. Current Variant B on master. |
| H1 context | Add to each of `.claude/agents/{developer,test-designer,verifier}.md` a "Context allowlist" section and mirror in `AGENTS.md`. Developer: the ADM-01 spec/plan/tasks, the `src/` files plan.md names and their direct imports, and the doc sections it edits. Test-designer: ADM-01 spec folder, `workflow/security/threat-model.md`, the ADM-01 part of `docs/UserStories.md`, existing test helpers. Verifier: spec folder, the diff and changed files, the test report, the doc sections touched. Add: "Ignore the AGENTS.md 'Read first' list; read other files only after reporting a gap." Nothing is removed. |
| H2 verifier | Edit `verifier.md` and the verifier step of `workflow/coordination.md` (mirror in `AGENTS.md`). The orchestrator must pass the verifier: the labelled spec items from `spec.md`, `git diff --stat` plus the changed-file list, and the test-designer's suite report. The verifier reads only spec/plan, changed files and that report; runs the suite once on the first pass and once after the final fix (not after each re-check); outputs a per-item table (label, evidence `file:line` or test name, met/unmet); re-checks only previously failed items. |
| H3 model tier | `model: haiku` (was `sonnet`) in `developer.md` and `test-designer.md`. Nothing else. |
| C single agent | No agent-file change. One session, no subagents, spec-first and tests-first, as the baseline in `workflow/variants/README.md`. |

## 2. Controls (identical for every arm)
- Same start commit (tag `adm01-start`), same frozen spec/plan/tasks, same models except where the arm says otherwise, same prompt template, same 2-revision-round cap.
- Fresh session per arm, in its own worktree folder (`..\adm01-wt\<arm>`, outside the repo) opened as the session's project root, so that folder's `.claude/agents/` is what loads.
- The arm sessions skip the token-tracking lifecycle in `coordination.md` (no manifest, no resource-log); you measure from logs afterwards. They may still write `workflow/notes.md` handoffs.
- No help beyond the cap. Every USER intervention or approval wait over 60 s is logged (cause, minutes).
- Run order randomised (`random.seed(2610)`), recorded. Start each arm at least 65 minutes after the previous arm's last request, so cross-arm prompt-cache reuse cannot happen. Record `cache_read` on each session's first request; if non-zero, flag the arm.
- Experiment material (frozen tests, grader, scripts, prompts, results) lives only on `exp/adm01-coord` and `exp/adm01-frozen`, never in an arm branch.
- Spec-writing is a shared pre-step; report its cost separately and exclude it from arm totals.

## 3. Quality (the gate every arm must pass)
Judged by a standard outside the arms. The developer sees the spec and plan (which contain the acceptance criteria and security requirements); it never sees the frozen tests or grader output.
- **Q1:** pass rate on the frozen acceptance suite (must be 100% to qualify).
- **Q2:** blocking findings from a blind grader (must be 0): the unchanged master `verifier` definition, one fresh read-only run per arm on a detached worktree named `x1..x5` (arm label not shown; mapping in `grading/key.json`, not given to the grader). It checks spec criteria, security (admin-only access, no private chat content, server-side enforcement), robustness (concurrency, input normalisation), and that `docs/UserGuide.md` and `docs/DeveloperGuide.md` match the product.
- **Q3:** non-blocking findings (reported, not gating).
- **Converged:** reached its own done/PASS within 2 revision rounds with no human help.
An arm that fails any of these is **not qualified**: its cost is reported but cannot count as a win. Grader runs are excluded from arm cost.
Frozen-suite triage: if a frozen test fails, decide with the USER whether it contradicts the approved spec/plan (fix the test, bump the suite to v2 and re-grade **all** arms) or the arm is wrong. Record every triage.

## 4. Metrics (per invocation, then per arm)
Reuse TRK-02 numbers: model(s), effort, elapsed, requests, input/cache-read/cache-write(5m,1h)/output/reasoning tokens, cost. Add (derive from logs; if a field cannot be derived, write "unavailable"):
1. Arm, phase (build/fix/verify/re-verify), revision round, trigger (first/retry/revision/resume), requested vs observed model, agent-definition hash, start/end commit.
2. Cost split by token type; reasoning share = reasoning/output.
3. Cache: hit ratio = cache_read/(input+cache_read+cache_write); requests with zero cache read after the first; cache writes following a gap over 5 min; first, max and mean context size per request.
4. Tool calls by name, failed calls, total vs distinct files read, repeated reads of the same path, file paths read (paths only).
5. Time: elapsed, active (first to last request), tool time (esp. test runs), wait before start (gap after the previous dependent stage), and run wall-clock.
6. Orchestrator (main session) as its own rows by phase, not hidden in totals.
7. Output: files changed, lines added/removed, commits, test-suite runs and their pass/fail.
8. Human messages and approval waits beyond the first prompt.
9. Static context: character size of `CLAUDE.md`+`AGENTS.md` and each agent file per arm.

## 5. Steps and gates

**Phase 0: preflight (read-only, no writes)**
1. `git status`; confirm branch `master` and the unrelated changes noted in section 0.
2. Check `workflow/tools/token-tracker/prices.json`: Sonnet and Opus 5.5 are present, **Haiku is missing**.
3. Log probe: inspect the latest Claude session under `~/.claude/projects/<this repo>/` that has `subagents/`. List which fields exist (timestamps, usage, tool_use/tool_result, stop reason, user vs tool-result messages, how a resumed subagent appears, where a worktree-isolated subagent's log lands). Decide how to rebuild invocations (a subagent resumed by SendMessage = one invocation per new user prompt) and which section 4 metrics are derivable. Write findings to `workflow/experiments/adm01/README.md` section "Log probe".

**GATE G0 (AskUserQuestion):**
- Slice: backend only (events + admin report API + docs), report page afterwards (recommended), or full stack.
- Haiku 5.5 USD-per-million prices from the official page (USER supplies; you add them to a copy of the prices file inside `workflow/experiments/adm01/`, not the tracker's). Or compare H3 on tokens only.
- Per-arm cost cap in USD (suggest 15: STU-01 whole slice was 14.37, CHK-01 9.73). If a running arm exceeds it, ask the USER whether to stop.
- Approve the arms, controls, quality gate and metrics list. State a rough total (about 5 arms at the cost of comparable past slices, and say it is an estimate).
- Confirm the USER will launch each arm session.
- Whether adding a `resource-log.md` row and `STATUS.md` update is approved later (decided at G5).

**Phase 1: shared spec**
4. `git switch -c exp/adm01-setup` in the main folder.
5. Run the `spec-writer` subagent for ADM-01 (agreed slice): `workflow/specs/ADM-01/{spec,plan,tasks}.md`. It must fix the contract (endpoints, schemas, error codes) and flag open questions, including: event definitions for chatbot requests, practice completion and AI generation success; reporting period and timezone; success definition and denominator; "no activity" vs "unavailable"; admin-only access; no private chat content in events. Do not decide these yourself.
6. `Set-Location workflow\tools\speccheck`, then `python -m speccheck ..\..\specs\ADM-01`. Fix findings via the spec-writer until it passes.

**GATE G1:** present spec, plan, tasks and every open question. USER decides each. Mark Approved. Commit by path. `git tag adm01-start`. Record the commit hash.

**Phase 2: frozen suite and tooling**
7. Start the baseline `test-designer` with worktree isolation and `adm01-start`, from spec/plan only, writing `src/backend/tests/grader/test_adm01_grader.py` (mocked LLM, named `test_adm01_...`, adversarial cases from the threat model). Commit on `exp/adm01-frozen`. Produce a table mapping each spec acceptance label to test names; flag uncovered labels.
8. `git switch -c exp/adm01-coord adm01-start`. Tests first, then `workflow/experiments/adm01/tools/collect.py` (rebuild invocations from logs, compute section 4, write `runs/<arm>/invocations.csv`, `metrics.csv`, and a TRK-02-style `report.md`) and `grade_arm.py` (copy the `stu02/grade_run.py` pattern; frozen file from `exp/adm01-frozen`; writes `grading/<arm>-frozen.json`) and `compare.py` (percent difference vs A, `results/comparison.csv` and `.md`).
9. Validate `collect.py` on a past session: its per-invocation sums must equal `python -m tracker report` for the same sessions. Report any mismatch.

**GATE G2:** USER skims the criteria-to-test table, the metric names with their "unavailable" list, and the validation result.

**Phase 3: arms**
10. For A, H1, H2, H3, C: `git worktree add ..\adm01-wt\<arm> -b exp/adm01-<arm> adm01-start`. Apply only the arm's change, commit, and check `git diff --stat adm01-start..exp/adm01-<arm>` touches only the allowed files. Record each file's hash in `runs/<arm>/config.json`.
11. Write `prompts/<arm>.md`. A/H1/H2/H3: "Implement the ADM-01 build phase as specified in workflow/specs/ADM-01 (spec and plan are approved; start at the build phase). Use Variant B exactly as in workflow/coordination.md: developer and test-designer in parallel (start commit `<hash>`), then the verifier, at most 2 revision rounds. Skip the token-tracking lifecycle; the experiment measures usage afterwards. Commit everything on this branch and end with your final summary." C: "Work alone without subagents, spec-first and tests-first, as the baseline in workflow/variants/README.md; update docs; commit everything on this branch; end with a summary." Same wording otherwise.
12. Write `launch-card.md`: the randomised order, and for each arm the folder, branch and prompt file.

**GATE G3 (once per arm, in order):** tell the USER: open a **new** Claude Code session with `..\adm01-wt\<arm>` as the project root, same permission mode as the other arms, paste `prompts/<arm>.md`, and answer only permission prompts (note any wait over 60 s). Wait for "arm X done". Stall over 30 minutes: ask the USER whether to stop.

**Phase 4: after each arm**
13. Check the work is committed on the branch. Run `collect.py` and `grade_arm.py`. Record interventions and the first-request cache check.

**Phase 5: grading and comparison**
14. After all arms: create detached worktrees `x1..x5` with a random mapping in `grading/key.json`; run the unchanged `verifier` once on each; save `grading/<code>-blind.md`; unblind afterwards.
15. Do the frozen-suite triage with the USER (section 3). Run `compare.py`.
16. Write `results/review-pack.md` (section 6) and `results/reflection-draft.md` (section 7).

**GATE G4:** USER reviews (section 6).

**GATE G5:** approve the reflection text; copy it to `docs/Reflections.md`? Add a `resource-log.md` row and `STATUS.md` update? Open a PR for the winning arm's ADM-01 backend (from that arm branch minus agent-config changes, never the experiment material), and adopt accepted hypotheses into `.claude/agents/` and `AGENTS.md` through a normal PR? Do nothing you were not approved for. Add a `logs/` session summary verified against what happened, and a handoff in `workflow/notes.md`, if the USER approves.

## 6. Decision rule
- Compare only **qualified** arms. Report each metric as % change vs A.
- **Adopt** H1/H2/H3 if qualified and USD cost is at least 10% below A; **inconclusive** within 10%; **reject** if not qualified or costlier. Report tokens and time alongside; do not call a difference of 10% or less a finding. With one run per arm, say that.
- C vs A answers the secondary question: if C is qualified and clearly cheaper, state what multi-agent still bought (security findings, docs accuracy, independent tests) using the grader's findings. If C failed Q1/Q2, say what the verifier or independent tests caught.
- Do not use revision-round count as a quality proxy (see `stu02-decision.md`); compare what was delivered first.

## 7. Review pack and reflection (so the USER can review quickly)
`results/review-pack.md`, in this order:
1. One table, one row per arm: qualified? (Q1, Q2, Q3, converged), USD, tokens, wall time, active vs wait time, revision rounds, interventions. % vs A.
2. Where the money went: cost by role and by token type (including the orchestrator), per arm.
3. Per-invocation tables, one per arm, with the section 4 columns.
4. Context evidence for H1: files read (total vs distinct, repeats) and context size per invocation, A vs H1.
5. Verifier evidence for H2: requests and cost per verifier pass, A vs H2.
6. Anomalies: interventions, stalls, cache-leak flags, triage decisions, unavailable metrics, tainted arms.
7. Limits: one run per arm, tests designed by an AI, list-price estimates.
USER checks: (a) every claim cites a file; (b) a "cheaper" arm did not do less (lines, tests, grader result); (c) the qualification calls are right; (d) interventions did not skew time.

`results/reflection-draft.md` has two sections, one per question. Each paragraph is: claim, then number, then source file path. Cover the highest-token task types, per-agent breakdown, what each hypothesis changed, idle/blocked findings, retries and repeated reads, cache-miss findings, reasoning-token share, which hypotheses were adopted, and C vs A. No claim without a measured figure.

## 8. Layout
`workflow/experiments/adm01/`: `README.md` (this plan + log probe), `prompts/`, `launch-card.md`, `tools/`, `runs/<arm>/` (`config.json`, `invocations.csv`, `metrics.csv`, `report.md`), `grading/`, `results/`.
Stop and ask the USER if the spec or plan proves ambiguous, an arm cannot be isolated, or any measure cannot be trusted.
````

**User:** [Image attached: a provider pricing table (USD per million tokens) for Claude Fable 5.1, Claude Opus 5.5, Claude Sonnet 5.5 and Claude Haiku 5.5, with columns for input, output, 5m cache writes, 1h cache writes and cache hits/refreshes. Fable 5.1: 10 / 50 / 12.50 / 20 / 0.25. Opus 5.5: 4 / 20 / 5 / 8 / 0.20. Sonnet 5.5: 2 / 10 / 2.50 / 4 / 0.10. Haiku 5.5, for prompts up to 100,000 tokens: 0.10 / 0.50 / 0.125 / 0.20 / 0.01; for prompts over 100,000 tokens: 0.50 / 2.50 / 0.625 / 1 / 0.05.]

I want TRK 03 to be incorporated first. And to resolve the all questions like haiku price, and sure, you can log resource-log.md too

Update the pasteable plan, and ensure that there are no more open abiguous questions.

I want ADM-01 to be fully implemented and testable, not partial for the experiment, as much as possible. But if you think it will blow up my token usage, then keep to your scoped plan, and also how I view the test results & their comparisons

**Assistant (Claude Sonnet 5.5):** Written for: a fresh Claude Code session that executes the work, with you approving at the gates.

**What changed**
- **TRK-03 now runs first.** It goes through the normal spec, tests and verifier path and is merged to `master` before ADM-01 starts. The experiment then uses TRK-03 for measurement, so there is no one-off collection script.
- **Haiku prices are resolved from your screenshot.** The price file has no tier support, so TRK-03 adds it. Haiku's rates depend on prompt size per request: 100,000 tokens or fewer uses the low tier, and more than 100,000 uses the high tier. Sonnet and Opus match your existing `prices.json`, so they stay unchanged.
- **I picked defaults for every open question.** The one thing still waiting on you is the ADM-01 spec approval, which the repo rules require. Even there, the product decisions are pre-filled and you can override them at that gate.
- **`resource-log.md`, `STATUS.md`, `notes.md` and `logs/` updates are pre-approved.** The coordinator writes them at the end. Pushes, PRs, `docs/Reflections.md` and agent-file adoption still need your approval.
- **Scope: I kept the backend-complete slice.** Past rows show what a frontend adds: a backend run cost 1.46 USD and the STU-02 frontend run 5.49 USD, and the SHR-01 whole slice cost 30.24 USD. Estimated worst case with a frontend per arm is roughly 60–100 USD. The backend slice should land near 30–60 USD, which includes TRK-03, the shared spec, the five arms and grading. These are estimates from comparable past rows.
- **"Fully implemented and testable" is still met.** The backend slice has event recording wired into the chatbot, practice submission and AI generation flows, a period-filtered admin-only report API, a migration, and docs. You can try it through pytest, the OpenAPI page, and a `try-it.md`. The report page is built once after the experiment, with the winning workflow, as ADM-01-frontend.
- **How you view the results:** an offline `comparison.html`, plus a test matrix, in the plan below.

One assumption is recorded rather than checked: that provider tiers use total prompt tokens (input + cache read + cache write) per request. It is noted as unverified against billing, like the tracker's other limits.

````markdown
# TRK-03 then ADM-01 workflow experiment: execution plan

You are the **experiment coordinator**. Work in one role at a time and say which. You prepare, measure, grade and report. The human (USER) runs each arm session. Use AskUserQuestion at every gate and stop until answered. All other decisions are already made below; do not ask about them.

## 0. Rules
- Allowed writes: `workflow/specs/TRK-03/`, `workflow/specs/ADM-01/`, `workflow/tools/token-tracker/` (TRK-03 only), tracker docs (`workflow/usage/README.md`, `workflow/tools/token-tracker/README.md`), `workflow/experiments/adm01/**`, branches/tags/worktrees named below. **Pre-approved, done at the end without asking:** new rows in `workflow/experiments/resource-log.md`, rows in `workflow/STATUS.md`, a handoff in `workflow/notes.md`, a verified `logs/` session summary. Everything else (pushing, PRs, `docs/Reflections.md`, editing `.claude/agents/` or `AGENTS.md` on master) needs a gate approval. Do not touch other files under `workflow/experiments/`, `workflow/usage/runs/`, `exp/cmp-*` or `..\cmp-wt\`.
- Never commit to `master`. Stage by path only. The USER's uncommitted `.gitignore` change and untracked `logs/isaac/transcript.md` are not yours: never stage them. No secrets, no raw provider logs or prompts in commits.
- PowerShell 5.1: no `&&`, one command per line, start each with `Set-Location (git rev-parse --show-toplevel)`.
- Unavailable data is "unavailable", never estimated. Costs are "tracker list-price estimates, not billed".
- Keep the main folder on the branch named in each phase. Agent definitions load from the session's project root.

Read first: `AGENTS.md`, `workflow/README.md`, `workflow/coordination.md`, `workflow/variants/README.md`, `workflow/experiments/results/stu02-decision.md`, `workflow/experiments/stu02/{procedure.md,grade_run.py,html_report.py}` (patterns only; copy, never edit), `workflow/tools/token-tracker/` (README, `tracker/`, tests, `prices.json`), `workflow/specs/TRK-02/`, `workflow/usage/README.md`, `workflow/tools/speccheck/README.md`, `docs/FeatureList.md`, ADM-01 plus "Shared acceptance criteria" and "Decisions to resolve" in `docs/UserStories.md`, `workflow/STATUS.md`, top of `workflow/notes.md`.

## 1. Question and design
Goal: cut tokens and time per feature without losing quality. Reflection questions answered: **primary** which task types consume the most tokens and did we reduce them; **secondary** did multi-agent benefits outweigh costs and when to use it.

Five runs of the ADM-01 **build phase** on one frozen spec/plan. Scope (decided): the **backend-complete slice**: server-side event recording wired into the companion chat route, whole-set practice submission and the notes/MCQ generation flows; the admin report API; the migration; tests; `docs/DeveloperGuide.md` and `docs/UserGuide.md`. The admin report page is built after the experiment as ADM-01-frontend with the winning workflow.

| Arm | Change from A (only these files may differ) |
|---|---|
| A | None. Current Variant B on master. |
| H1 context | Add a "Context allowlist" section to `.claude/agents/{developer,test-designer,verifier}.md`, mirrored in `AGENTS.md`. Developer: ADM-01 spec/plan/tasks, the `src/` files plan.md names and their direct imports, the doc sections it edits. Test-designer: ADM-01 spec folder, `workflow/security/threat-model.md`, the ADM-01 part of `docs/UserStories.md`, existing test helpers. Verifier: spec folder, the diff and changed files, the test report, doc sections touched. Add "Ignore the AGENTS.md 'Read first' list; read other files only after reporting a gap." Nothing is removed. |
| H2 verifier | Edit `verifier.md` and the verifier step in `workflow/coordination.md`, mirrored in `AGENTS.md`. The orchestrator passes the verifier: the labelled spec items from `spec.md`, `git diff --stat` and the changed-file list, and the test-designer's suite report. The verifier reads only spec/plan, changed files and that report; runs the suite once on the first pass and once after the final fix (not after each re-check); outputs a per-item table (label, evidence `file:line` or test name, met/unmet); re-checks only previously failed items. |
| H3 model tier | `model: haiku` (was `sonnet`) in `developer.md` and `test-designer.md`. Nothing else. |
| C single agent | No agent-file change. One session, no subagents, spec-first and tests-first, per the baseline in `workflow/variants/README.md`. |

## 2. Controls (all arms)
- Same start commit (tag `adm01-start`), same frozen spec/plan/tasks, same models except where the arm says, same prompt template, same 2-revision-round cap.
- Fresh session per arm, own worktree `..\adm01-wt\<arm>` opened as the session's project root.
- Arm sessions skip the token-tracking lifecycle in `coordination.md` (no manifest, no resource-log); TRK-03 measures from logs afterwards. They may write `workflow/notes.md` handoffs.
- No help beyond the cap. Log every USER intervention and every approval wait over 60 s (cause, minutes). Same permission mode for all arms.
- Order randomised with `random.seed(2610)` and recorded. Each arm starts at least 65 minutes after the previous arm's last request (1-hour cache TTL). Flag an arm if its first request has non-zero cache read.
- Experiment material (frozen tests, grader, scripts, prompts, results) lives only on `exp/adm01-coord` and `exp/adm01-frozen`, never in arm branches.
- Spec-writing is a shared pre-step: report its cost separately; exclude it and the grader from arm totals.
- **Per-arm cost cap: 15 USD** (total about 75 USD). If a running arm passes the cap, stop and ask the USER at that point.

## 3. Quality gate (judged outside the arms)
The developer sees the spec/plan (acceptance criteria and security requirements) but never the frozen tests or grader output.
- **Q1** frozen acceptance suite pass rate: must be 100%.
- **Q2** blocking findings from a blind grader: must be 0. Grader = the unchanged master `verifier` definition, one fresh read-only run per arm on a detached worktree `x1..x5` (arm label hidden; mapping in `grading/key.json`, which the grader never reads). Checks: spec criteria, admin-only access enforced on the server, no private chat content stored or returned, concurrency and input normalisation, docs matching the product.
- **Q3** non-blocking findings: reported only.
- **Converged:** the arm reached its own done/PASS within 2 revision rounds without USER help.
An arm failing any of these is **not qualified**: its cost is shown but cannot count as a win.
Frozen-suite triage: for each failing frozen test, decide with the USER whether it contradicts the approved spec/plan (fix the test, bump to suite v2, re-grade **all** arms) or the arm is wrong. Record each triage.

## 4. Steps and gates

### Phase T: TRK-03 (runs first, then merged to master)
T1. Preflight (read-only): `git status`; confirm `master` and the unrelated changes in section 0; run the tracker's tests to confirm they pass.
T2. Log probe: inspect the latest Claude session under `~/.claude/projects/<this repo>/` that has `subagents/`. List which fields exist: timestamps, usage, tool_use/tool_result, stop reason, human vs tool-result messages, how a resumed subagent appears, where a worktree-isolated subagent's log lands, whether a main-session usage row has a blank agent id. Write `workflow/specs/TRK-03/log-probe.md` (field names and counts only, no prompt text).
T3. `git switch -c feat/token-tracker-trk03 master`. Run the `spec-writer` for TRK-03 with the requirements below; the spec uses the template labels and must pass `python -m speccheck ..\..\specs\TRK-03` run from `workflow\tools\speccheck`.

**TRK-03 requirements the spec must contain:**
- **R1 Pricing.** Add Claude Haiku 5.5 with per-request tiers, prices USD per million tokens, `as_of` 2026-11-05, source = provider pricing page (user-supplied screenshot, 2026-11-05). A request's prompt size = input + cache-read + cache-write (5m and 1h) tokens; up to and including 100,000 uses the first row, above 100,000 the second. Sonnet 5.5 and Opus 5.5 are unchanged (they match the page).

| Haiku 5.5 | input | cache write 5m | cache write 1h | cache read | output |
|---|---|---|---|---|---|
| prompt up to 100,000 | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 |
| prompt over 100,000 | 0.50 | 0.625 | 1.00 | 0.05 | 2.50 |

  The tier rule is an unverified assumption; document it with the other known limits. A model or tier without a price still gives a blank cost, never a guess. Existing model entries must keep working unchanged.
- **R2 Rebuild invocations from logs.** A new command (name fixed by the spec) takes one or more session IDs and rebuilds invocations without a hand-written manifest: one per subagent prompt (resumed agents split per new human/orchestrator prompt), and the main session as `orchestrator` rows, so orchestrator spend is visible. Role from the subagent's agent type; ID format `<run>-<role>-<seq>`. Existing `run-report` and the `invocation-v1` manifest format keep working unchanged.
- **R3 Per-invocation metrics**, each derived from logs or written "unavailable": observed model vs requested; cost split by token type; reasoning share of output; cache hit ratio = cache_read/(input+cache_read+cache_write); requests with zero cache read after the first; cache writes after a gap over 5 minutes; first, max and mean per-request context size; tool calls by name; failed tool calls; total vs distinct files read and repeated reads (paths only, never contents); elapsed, active (first to last request), tool time (including test-command time), wait before start after the previous dependent stage; human messages beyond the first prompt.
- **R4 Optional metadata sidecar** (CSV keyed by invocation ID): arm, phase, revision round, trigger (first/retry/revision/resume), start and end commit, agent-definition hash. Output rows carry them when given.
- **R5 Output formats:** `invocation-v2` Markdown report and a metrics CSV, deterministic, one row per invocation plus a run total and an unattributed-usage line. Elapsed for the run total is latest finish minus earliest start.
- **R6 Cross-check:** per-invocation sums must equal what the existing `report` gives for the same sessions; a mismatch is an error, not a silent difference.
- **R7 Privacy:** only numbers, IDs, model names, roles, timestamps, branch names, folder and file paths; no prompts, replies or file contents. A test must fail if text from a prompt or reply appears in any output.
- **R8** Update the tracker README and `workflow/usage/README.md` in the same change; state the known limits.

**GATE T-1 (AskUserQuestion):** USER approves `spec.md`, `plan.md`, `tasks.md`. Mark Approved; run speccheck again.
T4. Build, tests first (red before green): developer role writes tests then code in the tracker folder, following the plan contract exactly; run `python -m unittest discover -s tests`. Then start the `verifier` subagent (read-only) once on the diff; at most 2 revision rounds. Validate R6 on one real past session and report the numbers.

**GATE T-2:** USER reviews results. Ask whether to push the branch and open a PR into `master`; do it only if approved, then stop until the USER confirms the PR is merged to `master`. Then `git switch master` and `git pull`.

### Phase 1: shared ADM-01 spec
1. `git switch -c exp/adm01-setup`. Run the `spec-writer` for the ADM-01 backend slice. It must adopt these **product defaults** (the USER may override at G1) and still list them as resolved Open questions:
   - Events are append-only, written server-side by existing flows, in PostgreSQL with an Alembic migration (follow how teacher modules store data). Types: `chatbot_request` (an authenticated student message accepted by the companion route), `practice_completed` (a whole-set submission successfully recorded), and for each of notes and MCQs `generation_requested`, `generation_succeeded`, `generation_failed`.
   - Events store type, timestamp and feature only. No message text, answers, user ids or file content.
   - Reporting period: UTC calendar days, `start` and `end` dates inclusive, default last 7 days, maximum 366 days, invalid or reversed range is a 422.
   - Success definition: success = a draft was stored; denominator = generation requests that passed authentication and input validation (including those that then failed at the LLM or on output validation); requests rejected by our own rate limit or validation are excluded and not counted. The success percentage is `null` when the denominator is 0.
   - "No activity" = recording covered the whole period and the count is 0. "Unavailable" = any part of the period predates the first recorded event/recording start; the response flags it and shows no percentage.
   - Access: admin only through the existing session auth, with 401 and 403 as in SHR-01. Report responses never contain private chat content.
2. `Set-Location workflow\tools\speccheck`, then `python -m speccheck ..\..\specs\ADM-01`; fix findings via the spec-writer.

**GATE G1:** USER approves spec, plan, tasks and every default or open question. Commit by path. `git tag adm01-start` and record the hash.

### Phase 2: frozen suite and experiment tools
3. Start the baseline `test-designer` with worktree isolation and `adm01-start`, spec/plan only, writing `src/backend/tests/grader/test_adm01_grader.py` (mocked LLM, `test_adm01_...` names, adversarial cases from the threat model). Commit on `exp/adm01-frozen`. Produce a table mapping each spec acceptance label to test names and flag uncovered labels.
4. `git switch -c exp/adm01-coord adm01-start`. Tests first, then in `workflow/experiments/adm01/tools/`: `grade_arm.py` (copy the `stu02/grade_run.py` pattern; frozen file from `exp/adm01-frozen`; also runs the arm's own tests; writes `grading/<arm>-frozen.json` with per-test pass/fail), `compare.py` (percent change vs A; writes `results/comparison.csv` and `.md`), `html_report.py` (see section 6), `blind.py` (creates `x1..x5` worktrees and `grading/key.json`).

**GATE G2:** USER skims the criteria-to-test table.

### Phase 3: arms
5. For A, H1, H2, H3, C: `git worktree add ..\adm01-wt\<arm> -b exp/adm01-<arm> adm01-start`. Apply only the arm's change, commit, and verify `git diff --stat adm01-start..exp/adm01-<arm>` touches only the allowed files. Save file hashes to `runs/<arm>/config.json`.
6. Write `prompts/<arm>.md`. A/H1/H2/H3: "Implement the ADM-01 build phase as specified in workflow/specs/ADM-01 (spec and plan are approved; start at the build phase). Use Variant B exactly as in workflow/coordination.md: developer and test-designer in parallel (start commit `<hash>`), then the verifier, at most 2 revision rounds. Skip the token-tracking lifecycle; usage is measured afterwards. Commit everything on this branch and end with your final summary." C: "Work alone without subagents, spec-first and tests-first, as the baseline in workflow/variants/README.md; update the docs; commit everything on this branch; end with a summary." Same wording otherwise.
7. Write `launch-card.md` (randomised order; folder, branch and prompt per arm).

**GATE G3 (once per arm, in order):** tell the USER to open a **new** Claude Code session with `..\adm01-wt\<arm>` as the project root, paste `prompts/<arm>.md`, answer only permission prompts, and note waits over 60 s. Wait for "arm X done". If an arm stalls over 30 minutes, ask the USER whether to stop it.

### Phase 4: after each arm
8. Check the work is committed on the branch. Run the TRK-03 command on that arm's sessions with the sidecar (arm, phase, round, trigger, commits, agent-definition hash) and save to `runs/<arm>/`. Run `grade_arm.py`. Record interventions, wait times and the first-request cache check.

### Phase 5: grade, compare, report
9. After all arms: `blind.py`; run the unchanged `verifier` once on each `x1..x5`; save `grading/<code>-blind.md`; unblind. Triage frozen failures with the USER (section 3).
10. Run `compare.py` and `html_report.py`; write `results/review-pack.md`, `results/try-it.md` and `results/reflection-draft.md` (section 6 and 7).

**GATE G4:** USER reviews the results (section 6).

**GATE G5 (separate asks, then act only on approvals):** (a) approve the reflection text, then copy it into `docs/Reflections.md`; (b) open a PR for the winning arm's ADM-01 backend (arm branch minus agent-config changes, never experiment material); (c) adopt the accepted hypotheses into `.claude/agents/` and `AGENTS.md` through a normal PR; (d) push anything. After G5, write the pre-approved records: resource-log rows (TRK-03; the shared spec; one row per arm; the experiment total), `STATUS.md` (TRK-03, ADM-01), a `workflow/notes.md` handoff, and a `logs/` summary verified against what happened.

## 5. Decision rule
- Compare only **qualified** arms; report every metric as % change vs A.
- **Adopt** H1/H2/H3 if qualified and USD cost is at least 10% below A. **Inconclusive** within 10%. **Reject** if not qualified or costlier. Report tokens and time next to cost. With one run per arm, say so.
- C vs A answers the secondary question. If C qualified and is clearly cheaper, state what multi-agent still bought (grader findings, docs accuracy, independent tests). If C failed Q1 or Q2, state what the verifier or independent tests caught.
- Do not use revision-round count as a quality proxy (see `stu02-decision.md`); compare what was delivered first.

## 6. How the USER views results
1. **Open the report:** `Start-Process (Resolve-Path workflow\experiments\adm01\results\comparison.html)`. It is one offline file (no network, light and dark, phone-width), regenerated with `python workflow\experiments\adm01\tools\compare.py` then `python workflow\experiments\adm01\tools\html_report.py`. Sections, in order:
   - Summary table, one row per arm: qualified? (Q1, Q2, Q3, converged), USD, tokens, wall time, active vs wait time, revision rounds, interventions, each % vs A.
   - Where the money went: cost by role and by token type (including the orchestrator), per arm; charts for total cost, cost by role, and time split.
   - **Test results matrix:** rows = every frozen test (named by feature label), columns = arms, cells pass/fail, with each arm's own test count and pass rate beneath. Failing cells link to the triage note.
   - Blind-grader findings per arm (blocking and non-blocking, with file and line).
   - Per-invocation tables for each arm with every TRK-03 metric, "unavailable" where applicable.
   - Context evidence for H1 (files read total vs distinct, repeated reads, context size) and verifier evidence for H2 (requests and cost per pass), each A vs the arm.
   - Anomalies and limits: interventions, stalls, cache-leak flags, triage decisions, tainted arms; one run per arm; tests designed by an AI; list-price estimates.
2. **Try the feature yourself** per arm using `results/try-it.md`, which you write from `docs/DeveloperGuide.md` and the auth seed: `Set-Location ..\adm01-wt\<arm>\src\backend`, `uv sync --frozen`, `uv run uvicorn main:app --host 127.0.0.1 --port 8000`, then the admin sign-in and report calls (and the OpenAPI page at `/docs`). Re-run an arm's tests: `uv run pytest -q` in the same folder.
3. **Check before accepting:** every claim cites a file; a "cheaper" arm did not simply do less (lines changed, tests, grader result); qualification calls are right; interventions did not skew time.

## 7. Reflection draft
`results/reflection-draft.md` has two sections, one per question. Each paragraph is: claim, then number, then source file path. Cover the highest-token task types and per-agent breakdown, what each hypothesis changed, idle and blocked time, retries and repeated reads, cache-miss behaviour and its share of cost, reasoning-token share, which hypotheses were adopted, and C vs A. No claim without a measured figure; "unavailable" where TRK-03 could not measure.

## 8. Layout
`workflow/experiments/adm01/`: `README.md` (this plan), `prompts/`, `launch-card.md`, `tools/`, `runs/<arm>/` (`config.json`, `invocations.csv`, `metrics.csv`, `report.md`), `grading/`, `results/`. Stop and ask the USER only if a spec or plan is ambiguous, an arm cannot be isolated, or a measure cannot be trusted.
````

**User:** sorry, can you have 2 plans, one to implement TRK03 first and the other is the experiment?

I am thinking of implementing TRK03 on the token-tracker-invocation-report branch, and the experiment on another branch. Suggest suitable branch names too

**Assistant (Claude Sonnet 5.5):** Written for: two fresh Claude Code sessions run one after the other (Plan 1, then Plan 2), with you approving at the gates.

**Branch names**

| Purpose | Branch |
|---|---|
| TRK-03 (Plan 1) | `feat/trk03-invocation-metrics`, from current `master` |
| ADM-01 shared spec (Plan 2) | `exp/adm01-setup`, tagged `adm01-start` |
| Frozen grader tests | `exp/adm01-frozen` |
| Experiment tooling and results | `exp/adm01-coord` |
| Arms | `exp/adm01-A`, `exp/adm01-H1`, `exp/adm01-H2`, `exp/adm01-H3`, `exp/adm01-C` |

The arm names follow your earlier `exp/stu02-A` pattern.

**Please don't reuse `feat/token-tracker-invocation-report`.** That branch was already merged into `master` in PR #20, so it is behind `master`. Reusing it would mix TRK-02 and TRK-03 history, and a reopened PR on a merged branch name is confusing for your reviewer. A fresh branch off `master` gives a clean TRK-03 diff. If you still want to reuse it, only Plan 1 step 1 changes: fast-forward it to `master` first with `git switch feat/token-tracker-invocation-report` then `git merge --ff-only master`.

Plan 2 checks at the start that TRK-03 is in `master` and stops if it isn't.

**Plan 1: TRK-03**

````markdown
# Plan 1: TRK-03 invocation metrics and Haiku pricing

You are the **TRK-03 coordinator**. Work in one role at a time and say which. Use AskUserQuestion at every gate and stop until answered. All other decisions are already made; do not ask about them.

## Rules
- Allowed writes: `workflow/specs/TRK-03/`, `workflow/tools/token-tracker/`, `workflow/usage/README.md`, branch `feat/trk03-invocation-metrics`. **Pre-approved, done at the end without asking:** a TRK-03 row in `workflow/experiments/resource-log.md`, a TRK-03 update in `workflow/STATUS.md`, a handoff in `workflow/notes.md`, a verified `logs/` session summary. Pushing and opening the PR need the gate approval. Touch nothing else under `workflow/experiments/`.
- Never commit to `master`. Stage by path only (never `git add -A` or `.`). The USER's uncommitted `.gitignore` change and untracked `logs/isaac/transcript.md` are not yours: never stage them. No secrets, no raw provider logs or prompts in commits.
- PowerShell 5.1: no `&&`, one command per line, start each with `Set-Location (git rev-parse --show-toplevel)`.
- Unavailable data is "unavailable", never estimated. Costs are "tracker list-price estimates, not billed".
- Follow the repo rules: spec first, tests first (red before green), SRP/DRY, update docs in the same change, record resource use.

Read first: `AGENTS.md`, `workflow/README.md`, `workflow/coordination.md`, `workflow/tools/token-tracker/` (README, `tracker/`, tests, `prices.json`), `workflow/specs/TRK-02/`, `workflow/usage/README.md`, `workflow/tools/speccheck/README.md`, `workflow/STATUS.md`, top of `workflow/notes.md`.

## Why
The ADM-01 workflow experiment (Plan 2) needs per-invocation detail the tracker lacks: cache behaviour, tool and file-read counts, time split, orchestrator rows, and a Haiku price. TRK-03 adds these, so Plan 2 needs no one-off scripts.

## Steps and gates
1. Preflight (read-only): `git status`; confirm branch `master` and the unrelated changes above; run the tracker tests (`Set-Location workflow\tools\token-tracker`, `python -m unittest discover -s tests`) and confirm they pass. Then `git switch -c feat/trk03-invocation-metrics master`.
2. Log probe: inspect the latest Claude session under `~/.claude/projects/<this repo>/` that has `subagents/`. List which fields exist: timestamps, usage, tool_use/tool_result, stop reason, human vs tool-result messages, how a resumed subagent appears, where a worktree-isolated subagent's log lands, whether a main-session usage row has a blank agent id. Write `workflow/specs/TRK-03/log-probe.md` (field names and counts only, no prompt text).
3. Run the `spec-writer` subagent for TRK-03 with the requirements below. The spec uses the template labels and must pass speccheck (`Set-Location workflow\tools\speccheck`, then `python -m speccheck ..\..\specs\TRK-03`).

**TRK-03 requirements the spec must contain**
- **R1 Pricing.** Add Claude Haiku 5.5 with per-request tiers, USD per million tokens, `as_of` 2026-11-05, source = provider pricing page (user-supplied screenshot, 2026-11-05). A request's prompt size = input + cache-read + cache-write (5m and 1h) tokens; up to and including 100,000 uses the first row, above 100,000 the second. Sonnet 5.5 and Opus 5.5 are unchanged (they match the page).

| Haiku 5.5 | input | cache write 5m | cache write 1h | cache read | output |
|---|---|---|---|---|---|
| prompt up to 100,000 | 0.10 | 0.125 | 0.20 | 0.01 | 0.50 |
| prompt over 100,000 | 0.50 | 0.625 | 1.00 | 0.05 | 2.50 |

  The tier rule is an unverified assumption; document it with the other known limits. A model or tier without a price still gives a blank cost. Existing model entries must keep working unchanged.
- **R2 Rebuild invocations from logs.** A new command (name fixed by the spec) takes one or more session IDs and rebuilds invocations without a hand-written manifest: one per subagent prompt (a resumed agent splits per new prompt), and the main session as `orchestrator` rows so orchestrator spend is visible. Role comes from the subagent's agent type; ID format `<run>-<role>-<seq>`. Existing `run-report` and the `invocation-v1` manifest keep working unchanged.
- **R3 Per-invocation metrics**, each derived from logs or written "unavailable": observed model vs requested; cost split by token type; reasoning share of output; cache hit ratio = cache_read/(input+cache_read+cache_write); requests with zero cache read after the first; cache writes after a gap over 5 minutes; first, max and mean per-request context size; tool calls by name; failed tool calls; total vs distinct files read and repeated reads (paths only, never contents); elapsed, active (first to last request), tool time (including test-command time), wait before start after the previous dependent stage; human messages beyond the first prompt.
- **R4 Optional metadata sidecar** (CSV keyed by invocation ID): arm, phase, revision round, trigger (first/retry/revision/resume), start and end commit, agent-definition hash. Output rows carry them when given.
- **R5 Output formats:** `invocation-v2` Markdown report and a metrics CSV, deterministic, one row per invocation plus a run total and an unattributed-usage line. Run-total elapsed is latest finish minus earliest start.
- **R6 Cross-check:** per-invocation sums must equal what the existing `report` gives for the same sessions; a mismatch is an error, not a silent difference.
- **R7 Privacy:** only numbers, IDs, model names, roles, timestamps, branch names, folder and file paths; no prompts, replies or file contents. A test must fail if text from a prompt or reply appears in any output.
- **R8 Docs:** update the tracker README and `workflow/usage/README.md` in the same change; state the known limits.

**GATE T-1:** USER approves `spec.md`, `plan.md` and `tasks.md`. Mark Approved and re-run speccheck. Commit by path.

4. Build (developer role, same session): write the tests first using synthetic logs in temporary folders (no real logs in the repo), confirm red, then implement exactly per the plan contract. Run `python -m unittest discover -s tests`. Commit by path.
5. Start the `verifier` subagent once, read-only, on the diff. At most 2 revision rounds; after round 2 escalate to the USER.
6. Real-session validation (local only, nothing committed): run the new command on one recent real session. Check R6 (sums equal `report`), check the output has no prompt or reply text, and list every metric that came out "unavailable".

**GATE T-2:** show the USER the sample `invocation-v2` report (as a local file path), the validation numbers, the unavailable list, the test count and the verifier result. Ask whether to push the branch and open a PR into `master` (end the PR body with the attribution line required by the session). Do it only if approved. Then **stop** and tell the USER to merge it (or have a teammate review and merge); do nothing else until they confirm the merge.

7. After the merge is confirmed, write the pre-approved records: the resource-log row (model, tokens, cost, revision rounds, linked to the verified summary), the `STATUS.md` TRK-03 row, a `notes.md` handoff (using `workflow/templates/handoff.md`), and the `logs/` summary checked against what actually happened. Commit these on a small docs branch or the same branch as the USER prefers, and report. End with: "Plan 2 can start from `master`."
````

**Plan 2: the experiment**

````markdown
# Plan 2: ADM-01 workflow experiment

Prerequisite: Plan 1 (TRK-03) is merged to `master`.

You are the **experiment coordinator**. Work in one role at a time and say which. You prepare, measure, grade and report. The human (USER) runs each arm session. Use AskUserQuestion at every gate and stop until answered. All other decisions are already made below; do not ask about them.

## 0. Rules
- Allowed writes: `workflow/specs/ADM-01/`, `workflow/experiments/adm01/**`, and the branches/tags/worktrees named below. **Pre-approved, done at the end without asking:** new rows in `workflow/experiments/resource-log.md`, rows in `workflow/STATUS.md`, a handoff in `workflow/notes.md`, a verified `logs/` session summary. Everything else (pushing, PRs, `docs/Reflections.md`, editing `.claude/agents/` or `AGENTS.md` on master) needs a gate approval. Do not touch other files under `workflow/experiments/`, `workflow/usage/runs/`, `workflow/tools/`, `exp/cmp-*` or `..\cmp-wt\`.
- Never commit to `master`. Stage by path only. The USER's uncommitted `.gitignore` change and untracked `logs/isaac/transcript.md` are not yours: never stage them. No secrets, no raw provider logs or prompts in commits.
- PowerShell 5.1: no `&&`, one command per line, start each with `Set-Location (git rev-parse --show-toplevel)`.
- Unavailable data is "unavailable", never estimated. Costs are "tracker list-price estimates, not billed".
- Keep the main folder on the branch named in each phase. Agent definitions load from the session's project root.

Read first: `AGENTS.md`, `workflow/README.md`, `workflow/coordination.md`, `workflow/variants/README.md`, `workflow/experiments/results/stu02-decision.md`, `workflow/experiments/stu02/{procedure.md,grade_run.py,html_report.py}` (patterns only; copy, never edit), the tracker README (TRK-03 command, metrics, limits), `workflow/tools/speccheck/README.md`, `docs/FeatureList.md`, ADM-01 plus "Shared acceptance criteria" and "Decisions to resolve" in `docs/UserStories.md`, `workflow/STATUS.md`, top of `workflow/notes.md`.

## 1. Question and design
Goal: cut tokens and time per feature without losing quality. Reflection questions answered: **primary** which task types consume the most tokens and did we reduce them; **secondary** did multi-agent benefits outweigh costs and when to use it.

Five runs of the ADM-01 **build phase** on one frozen spec/plan. Scope (decided): the **backend-complete slice**: server-side event recording wired into the companion chat route, whole-set practice submission and the notes/MCQ generation flows; the admin report API; the migration; tests; `docs/DeveloperGuide.md` and `docs/UserGuide.md`. The admin report page is built after the experiment as ADM-01-frontend with the winning workflow.

| Arm | Branch | Change from A (only these files may differ) |
|---|---|---|
| A | `exp/adm01-A` | None. Current Variant B on master. |
| H1 context | `exp/adm01-H1` | Add a "Context allowlist" section to `.claude/agents/{developer,test-designer,verifier}.md`, mirrored in `AGENTS.md`. Developer: ADM-01 spec/plan/tasks, the `src/` files plan.md names and their direct imports, the doc sections it edits. Test-designer: ADM-01 spec folder, `workflow/security/threat-model.md`, the ADM-01 part of `docs/UserStories.md`, existing test helpers. Verifier: spec folder, the diff and changed files, the test report, doc sections touched. Add "Ignore the AGENTS.md 'Read first' list; read other files only after reporting a gap." Nothing is removed. |
| H2 verifier | `exp/adm01-H2` | Edit `verifier.md` and the verifier step in `workflow/coordination.md`, mirrored in `AGENTS.md`. The orchestrator passes the verifier: the labelled spec items from `spec.md`, `git diff --stat` and the changed-file list, and the test-designer's suite report. The verifier reads only spec/plan, changed files and that report; runs the suite once on the first pass and once after the final fix (not after each re-check); outputs a per-item table (label, evidence `file:line` or test name, met/unmet); re-checks only previously failed items. |
| H3 model tier | `exp/adm01-H3` | `model: haiku` (was `sonnet`) in `developer.md` and `test-designer.md`. Nothing else. |
| C single agent | `exp/adm01-C` | No agent-file change. One session, no subagents, spec-first and tests-first, per the baseline in `workflow/variants/README.md`. |

Other branches: `exp/adm01-setup` (shared spec, tagged `adm01-start`), `exp/adm01-frozen` (grader tests), `exp/adm01-coord` (tools, prompts, results). Experiment material never goes in arm branches.

## 2. Controls (all arms)
- Same start commit (`adm01-start`), same frozen spec/plan/tasks, same models except where the arm says, same prompt template, same 2-revision-round cap.
- Fresh session per arm, in its own worktree `..\adm01-wt\<arm>` opened as the session's project root.
- Arm sessions skip the token-tracking lifecycle in `coordination.md` (no manifest, no resource-log); TRK-03 measures from logs afterwards. They may write `workflow/notes.md` handoffs.
- No help beyond the cap. Log every USER intervention and every approval wait over 60 s (cause, minutes). Same permission mode for all arms.
- Order randomised with `random.seed(2610)` and recorded. Each arm starts at least 65 minutes after the previous arm's last request (1-hour cache TTL). Flag an arm if its first request has non-zero cache read.
- Spec-writing is a shared pre-step: report its cost separately; exclude it and the grader from arm totals.
- **Per-arm cost cap: 15 USD** (total about 75 USD). If a running arm passes the cap, stop and ask the USER at that point.

## 3. Quality gate (judged outside the arms)
The developer sees the spec/plan (acceptance criteria and security requirements) but never the frozen tests or grader output.
- **Q1** frozen acceptance suite pass rate: must be 100%.
- **Q2** blocking findings from a blind grader: must be 0. Grader = the unchanged master `verifier` definition, one fresh read-only run per arm on a detached worktree `x1..x5` (arm label hidden; mapping in `grading/key.json`, which the grader never reads). Checks: spec criteria, admin-only access enforced on the server, no private chat content stored or returned, concurrency and input normalisation, docs matching the product.
- **Q3** non-blocking findings: reported only.
- **Converged:** the arm reached its own done/PASS within 2 revision rounds without USER help.
An arm failing any of these is **not qualified**: its cost is shown but cannot count as a win.
Frozen-suite triage: for each failing frozen test, decide with the USER whether it contradicts the approved spec/plan (fix the test, bump to suite v2, re-grade **all** arms) or the arm is wrong. Record each triage.

## 4. Steps and gates

### Phase 0: preflight (read-only)
1. `git status`; confirm `master` and the unrelated changes in section 0. Confirm TRK-03 is in `master`: the tracker README documents the invocation-rebuild command, `prices.json` has Haiku 5.5 tiers, and the tracker tests pass. If not, **stop** and tell the USER to finish Plan 1.

### Phase 1: shared ADM-01 spec
2. `git switch -c exp/adm01-setup`. Run the `spec-writer` for the ADM-01 backend slice. It must adopt these **product defaults** (the USER may override at G1) and list them as resolved Open questions:
   - Events are append-only, written server-side by existing flows, in PostgreSQL with an Alembic migration (follow how teacher modules store data). Types: `chatbot_request` (an authenticated student message accepted by the companion route), `practice_completed` (a whole-set submission successfully recorded), and for each of notes and MCQs `generation_requested`, `generation_succeeded`, `generation_failed`.
   - Events store type, timestamp and feature only. No message text, answers, user ids or file content.
   - Reporting period: UTC calendar days, `start` and `end` dates inclusive, default last 7 days, maximum 366 days, invalid or reversed range is a 422.
   - Success = a draft was stored; denominator = generation requests that passed authentication and input validation (including those that then failed at the LLM or on output validation); requests rejected by our own rate limit or validation are excluded. The success percentage is `null` when the denominator is 0.
   - "No activity" = recording covered the whole period and the count is 0. "Unavailable" = any part of the period predates the first recorded event/recording start; the response flags it and shows no percentage.
   - Access: admin only through the existing session auth, with 401 and 403 as in SHR-01. Report responses never contain private chat content.
3. `Set-Location workflow\tools\speccheck`, then `python -m speccheck ..\..\specs\ADM-01`; fix findings via the spec-writer.

**GATE G1:** USER approves spec, plan, tasks and every default or open question. Commit by path. `git tag adm01-start` and record the hash.

### Phase 2: frozen suite and experiment tools
4. Start the baseline `test-designer` with worktree isolation and `adm01-start`, spec/plan only, writing `src/backend/tests/grader/test_adm01_grader.py` (mocked LLM, `test_adm01_...` names, adversarial cases from the threat model). Commit on `exp/adm01-frozen`. Produce a table mapping each spec acceptance label to test names and flag uncovered labels.
5. `git switch -c exp/adm01-coord adm01-start`. Tests first, then in `workflow/experiments/adm01/tools/`: `grade_arm.py` (copy the `stu02/grade_run.py` pattern; frozen file from `exp/adm01-frozen`; also runs the arm's own tests; writes `grading/<arm>-frozen.json` with per-test pass/fail), `compare.py` (percent change vs A; writes `results/comparison.csv` and `.md`), `html_report.py` (see section 6), `blind.py` (creates `x1..x5` worktrees and `grading/key.json`).

**GATE G2:** USER skims the criteria-to-test table.

### Phase 3: arms
6. For A, H1, H2, H3, C: `git worktree add ..\adm01-wt\<arm> -b exp/adm01-<arm> adm01-start`. Apply only the arm's change, commit, and verify `git diff --stat adm01-start..exp/adm01-<arm>` touches only the allowed files. Save file hashes to `runs/<arm>/config.json`.
7. Write `prompts/<arm>.md`. A/H1/H2/H3: "Implement the ADM-01 build phase as specified in workflow/specs/ADM-01 (spec and plan are approved; start at the build phase). Use Variant B exactly as in workflow/coordination.md: developer and test-designer in parallel (start commit `<hash>`), then the verifier, at most 2 revision rounds. Skip the token-tracking lifecycle; usage is measured afterwards. Commit everything on this branch and end with your final summary." C: "Work alone without subagents, spec-first and tests-first, as the baseline in workflow/variants/README.md; update the docs; commit everything on this branch; end with a summary." Same wording otherwise.
8. Write `launch-card.md` (randomised order; folder, branch and prompt per arm).

**GATE G3 (once per arm, in order):** tell the USER to open a **new** Claude Code session with `..\adm01-wt\<arm>` as the project root, paste `prompts/<arm>.md`, answer only permission prompts, and note waits over 60 s. Wait for "arm X done". If an arm stalls over 30 minutes, ask the USER whether to stop it.

### Phase 4: after each arm
9. Check the work is committed on the branch. Run the TRK-03 command on that arm's sessions with the sidecar (arm, phase, round, trigger, commits, agent-definition hash) and save to `runs/<arm>/`. Run `grade_arm.py`. Record interventions, wait times and the first-request cache check.

### Phase 5: grade, compare, report
10. After all arms: `blind.py`; run the unchanged `verifier` once on each `x1..x5`; save `grading/<code>-blind.md`; unblind. Triage frozen failures with the USER (section 3).
11. Run `compare.py` and `html_report.py`; write `results/review-pack.md`, `results/try-it.md` and `results/reflection-draft.md` (sections 6 and 7).

**GATE G4:** USER reviews the results (section 6).

**GATE G5 (separate asks, then act only on approvals):** (a) approve the reflection text, then copy it into `docs/Reflections.md`; (b) open a PR for the winning arm's ADM-01 backend (arm branch minus agent-config changes, never experiment material); (c) adopt the accepted hypotheses into `.claude/agents/` and `AGENTS.md` through a normal PR; (d) push anything. After G5, write the pre-approved records: resource-log rows (the shared spec; one row per arm; the experiment total), `STATUS.md` (ADM-01), a `workflow/notes.md` handoff, and a `logs/` summary verified against what happened.

## 5. Decision rule
- Compare only **qualified** arms; report every metric as % change vs A.
- **Adopt** H1/H2/H3 if qualified and USD cost is at least 10% below A. **Inconclusive** within 10%. **Reject** if not qualified or costlier. Report tokens and time next to cost. With one run per arm, say so.
- C vs A answers the secondary question. If C qualified and is clearly cheaper, state what multi-agent still bought (grader findings, docs accuracy, independent tests). If C failed Q1 or Q2, state what the verifier or independent tests caught.
- Do not use revision-round count as a quality proxy (see `stu02-decision.md`); compare what was delivered first.

## 6. How the USER views results
1. **Open the report:** `Start-Process (Resolve-Path workflow\experiments\adm01\results\comparison.html)`. One offline file (no network, light and dark, phone-width), regenerated with `python workflow\experiments\adm01\tools\compare.py` then `python workflow\experiments\adm01\tools\html_report.py`. Sections, in order:
   - Summary table, one row per arm: qualified? (Q1, Q2, Q3, converged), USD, tokens, wall time, active vs wait time, revision rounds, interventions, each % vs A.
   - Where the money went: cost by role and by token type (including the orchestrator), per arm; charts for total cost, cost by role, and time split.
   - **Test results matrix:** rows = every frozen test (named by feature label), columns = arms, cells pass/fail, with each arm's own test count and pass rate beneath. Failing cells link to the triage note.
   - Blind-grader findings per arm (blocking and non-blocking, with file and line).
   - Per-invocation tables for each arm with every TRK-03 metric, "unavailable" where applicable.
   - Context evidence for H1 (files read total vs distinct, repeated reads, context size) and verifier evidence for H2 (requests and cost per pass), each A vs the arm.
   - Anomalies and limits: interventions, stalls, cache-leak flags, triage decisions, tainted arms; one run per arm; tests designed by an AI; list-price estimates.
2. **Try the feature yourself** per arm using `results/try-it.md`, which you write from `docs/DeveloperGuide.md` and the auth seed: `Set-Location ..\adm01-wt\<arm>\src\backend`, `uv sync --frozen`, `uv run uvicorn main:app --host 127.0.0.1 --port 8000`, then the admin sign-in and report calls (and the OpenAPI page at `/docs`). Re-run an arm's tests: `uv run pytest -q` in the same folder.
3. **Check before accepting:** every claim cites a file; a "cheaper" arm did not simply do less (lines changed, tests, grader result); qualification calls are right; interventions did not skew time.

## 7. Reflection draft
`results/reflection-draft.md` has two sections, one per question. Each paragraph is: claim, then number, then source file path. Cover the highest-token task types and per-agent breakdown, what each hypothesis changed, idle and blocked time, retries and repeated reads, cache-miss behaviour and its share of cost, reasoning-token share, which hypotheses were adopted, and C vs A. No claim without a measured figure; "unavailable" where TRK-03 could not measure.

## 8. Layout
`workflow/experiments/adm01/`: `README.md` (this plan), `prompts/`, `launch-card.md`, `tools/`, `runs/<arm>/` (`config.json`, `invocations.csv`, `metrics.csv`, `report.md`), `grading/`, `results/`. Stop and ask the USER only if a spec or plan is ambiguous, an arm cannot be isolated, or a measure cannot be trusted.
````
``````

### Summary of Actions Taken

- Answered which reflection questions to attempt (primary: which task types consume the most tokens and whether usage was reduced; secondary: whether multi-agent benefits outweigh costs) and critiqued the two-branch A/B idea.
- Read the codebase (read-only) to ground the plans: `docs/UserStories.md` and `docs/FeatureList.md` (ADM-01), `workflow/` coordination, variants, STATUS, resource-log and the stu02 decision/procedure, the token-tracker (TRK-02) README, models, run report and `prices.json`, `.claude/agents/*.md`, `AGENTS.md`, the backend layout and existing worktrees and branches.
- Found that ADM-01 has no spec or code yet, that `prices.json` had no Haiku entry, that `feat/token-tracker-invocation-report` was already merged in PR #20, and that earlier `exp/cmp-*` worktrees belong to another comparison.
- Produced the experiment design: five arms (A, H1 context allowlist, H2 verifier checklist, H3 Haiku for developer and test-designer, C single agent) on a frozen ADM-01 spec, a quality gate outside the arms (frozen suite, blind grader), controls for confounders, a decision rule, and how to view results (offline `comparison.html`, test matrix, `try-it.md`).
- Specified TRK-03 (Haiku tiered pricing from the user's screenshot, invocation rebuild from logs, per-invocation metrics, metadata sidecar, privacy and cross-check rules) and split the work into two pasteable plans with suggested branch names, pre-approved record updates and explicit gates.
- No code, specs, branches, tags, worktrees or tests were created or run; the only file written is this log.
- Note: the reasoning setting for each assistant message was not available in the thread metadata and is not recorded. The thread-start timestamp was not available, so the entry is dated by day. The exact wording of the first assistant turn (before the instruction was added to say what I was doing) and the two short progress lines is preserved; tool calls and command output were excluded as the log skill requires. The embedded screenshot is represented by a bracketed description of its table values.
