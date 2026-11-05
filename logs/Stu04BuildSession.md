# STU-04 progress dashboard: 2026-11-05

## Request and scope

Discuss STU-04 first, then run the normal workflow: spec, approval, independent tests and code in parallel, verification, docs and logs. Branch `claude/stu04-spec-4c7d06`. Also record first-run browser failures for the spec-template evaluation.

## What happened

1. Read the STU-04 stories, shared criteria, STATUS, and the STU-01 and STU-02 code. Found: practice attempts were held in server memory, practice questions had no topic, and the Overview showed a fake 82% and sample chart.
2. The user agreed to seven decisions: persist attempts in PostgreSQL, add a topic to questions, a weak-topic rule (at least 3 answers and under 60% on the latest submitted attempt per set), best and latest score per set, the empty states, a scoped endpoint plus page, and real figures on the Overview.
3. Spec-writer drafted spec, plan and tasks. It had no shell, so I ran the spec checker myself: it passed. The user approved the spec with the default answers to the open questions. Spec committed as `6acff63`.
4. Test-designer (own worktree) and developer built in parallel. Merged at `d0bac7d`.
5. Verifier round 1 FAIL: 6 developer defects (copy, session reset after logout, 390 px overflow, empty-state markup, NUL attempt id gave 503, a weaker database CHECK than the tests), 4 test bugs, 3 stale old tests. Fixes merged at `9781efe`.
6. Verifier round 2 FAIL (cap reached): the logout fix keyed pages by sign-in status, so a signed-in 401 remounted the page and sent a second request; one migration test contradicted the tightened CHECK. The session was interrupted here; Docker was not running when I resumed, and the user started it.
7. With the user's approval a third round fixed both. Verifier round 3 PASS at `6c4eaca`.

## Verification and what is not verified

Verified by the independent verifier at `6c4eaca`: backend 149 of 149 (STU-04, STU-01 migration, TEA-01 materials), Playwright 178 of 178 on the affected specs, typecheck and lint clean. Not verified: the full Playwright suite after round 2 (it was 419 of 423 then; the failures were the defect fixed in round 3 and one known load flake), the full backend suite (it takes about 35 minutes per half on Windows; `test_shr01_sec_auth_12` hangs and was skipped), GitHub CI on this branch, and any live deployment. Files such as the results table come from the verifier's reported counts, whose split between STU-04 and older specs did not add up exactly; the file says so.

## Open

PR not opened and nothing pushed. Known limits: no attempt cap, question reuse undecided, practice not course-scoped, one non-blocking loading-state race after logout then an immediate Back, and the Shell "Demo · Sample data" pill for signed-in students (predates STU-04). Details in `workflow/notes.md`. The 2-revision-round cap was exceeded by one user-authorised round.
