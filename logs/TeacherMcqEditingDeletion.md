# Teacher MCQ editing and unpublished-work deletion

## Approved start — 2026-11-04

The user approved real teacher authentication, versioned editing of three-question MCQ batches, confirmed permanent deletion of unpublished notes/batches, and deletion of unreferenced source materials. Any managing teacher may act. Publication, unpublishing, individual-question deletion and student-history changes are excluded.

Created `feat/tea03-edit-mcqs-delete-drafts` from clean master `da57eab` (PR16 authentication, after PR15 PostgreSQL storage). Approved specifications and user stories were committed as `0038b47` before application changes. Developer and independent test designer started from that identical commit in separate folders under Variant B.

Docker could not launch because its installed executable is missing. A sandboxed initdb attempt failed on shared-memory access; approved elevated commands created a separate temporary PostgreSQL cluster on loopback port 55439, database learnswe_test. Tests use isolated schemas. The developer database, original files and actual .env were untouched. No live LLM requests, deployment, push, PR publication or merge into master occurred.

## Independent evidence

- Baseline before source changes: 692 backend tests passed (101.81s), 224 browser tests passed (2.0m). The existing note Back/Forward test passed; no speculative navigation fix was made.
- Independent backend tests `b56bc12` and browser tests `3d80b0c` were committed before source visibility. Legacy authentication expectations were adapted in `260035e`, preserving stronger cookie/CSRF and access assertions.
- RED on old source: cookie-auth upload returned401 demanding the old demo header; anonymous teacher-data screen lacked the required sign-in guidance and fetched records.
- Developer source and product guides: `d19bdf4`. Types, lint, build, source formatting, compilation and 62 existing health/text/LLM tests passed before independent integration. Shared llm_client.py remained unchanged.
- Designer merged implementation only after committing tests (`5771e15`). Initial backend: 726 passed, one test-wire failure. httpx cannot directly encode a lone surrogate; `334367f` sends escaped JSON and retains the rejection assertion.

## Integration correction round 1 (cap: 2 total)

| Finding | Resolution |
|---|---|
| Over-limit MCQ fields hide their counters | `66ccbd8` keeps counters alongside validation/duplicate messages. |
| A dirty editor intercepts the session-expiry redirect, although private content clears | `66ccbd8` schedules expiry/logout navigation after protected views and blockers unmount. Normal unsaved-work protection and failed-logout behaviour remain. |
| Anonymous guidance locator includes its child link; initial-focus test assumes an unspecified button | Test fixtures target the alert container and verify focus lies inside the dialog, matching the approved contract. |
| Intermittent mobile Cancel failure after full-page screenshot | Event trace proves pointer-down on Cancel at scroll2558 but pointer-up/click on other fields after scroll1351. The app never receives Cancel. Visual capture is now the last action in separate tests; all functional Cancel/discard/delete/focus assertions remain. No application workaround. Fifteen focused mobile repetitions passed (`26b5874`). |

## Verification in progress

Final integrated backend: 727 passed (81.33s). Integrated types, lint, format and build passed. Final browser run: 245 passed (2.1m; 224 baseline plus 21 new, including separate visual checks). Tests merged into the run branch as `0ca14b1`. Parent inspected mobile light/desktop dark editors and mobile dark/desktop light confirmations: readable, visible controls, no horizontal overflow. Full-page modal captures paint fixed elements relative to the current viewport; functional focus assertions passed. Strongest read-only verifier is running against the frozen application/test tree.

The token tracker was run with the feature-branch filter but found no attributable requests. Its zero-row summary means unavailable measurement, not zero actual usage or cost. Final resource and handoff records will preserve this limitation.


## Independent review and correction round 2

The strongest read-only verifier reran the frozen tree: 727 backend passed (121.66s), 245 browser passed (2.2m), types/lint/format/build passed. Additional probes confirmed dirty successful logout clears/redirects and failed logout retains the editor. Review identified two blockers and stale guide wording:

1. Concurrent unsafe requests sharing an expired cookie both hold session FOR SHARE locks, then expired-session cleanup attempts DELETE lock upgrades. Probe returned503 and401 instead of two401 responses.
2. Successful note, MCQ and material deletion removes the original trigger, leaving keyboard focus on BODY instead of a surviving list heading.
3. UserGuide and DeveloperGuide still contained old demo-authorization statements.

Final correction round starts at `83d34c3` (application/test tree unchanged from0ca14b1). Independent regressions `94901d4`, with formatting-only `78622a5`, were committed before fixes. Backend RED reproduced503 instead of401 (1.51s); all three browser deletion-focus checks were RED. The developer was released to change application code only after these results. The fix must retain concurrent live-session writes, revocation protection and normal dirty navigation. A scoped verifier recheck is required after integration; no additional correction round remains beyond this one.
