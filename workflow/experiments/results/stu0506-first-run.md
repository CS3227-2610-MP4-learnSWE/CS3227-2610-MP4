# STU-05-06 first integration run (spec-template evaluation, fourth data point)

Run 2026-11-07 on `claude/stu05-06-9f4264`. This was a verification slice (no new screens, routes or endpoints), so it is not directly comparable with STU-01, STU-04 or STU-02-published-sets. Spec committed at `36d9857` (later amended), tests at `f559bc0`, developer change at `6751a94`.

## First runs

| Measure | STU-05-06 |
|---|---|
| New browser tests, first run against the code at the start commit | 19 written, 18 passed, 1 failed (5.3%): the sender label test, which failed because the label did not exist yet (expected: the label was the one feature in the slice) |
| New backend tests, first run | 25 written, 25 passed once the database URL used the scheme `postgresql+psycopg://` (first attempt: every login 503, environment, not spec or code) |
| Test-designer's own first-run errors | 3: one assertion on a level-1 heading `Feedback requests` that the page renders as level 2 (plan text wrong), one guessed assertion that only messages are `article` elements (not in the spec), one unused TypeScript import |
| Spec gap or ambiguity | 3 found by the test-designer: heading level in the plan (wrong), sent-time format (unspecified; tests assert only the year), UI behaviour on 401 or 403 of an inbox read (unspecified, so untested) |
| Copy, label or accessible-name mismatches | 1 of 19 (the heading level) |
| Cause shared across many tests | none |
| Existing tests broken by the merged work | 1 (STU-02 picker request-count test, caught by the CI of PR 31 and by the test-designer; fixed upstream by master `09a77ce`) |
| Full browser suite by the verifier (merged code, before the master merge) | 728 tests, 723 passed, 5 failed (0.7%): 5 navigation timeouts on admin pages (`admin-ui.spec.ts:227` x4, `app.spec.ts:201`), load flakes; `app.spec.ts:201` passed alone and `admin-ui` passed 4 of 4 with one worker |
| Full backend suite by the verifier | 1513 passed, 8 deselected (hang-prone `test_shr01_sec_auth_12_*`), 0 failed |
| Code bugs found by the suites | 0 |
| Verifier | round 1 PASS, 0 blocking, 5 non-blocking (2 doc wording errors fixed, 1 coverage note, 2 findings for the ADM-02 and ADM-04 owners) |

## Reading

The table-driven spec worked for copy: the exact labels were taken from the ADM-02 plan and the PR 31 code, and only the heading level was wrong. The spec could not predict the one cross-feature effect (PR 31's badge changing another feature's request-count test); the CI of the other PR and the independent test-designer found it, not the spec. No data point for wrong-role, history or request-count failures: those were already covered by ADM-02 and ADM-04.

## Round 2: student form presentation (AC15 to AC18), added from user feedback

Run 2026-11-07 after the user tried the form. Spec amended at `a4b3c73`, tests first.

| Measure | Round 2 |
|---|---|
| New browser tests, first run on the old code | 31 written, 26 RED, 5 green regression guards; all RED were genuine missing behaviour (duplicate prompt, label positions, no markers, no padding) |
| Test-designer assertions that over-read the spec | 2: the page alert persisting after an autosave (spec said only 'unchanged'), and label edge aligned to the radio box edge at 390px (spec said only left/right association); the second turned out to be a real 9px misalignment once the developer fixed the CSS, and was restored |
| Existing test broken by the requested change | 1 (`adm02-feedback.spec.ts` dropdown label test, superseded by AC15; rewritten with the same intent and stronger checks) |
| Defects found only by the verifier | 2 blocking (focus jumping on every keystroke after a failed submit; no focus cue on a marked field), plus touching cards and, after round 2, full-width buttons; none could be found by tests that fill a field in one step |
| Defect introduced while fixing | 1 (a hover rule hid the red marker; caught by existing AC17 tests) |
| Spec gap | the spec did not say that markers must not move focus while the student types, or what 'visible focus' means for a marked field; both came from the verifier |
| Rounds | verifier 2 (FAIL then PASS), developer 3 invocations, test-designer 3 invocations, spec-writer 1; within the 2-round cap |
| Full frontend suite, final code | 752 tests, 742 passed, 10 failed (1.3%), none in our files: 6 known flakes, 3 that passed alone, 1 new sibling of a known race |

Reading: presentation specs written as exact copy and names were enough for the tests; behaviour on interaction (focus while typing, hover and focus combinations of a red marker) was not, and was found by the verifier reading the code. A UI-contract entry for 'focus and typing after a failed submit' would have caught the blocking defect earlier.
