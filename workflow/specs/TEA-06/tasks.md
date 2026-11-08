# Tasks: TEA-06 Teacher feedback and inbox (verification slice)

| # | Task | Owner agent | Depends on | Status |
|---|---|---|---|---|
| 0 | User approves spec and plan and answers Open question 1 (anonymous `/teacher/feedback`); orchestrator creates the run manifest and runs speccheck | orchestrator | spec + plan | done |
| 1 | Design tests from the plan's evidence matrix: `test_tea06_access.py` and `tea06-inbox.spec.ts` (gaps only); confirm the "Existing evidence" column against the test folders (no `src/` access); mock the 422/network/timeout cases | test-designer | 0 | todo |
| 2 | Replace the `/teacher/feedback` element in the `/teacher` block of `App.tsx` with the signed-in redirect component from the plan; no other source change | developer | 0 | todo |
| 3 | Add `Teacher inbox` section to `docs/UserGuide.md`, correct the teacher paragraph near line 35, add TEA-06 notes to `docs/DeveloperGuide.md` next to the STU-05-06 notes (including the Open question 2 note for the ADM-02 owner) | developer | 0 | todo |
| 4 | Concurrency tests `test_tea06_concurrency.py`: simultaneous mark-read on one delivery and simultaneous submit of one form | test-designer | 0 | todo |
| 5 | Cross-user tests: second teacher, student without a recipient row, admin and anonymous cannot read or change a teacher's form, response, draft or delivery | test-designer | 0 | todo |
| 6 | Run the new tests plus the existing ADM-02, ADM-04 and STU-05-06 suites; report pass/fail per test | test-designer | 1, 2, 4, 5 | todo |
| 7 | Verify: acceptance criteria, security cases, docs match the product, no shared-code change in the diff; re-run suite | verifier | 6 | todo |
| 8 | Fix defects (max 2 rounds), verifier re-checks | developer, verifier | 7 | todo |
| 9 | Record security results in `workflow/security/`, first-run browser failures, resource log and usage report; handoff | orchestrator | 8 | todo |

Tasks 1 to 5 run in parallel after task 0. If the user chooses Open question 1 option B, task 2 uses an unconditional redirect and the AC14 anonymous test is dropped.
