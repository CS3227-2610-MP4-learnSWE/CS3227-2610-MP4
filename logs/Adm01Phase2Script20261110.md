# ADM-01 Phase 2 script experiment (H4, H5) and workflow adoption, 9-10 Nov 2026

Branch: `chore/adopt-phase2-script` (from `master`; cherry-picked the A2 documentation commit). The experiment runs were on `exp/adm01-H4a`, `exp/adm01-H5` and the baseline `exp/adm01-A2` (see `logs/Adm01BaselineRerun20261109.md`). Roles: coordinator, independent arm sessions, read-only verifier for the blind reviews.

## What was done
- Chose the lever from the baseline's cost breakdown (the test-designer's second run, 16% of $2.60) and pre-registered the rule before running.
- H4: a script merges the run branch, runs the backend suite and writes a report, replacing the agent. It cost less at round 1 but did not converge: test defects had no owner and a test-designer had to be restarted.
- H5: H4 plus a test-designer fix pass fed only the failure report. $2.14 vs $2.60, one revision round, 153/153 frozen tests, blind review with no blocking defect.
- Adopted H5 provisionally into the workflow: added `workflow/tools/phase2/` (script, 4 parser tests, README), and updated `workflow/coordination.md`, `.claude/agents/test-designer.md`, `AGENTS.md` and the `workflow/README.md` index. Recorded the experiment in `docs/Reflections.md` and `workflow/experiments/results/adm01-phase2-script.md`, usage reports under `workflow/usage/runs/`, and resource-log rows.

## Deviations and limits (checked against what happened)
- H4 was reduced from two runs plus a baseline replicate to one run (amendment recorded before any run). H4 was stopped after round 1 at the user's decision for a fair comparison; a second round had started (test-designer restart) and its cost is reported separately.
- The arms were started as sessions from a coordinator session (inherited model and permissions, database through an untracked settings file), not by hand in VS Code. First-request cache reads were not extracted for H4 and H5.
- H5's "through verifier PASS" cost (about $2.06) is an estimate; the whole-session figure ($2.14) is the tracker total. The blind reviewer saw the workflow files in the diff.
- The adopted script covers backend suites only (frontend suites still run by the test-designer) and was tested on one backend slice. The full backend suite takes about 30 minutes in the script versus about 17 for the agent. Adoption rests on one sample after a design change and should be re-measured.
- Nothing was pushed. Tests: `python -m pytest workflow/tools/phase2 -q` (4 passed). No application code changed.
