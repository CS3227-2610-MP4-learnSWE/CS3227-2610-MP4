# Decision: Variant B (merged verification) becomes the team workflow

Decided by the user on 29 Oct 2026, after the STU-02 comparison. To be confirmed with the team in the PR that switches the workflow.

## Evidence
| | Run A, split verification (5 agents) | Run B, merged verification (3 agents) | Baseline, single session (reference) |
|---|---|---|---|
| Hidden grader | 18/18 | 18/18 | 18/18 |
| Own tests | 44 | 42 | 32 |
| Cost (API list prices) | 2.76 USD | 1.56 USD | 0.52 USD |
| Requests | 87 | 54 | 14 |
| Revision rounds | 1 | 1 | 0 |
| Interventions | 1 (stalled security-reviewer) | 0 | 0 |
| Save/submit race | found and fixed | found, rated non-blocking, left open | double-submit race fixed |
| Student id trimming | yes | no | not checked |
| Blind API usability review | preferred narrowly (typed status, trimmed id) | slightly clearer messages | not reviewed |

## Why B
1. The decision rule: all runs qualify (100% of the hidden grader, no leakage or ownership failure); the baseline is a reference only because the assignment requires multi-agent SE; between A and B, B is 43% cheaper, well outside the 15% tie band.
2. The quality gap is small and fixable: B's two known defects (save/submit race, untrimmed student id) are small code changes, and the blind API review found A and B behaviourally identical against the contract.
3. B finished without a stall or intervention, in about 8 minutes, and re-verified after its fix round, which A did not.

## What B gives up, and how we compensate
B's single verifier noticed both defects but rated them non-blocking, while A's dedicated security-reviewer insisted the race be fixed. Merging the reviewers spreads one agent's attention across code quality, docs, security and tests. Three gaps allowed this:
1. The STU-02 spec did not state concurrency safety or identity normalisation, so neither the grader nor the verifier treated them as required.
2. The verifier's definition gives no guidance on severity: a violation of an acceptance criterion under concurrent requests should be blocking.
3. The independent API review sent one request at a time, so it could not observe the race.

Compensations to apply with the switch (proposed, not yet done): fix B's race and trimming before merging its code; add a severity rule to the verifier (any way to break an acceptance criterion, including concurrent requests, is blocking); add concurrency and input normalisation to the spec template's security section; consider a dedicated security pass for features touching authentication or AI.

## Shared problems to fix whichever version is merged
OpenAPI does not document the 401/403/404/409 responses or their codes; `X-Student-Id` shows as optional with no description; business and body-shape 422 errors have different shapes; messages do not name the offending question or choice.

## Limits
One run per condition. Runs A and B used older agent definitions loaded from the main folder (documented in `../stu02/procedure.md`); B's verifier ran as a general-purpose agent. A's cost includes a stall. Review minutes and human quality scores were not measured. Costs are tracker estimates at API list prices.
