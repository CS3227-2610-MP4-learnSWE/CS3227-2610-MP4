# Retro: ADM-06 AI usage monitoring

Feature: ADM-06 | Branch: feat/adm06-ai-usage-monitoring | PR: pending (local verified change) | Verified on:2026-11-06

## Revision rounds
Rounds used:1/2. Independent activation/CLI tests found ORM autoflush before coverage timestamp; fixed27cd224. Same batchc4df076 corrected inherited demo badge and stale guide text. No verifier source defect remained.

## Defects found
| Defect | Found by | Blocking? | Fixed in round |
|---|---|---|---|
| Activation enables before timestamp due autoflush | independent designer | yes | 1 |
| Authenticated report labelled sample | designer visual QA | non-blocking | 1 |
| Timeout test froze before lazy mount | verifier | test harness | no source round |

## Resource use
Tracker run yes;7invocations. Tokens/cost unavailable: no matching local usage records, report zeros not measured zero usage. One verifier targeted timeout rerun; other fixture/tool recoveries in logs/Adm06Implementation.md. [Resource log](../../experiments/resource-log.md), [report](../../usage/runs/2026-11-06-ADM06-01/report.md).

## RED before GREEN
| Criterion or defect | Test commit (RED) | Fix commit (GREEN) |
|---|---|---|
| AC1-13 missing feature | 9308f15 (77backend cases RED; browser compile/list only, no initial browserRED claimed) | 3c603c1 plus27cd224/c4df076; final independent casesPASS |
| Activation service and CLI | 9308f15, initial integration2FAIL | 27cd224 |
| Live badge | visual inspection before correction; ab26ec2 formal regression added after fix, no formalRED claimed | c4df076 |

## Steps done outside the pipeline
Orchestrator inspected existing source interfaces and amended approved integration contract before launching build roles; no application code by orchestrator. Test designer corrected historical migration targets and invalid harness assumptions without removing data/behavior checks. Tests merged after initial results; strongest final review/full reruns overlapped designer finalfocused recovery. Final browser full512PASS+1fixtureFAIL then corrected1PASS, not a single entirelygreen run. No liveAI/developerDB writes. Remote PR not opened: GitHubCLI unavailable, local review text prepared.

## What to change next time
- workflow/specs/ADM-06/plan.md: retain explicit source-aware compatibility step for shared fake/transport contracts.
- workflow/templates/plan.md: consider lazy-page bootstrap in fake-clock timeout test guidance.
- workflow/usage/README.md: verify provider-log availability before relying on invocation attribution.
