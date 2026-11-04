# Retro: TEA-03 authenticated MCQ editing and draft deletion

Feature: TEA-03-mcqs-cleanup | Branch: feat/tea03-edit-mcqs-delete-drafts | PR: not published | Closed locally: 2026-11-04

## Revision rounds

Two correction rounds (cap2). Round1 fixed invalid-field counters and session-expiry redirect ordering. Round2 fixed expired-session lock upgrades, post-deletion keyboard focus and stale guide wording. Final strongest read-only verifier PASS at5df6934. Additional Docker/PostgreSQL16 full backend run passed728tests (104.65s); no CI execution claimed.

## Defects found

| Defect | Found by | Blocking? | Fixed in round |
|---|---|---|---|
| Invalid MCQ field hides its counter | Independent test designer | Yes, UI contract | 1 |
| Dirty editor blocks expiry redirect | Independent test designer | Yes | 1 |
| Concurrent expired-cookie mutations deadlock | Strongest verifier | Yes | 2 |
| Successful deletion loses keyboard focus | Strongest verifier | Yes, UI contract | 2 |
| Guides describe obsolete demo authorization | Strongest verifier | No | 2 |

## Resource use

Tracker run: yes, attempted branch filter; no matching attributed requests. Actual token/cost totals unavailable, not zero. Summary: ../../experiments/results/tea03-mcqs-cleanup.csv. Resource-log row: ../../experiments/resource-log.md. Inherited Codex roles and gpt-6-astra high verifier. Sandbox retry for test-cluster initialization; test-harness corrections documented in the session log.

## RED before GREEN

| Criterion or defect | Test commit (RED) | Fix commit (GREEN) |
|---|---|---|
| Cookie-only teacher identity and anonymous data guidance | b56bc12 / 3d80b0c, before implementation visibility | d19bdf4 |
| MCQ counter and expiry redirect | 3d80b0c (integrated tests) | 66ccbd8 |
| Concurrent expired requests both return401 | 94901d4 | 6c18dc9 |
| Note/MCQ/material deletion focus | 94901d4; material locator clarified340154a | 6c18dc9 |
| Remaining feature scenarios | Independently committed before source visibility; no individual RED claimed | Final integrated suites728backend /245browser PASS |

## Steps outside the pipeline

Parent created the branch/worktree, ran baseline checks, managed isolated test infrastructure, visually inspected captures, merged tests and maintained records. Developer and designer used the same approved0038b47 start. Source fixes waited for committed RED regressions in round2. The verifier was read-only throughout. No live provider calls or development-data changes.

Test-harness corrections preserved criteria: escaped surrogate JSON, accessible alert-container copy, focus inside the dialog rather than an unspecified initial button, and count-aware material-heading lookup. A full-page screenshot caused scroll restoration between pointer-down/up; separate last-action visual captures retain all functional Cancel/delete assertions. Fifteen focused mobile repetitions passed.

## What to change next time

- Keep exact accessible control/state contracts in workflow/templates/spec.md and plan.md; include focus after destructive-action success explicitly.
- In workflow/coordination.md test planning, include parallel expired sessions whenever adding authorization locks.
- Separate full-page visual captures from subsequent pointer interactions in long mobile forms.
