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
