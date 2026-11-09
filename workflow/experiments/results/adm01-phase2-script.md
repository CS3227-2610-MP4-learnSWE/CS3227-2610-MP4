# ADM-01 experiment: replacing the test-designer's Phase 2 with a script (H4, H5)

Status: H5 adopted into the workflow provisionally (one sample). Branch of the runs: `exp/adm01-H4a` (H4) and `exp/adm01-H5` (H5), both cut from tag `adm01-start`; baseline A2 is described in `docs/Reflections.md`. Costs are tracker list-price estimates, not billed. Tracker reports: `workflow/usage/runs/2026-11-09-ADM01-H4/`, `2026-11-10-ADM01-H5/` and `2026-11-09-ADM01-A2/`. The arms ran as separate sessions started from a coordinator session (inherited model and permission mode), not by hand in VS Code.

## Summary
| | A2 baseline | H4 (through round 1 / full session) | H5 |
|---|---|---|---|
| Cost USD | 2.604 | 1.830 / 2.066 | 2.140 |
| Requests | 113 | 77 / 84 | 85 |
| Revision rounds | 1 | 1 (not converged) / 2 | 1 |
| Frozen suite 153 | 153/153 | 153/153 at round 1 | 153/153 |
| Blind review | pass, 0 blocking | pass, 0 blocking | pass, 0 blocking |

Verdict: H4 looked cheaper at round 1 but had not converged (three test defects had no owner; a test-designer had to be restarted, 2 rounds). H5 added a test-fix pass and passed the pre-registered rule: 18% cheaper than A2, one revision round, 153/153, no blocking defect. One sample, designed after seeing H4.

## Pre-registration H4 (with amendments)
Written: 2026-11-09 23:54:42 +0800 (before the first H4 run). Not to be changed after any run starts.

## Hypothesis
Replacing the test-designer's second invocation (Phase 2: merge run branch, run suite, report pass/fail per test) with a deterministic script run by the orchestrator (no agent) cuts total cost by about 16% with quality unchanged. Phase 1 and the verifier are unchanged.

## Design
Baseline: A2 (measured: $2.604, 113 requests, 7 invocations, 1 revision round, frozen 153/153, blind PASS) plus one replicate A3 (same tag adm01-start, no changes).
Treatment: H4a and H4b (tag adm01-start + one commit: script, agent-file edits). Order H4a, A3, H4b. Prompt: the arm prompt (workflow/experiments/adm01 on exp/adm01-coord, prompts/arm-template.md) unchanged.

## Decision rule
Adopt H4 only if ALL hold:
1. Mean total cost of H4 runs (all agents, orchestrator, verifier) is >=10% below the mean of baseline runs (A2 and A3).
2. Every H4 run passes the frozen suite 153/153.
3. The blind review of every H4 run has no blocking defect.
4. Revision rounds in H4 are not higher than baseline.
A difference of 10% or less is inconclusive, not a finding. Reject if quality criteria fail. Costs are tracker list-price estimates, not billed. Reported either way, including verifier cost rising.

## Amendment 1 (at the user's request, written 2026-11-10 00:20:01 +0800, before any run started)
Reduced to a single treatment run to save time and quota. Design: H4a compared with the already measured baseline A2. H4b and A3 are not run. The decision rule above applies with one run on each side: H4a total cost at least 10% below A2 (.604), H4a passes the frozen suite 153/153, its blind review has no blocking defect, and its revision rounds are not higher than A2's (1). Within 10% is inconclusive; above A2 or failing quality is a rejection. A single sample cannot separate run-to-run noise from effect (A and A2 differed by 54% but also differed in database availability, so they are not a noise estimate); any result is reported as one sample. The rule is not changed by this amendment; only the number of runs is.

Naming note (2026-11-10 00:20 +0800): the single treatment run is called "H4" in all reports and slides. Its branch and folder keep the name H4a (exp/adm01-H4a, adm01-wt\H4a) because it was already running; renaming mid-run could disturb the session. H4b and A3 are not run.

Intervention log (2026-11-10 01:18 +0800): H4 paused before round 2 because the remaining defects were in tests and no agent owned test fixes once Phase 2 was removed. At the user's decision ("let it run a second round") the run was told to continue round 2 and to restart the test-designer for the test fixes. This restart is a deviation from H4 as designed, is counted in the run cost, and is itself a finding.

Decision (2026-11-10, relayed from the presentation session): H4 counts as a ONE-round run, for comparability with A2/H1-H3. Round 1 ends at commit 7b1c5d5 (01:06). Commits 851a3fe and 3bb1a9e (01:18, test fixes) are round 2 and are excluded from the graded result. Two costs are reported: through round 1, and the full session total.

## H4 results
One treatment run (H4, branch exp/adm01-H4a) against the already measured baseline A2. Costs are tracker list-price estimates, not billed. Tracker output: `workflow/usage/runs/2026-11-09-ADM01-H4/report.md`, `inv.csv`.

## Pre-registered rule (this file (H4 pre-registration), with its amendments)
Adopt H4 only if: (1) cost at least 10% below baseline; (2) frozen suite 153/153; (3) blind review has no blocking defect; (4) revision rounds not higher than baseline's. Within 10% is inconclusive. Amendment 1: one H4 run vs A2 only (H4b and A3 not run). Decision (relayed 2026-11-10): H4 counts as a one-round run (round 1 ends at commit 7b1c5d5); commits 851a3fe and 3bb1a9e are round 2. Logged intervention: round 2 was run at the user's decision, with the test-designer restarted for test fixes.

## Runs

| | A2 (baseline) | H4 through round 1 | H4 full session |
|---|---|---|---|
| Cost (USD) | 2.604 | 1.830 (see caveat) | 2.066 |
| Requests | 113 | 77 | 84 |
| Invocations | 7 | 5 | 6 |
| Orchestrator | 0.390 (15%) | 0.484 (26%) | 0.484 (23%) |
| Developer | 0.893 (34%) | 0.673 (37%) | 0.673 (33%) |
| Test-designer | 0.866 (33%) | 0.426 (23%) | 0.662 (32%) |
| Verifier | 0.455 (17%) | 0.248 (14%) | 0.248 (12%) |
| Second test-designer invocation | yes (0.426, 16%) | no (script) | yes: round-2 restart, 0.236 (11%) |
| Verifier invocations | 2 | 1 (no re-check) | 1 |
| Revision rounds | 1 | 1 (not converged) | 2 |
| Frozen suite 153 | 153/153 | 153/153 (graded at 7b1c5d5) | not graded |
| Blind review | PASS, 0 blocking, 4 non-blocking | PASS, 0 blocking, 4 non-blocking | not reviewed |
| First-request cache read | 45,866 (non-zero) | not extracted | not extracted |

Caveat on "through round 1": it is the full session minus the round-2 test-designer restart. The orchestrator row (25 requests, 0.484) also includes a few round-2 orchestration turns the logs do not let me separate, so 1.830 is a slight overestimate of round-1 cost.

## Comparison
- Round 1 vs A2: 1.830 / 2.604 = -29.7%.
- Full session vs A2: 2.066 / 2.604 = -20.7%.

## Verdict by the pre-registered rule
- Literal reading, round 1 only: criteria 1, 2, 3 and 4 all hold (cost -29.7%, 153/153, 0 blocking, 1 round vs 1). That is a formal "adopt".
- I do not recommend adopting it. At 7b1c5d5 the run had not converged: the round-1 verifier had failed the build on the missing no-store header and reported three test defects (wrong history field name, over-broad regex, stale head assertion in test_tea03_publications.py) that were still open, and there was no verifier re-check. A2 paid for a re-check and a converged result; H4 round 1 did not. The comparison is not like-for-like.
- Full session reading (what actually happened): 2 rounds against A2's 1, so criterion 4 fails, which is a rejection as designed. The saving that remains is -20.7%, and it needed a test-designer restart, which is a deviation from H4.
- Net: the 16% Phase 2 saving is real in the arithmetic (A2's second test-designer cost 0.426), and the script worked, but H4 as designed is not shown to hold quality. Report as one sample; run-to-run noise is unknown (A and A2 differed by 54% for other reasons).

## What moved cost elsewhere
- Orchestrator cost rose (0.390 to 0.484) and its share rose; it now owns recording the script report and triaging failures.
- Verifier fell (0.455 to 0.248) only because the re-check never ran, not because verification got cheaper.
- Developer fell (0.893 to 0.673); the cause is not attributable from one sample.

## Findings
- Removing Phase 2 left no owner for test defects. The test-designer used to see failing tests in its own suite run and fix its own wrong tests; with a script, defects in tests had nobody to go to, the run paused, and a test-designer had to be restarted anyway (cost 0.236). A usable H4 needs a rule for who fixes test defects, e.g. a cheap targeted test-designer call only when the script's hint says "possible logic bug in test" (the script's hint is only a keyword heuristic).
- The script did well: per the arm session, it ran the full backend suite in one deterministic step with no agent and produced a report, 938 passed and 11 failed (figures relayed by the presentation session; I did not re-run it). The 11 failures included the open test defects, i.e. it surfaced what the agent would have.
- Frozen-suite and blind-review quality were fine at round 1 (153/153, 0 blocking); the blind reviewer's non-blocking list includes a nested pooled connection during generation, a narrow exception catch in the recorder, a Developer Guide gap and the unrelated workflow-tool files in the diff. It saw the phase2 files in the diff, so the arm was not fully blind.

## Harness differences and limits
- One H4 run, one baseline run; no replicate (A3, H4b not run), so noise is unknown.
- The arm inherited the coordinator's model and permission mode; it was started by another session, not by hand in VS Code.
- Cold cache was not guaranteed (A2's first request read 45,866 tokens from cache; H4's not extracted).
- No full backend suite in A2 (test_shr01_access.py hung); H4's script ran it.
- Round-1/round-2 split is by commit and invocation start time, not exact.
- The blind verifier did not run tests; its cost was excluded from the arm totals in A2 and here.
- Tracker times are UTC (local +8).



## Pre-registration H5
Written: 2026-11-10 01:28:42 +0800, before the H5 run starts. Not to be changed after the run starts.

## Why H5 exists
H4 (script replaces the test-designer's second run) saved cost on paper but did not converge: removing Phase 2 left test defects with no owner, the run stalled, and a test-designer was restarted outside the design. H5 is the same idea with that gap fixed in the design, decided after seeing H4. It is iteration 2, not a fresh hypothesis; both iterations are reported. A passing H5 is one sample after a design change and must be described that way.

## Change from H4 (branch exp/adm01-H5 = start tag + H4 commit + one commit)
After phase2.py: if its report shows failures, start the test-designer ONCE in fix mode with only that report (fix its own wrong tests, never weaken a test, never edit code, one short pass), then re-run phase2.py once; remaining failures go to the verifier as known. This pre-verification test-fix pass is a cycle, not a revision round, and its cost counts toward the total. Everything else is as in H4 and A2.

## Hypothesis
With a test-fix owner defined, the build converges in the same number of revision rounds as the baseline (1) and total cost is at least 10% below A2.

## Projection (from H4 numbers, not a result)
H4 through round 1 (1.830) + test-designer fix call (about 0.236, the H4 restart cost) + one verifier re-check (about 0.112, A2's) = about 2.18, i.e. about 16% below A2 (2.604).

## Baseline and design
Baseline A2: 2.604 USD, 1 revision round, frozen 153/153, blind PASS. One H5 run (H4 results in this file (H4 results)). Prompt: the arm prompt (workflow/experiments/adm01 on exp/adm01-coord, prompts/arm-template.md) unchanged. Same harness as A2/H4 (session started by the coordinator, inherited model and permissions, database through .claude/settings.local.json).

## Decision rule
Adopt H5 only if ALL hold: (1) total cost (all agents, orchestrator, verifier, including the test-fix pass) at least 10% below A2; (2) the run reaches a verifier PASS within 2 revision rounds and its revision rounds are not higher than A2's (1); (3) frozen suite 153/153 on the final code; (4) blind review of the final code has no blocking defect. Within 10% is inconclusive. Any failed criterion is a rejection. No mid-run intervention except a genuine blocker, logged. Report the outcome whichever way it falls. Costs are tracker list-price estimates, not billed.

## H5 results
One run (branch exp/adm01-H5, HEAD 88622a3) against baseline A2, compared also with H4. Costs are tracker list-price estimates, not billed. Tracker output: `workflow/usage/runs/2026-11-10-ADM01-H5/report.md`, `inv.csv`. Rule: `this file (H5 pre-registration)` (unchanged).

## Runs

| | A2 | H4 (through round 1 / full) | H5 |
|---|---|---|---|
| Cost, whole session (USD) | 2.604 | 1.830 / 2.066 | 2.140 |
| Cost through verifier PASS (USD) | 2.604 | n/a (no PASS) | about 2.06 (estimate) |
| Requests | 113 | 77 / 84 | 85 |
| Invocations | 7 | 5 / 6 | 7 |
| Orchestrator | 0.390 (15%) | 0.484 | 0.628 (29%) |
| Developer | 0.893 (34%) | 0.673 | 0.721 (34%) |
| Test-designer | 0.866 (33%) | 0.426 / 0.662 | 0.528 (25%): design 0.362 + fix 0.166 |
| Verifier | 0.455 (17%) | 0.248 | 0.263 (12%): 0.218 + re-check 0.044 |
| Test-designer second start | yes, Phase 2 (0.426, 16%) | no / restart (0.236) | yes, fix mode only: 2 requests, 16 s, one Edit, 0.166 (8%) |
| Revision rounds | 1 | 1 not converged / 2 | 1, verifier PASS on re-check |
| Frozen suite 153 | 153/153 | 153/153 at round 1 | 153/153 (final code) |
| Blind review | PASS, 0 blocking, 4 non-blocking | PASS, 0 blocking, 4 non-blocking | PASS, 0 blocking, 6 non-blocking |
| First-request cache read | 45,866 (non-zero) | not extracted | not extracted |

How the two H5 costs were made: the whole-session figure is the tracker total, 2.140. For "through the verifier PASS" I removed the orchestrator's turns after the last verifier return (18:46 UTC), which waited for the full-suite run. The logs hold no per-turn cost, so I estimated them as 4 of 36 orchestrator requests, weighted by tokens at assumed list prices, about 12.5% of 0.628, i.e. about 0.08. Treat 2.06 as approximate (plus or minus a few cents).

## phase2.py in this run
- First run: 921 passed, 10 failed, 0 skipped, in the background, about 30 minutes wall-clock (17:43:50 to 18:13:30 UTC), notified on completion; no polling visible in the log. A second run took about 28 minutes. I did not extract that run's counts; the presentation session reports the later full suite as 930 passed and 1 failed (stale head assertion in test_tea03_publications.py, a known side effect of ADM-01's migration; left unedited).
- The 10 failures were the arm's own wrong tests (hints said "possible contract mismatch", heuristic only). The test-designer was started once in fix mode with only the report (16 s, 2 requests, 0.166) and fixed them; this is the designed owner for test defects.
- No script failures recorded.

## Comparison and verdict by the pre-registered rule
1. Cost at least 10% below A2: whole session 2.140 vs 2.604 = -17.8%; through PASS about 2.06 = -20.8%. Holds on both.
2. Verifier PASS within 2 rounds, rounds not above A2's 1: one round, PASS on re-check. Holds.
3. Frozen suite 153/153 on final code: holds.
4. Blind review no blocking defect: holds (0 blocking, 6 non-blocking).

**Verdict: adopt**, as one sample after a design change made after seeing H4. Versus H4: H5 cost 0.07 more than H4's full session (2.140 vs 2.066) but actually converged, with the saving over A2 at 18 to 21% rather than the 30% H4 appeared to show at round 1.

## What moved cost elsewhere
- Orchestrator cost rose from 0.390 to 0.628 (about 0.24 more): it runs the script, waits for it, triages the report and starts the fix pass. About 0.08 of that is idle waiting for the post-verifier full suite, which A2 never ran.
- The test-fix pass (0.166) took the place of A2's 0.426 Phase 2 test-designer; most of the saving is that difference, partly eaten by the orchestrator.
- Verifier fell from 0.455 to 0.263: its re-check was cheaper here (0.044), and its first pass was also cheaper. Not attributable to H5 from one sample.
- Wall-clock got worse, not better: Phase 2 ran the whole backend suite (about 30 minutes) where A2's test-designer took about 17 minutes. Not a cost metric, but a real downside.

## Was the H4 ownership gap closed?
Yes. The 10 failing tests were fixed by the test-designer in one 16-second pass, no intervention, no stall, and the run converged in one revision round. This is a single run, so it shows the design can work, not that it always will.

## Limits
- One sample on each side; run-to-run noise is unknown (A and A2 differed by 54% for other reasons).
- Iteration 2, designed after seeing H4's result; the saving and the fix-pass cost were projected from H4 numbers (projection 2.18 vs actual 2.14).
- Harness: inherited model and permissions, started by the coordinator rather than by hand in VS Code; cold cache not guaranteed (A2's first request read 45,866 tokens from cache; H5's not extracted).
- A2 never ran the full backend suite, H5 did, so the arms did slightly different work after the build.
- Through-PASS cost is an estimate (see above). Blind reviewer saw the workflow files in the diff, so the arm was not fully blind; its cost is excluded from arm totals, as in A2.
- Tracker times are UTC (local +8).


