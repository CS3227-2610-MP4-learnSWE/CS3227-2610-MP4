# STU-01 first integration run (spec-template evaluation data)

Run 2026-11-04 on `feat/stu01-spec` at `d4a7c59` (spec, developer code and the independent tests merged, nothing fixed yet). Mocked Playwright, one run, backend not running at the same time.

| Measure | STU-01 |
|---|---|
| Whole suite, first run | 321 tests, 285 passed, 36 failed (11.2% of the suite) |
| STU-01 browser tests at first run | 101 (`stu01-lesson`, `stu01-materials`, `stu01-overview`); all 36 failures are among them (35.6%) |
| Failures that were UI-detail mismatches with the spec's "UI states and copy" table or the plan's UI contract (loading text, labels, accessible names, messages, control types) | 0 of 36 |
| Logic or integration bugs in the code | 33 of 36: 32 from one cause (React StrictMode runs effects twice in development, so every page sent its GET twice and the mock's scripted replies were consumed by the discarded first request), 1 from an effect dependency that refetched on a 401 |
| Test bug or spec ambiguity | 3 of 36: two tests expected a 403 alert for a teacher opening `/student/...` although the SHR-01 role guard redirects first; one test assumed the lesson's "All study materials" link replaces the history entry (the spec did not say push or replace) |
| Rounds to green | Browser: 1 developer round and 1 test-side round plus two spec clarifications; the verifier then found a blocking defect introduced by the round-1 fix (shared in-flight GET across sessions), fixed in revision round 2 (the cap). Final: 328 of 329 passed, the one failure (layout sweep) passes alone |
| Backend, first full run | 814 passed, 2 failed (both test-side mistakes) |

Failures were classified by the developer who also wrote the code (not independent); the verifier did not reclassify them.

## Comparison with SHR-01 (the slice before the template change)

SHR-01's first merged Playwright runs: 19 failures (backend suite running at the same time) and 26 (quiet machine) of 217 tests, i.e. 8.8% to 12.0% of the suite. The notes call most of them unspecified UI details (loading text, tab versus button, logout failure behaviour, the `/api/auth/me` timeout); no per-test classification was kept, and five of them were teacher specs. The auth specs are 65 tests today; their count at the time was not recorded, so a feature-level rate for SHR-01 cannot be given reliably.

Reading: the overall first-run failure rate was similar (about 11% of the suite for STU-01 against about 9% to 12% for SHR-01), so the template did not reduce the amount of rework we measured. The composition differs: none of the STU-01 failures were mismatches of copy, labels or accessible names, which is the class the template targets, but three were UI behaviours the table did not state (wrong-role navigation, history push versus replace) and 32 came from a behaviour no one specified (how many requests a page sends per load, under StrictMode in development). This is one feature against one feature, of different size and screens, classified by one agent; it is an observation consistent with the template helping with copy and labels, not evidence that it helps in general.
