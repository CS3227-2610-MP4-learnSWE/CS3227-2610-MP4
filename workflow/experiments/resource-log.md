# Resource log

One hand-written row per notable task. Take the numbers from a token-tracker summary (see "Measuring token usage" in `../README.md`) and link the summary file; do not paste raw logs. Mark estimates as estimates.

| Date | Task / feature | Branch | Agent / workflow | Model | Input tok | Cache read tok | Output tok | Reasoning tok | Cost USD | Revision rounds | Notes / summary file |
|---|---|---|---|---|---|---|---|---|---|---|---|
| 2026-10-28 | Workflow scaffolding (PR 1) | chore/sdd-scaffolding | single session | sonnet | 178 | 8,781,224 | 54,240 | 6,717 | 2.14 | n/a | Measured 2026-10-29 by the tracker; also 180,170 cache-write tokens |
| 2026-10-29 | TRK-01 token tracker (PR 2) | feat/token-tracker | single session | sonnet | 50 | 4,339,434 | 38,432 | 9,491 | 1.01 | n/a | Spec and tests first; 48,577 cache-write tokens |
| 2026-10-29 | STU-02 experiment setup (spec, plan, docs) | exp/stu02-setup | single session | sonnet, then opus | 58 | 5,408,839 | 25,466 | 7,850 | 0.96 | n/a | Partial: session still running when measured |
| 2026-10-29 | Experiment tooling (local branch, withheld from runs) | not named here | single session | sonnet, then opus | 84 | 9,395,915 | 50,949 | 12,475 | 4.16 | n/a | Partial. After switching the session to opus, 5 requests cost 2.69 USD, mostly a ~280k-token cache rewrite at the opus 1-hour write price: a model switch cannot reuse the earlier model's prompt cache |

Cache reads dominate token volume (millions per task) but are cheap per token; output and cache writes dominate cost. Switching model mid-session is expensive because the whole context is written to cache again.

Also record: tasks that consumed the most tokens, what was tried to reduce it, and the SoC LLM request counts and rate-limit hits for the in-app AI features.
