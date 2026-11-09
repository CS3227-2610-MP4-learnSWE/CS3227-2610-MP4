# STU-03 lesson grounding: build and verification

Date: 2026-11-09
Branch: `claude/stu03-lesson-grounding-5ac797` (local; not pushed, no pull request)

## Work completed
- Spec approved by the user; run `2026-11-09-STU03G-01` created before agents started.
- Developer implemented lesson mode; independent test-designer wrote backend and Playwright tests; a disposable local PostgreSQL (port 55433) made the database tests run.
- Verifier round 1 FAIL (leak check before marker removal; marker visible), fix rounds 1 and 2; third verifier pass: no blocking defect.
- Usage report: `workflow/usage/runs/2026-11-09-STU03G-01/report.md`.

## Not done / open
- 5 over-strict regression tests (`test_stu03_grounding_marker2.py`) still fail; user decision needed (see `workflow/notes.md`).
- Full backend and full Playwright suites not re-run after the last fix; GitHub CI not run; AC29 live check not run; no push or PR.
