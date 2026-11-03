# SHR-01 build: 2026-11-03

## Request and scope

Build the approved SHR-01 spec (workflow/specs/SHR-01) with Variant B: developer and independent test-designer in parallel from commit 99b45ca, then integration. The user owns the student side; teacher/admin route migration is a handoff to teammates.

## What happened

1. Developer committed the auth core, student route migration, login UI and docs on feat/shr01-auth-spec (a285056, d3b8edf, ad5e963, 4540741). Test-designer wrote backend and Playwright tests in its own worktree from the spec only (f353b89, 27c8eae); RED run at the start commit confirmed they failed for the right reason (333 backend failures, mostly the missing auth seed).
2. I merged the run branch into the test branch (3271262) and ran the backend suite: 659 passed, 7 failed. Triage: 6 test-side (an over-strict 403 check, a no-cookie 401, a test leaving a teacher row behind, a lone-surrogate JSON case, an unmigrated teacher upload test) and 1 docs gap (SharedDataContract). Test-designer fixed the six (4a4ef16); developer added the docs section (8a3ad9d). Backend rerun: 666 passed.
3. Mocked Playwright: first run 198 passed, 19 failed while the backend suite ran at the same time; second run on a quiet machine 191 passed, 26 failed. Failures include five teacher specs and several new auth specs.

## Verification and honesty notes

I read only summaries and short error lines, not traces. Causes of the Playwright failures are hypotheses (see workflow/notes.md). Backend tests ran against a pgserver Postgres, not the project's Docker database. One test was relaxed for a spec ambiguity (lone surrogate in a password gives an empty fields list) and needs the user's confirmation. The verifier did not run. No push, no PR, no merge into the run branch.

## Open

Frontend fix round, verifier, merge of the test branch, security log and threat model entries, CI job changes for the real-backend test.

## Update 2026-11-04: fix rounds, verification and wrap-up

4. Frontend fix round (`90ee734`): the developer bounded `/api/auth/me` with a 2.5 s timeout, changed the loading text, made "Create account" a button and pushed history on logout. The earlier hypothesis that the proxy hung was only partly right: with no backend it returns a fast 500. Playwright went from 26 failed to 4 failed; two test-side fixes (`193b3a4`) left 216 passed, 1 failed (a slow layout test).
5. Verifier round 1 (193b3a4): NOT PASS. Blocking: parallel wrong-password logins could pass the limit check together. Non-blocking: stale UserGuide lines, limiter memory, failed logout leaving a live session, email lower-casing, proxy and TLS notes.
6. Correction round 1: the test-designer wrote concurrency regression tests first (3 of 4 RED, one control that passed); the developer made the limiter atomic with reservations (`a8ac30c`) and fixed the guide and logout. That over-throttled parallel correct logins (the control test failed).
7. Correction round 2 (cap): per-key serialisation of login attempts (`b320c7f`) and the logout test updated (`2e9a2b5`). 23 rate-limit tests pass.
8. Verifier round 2 (aca74c0): PASS, five non-blocking notes. Full backend suite on the final code: 670 passed. CI real-backend job extended (Postgres service, migrate, seeds, masked password); the same flow passed locally. `format:check` fixed for two test files.
9. Records: security log SEC-AUTH-01..14, threat model, task statuses, notes, resource log, reflections.

## Verification honesty

Backend runs used a temporary pgserver Postgres, not Docker. The full mocked Playwright suite was rerun on the final code and passed (219 passed, 0 failed, one clean run). GitHub CI, deployment and load behaviour are unverified. Two Playwright tests are known flaky. I did not read the traces of earlier failures, only summaries and short errors. Leftover helper processes from agents (temporary Postgres servers) may still run until their timers end; the uvicorn I started was stopped.

## Open

Push and PR need the user. Deployment decisions (login DoS guard, proxy settings, cookie settings, demo flag, teacher file storage on Render) belong to the team.
