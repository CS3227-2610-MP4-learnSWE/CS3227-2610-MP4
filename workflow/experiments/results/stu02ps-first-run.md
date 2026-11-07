# STU-02-published-sets first integration run (spec-template evaluation, third data point)

Run 2026-11-06 on `claude/stu02-published-sets-6e8525`: spec committed at `be2582d`, developer code and the independent tests merged at `d5266c0`, then the test-designer's four backend fixes merged before the clean browser run. Mocked Playwright; backend run separately against a local PostgreSQL (port 5433). Classified by the orchestrator from the failure output and by the verifier afterwards (as for STU-04, not by the developer).

## Two browser runs that do not count

The first two full Playwright runs (150 and 151 failures of 522) tested the wrong code. `playwright.config.ts` reuses an existing server outside CI, and a Vite dev server on port 5173 and a backend on port 8000 from another worktree (`stu04-spec-4c7d06`) were running. Pages loaded the old code (`PRACTICE_SET_ID`, no picker), and the backend returned 401 for `/api/progress`, which signed the mocked student out. These failures say nothing about the spec or the code. The developer found the cause; the third run used a temporary config on ports 5183/5184 with the API port unreachable.

## First valid run

| Measure | STU-02-published-sets |
|---|---|
| Whole browser suite, first valid run | 522 tests, 517 passed, 5 failed (1.0% of the suite) |
| Backend, first run on the merged code | 1113 tests, 1109 passed, 4 failed (0.4%); 9 hang-prone tests deselected on Windows |
| Lint, first run | 1 error (a control character in a regular expression in a test) |
| Code bugs in the first runs | 0 |
| Spec gap or ambiguity | 1 backend: the spec names no code for a non-string choice value (pydantic's own 422 shape reached a test that expected `invalid_choice`) |
| Test bug | 6 backend and browser: 3 old tests not rewritten (`app.spec.ts:149`, `practice.spec.ts:659` and `:674`, they still clicked the sidebar link and expected the old page); the encoded-slash test expected 404 where the framework answers 307 (2 params); a new test left a teacher enrolment that an older TEA-01 test listed |
| Load flake | 2 (`stu02ps-picker.spec.ts:509`, `stu04-progress.spec.ts:571`); both passed alone at the time. The verifier later showed both are click-then-immediate-Back races in the tests, not load alone: `:509` fails every time when the click is followed at once by Back, `:571` is identical on master |
| Stale-server runs | 2 invalid runs (see above) |

## After verification (what the first runs did not show)

The verifier failed round 1 with 2 blocking defects the suites did not catch, and passed round 2:

1. **CI answer-key control pointed at the deleted fixture** (plan gap: the plan edited `ci.yml` for the seed step but did not list the bundle-scan control that greps the backend fixture). Every CI run would have failed.
2. **Companion rejected a submitted attempt when the URL spelled the set id differently** (uppercase or braced UUID). The spec promised any accepted spelling finds the same set, and the new companion consistency check compared exact text. Code and spec interaction; no test covered it.

Non-blocking: a stale in-flight run could continue after switching sets (guard added), two more click-then-Back test races, a stale sentence in `docs/SharedDataContract.md`, `parse_uuid` accepting a space or underscore inside an id (kept as the TEA-03 behaviour; the AC11 wording differs).

Rounds: verifier 2 (round 1 FAIL, round 2 PASS), developer 3 invocations, test-designer 5 invocations (includes interim re-entries), spec-writer 3 (two for user decisions, one for the 422 change). Within the 2-round cap.

## Comparison with STU-01, SHR-01 and STU-04

| | SHR-01 (before template) | STU-01 | STU-04 | STU-02-published-sets |
|---|---|---|---|---|
| First-run browser failures, share of suite | 8.8% to 12.0% | 11.2% | 4.5% | 1.0% (after discarding two invalid runs) |
| Copy, label or accessible-name mismatches | most of them | 0 of 36 | 3 of 19 | 0 of 5 |
| Behaviour the table did not state | several | 3 | 3 | 0 in the browser; 1 backend (non-string choice code) |
| Cause shared across many tests | no record | 32 of 36 | none | none in the valid run (the 150 were environmental) |
| Regression introduced by a fix | not recorded | 1 | 1 | 0 observed |
| Blocking defects found only by the verifier | n/a | n/a | 1 (NUL id) | 2 (CI control, spelling of ids in the companion) |

Reading: the first-run browser share was the lowest of the four, and none of the five failures was a copy or UI-state gap, which is what the UI states table and the request-count entry were meant to prevent. The verifier-only findings were outside the UI table (a CI step and an identifier-normalisation interaction between two features), so the table does not help there; the plan's file list and the "normalisation of identifiers" check did. Three of the five failures were tests that the independent test-designer was told to rewrite but missed, which points to a grep-based list in the plan being incomplete rather than to the spec template.

Limits: one feature, one run per arm, three different feature sizes, a larger suite than before (522 against 423 and 321 tests), and a first-run count that excludes two runs invalidated by the environment. The 1.0% is an observation, not evidence that the template helps in general.
