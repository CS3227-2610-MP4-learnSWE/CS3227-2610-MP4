# ADM-01 workflow experiment (Plan 2 v2, usage-protected)

Condensed from the approved plan. The coordinator reads this file and `state.json` on resume. Use AskUserQuestion at every gate and stop until answered.

## Rules
- Allowed writes: `workflow/specs/ADM-01/`, `workflow/experiments/adm01/**`, and the branches, tags and worktrees named here. Pre-approved at the end: rows in `workflow/experiments/resource-log.md` and `workflow/STATUS.md`, a `workflow/notes.md` handoff, a verified `logs/` summary. Everything else (push, PRs, `docs/Reflections.md`, editing `.claude/agents/` or `AGENTS.md` on master) needs a gate approval.
- Do not touch other files under `workflow/experiments/`, `workflow/usage/runs/`, `workflow/tools/`, `exp/cmp-*`, `..\cmp-wt\`.
- Never commit to `master`. Stage by path only. Never stage the USER's `.gitignore` change or `logs/isaac/transcript.md`. No secrets, no raw provider logs or prompts.
- PowerShell 5.1: no `&&`, one command per line, start with `Set-Location (git rev-parse --show-toplevel)`.
- Unavailable data is "unavailable", never estimated. Costs are "tracker list-price estimates, not billed".

## Usage protection
1. One unit of work per coordinator session. At the end of each phase/arm: update `state.json`, commit on `exp/adm01-coord`, tell the USER "safe to close this session; start a new one and paste: *Resume Plan 2 from state.json*".
2. Trimmed reads: only files a phase names; Grep with line ranges.
3. Fixed arm order: A, H3, H1, H2, C (replaces the earlier randomised order; no `random.seed(2610)`).
4. Budget: arm A hard cap 15 USD. Later arms cap = 1.5 x A's tracker cost, never above 15 USD. Over cap: stop, ask USER (record "capped" or allow a stated extra). Capped = not qualified.
5. Gate G3 before every arm: USER runs `/usage`; answer start now / defer / stop. Recommend start only with headroom >= 1.5 x A's cost (for A: about 15 USD-equivalent). Never start an arm without headroom.
6. Partial results are valid: every tool treats an arm with no run as "not run".
7. Scope ladder if A costs more than expected, in order: (a) drop C; (b) drop blind-grader run for arms not qualified on Q1; (c) cap revision rounds at 1 for H arms only if A also finished within 1 round.
8. Coordinator on a mid-tier model; spec-writer, test-designer, grader keep normal models; grader unchanged.
9. The 65-minute gap between arms is free; arms may run on different days.

## Design
Five runs of the ADM-01 build phase (backend-complete slice) on one frozen spec/plan. Admin report page is later ADM-01-frontend.

| Arm | Branch | Change from A |
|---|---|---|
| A | `exp/adm01-A` | None (Variant B on master) |
| H3 | `exp/adm01-H3` | `model: haiku` (was `sonnet`) in `developer.md` and `test-designer.md` only |
| H1 | `exp/adm01-H1` | "Context allowlist" section in developer/test-designer/verifier .md, mirrored in `AGENTS.md`; "Ignore the AGENTS.md 'Read first' list; read other files only after reporting a gap." Nothing removed |
| H2 | `exp/adm01-H2` | Edit `verifier.md` and the verifier step in `workflow/coordination.md`, mirrored in `AGENTS.md`: orchestrator passes labelled spec items, `git diff --stat`, changed-file list, test-designer report; per-item table; suite run once first pass and once after final fix; re-check only failed items |
| C | `exp/adm01-C` | No agent-file change; single session, no subagents, spec-first, tests-first |

Other branches: `exp/adm01-setup` (shared spec, tag `adm01-start`), `exp/adm01-frozen` (grader tests), `exp/adm01-coord` (tools, prompts, state, results; at step 6 merge `adm01-start` into it). Experiment material never goes in arm branches.

## Controls
Same start commit, spec/plan/tasks, models (except arm change), prompt template, 2-revision-round cap. Fresh session per arm in worktree `..\adm01-wt\<arm>` as project root. Arm sessions skip the token-tracking lifecycle. Log every USER intervention and approval wait over 60 s. Same permission mode. Each arm starts >= 65 min after the previous arm's last request; flag non-zero cache read on first request. Spec-writing cost reported separately, excluded with grader from arm totals.

## Quality gate
Q1 frozen suite 100%. Q2 blind grader (unchanged master `verifier`, fresh read-only run on detached worktree `x1..xN`, label hidden, key in `grading/key.json`) 0 blocking. Q3 non-blocking reported only. Converged = own done/PASS within round cap without USER help. Failing any, or capped = not qualified. Frozen-suite failures: triage with USER (fix test -> suite v2 -> re-grade all finished arms, or arm is wrong).

## Phases and gates
0 preflight (done 2026-11-05). 1 shared spec on `exp/adm01-setup` with product defaults (append-only events chatbot_request/practice_completed/{notes,mcq}_generation_{requested,succeeded,failed}; no message text/answers/user ids/file content; UTC day periods inclusive, default 7 days, max 366, bad range 422; success definition and null percentage; "no activity" vs "unavailable"; admin only, 401/403) -> speccheck -> **G1**, tag `adm01-start`. 2 frozen suite via test-designer on `exp/adm01-frozen`, then tools in `workflow/experiments/adm01/tools/` (`grade_arm.py`, `compare.py`, `html_report.py`, `blind.py`, `budget.py`), tests first -> **G2**. 3 arm worktrees, prompts, `launch-card.md` -> **G3** per arm. 4 after each arm: TRK-03 command with sidecar, `budget.py`, `grade_arm.py`, update state. 5 blind grade, compare, report, `review-pack.md`, `try-it.md`, `reflection-draft.md` -> **G4**, then **G5** (a reflection, b PR for winner, c adopt hypotheses, d push; separate asks), then pre-approved records.

## Decision rule
Compare only qualified arms, % change vs A. Adopt H if qualified and USD >= 10% below A; inconclusive within 10%; reject if unqualified or costlier; not run = no verdict. C vs A answers the secondary question (see original plan). Do not use revision rounds as a quality proxy.

## Layout
`README.md`, `state.json`, `prompts/`, `launch-card.md`, `tools/`, `runs/<arm>/` (config.json, invocations.csv, metrics.csv, report.md), `grading/`, `results/`. Stop and ask only if spec/plan is ambiguous, an arm cannot be isolated, a measure cannot be trusted, or an arm passes its cap.
