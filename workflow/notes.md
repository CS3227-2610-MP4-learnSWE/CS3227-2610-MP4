# Handoff notes

Newest entry first. Older entries describe the state at the time; the newest entry supersedes their open/merged status. Keep the newest 10 entries here; older ones are in `notes-archive.md`. Feature state is in `STATUS.md`.

## 2026-11-06: spec-writer ADM-06 draft contract
- Done: drafted AI service-attempt reporting, privacy-safe persistent metadata and coverage, independent recorded-token availability and accessible admin UI contracts. No application code/tests/SoC calls; spec and plan remain Draft.
- Next: human reviews UTC 31-day date range, grouped TEA-02 calls, forward-only coverage and fail-closed metadata reservation. Orchestrator resolves source-aware existing module/provider-field compatibility before independent designer/developer begin; no guessed provider availability.
- Validation: ADM-06 speccheck PASS (1 checked, 0 failed, 0 waived). Contract includes count/retry unit, pending/coverage gaps, no inferred tokens, auth/session/history/error states, concurrency and privacy tests.
- Files touched: workflow/specs/ADM-06/spec.md, plan.md, tasks.md; notes/archive handoff only.
- Invocation ID: 2026-11-06-ADM06-01-spec-writer-01. Source session: 01a1b002-09f9-7d50-8aaf-7b12499d0b9d. Model/effort inherited, exact attribution unavailable; elapsed: manifest timestamps authoritative.
- Feature-run report: workflow/usage/runs/2026-11-06-ADM06-01/report.md (orchestrator generates at run close).
- Resource use: tracker not run by spec-writer (orchestrator-owned); total tokens/cost unavailable until report. No retries or feature correction rounds. Blocking: human spec/plan approval and source-aware compatibility mapping; no feature implementation authorised through this draft.
## 2026-11-06: developer frontend CI maintenance
- Done: restored sidebar tip/companion shortcut in short viewports; Progress reads now depend on the router history-entry key as well as retry state. Existing approved shell/STU-04 contracts and all test assertions retained; both guides updated.
- Validation: isolated full browser suite 473/473 PASS (4.5 minutes, no retries); first reused-local-server run 472 PASS/1 unrelated backend-interference failure; 40 repeated reported cases PASS (20 each), types/lint/build and LF-normalized formatting of 108 frontend files PASS. Raw format check reports existing Windows CRLF warnings. Historical Progress flake not reproduced before source hardening; no proven original flake mechanism claimed.
- Next: review local commit and rerun remote frontend CI after push (not performed here). No backend or deployment changes.
- Files: styles.css, Progress.tsx, both guides, logs/FrontendCiFix.md and workflow records.
- Resources: single-session small-fix exemption; no agents/invocation manifest/report/tracker. Inherited Codex model/effort; exact tokens/cost/elapsed attribution unavailable. Diagnostic/configuration recoveries and profile warning; no new feature correction rounds. See session log for run timing caveats.

## 2026-11-06: developer shared sidebar/logout confirmation and spec synchronisation
- Done: dismissible sidebar guidance card and Confirm logout dialog for every signed-in role; cancellation makes no request, pending prevents duplicate/dismissal, failure keeps session/dialog for retry, expiry stays immediate. Dismissal is in-memory per role/account until refresh/remount. Prior toast/reset/details-overlay/sidebar fixes remain.
- Specs: SHR-01 original logout AC/current transport and follow-up spec/plan; ADM-05 AC23-27; STU-01/STU-04 inherited logout semantics; guides synchronised. RED five tests and contracts committedf1c9268 before source.
- Validation: 111 targeted browser PASS; visual five PASS with inspected tip-X/logout dialog images; types/lint/build/format/spec7/0/12existingwaivers/diff PASS. No server changes or backend/full-suite rerun; no independent verifier claim. Evidence logs/SharedShellConfirmationFollowup.md.
- Next: user refreshes frontend, dismisses tip with X and confirms/cancels logout. No env/database change or backend restart required. Local commit only; no push/deployment.
- Resources: single-session maintenance, no agents/manifest/tracker; inherited model/effort, per-task tokens/cost unavailable. No new feature revision rounds.

## 2026-11-06: developer ADM-05 UI and fresh-browser login follow-up
- Done: green creation toast, clear name/email/passwords while retaining role, immediate Account details modal with close/confirmation/focus behaviour, and visible aligned logout in short desktop/mobile windows. User-approved spec/plan and RED tests committed99c3c23 before source; no authentication-code/password changes.
- Login: recent saved student/teacher records enabled with hashes. Isolated real form creation/fresh browser login+reload PASS for both roles; user subsequently confirmed their own login works. Set ignored local development SESSION_COOKIE_SECURE=false for plain HTTP and user restarted. Initial credential401 cause not reproduced; do not conflate it with cookie loss after login.
- Validation: 227 backend PASS, 82 auth/admin browser PASS, four follow-up desktop/mobile cases PASS, two no-mock real-browser cases PASS; types/lint/build/format/spec7/0/12existingwaivers/diff PASS. Screenshots inspected. Details/recoveries: logs/Adm05UiFollowup.md.
- Files: AdminAccounts/styles, independent cookie/browser regressions and opt-in real E2E, approved contract/guides and workflow records. No user database writes/resets, production config changes, live AI, push or deployment.
- Next: refresh frontend; use Account details overlay and creation toast. Login works per user confirmation. Local commit only.
- Resource use: single-session scoped maintenance after feature closure; no agents/tracker/manifest. Inherited model/effort and per-task tokens/cost unavailable. Harness/test-interaction recoveries in session log, no extension of original feature correction rounds.

## 2026-11-06: developer resolved master/STU-04 merge into ADM-05
- Done: merged master eccc8f0 into ADM-05, preserving both routers, both private-cache protections and both guide/handoff histories. Added no-op20261106_merge_adm05_stu04 joining both unchanged historical heads; populated upgrade tests cover retained disabled accounts and saved attempts. Feature migration tests pin their own revisions; auth/progress browser helpers isolate unrelated API requests from a running local backend.
- Validation: 209 focused backend PASS, 173 focused browser PASS; types/lint/build/line-ending-aware formatting/diff/conflict checks PASS; speccheck7/0/12existingwaivers. No complete post-merge suite or independent verifier pass claimed. Exact recoveries in logs/Adm05Stu04MasterMerge.md.
- Next: user applies uv run --env-file .env alembic upgrade head, restarts backend and starts frontend in a second terminal; sign in with their own configured admin credentials and follow Users/Courses smoke checks. Local merge only, no push.
- Files: five conflict resolutions, additive merge migration/regression, pinned feature migration tests, browser fixture isolation and workflow/session records. No agent changes to developer env/database/seeds/live AI/unrelated worktrees.
- Resources: single-session merge-maintenance exemption, no agents/manifest/tracker; inherited model/effort, exact per-task tokens/cost unavailable. One incomplete broad run, fixture recoveries and redundant diagnostic backend rerun recorded; no new feature correction rounds.

## 2026-11-06: developer documentation follow-up for local ADM-05 login/testing
- Done: added step-by-step UserGuide/DeveloperGuide env, Docker/database, migrate/seed/reset, restart and sign-in walkthroughs. Explain no default admin credentials, unchanged seed hashes, all-configured-role reset scope, quoted public example password, frontend Origin/proxy settings and 401/403/429/503 recovery. Added focused/full automated test commands and isolated test-run directories.
- Validation: 15 PowerShell command blocks parse; temporary sample env quoting/password/origin check PASS; diff check PASS. Documentation only, no runtime tests or developer .env/DB/process changes. One temporary-env argument-format retry; no application correction rounds.
- Next: user follows docs/UserGuide.md local sign-in setup, then account/course checks; DeveloperGuide includes fresh database and automated testing steps.
- Files: UserGuide, DeveloperGuide, logs/Adm05LoginTestingWalkthrough.md, notes/archive and resource log. Single-session documentation exemption; no agents/run manifest. Inherited Codex model/effort, per-task tokens/cost and elapsed attribution unavailable; tracker not run for this docs-only follow-up.

## 2026-11-06: orchestrator ADM-05 verified and committed locally
- Done: synchronised the user's expanded admin stories, preserved ADM-01?04/ADM-06 text, and implemented fixed-role account creation/lifecycle, courses with atomic General topic, student enrolments and teacher management assignments. No promotion/demotion or password-change flow. Source `07deb57`; strongest read-only verifier PASS, no remaining defects. Two application correction rounds used.
- Evidence: clean full browser 391/391 PASS; all 968 final backend cases covered across full/focused runs, including 87 ADM-05 cases. Historical publication migration assumptions corrected without weakening; Windows TEMP and browser harness collisions recovered. Types/lint/build, all-spec check 6/0/12existingwaivers, diff and line-ending-aware formatting PASS. See logs/Adm05Verification.md and workflow/security/test-log.md.
- Next: human may test using UserGuide/DeveloperGuide. Apply `uv run --env-file .env alembic upgrade head` in src/backend before restarting backend. Local commits only; no remote PR/push/deployment performed. Course-aware companion retrieval, TEA-05 reporting and other admin workflows remain outside this implementation.
- Files: feature/stories/spec/plan/tasks; admin backend/frontend and shared authentication; additive migration; independent tests and guides; status/security/session/resource records. Developer .env/schema/live AI and unrelated .claude/worktrees untouched.
- Invocation IDs: 2026-11-06-ADM05-01 manifest has 12 invocations, including interrupted/resumed developer and spec resynchronisations. Parent gpt-6.1-sol observed; others inherited; requested verifier gpt-6-astra high. Elapsed intervals in report include interruption/idle time where observed.
- Feature-run report: workflow/usage/runs/2026-11-06-ADM05-01/report.md. Tracker run yes; matched parent subtotal 543 requests, 598671 input, 59384448 cache-read, 137384 output (27251 reasoning subset), including prior advisory discussion. Child attribution and whole-run tokens/cost unavailable; zero usage is not claimed. Two correction rounds; environmental command recoveries listed in verification log.

## 2026-11-06: developer ADM-05 final correction round 2
- Fixed verifier blocker after independent RED regression: generic client requests capture their originating session generation, and a delayed 401 only clears authentication when it still belongs to the active session. An account A response cannot log out newly signed-in account B.
- Validation: frontend typecheck/lint/build PASS; existing auth-guard, STU-01 session isolation and teacher HTTP cache suites 32 PASS (40 seconds). Independent new regression and final full suites remain designer/verifier-owned. No tests inspected or edited.
- Files: services/client.ts, this handoff and implementation log. Revision rounds used 2/2; additional blocking source findings must escalate. Resource attribution remains orchestrator-owned, exact model/effort/tokens/cost unavailable.

## 2026-11-06: developer ADM-05 correction 1 integration follow-up
- Fixed after approved General-topic amendment and independent RED regression: course creation now adds one General topic atomically, so assigned teachers can use existing publishing forms immediately. Guides updated. Existing courses unchanged.
- Mobile account rows now stack identity, role/status and action within the viewport; clicking Manage no longer scrolls name/email out of the horizontal table. Original screenshot issue was action-induced internal scrolling, not a hidden-column CSS rule.
- Validation: typecheck/lint/build and Python compilation PASS. Designer owns new regression/full rerun and fresh visual capture. Tests not inspected/edited. Same correction1 batch; no additional revision round. Resource attribution remains orchestrator-owned.

## 2026-11-06: spec-writer ADM-05 usable new-course integration
- Done: extended the course-creation story criterion and matching spec AC16 to require an automatic same-course General topic, atomically created with each new course. Existing teacher publishing requires a topic, while topic creation is not otherwise exposed.
- Contract: account and course API shapes and admin UI unchanged. Reuse Topic, do not alter existing courses, and create no publication automatically. Teacher workflow/guide integration should demonstrate General after teacher assignment; no topic-management feature added.
- Next: developer implements atomic Course/Topic creation; independent designer regresses same-course topic visibility/publication compatibility and rollback. Orchestrator owns follow-up invocation/report.
- Validation: ADM-05 speccheck and diff check PASS. Files: UserStories, ADM-05 spec/plan, this note and synchronization log. No app/tests/guides touched by spec-writer.
- Resource use: inherited model/effort; exact tokens/cost unavailable; no retries or application correction rounds in this documentation invocation.
