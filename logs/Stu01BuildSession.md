# STU-01 study materials: 2026-11-04

## Request and scope

Pull `master`, pick the next student feature (STU-01, then STU-04 later), spec it, build it with the multi-agent workflow and verify it. STU-04, STU-05 and STU-06 are not started.

## What happened

1. Pulled `master` (fast-forward of 77 commits to `da57eab`, includes SHR-01) and recommended STU-01 because teachers' published lessons exist but students cannot read them. Created `feat/stu01-spec`.
2. Spec-writer drafted spec, plan and tasks. The user answered the open questions (STU-01 owns `published_lesson`; a `publish_lesson` helper for TEA-03; withdraw column without endpoint; General topic; republish makes a new lesson; demo samples removed; companion label; no enrolment UI; 500-lesson cap). Spec committed as `7aa96d6`.
3. Test-designer (worktree) and developer built in parallel; tests merged at `d4a7c59`.
4. First full runs: backend 814 passed, 2 failed (test-side); Playwright 321 tests, 36 failed, all STU-01. A mistake of mine (database URL without the `+psycopg` scheme) first made the backend run fail almost everything; fixed after one failing test showed the cause.
5. Developer round 1 fixed 33 of the 36 (React StrictMode double fetch, one effect dependency). The other three were test or spec gaps; with the user's approval the spec was clarified and the test-designer fixed the tests.
6. Verifier round 1 NOT PASS: the round-1 fix shared in-flight GETs across sessions and saves (data leak between users, stale list). Developer round 2 plus four new regression tests fixed it; verifier round 2 PASS. Fixes also covered a possible 500 on membership change and `no-store` on error responses.
7. Final runs: backend 816 passed; Playwright 328 of 329 (one load-related layout failure that passes alone); typecheck and lint clean.

## Verification and what is not verified

The test numbers above are from runs I did myself this session; developer and verifier figures were compared with those full runs. Not verified: GitHub CI on this branch, the real-backend Playwright test (task 13, not written), deployment, and any use with a real teacher publishing flow (lessons come from the seed). A second verification session the user started locally was not used. The cost number covers branch-matched usage only.

## Open

PR not opened; the branch was pushed at `d4a7c59` and later commits are local. TEA-03 publish route and ADM-05 course access are teammate tasks. Proposed spec-template additions (requests per load, wrong-role behaviour, history push versus replace) await the user's decision.
