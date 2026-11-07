# Frontend CI repair: messaging debounce and practice picker - 2026-11-07

## Report and diagnosis

User supplied GitHub Actions output: 709 tests, 707 passed, two failed on both attempts. ADM-04's search/role test observed four recipient reads instead of three. STU-02's picker test observed the new shell unread-count request in addition to its single catalog read.

The picker mismatch reproduced locally before edits. The reported ADM-04 four-read failure did not reproduce in 10 normal or six 6x CPU-throttled diagnostic repetitions. Inspection found an unconditional 300ms initial no-op debounce; a new regression demonstrated that after selecting page 2 it reset the page to 1. This test failed before the source fix. Installing a fake clock after mounting also mixes pre-existing native timers with simulated timers; the original search test now installs its clock before navigation. Exact request-count and stale-response assertions are unchanged.

## Change

- Composer only debounces a changed trimmed search query. Unchanged initial input cannot reset pagination; a changed query still applies after 300ms and resets page once.
- Added the initial-search pagination regression and retained existing selected-recipient persistence checks.
- Picker integration explicitly expects one catalog read and one metadata-only shell unread summary, in either network order. Existing exact catalog count remains; unexpected study/course/progress/message-body requests still fail the assertion.
- Clarified STU-02 published-sets spec/plan to distinguish its one picker-data read from the already-approved shared shell summary. Updated UserGuide and DeveloperGuide. No server/schema/authentication/AI changes, no retries or timeouts increased.

## Verification

- Initial reproduction: picker request assertion RED; original search test passed locally. Diagnostic repeated original search: 10 normal + six CPU-throttled PASS (not proof that CI was healthy).
- New pagination regression RED before source edit, then GREEN.
- Four affected scenarios repeated five times: 20/20 PASS, no retries. Final clock-setup adjustment is included in the full suite below.
- Typecheck, lint, production build and scoped Prettier PASS; all 137 tracked frontend format targets pass after LF normalization (Windows working-copy line endings preserved). STU-02-published-sets spec checker: 1 checked, 0 failed, 0 waived.
- First full browser suite: 708/710 PASS, two failures, zero skips/flaky/retries (382.648s); both reported CI cases passed. It exposed a separate Overview Back test race: it waited for any h1 after the Practice URL changed, which could still be the old Overview heading before React committed the destination. Wait now names the exact Choose a practice set heading before Back; the original exact progress request-count assertions are retained. The message-recovery test also checked its recipient GET synchronously as soon as the new input rendered, before the effect dispatched; it now polls for the same exact one-GET count. Second full suite: 709/710 PASS, one failure, zero skips/flaky/retries (387.984s). A different Overview-to-Progress history test navigated while report data were pending; readOnce intentionally coalesced identical in-flight reads. It now awaits the initial Overview figures and the loaded Lesson progress region before navigating; its original >=3 count assertion is retained. Final third full suite: 710/710 PASS in 366.824s, zero failures/errors/skips/flaky/retries. JSON stats and all 710 result retry indexes verified.

Used isolated owned Playwright servers on ports 5197/5198, unused API_PORT=59999, two workers, zero retries, both mocked and demo-off projects. Build output and JSON evidence are ignored under node_modules/.cache. Temporary diagnostic spec and isolated test configuration removed. No user API/server processes, .env or database changes. No live AI. CI itself has not been rerun remotely; no commit or push requested.

Single-session small CI-maintenance exemption; no delegated agents or explicitly invoked project workflow, so no new invocation manifest/report. Model/effort inherited, exact per-task tokens/cost unavailable. Resource/handoff entries are recorded at closeout.
