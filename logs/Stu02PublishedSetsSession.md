# STU-02 practice on teacher-published sets: 2026-11-06

## Request and scope

Make student practice work on teacher-published practice sets instead of the single fixture set `intro-se-1`, and switch only the AI companion's set lookup to the same source. Branch `claude/stu02-published-sets-6e8525` (local only; nothing pushed). Companion prompts, hint quality and lesson grounding were out of scope (a separate STU-03 run). Also record first-run browser failures for the spec-template evaluation.

## What happened

1. Branch was already current with `origin/master` (`eccc8f0`). Created the token-tracker run manifest `workflow/usage/runs/2026-11-06-STU02PS-01/invocations.csv` before the first agent started.
2. Spec-writer drafted spec, plan and tasks (no shell, so I ran speccheck: it passed). The user asked why the TEA-03 student route could not be reused for the picker. We agreed the real problem was two places answering "which sets can this student see", and chose one shared `set_provider` that the teacher's two student routes also call (the user accepted editing the teacher's files and telling the teacher). The user then asked to standardise malformed set ids on 422 on both sides. Spec-writer revised twice; the user approved with the recommended answers; spec committed at `be2582d`.
3. Test-designer (own worktree, reset to `be2582d`) and developer built in parallel. Merged at `d5266c0`. Backend first run on the merged code: 1109 of 1113 passed; the 4 failures were test-side.
4. First two Playwright runs (150 and 151 failures) were invalid: a dev server and backend from another worktree held ports 5173 and 8000. The developer found the cause. I did not kill those processes; I ran a temporary config on ports 5183/5184 with the API unreachable. First valid run: 5 failures of 522 (3 stale tests the test-designer missed, 2 click-then-Back races).
5. Verifier round 1 FAIL: the CI answer-key positive control grepped the deleted fixture (every CI run would fail), and the companion rejected a submitted attempt when the URL spelled the set id differently. Plus 2 test races and a missing test. Round 2 fixes: CI control now greps the seed, companion compares the canonical id, epoch guards in the practice state, docs line. Verifier round 2 PASS at `2a4b5e4`.
6. Records: first-run file, STATUS, notes, security test log (29 cases), resource log, token report (`report-v2.md`, rebuilt from session logs because the manifest-based report rejected the orchestrator's own usage before the first agent).

## Verification and what is not verified

Verified by the independent verifier at `2a4b5e4`: backend 1123 passed and 1 load flake (TEA-03 MCQ concurrency test, passed 5 of 5 alone, file untouched), 9 hang-prone tests deselected; mocked Playwright 507 of 510 with the 3 failures passing 8 of 8 alone; typecheck and lint clean; one Alembic head. Not verified: real-backend Playwright, GitHub CI, live SoC LLM behaviour, the picker with a real teacher-published set in a browser.

## Corrections to earlier claims

I first reported 150 browser failures as a likely render loop in the new code. That was wrong: they came from stale servers on this machine. I also first described the two later failures as load flakes; the verifier showed both are click-then-immediate-Back races in the tests.

## Things the user must do or decide

- Brief the teacher before merge: his `teacher_publications/routes.py` student routes, a new `seed.py` in his folder, one rewritten test in `test_tea03_publications.py`.
- Decide whether `parse_uuid` should reject a space or underscore inside an id (it is the teacher's helper and was reused unchanged).
- Ask before pushing: rename the branch to `claude/stu02-published-sets` first (agreed), then push and open a PR.
