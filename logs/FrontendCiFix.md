# Frontend CI maintenance, 2026-11-06

Role: developer, single-session small-fix exemption in workflow/coordination.md. Existing approved SHR-01 shell and STU-04 navigation contracts apply; no new feature contract or tests. Branch: feat/adm05-user-and-access-management.

The supplied CI log reports one hard failure (mobile Open companion) and one flaky Progress Back/Forward test, with 471 other passes. The short-height CSS rule hid the complete sidebar tip at a 700px viewport, including its actionable companion shortcut. Removed that rule; navigation already scrolls independently and the account footer remains fixed within the sidebar flex layout. Existing 500px desktop/mobile logout regressions pass.

Progress now includes the router location key in its loading effect dependencies, associating the request with the history entry rather than only mount/retry. The historical intermittent failure was not reproduced locally before this change; this is navigation lifecycle hardening, not proof of the original flake mechanism. Existing tests and assertions are unchanged.

Validation:
- Initial focused two-case run passed; CSS was edited while that diagnostic dev-server run was still active, so it is not an independent RED/GREEN run.
- Both reported tests repeated 20 times each: 40 passed, no retries (40.4 seconds), separate output directory.
- First full 473-case run against the reused local dev server: 472 passed, one unrelated STU-03 materials-page companion timeout. Snapshot shows login: an unmocked study request reached the running real backend and expired the mocked session. No CI/source regression inferred.
- Isolated full run: 473 passed (4.5 minutes), two workers, no retries. Temporary ignored config in node_modules/.cache uses port 5175 and API_PROXY_TARGET=http://127.0.0.1:1, reproducing the supplied CI no-backend environment without stopping the user's servers. No tracked config/test edits.
- Typecheck, lint and production build pass, repeated after the functional source changes.
- Raw format:check reports 96 existing CRLF-related warnings in this Windows checkout. Read-only Prettier checks after normalizing CRLF to LF: all 108 selected frontend files pass, including both changed source files. No mass reformat performed.
- git diff --check passes after removing a trailing blank line introduced by handoff rotation.

Diagnostics/recoveries: shell profile execution-policy warning avoided with non-login calls; one rg glob path did not expand on Windows; one inline Node audit lost quotes through PowerShell, recovered using stdin. Temporary-config recoveries: TypeScript under node_modules is unsupported by Node26, so changed the config to mjs; then supplied explicit frontend cwd because Playwright resolves webServer commands relative to the config. No backend suite, independent verifier, live AI, deployment, push, env or database changes. A source comment was added while the full dev-server suite ran; functional changes were present before the Progress cases ran.

Resources: inherited Codex model/effort; exact task token counts/cost unavailable. No subagents, tracker or multi-agent manifest for this maintenance exemption. No new feature revision rounds.
