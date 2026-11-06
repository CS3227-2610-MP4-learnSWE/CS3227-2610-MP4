# STU-04 first integration run (spec-template evaluation, second data point)

Run 2026-11-05 on `claude/stu04-spec-4c7d06` at `d0bac7d` (spec, developer code and the independent tests merged, nothing fixed yet). Mocked Playwright, one run. Backend run separately against a Docker PostgreSQL.

Unlike STU-01, the failures were classified by the independent verifier (round 1), not by the developer who wrote the code.

| Measure | STU-04 |
|---|---|
| Whole suite, first run | 423 tests, 404 passed, 19 failed (4.5% of the suite) |
| Where the 19 failures were | By the verifier's classes below (they sum to 19). Its split between `stu04-*` specs and older specs was reported as 13 and 6 or 7, which does not add up exactly; the per-class counts are the reliable figures. Older specs: `stu01-overview` (6: 3 code bug from the Overview copy, 3 test bug) and `app.spec.ts:43` (stale) |
| Code bug | 6: Overview failure copy 3, counted in `stu01-overview` (the class the template targets: text longer than the spec's exact copy), session reset after logout 1, layout overflow at 390 px 2 |
| Spec gap or ambiguity | 3: "No topics need..." line when every topic is insufficient 1; empty-state sentence and link in one element, not fixed by the UI contract 2 |
| Test bug | 7: strict-mode duplicate text 3, scripted abort consumed by the Overview's own request 1, body-wide "Sample" matching the Shell pill 2, Back pressed before the page rendered 1 |
| Stale old test | 1 browser (`app.spec.ts:43`, Overview now calls `/api/progress`) |
| Load flake, not STU-04 | 2 (`app.spec.ts:186`, `teacher-edit-notes.spec.ts:307`) |
| Backend, first run | 5 failures: 1 spec gap (the plan's state CHECK was weaker than the test), 4 stale tests (3 migration-head tests, 1 TEA-01 one-topic test). One real defect (a NUL byte in an attempt id gave 503, not 404) was found only by the verifier's probe; no test covered it |
| Rounds to green | Round 1: developer and test-side fixes. Round 2 (verifier FAIL): the logout fix remounted pages, so a signed-in 401 sent a second request (3 tests); one migration test contradicted the tightened CHECK. Round 3 (user-authorised beyond the 2-round cap): both fixed, verifier PASS |
| Final | Backend 149 of 149 on the STU-04, STU-01 migration and TEA-01 materials files; Playwright 178 of 178 on the affected specs (2 workers). The full Playwright suite was last run at round 2 (419 of 423; 3 were the then-open defect, 1 a load flake) |

## Comparison with STU-01 and SHR-01

| | SHR-01 (before template) | STU-01 | STU-04 |
|---|---|---|---|
| First-run browser failures, share of suite | 8.8% to 12.0% | 11.2% | 4.5% |
| Copy, label or accessible-name mismatches | most of them (notes) | 0 of 36 | 3 of 19 (all Overview error text) |
| Behaviour the table did not state | several | 3 (wrong role, push/replace) | 3 (an all-insufficient line, sentence/link markup) |
| Cause shared across many tests | no per-test record | 32 of 36 (StrictMode double fetch) | none; the request-count entry stopped that class |
| Regression introduced by a fix | not recorded | 1 (shared in-flight GET) | 1 (key remount sent a second request) |

Reading: the "Requests per load and per retry" entry appears to have removed the biggest STU-01 class (32 failures from one cause), and the first-run share fell to 4.5%. Copy mismatches were not zero: a long message was reused for a stat detail where the spec listed a shorter one. Test bugs (7 of 19) are a large share this time; the independent test-designer could not see the code and wrote strict text lookups that the shared stat copy broke. Both features also had a regression introduced by a round-1 fix, which suggests that fixes to session and request behaviour need a regression test for the whole table entry, not only for the failing case.

Limits: two features of different size, one agent each for writing and a different one for classifying (STU-01 classified by the developer, STU-04 by the verifier), and the suite grew between runs. This is an observation, not evidence that the template helps in general. A smaller first-run failure share also follows from a larger suite (423 against 321 tests).
