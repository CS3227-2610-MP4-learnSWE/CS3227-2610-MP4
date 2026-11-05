# TRK-03 invocation metrics from logs and Haiku pricing

Date: 2026-11-05
Branch: `feat/trk03-invocation-metrics` (pushed; pull request into `master` not yet opened, see "Pull request")

## Work completed

- Preflight on `master`: tracker suite passed (37 tests). The working tree was clean, so the `.gitignore` change and untracked transcript named in the plan were not present (the transcript is already committed).
- Log probe of the one local Claude session that has `subagents/` (field names and counts only): `workflow/specs/TRK-03/log-probe.md`.
- Spec-writer subagent wrote `spec.md`, `plan.md` and `tasks.md` in `workflow/specs/TRK-03/`. The user asked for plain-language explanations of the open questions and changed four defaults (below); the spec-writer revised once. Spec approved by the user at Gate T-1.
- Tests written first and committed red (`c804c85`), then implementation (`b668bec`), then two doc fixes (`69e9da1`).
- Added `python -m tracker invocations-from-logs --run-id RUN SESSION_ID...`:
  - one `orchestrator` row per session and one row per subagent prompt (a resumed subagent splits per prompt);
  - an `invocation-v2` Markdown report and a 57-column metrics CSV, deterministic, with a run total and an unattributed-usage line;
  - metrics from the logs or `unavailable`, never estimated (cost split, reasoning share, cache hit ratio, zero cache reads, cache writes after a gap, context size, tool calls and failures, file reads, elapsed/active/tool time, wait before start, human messages);
  - optional `--meta` sidecar (role label, arm, phase, revision round, trigger, commits, agent-definition hash);
  - cross-check against the existing `report` code path: a mismatch exits 1, writes nothing and gives a descriptive message.
- Added Claude Haiku 5.5 to `prices.json` with two per-request tiers (prompt size up to and including 100,000 tokens, then above). Dated and bracketed IDs are priced as Haiku 5.5. Sonnet 5.5 and Opus 5.5 are unchanged.
- Updated `workflow/tools/token-tracker/README.md` and `workflow/usage/README.md`.
- `report`, `export`, `run-report` and `invocation-v1` are unchanged.

## Decisions made by the user

| Topic | Decision |
|---|---|
| Role tracking | Each helper agent's role must be visible. Added `requested_agent_type` (from the orchestrator's `Agent` call) and a sidecar `role_label`, alongside the logged `role`. |
| Haiku model IDs | Do not require the exact ID; any ID that implies Haiku 5.5 is priced as Haiku 5.5 (implemented as a prefix rule; provider-prefixed IDs such as `anthropic.claude-haiku-5-5` stay unpriced). |
| Orchestrator time | Report as logged and document it. |
| Cross-check failure | Exit 1 with a descriptive message, not a generic code; other errors also name the input that caused them. |
| Stray usage | Show on an `unattributed` line with a labelled guess of the likely agent, never added to that agent's totals. |

## Verification

- `python -m speccheck ..\..\specs\TRK-03`: passed (before and after approval).
- `python -m unittest discover -s tests` from `workflow/tools/token-tracker`: 167 passed (37 existing unmodified, 2 regression tests against output captured from the old code, 128 new). Before the implementation, the new tests failed (red); the regression tests and the 37 existing tests passed.
- `git diff --check`: passed.
- Verifier subagent (one pass, read-only): PASS, no blocking defects, 0 revision rounds. Six non-blocking findings: the two output files are written one after the other, not atomically (documented); concurrent runs on the same output paths are unsupported; `total_row` takes an unused `prices` parameter fixed by the plan; some test names differ from the plan's map; CSV cells starting with `=`, `+`, `-` or `@` are not escaped; the `prices.json` source wording was misleading (fixed).
- Real-session check (local only, outputs not committed): the 2026-10-30 session gave 10 invocations. Sums of requests (160), input (356), cache read (19,628,675), cache write 5m (409,017), cache write 1h (197,111), output (161,344) and reasoning (19,727) equal the aggregate `report` exactly; unattributed usage was 0; cost 9.040235 in both. Only `wait_before_start_s` was `unavailable` (3 of 10 invocations). A check of 94,781 text windows from the session's prompts, replies and tool text found 13 distinct matches in the outputs, all the session ID, one timestamp or a tool name (allowed); no prompt or reply text.

The tests use synthetic logs; no real provider logs or prompts were committed. This was a single-session build: the same session wrote the tests and the code, so there was no independent test-designer worktree. The verifier pass was independent.

## Pull request

- Pushed to `origin/feat/trk03-invocation-metrics` (4 commits ahead of `master`, 30 files).
- `gh` is not installed on this machine, so the PR was not opened from the command line. Open it at `https://github.com/CS3227-2610-MP4-learnSWE/CS3227-2610-MP4/pull/new/feat/trk03-invocation-metrics` with base `master`.
- Merge by the user or a teammate after the tests pass. The resource-log row, `STATUS.md` row and `notes.md` handoff for TRK-03 are written after the merge.

## Known limits

- The Claude Code log format is undocumented and was observed in one probe session.
- Where a worktree-isolated subagent's log is stored is unverified.
- Codex logs get no new metrics.
- The Haiku tier rule is an unverified assumption.
- Costs are tracker list-price estimates, not billed.

## Resource use

- Tracker run: no for this session (the tracker was run only on the 2026-10-30 session for validation).
- Models: orchestrator and developer role Sonnet 5.5; spec-writer subagent Sonnet 5.5; verifier subagent reported as Opus 5.5.
- Subagent tokens as reported by the harness: spec-writer about 104,000 (first draft) and 162,000 (after revision, as reported at return); verifier about 50,000. Cost not available. Orchestrator tokens not measured.
- Timing (UTC): spec-writer started about 08:12 and returned about 08:20; verifier started about 09:24 and took about 90 seconds.
- No run manifest was created under `workflow/usage/runs/` (outside the allowed writes for this task); agent start and finish times are recorded here instead.
- Retries/revision rounds: spec-writer 1 revision (user feedback); developer 0 verifier rounds beyond the first (PASS).
