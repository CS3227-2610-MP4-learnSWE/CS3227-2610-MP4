# Tasks: CHK-01 Spec checker

Workflow tooling; no stored records, so the template's concurrent-request and cross-user tasks are deleted (the tool is read-only and single-run).

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 1 | Design `unittest` suites for AC1 to AC24 against the plan contract (synthetic spec folders; no access to the tool's code) | test-designer | spec + plan approved | todo |
| 2 | Implement `registry.py`, `parse.py`, `rules.py`, `waivers.py`, `cli.py`, `__main__.py` per plan contract | developer | spec + plan approved | todo |
| 3 | Write `workflow/tools/speccheck/README.md`: usage, exit codes, rule table pointer (`--list-rules`), waiver rule, and a "Verifier only" section; developer-guide link | developer | 2 | todo |
| 4 | Run the checker on the existing specs; write `workflow/specs/speccheck-waivers.txt` (`all` where Tier 1, table or contract rules fail, `added-items` where only labelled items fail; reasons given; CHK-01 not listed) | developer | 2 | todo |
| 5 | Add the `spec-check` job to `.github/workflows/ci.yml` and the "Spec check gate" subsection to `workflow/coordination.md`; index line in `workflow/README.md` | developer | 2 | todo |
| 6 | Run suite; report pass/fail per test, separating contract mismatches from logic bugs | test-designer | 1, 2, 4 | todo |
| 7 | Verify: AC coverage, registry matches the plan table, code quality, read-only and crash-safety, docs, CI permissions; re-run suite and `--all` | verifier | 3, 5, 6 | todo |
| 8 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 7 | todo |
| 9 | Align the STU-01 branch's templates and spec-writer text with the item labels in the plan; record resource use and the handoff line | orchestrator, human | 8 | todo |

Tasks 1 and 2 run in parallel; 3, 4 and 5 can run in parallel after 2.
