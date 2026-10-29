# Decision: Variant A (split verification) is the team workflow

Decided on 30 Oct 2026 by the pre-set decision rule, applied to a fair comparison. This replaces an earlier choice of Variant B. To be confirmed with the team in the PR.

## What changed and why
- **First comparison (29 Oct): B chosen.** A cost 2.76 USD against B's 1.56 USD. That gap came from a setup flaw (both runs loaded older agent definitions from the main project folder) and a 1 h 40 min stall in A that expired its prompt cache.
- **Re-run of A alone:** with the correct definitions A cost 1.58 USD, the same as B, which removed the reason for choosing B.
- **Fair comparison (29-30 Oct):** at the user's request, A, B and a single-session baseline were all re-run from the same commit, with the same model, settings and correct definitions, the workflow being the only difference. Edge cases and planted bugs were set by an independent reviewer. Details: `../stu02/fair/README.md`.

## Fair results
| | A (5 agents) | B (3 agents) | Baseline |
|---|---|---|---|
| Hidden grader | 18/18 | 18/18 | 18/18 |
| Cost | 1.36 USD | 1.46 USD | 0.45 USD |
| Wall time | 6.3 min | 7.8 min | 2.2 min |
| Revision rounds | 0 | 1 | 0 |
| Interventions | 0 | 0 | 0 |
| Independent edge cases (115) | 107 | 107 | 107 |
| Planted bugs caught by own tests (62) | 62 | 62 | 62 |
| Blind API review | 3rd | 1st | 2nd |

## Why A
1. All three qualify. The baseline is a reference only, because the assignment requires multi-agent SE.
2. A and B are within the 15% cost band (A about 7% cheaper), so the rule's tie-break applies: fewer revision rounds and interventions. A needed 0 rounds and B needed 1.
3. Quality was otherwise level: the same independent edge-case score, the same failures, and every planted bug caught by both suites. The blind API review preferred B for following the documented check order on wrongly shaped bodies. We record this, but the rule does not weigh it.

## What neither workflow caught
Every run, including the baseline, shipped the save/submit race, and in the fair runs both A's security-reviewer and B's verifier saw it and rated it non-blocking. That is the clearest lesson: having a reviewer is not enough if severity is left to judgement. The chosen workflow's security-reviewer now carries a severity rule (any request sequence, including concurrent requests, that breaks an acceptance criterion, leaks data or lets one user act as another is blocking), and the spec template asks for concurrency and input normalisation.

## What multi-agent coordination bought here
On this small, precisely specified feature, little: the baseline matched both variants on correctness, edge cases and planted bugs at a third of the cost, and ranked second in the API review. Earlier unfair runs suggested a dedicated security reviewer makes code more robust, but that did not hold up in the fair runs. We use Variant A because the assignment requires multi-agent SE and A was the cheaper of the two; single sessions stay allowed for small fixes and docs (`../../coordination.md`).

## Limits
One run per condition. The independent tests were designed by an AI agent, not a person. Costs are tracker estimates at API list prices. Review time and human code-quality scores were not measured (user decision).
