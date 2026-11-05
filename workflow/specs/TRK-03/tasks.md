# Tasks: TRK-03 Per-invocation metrics from Claude Code logs

Workflow tooling with no stored records and no users, so the template's tasks 6 and 7 (concurrent-request and cross-user tests) are removed; see "Concurrent requests (same time)" in the spec. Tests are written before code. Paths are under `workflow/tools/token-tracker/` unless stated.

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Run the spec checker on `workflow/specs/TRK-03` and get the user's approval of spec.md and plan.md | orchestrator | spec + plan written | todo |
| 2 | Write `tests/helpers_trk03.py` (synthetic session builders: main file, subagent files with `.meta.json`, user/assistant/tool_use/tool_result lines, duplicate lines per message id, sentinel text) without editing `tests/helpers.py` | test-designer | 1 | todo |
| 3 | Design pricing tests (AC1 to AC3, AC26): tier boundary at 100,000, prompt size composition, flat and Sonnet/Opus unchanged, malformed tiers, `cost_breakdown`, variant model IDs (priced and not priced cases) | test-designer | 1 | todo |
| 4 | Design invocation-cutting tests (AC4 to AC8, AC27, AC28): per-prompt split, orchestrator row, ID numbering and order, role, `role_label`, `requested_agent_type` and meta handling, `launched_by`, error cases and their descriptive messages | test-designer | 2 | todo |
| 5 | Design metric tests (AC9 to AC14): one test per metric row of the spec table, including every "unavailable" rule | test-designer | 2 | todo |
| 6 | Design sidecar, output-format and determinism tests (AC15 to AC19), including exact Markdown headers and CSV columns | test-designer | 2 | todo |
| 7 | Design cross-check tests with the descriptive message (AC20, AC21), privacy tests with sentinels (AC22) and likely-agent tests (AC29, AC30: window, nearest, none, no-timestamp, grouping, not added to totals) | test-designer | 2 | todo |
| 8 | Design regression tests (AC24): `run-report`, `report`, `export` unchanged; existing tests not edited | test-designer | 2 | todo |
| 9 | Implement `prices.json` Haiku entry (with `match_variants`), `UsageRow.prompt_tokens`, `pricing.resolve_model_prices`, `pricing.cost_breakdown`, tiered `cost_usd` | developer | 1 | todo |
| 10 | Refactor `claude_logs` (`row_from_line`, `keep_largest`, `agent_meta`) and add `errors.py`, `timeutil.py`, `mdtable.py` (and `run_report._cell` delegating) with no output change | developer | 1 | todo |
| 11 | Implement `log_session.py` (file discovery, prompt windows, tool calls, request info) | developer | 10 | todo |
| 12 | Implement `invocations.py` (cutting, roles, numbering, `launched_by`, warnings) | developer | 9, 11 | todo |
| 13 | Implement `invocation_metrics.py` (all metrics, total row, unattributed row) | developer | 12 | todo |
| 14 | Implement `invocation_meta.py`, `crosscheck.py` (descriptive messages), `unattributed.py` (likely-agent rules), `invocation_render.py` and the `invocations-from-logs` CLI branch with the exact messages and exit codes | developer | 12, 13 | todo |
| 15 | Update `README.md` (tool) and `workflow/usage/README.md` per "R8 docs" in the plan; do not claim anything that does not work | developer | 14 | todo |
| 16 | Merge tests into the run branch; run `python -m unittest discover -s tests`; report pass/fail per test, separating contract mismatches from logic bugs | test-designer | 3 to 8, 15 | todo |
| 17 | Verify: every AC met and covered, DRY/SRP, no new dependencies, privacy, READMEs match behaviour, existing tests unmodified; re-run the suite | verifier | 16 | todo |
| 18 | Fix defects (max 2 rounds); verifier re-checks | developer, verifier | 17 | todo |
| 19 | Record the handoff in `workflow/notes.md`, resource use in `workflow/experiments/resource-log.md`, the token report for this run, and the `logs/` summary | orchestrator | 18 | todo |

Tasks 2 to 8 run in parallel with tasks 9 to 15 (test-designer and developer do not see each other's files). Task 1 gates both.
