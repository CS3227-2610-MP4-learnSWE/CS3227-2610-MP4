# ADM-01 baseline re-run (arm A2), 9 Nov 2026

Branch for the re-run: `exp/adm01-A2` (cut from tag `adm01-start`, worktree `..\adm01-wt\A2`). This log is written from the main folder on `feat/adm01-feature-analytics-build`; nothing on that branch's source was changed. Model: Claude Sonnet 5.5 (coordinator); the arm's agents ran on the models in the agent files (Sonnet developer and test-designer, Opus verifier).

## Why
Arm A of the ADM-01 workflow experiment had no test database, so its own ADM-01 tests were skipped (they skip without `TEA01_TEST_DATABASE_URL`) and its cost left out any test-and-fix loop. That made the baseline cheaper than the H1 to H3 arms, which started their own Postgres. The baseline was re-run once with a database to check the original verdicts.

## What was done
- Created branch and worktree from the tag; started a throwaway Postgres 16 container on port 55432; wrote an untracked `.claude/settings.local.json` in the A2 worktree with the database variable.
- Started the arm as a separate Claude Code session in the A2 folder with the same prompt text as the other arms (`prompts/arm-template.md` on `exp/adm01-coord`), no added hints. It ran developer and test-designer in parallel, one verifier pass, one revision round and a verifier re-check, and committed on `exp/adm01-A2` (last commit `2d04a29`).
- Measured it with `python -m tracker invocations-from-logs` on the arm's session. Report and CSV copied to `workflow/usage/runs/2026-11-09-ADM01-A2/`.
- Graded: frozen suite v2 (153 tests) on a detached copy of the branch against the same Postgres; blind review by the read-only verifier agent on that copy (arm name not given).

## Results
- Cost $2.604 list price, 7 invocations, 113 requests, one revision round, elapsed about 52 minutes (arm A: $1.691, 56 requests).
- Frozen suite 153 of 153 (arm A: 152). Blind review PASS: 0 blocking, 4 non-blocking.
- Against A2: H1 -0.2%, H2 +0.5%, H3 +15.8%. H1 and H2 are inconclusive under the 10% rule, H3 rejected; nothing adopted. Full reading in `docs/Reflections.md`.

## Deviations and limits (checked against what happened)
- The arm was not started in VS Code with a human answering prompts, as the earlier arms were: it was started from this coordinator session, so it inherited the coordinator's model and permission mode. The `claude` command-line tool is not installed on this machine.
- First request read 45,866 tokens from cache, so the 65-minute cold-cache control did not hold for that prefix.
- The first grading attempt failed twice because the operating system blocked a freshly created virtual-environment interpreter (`uv` error 4551, in the scratch folder and in a sibling folder). The frozen suite was then run with the main folder's existing interpreter against the detached copy; frozen files were copied into that copy only and the copy was restored before the blind review. The result is 153 passed in 76 seconds.
- The A2 session did not run the full backend suite: `test_shr01_access.py` hung for over 10 minutes and was not diagnosed. Its 328 passed covers ADM-01, notes, MCQ, companion and practice tests.
- The blind reviewer read code and did not run tests; its cost is excluded from the arm total.
- Nothing was committed from this task. The A2 branch commits were made by the arm. The report, resource-log row and Reflections edits are uncommitted working-tree changes on the feature branch. The Postgres container and the detached review copy were removed afterwards.
- One run; list prices, not billed.

Usage: [A2 report](../workflow/usage/runs/2026-11-09-ADM01-A2/report-v2.md) (the coordinator's own tokens for this task are not included).
