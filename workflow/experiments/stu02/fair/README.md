# STU-02 fair comparison (the result we rely on)

## Why this exists
The first comparison was unfair: subagent definitions load from the main project folder, which held older agent files during the original Runs A and B, and Run A stalled for 1 h 40 min. A re-run of A alone with the correct definitions then cost the same as B, so the user asked for all three conditions to be re-run with the workflow as the only difference, and for the edge cases to be set by an independent reviewer.

## Conditions (identical except the workflow)
- Same start commit `70ab114` (spec, plan, tasks, prices, pilot fixes); B adds only its agent switch (`540293c`), the baseline only its removal of agent files (`464ecf4`).
- Same model (Claude Sonnet 5.5, Opus for the security-reviewer or verifier as each variant defines), same effort, fresh session each, own worktree each, run one after another on 29 Oct 2026.
- The main project folder was on each run's own branch for the whole run, so each loaded exactly its own agent definitions.
- Same prompt per variant as in `../procedure.md`.

## Results
| | A (5 agents) | B (3 agents) | Baseline (1 session) |
|---|---|---|---|
| Hidden grader (18) | 18/18 | 18/18 | 18/18 |
| Own tests | 50 | 40 | 28 |
| Cost (USD, API list prices) | 1.36 | 1.46 | 0.45 |
| Requests | 47 | 62 | 10 |
| Wall time | 6.3 min | 7.8 min | 2.2 min |
| Revision rounds | 0 | 1 (docs) | 0 |
| Interventions | 0 | 0 | 0 |
| Independent edge cases (115) | 107 | 107 | 107 |
| Independent planted bugs caught by own tests (62) | 62 | 62 | 62 |
| Blind API review (rank) | 3rd | 1st | 2nd |

Cost by agent. A: orchestrator 0.38, security-reviewer (opus) 0.48, developer 0.22, test-designer 0.21, reviewer 0.07. B: orchestrator 0.55, verifier (opus) 0.46, developer 0.29, test-designer 0.16.

## The independent tests
Designed by a separate agent from `spec.md` and `plan.md` only, without seeing any implementation or our earlier tests (`independent-tests/`): 115 scenarios (75 contract, 40 robustness) and a reference implementation with 62 planted bugs. Self-check: the battery passes 115/115 on the clean reference and catches all 62 planted bugs.

All three runs fail the same 8 scenarios:
- six check-order cases (FastAPI rejects an unreadable or wrongly shaped body before the header, ownership and "already submitted" checks the plan puts first),
- one robustness case where FastAPI's default validation error echoes the rejected input,
- the save/submit race (CONC-08): in B and the baseline a submit reported 3/3 while the stored answers scored 2/3; in A the late save changed the submitted attempt and then failed with a 500.

Every run's own suite caught all 62 planted bugs (only the health test was excluded, as the reference has no health endpoint).

## Decision (pre-set rule)
All qualify (100% of the hidden grader, no leakage, ownership holds); the baseline is a reference only. A and B are within the 15% cost band (A 7% cheaper), so the tie-break is fewer revision rounds and interventions: A used 0 rounds, B 1. **The rule picks Variant A.** The blind API review preferred B (only B honoured the documented check order for wrongly shaped bodies); everything else was level.

## What reached the PR
The fair A run's code, with the race fixed (per-attempt lock around save and submit) and the student id trimmed. On the final code the independent battery scores 107/115: the race now passes; ID-05 fails by design, because the reviewer read the silent spec as "padded ids are different students" while we chose to trim; the other seven are the shared FastAPI check-order and echo cases.

## Files
`api-review.md` (blind review, unblinded), `raw/` (edge and mutation results per run and for the final PR code), `mutate_indep.py` (mutation runner using the independent reference), `independent-tests/`.
