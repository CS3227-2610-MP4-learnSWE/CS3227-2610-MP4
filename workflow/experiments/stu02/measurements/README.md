# STU-02 follow-up measurements: re-run of A, edge cases, mutation testing

Added after the first comparison, because every run scored 18/18 on the hidden grader and the user asked whether multi-agent work showed any benefit beyond the happy path.

## Versions measured
| Label | What it is |
|---|---|
| A | Original Run A (5 agents), older agent definitions, 1 h 40 min stall |
| A2 | Re-run of Variant A from the same start commit, with the correct agent definitions loaded |
| B | Original Run B (3 agents), older agent definitions, verifier run as a general-purpose agent |
| B-fixed | Run B's code with the race and id-trimming fixes (PR 3) |
| baseline | Single session, no subagents |

## Correctness, cost and time
| | A | A2 | B | baseline |
|---|---|---|---|---|
| Hidden grader | 18/18 | 18/18 | 18/18 | 18/18 |
| Cost (USD, API list prices) | 2.76 | 1.58 | 1.56 | 0.52 |
| Requests | 87 | 60 | 54 | 14 |
| Wall time (start to finish) | 157 min | 10 min | 8 min | 3 min |
| Working time (gaps over 20 min removed) | 26 min | 10 min | 8 min | 3 min |
| Interventions | 1 | 0 | 0 | 0 |

A2's cost by agent: orchestrator 0.42, security-reviewer (opus) 0.64, developer 0.28, test-designer 0.16, reviewer 0.07. With correct definitions and no stall, Variant A costs the same as B.

## Edge cases (`edge.py`, 34 scenarios)
Identity, lookups, odd input types, malformed and deeply nested bodies, the documented check order, concurrency (10 simultaneous submits; a save deliberately slowed between its state check and its write while a submit lands), privacy sweeps, server errors and error-body shape. Full table: `edge-table.md`; raw output: `raw/edge-*.json`.

| A | A2 | B | B-fixed | baseline |
|---|---|---|---|---|
| 30/34 | **33/34** | 28/34 | 30/34 | 29/34 |

- The **baseline** has the save/submit race (a submit scored 2/3, then the stored result read 3/3) and **crashes with a 500** on deeply nested JSON.
- **A2** is the only version with no race, no crash, the documented check order and one error shape throughout; it fails only the id-spacing case. Its security-reviewer found and fixed the race, double submit and the crash.
- **A, B and B-fixed** check the request body before ownership and state, against the documented order, and return FastAPI's list-shaped errors for bad bodies.

## Mutation testing (`mutate.py`, `ref/main.py`, 29 planted bugs)
Each run's own test suite was run against a neutral reference implementation written for this purpose, once clean and once per planted bug (16 obvious, 13 subtle). A suite catches a bug if any of its tests fails. Tests that fail on the clean reference (details the spec leaves open) are excluded. Full table: `mutation-table.md`.

| A | A2 | B | baseline | hidden grader |
|---|---|---|---|---|
| 22/29 | **29/29** | 28/29 | **29/29** | 21/29 |

Excluded tests: A 0, A2 4, B 1, baseline 1, grader 0.

## Independent API review (blind, three-way)
The reviewer ranked the baseline first (one error shape everywhere, documented check order, messages naming the question), then A, then B. A2 was not part of that review.

## Reading the results
- Correctness on the specified behaviour was identical in every version.
- Robustness beyond the spec differed: the version whose dedicated security reviewer worked with correct instructions (A2) was the most robust; the single session left a race and a crash.
- Test quality did not favour multi-agent: the single session wrote a suite as strong as A2's, and stronger than A's and B's. The single session's tests would have caught the race in someone else's code, yet its own code kept it.
- Cost: A2 and B are equal; the baseline is about a third of either.
- Limits: one run per version; B was not re-run with correct definitions, so A2 against B is not fully like for like; the edge cases and planted bugs were chosen by the AI that designed the experiment.
