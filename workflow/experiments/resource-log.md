# Resource log

One hand-written row per notable task. Take the numbers from a token-tracker summary (see "Measuring token usage" in `../README.md`) and link the summary file; do not paste raw logs. Mark estimates as estimates.

| Date | Task / feature | Branch | Agent / workflow | Model | Input tok | Cache read tok | Output tok | Reasoning tok | Cost USD | Revision rounds | Notes / summary file |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-28 | Workflow scaffolding (PR 1) | chore/sdd-scaffolding | single session | sonnet | 178 | 8,781,224 | 54,240 | 6,717 | 2.14 | n/a | Measured 2026-10-29 by the tracker; also 180,170 cache-write tokens |
| 2026-10-29 | TRK-01 token tracker (PR 2) | feat/token-tracker | single session | sonnet | 50 | 4,339,434 | 38,432 | 9,491 | 1.01 | n/a | Spec and tests first; 48,577 cache-write tokens |
| 2026-10-29 | STU-02 experiment setup (spec, plan, docs) | exp/stu02-setup | single session | sonnet, then opus | 58 | 5,408,839 | 25,466 | 7,850 | 0.96 | n/a | Partial: session still running when measured |
| 2026-10-29 | Experiment tooling (local branch, withheld from runs) | not named here | single session | sonnet, then opus | 84 | 9,395,915 | 50,949 | 12,475 | 4.16 | n/a | Partial. After switching the session to opus, 5 requests cost 2.69 USD, mostly a ~280k-token cache rewrite at the opus 1-hour write price: a model switch cannot reuse the earlier model's prompt cache |
| 2026-10-29 | STU-02 pilot, endpoints 1-2 (discarded) | claude/stu02-pilot-ab66d7 | Variant A (5 agents) | sonnet; opus security-reviewer | 146 | 2,975,117 | 41,742 | 5,531 | 1.46 | 1 | Attributed by session. Orchestrator 0.57, security-reviewer 0.54, developer 0.14, test-designer 0.14, reviewer 0.08 |
| 2026-10-29 | STU-02 Run A, full feature | claude/stu02-run-a-eba95d | Variant A (5 agents) | sonnet; opus security-reviewer | 190 | 4,487,467 | 76,915 | 8,599 | 2.76 | 1 | Grader 18/18; 1 intervention (stall); by session |
| 2026-10-29 | STU-02 Run B, full feature | claude/stu02-run-b-223ec1 | Variant B (3 agents) | sonnet; opus verifier | 122 | 3,034,735 | 41,342 | 3,530 | 1.56 | 1 | Grader 18/18; verifier ran as general-purpose agent |
| 2026-10-29 | STU-02 baseline, full feature | claude/stu02-run-baseline-e1c0af | single session (reference) | sonnet | 28 | 1,183,177 | 21,681 | 1,021 | 0.52 | 0 | Grader 18/18; 14 requests, 3 min |
| 2026-10-29 | Coordinating session for the whole experiment (setup, pilot and run checks, grading, reviews, deck, fixes) | exp/stu02-setup + exp/stu02-grader | single session (orchestrating the runs) | sonnet, then opus | 594 | 91,374,027 | 240,105 | 55,811 | 29.18 | n/a | Partial, measured mid-session. Cost far above the runs themselves, mostly after the switch to opus: long context re-read on every turn |

Cache reads dominate token volume (millions per task) but are cheap per token; output and cache writes dominate cost. Switching model mid-session is expensive because the whole context is written to cache again.

Also record: tasks that consumed the most tokens, what was tried to reduce it, and the SoC LLM request counts and rate-limit hits for the in-app AI features.
