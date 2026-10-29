# STU-02 workflow comparison: findings

| Run | Grader | Own tests | Requests | Cost USD | Wall time | Revision rounds | Interventions |
|---|---|---|---|---|---|---|---|
| A, split verification (5 agents) | 18/18 | 44 | 87 | 2.76 | 2 h 37 min (1 h 40 min stalled) | 1 | 1 |
| B, merged verification (3 agents) | 18/18 | 42 | 54 | 1.56 | 8 min | 1 | 0 |
| Baseline, single session (reference) | 18/18 | 32 | 14 | 0.52 | 3 min | 0 | 0 |

Full table and charts: `stu02-comparison.csv`, `.md`, `.html`.

## Applying the decision rule
1. All three qualify: 100% of the hidden grader, no leakage or ownership failure.
2. The baseline is a reference only (the assignment requires multi-agent SE), so the choice is A or B. B is 43% cheaper than A, outside the 15% band, so the rule picks **B**.

## What the grader does not show
- Concurrency: A's security-reviewer found a save/submit race and A fixed it; B's verifier saw it and rated it non-blocking, so B ships with it; the baseline found and fixed a double-submit race in self-review. The hidden grader has no concurrency test, so all three score the same.
- Opus verification is the largest single cost in both multi-agent runs (A security-reviewer 1.13, B verifier 0.68).
- The orchestrator's own share is large (A 0.89, B 0.52): coordination overhead.

## Limits
One run per condition. Agent definitions loaded from the main folder were older copies for A and B (see `procedure.md`). A's cost includes a stall and a nudge. Review minutes and human quality scores were not measured (user decision). Absolute totals are tracker estimates at API list prices, not checked against the apps.
