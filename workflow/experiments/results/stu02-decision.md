# Decision: Variant B (merged verification) is the team workflow

Decided by the user on 30 Oct 2026, after a fair comparison. The pre-set rule pointed to A; the team overrode its tie-break for the reason below. To be confirmed with the team in the PR.

## How we got here
- **First comparison (29 Oct): B chosen.** A cost 2.76 USD and B 1.56 USD, but that gap came from a setup flaw (both runs loaded older agent definitions from the main project folder) and a 1 h 40 min stall in A.
- **Re-run of A alone:** with the correct definitions A cost 1.58 USD, the same as B.
- **Fair comparison (29-30 Oct):** A, B and a single-session baseline were re-run from the same commit with the same model, settings and correct definitions, so only the workflow differed. Edge cases and planted bugs were set by an independent reviewer. Details: `../stu02/fair/README.md`.

## Fair results
| | A (5 agents) | B (3 agents) | Baseline |
|---|---|---|---|
| Hidden grader | 18/18 | 18/18 | 18/18 |
| Cost | 1.36 USD | 1.46 USD | 0.45 USD |
| B's cost without its docs revision round | | about 1.25 USD | |
| Wall time | 6.3 min | 7.8 min | 2.2 min |
| Revision rounds | 0 | 1 (docs) | 0 |
| Independent edge cases (115) | 107 | 107 | 107 |
| Planted bugs caught by own tests (62) | 62 | 62 | 62 |
| Blind API review | 3rd | 1st | 2nd |
| Developer guide updated for the new backend | no | yes | no |

## What the rule said, and why we overrode it
The pre-set rule qualifies runs on the grader, then picks the cheapest unless within 15%, then prefers fewer revision rounds. A and B were within 7%, and A needed no revision round while B needed one, so the rule pointed to A.

Looking at what that round was for changed the picture. B's verifier treated the out-of-date `docs/DeveloperGuide.md` as blocking and had it fixed: that round cost about 0.21 USD (developer fix 0.09, verifier re-check 0.12) and is the whole cost difference; without it B would have been about 8% cheaper than A. A's reviewer noticed the same stale guide, rated it non-blocking, and A shipped without fixing it. The tie-break therefore rewarded A for leaving a defect the assignment cares about (the developer guide must match the product). On what each workflow delivered, B was at least as good: accurate docs, first place in the blind API review (the only run following the documented check order for wrongly shaped bodies), and the same tests and edge-case results as A. We expect that to matter more over the rest of the project, so we chose B and record the override here.

## What neither workflow caught
Every run, including the baseline, shipped the save/submit race; in the fair runs both A's security-reviewer and B's verifier saw it and rated it non-blocking because the store is an in-memory placeholder. The merged code fixes it. The chosen verifier now has a severity rule (any request sequence, including concurrent requests, that breaks an acceptance criterion, leaks data or lets one user act as another is blocking, whatever the spec says or the store is), and the spec template asks for concurrency and input normalisation.

## What multi-agent coordination bought here
On this small, precisely specified feature, little: the baseline matched both variants on correctness, edge cases and planted bugs at a third of the cost. We use Variant B because the assignment requires multi-agent SE and B delivered the most complete result; single sessions stay allowed for small fixes and docs (`../../coordination.md`).

## Lessons about the rule itself
"Fewer revision rounds" is a poor proxy for quality when a round can be avoided by waving a defect through. Future decision rules should compare what was delivered (docs accuracy, open defects) before counting rounds.

## Limits
One run per condition. The independent tests were designed by an AI agent, not a person. Costs are tracker estimates at API list prices. Review time and human code-quality scores were not measured (user decision).
