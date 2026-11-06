# Handoff notes

Newest entry first. Older entries describe the state at the time; the newest entry supersedes their open/merged status. Keep the newest 10 entries here; older ones are in `notes-archive.md`. Feature state is in `STATUS.md`.

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

## 2026-11-06: developer ADM-05 correction round 1
- Fixed: exact accessible field names now explicitly label the input elements, and select display names no longer include selected option text. Visible labels and required validation remain intact. Independent browser report identified these contract mismatches; tests were not read or changed.
- Validation: frontend typecheck/lint/build PASS. Independent designer previously reported backend 78 PASS and browser 8 PASS/4 FAIL before this correction; focused browser rerun remains designer-owned. Opaque account IDs already reject non-PostgreSQL text in the initial source commit.
- Files: AdminAccounts.tsx, AdminCourses.tsx, this note and implementation log. Next: designer rerun and verifier. Revision rounds used 1/2. Resource attribution remains orchestrator-owned, inherited model/effort and exact tokens/cost unavailable.

## 2026-11-06: developer ADM-05 implementation ready for independent verification
- Done: live Users/Courses pages, strict admin APIs, additive lifecycle migration, fixed-role account creation, disable/re-enable/archive/session invalidation, course creation and role-scoped memberships. Shared auth rejects inactive accounts; companion output rechecks fresh session/account. Guides include migration/manual walkthrough and validated public test-only password example. No tests changed/read from independent worktree.
- Validation: frontend typecheck/lint/build PASS; existing browser suite 376 PASS, 1 obsolete anonymous-admin route heading assertion FAIL (app.spec.ts:120). Existing SHR-01 historical seed migration tests 22 PASS after seeds were made independent of newer lifecycle columns; TEA-03 MCQ cleanup 36 PASS. Earlier full backend run was stopped at >89% because it began before the seed correction and retained imported old code; independent clean full rerun is required.
- Next: test-designer merges source and runs new/existing suites; orchestrator merges tests, then read-only verifier. Obsolete preview-only UI assertion belongs to test-designer; developer did not weaken it. No developer database migration, .env reads, live AI, push or deployment.
- Files: src/backend/admin_access, migration/auth lifecycle/session/login/seed/teacher access/companion integration; frontend admin pages/client/read hook/navigation/styles; UserGuide and DeveloperGuide.
- Invocation: adm05-developer-01; inherited model/effort, tokens/cost/session IDs unavailable; orchestrator owns run report under workflow/usage/runs/2026-11-06-ADM05-01. No application revision rounds yet. See logs/Adm05Implementation.md.

## 2026-11-06: spec-writer resynchronised expanded admin stories
- Done: preserved the user's newly expanded ADM-01 to ADM-04 and ADM-06 text exactly; reconciled only ADM-05 to the agreed six fixed-role stories, with labelled criteria and explicit scope boundaries. FeatureList ADM-01 to ADM-06 summaries now match the expanded stories.
- Contract: no endpoint, schema, UI, AC numbering or test mapping changes. Copied ADM-05 story criteria verbatim into spec AC1-19; derived AC20-22 unchanged. Teacher learning-results reporting remains TEA-05, outside ADM-05 implementation. Course joining/teacher approval decision was already resolved and remains so.
- Validation: speccheck ADM-05 PASS; diff check PASS; script asserted every character outside the ADM-05 section of UserStories was preserved from the user's supplied file. No application code or tests touched.
- Next: developer/test-designer continue against unchanged contract; orchestrator records invocation/report and verifies implementation.
- Files: docs/FeatureList.md, docs/UserStories.md, workflow/specs/ADM-05/spec.md and plan.md, this note and logs/Adm05AdminStorySynchronization.md.
- Resource use: follow-up spec-writer invocation; inherited model/effort, exact tokens/cost unavailable; tracker/report owned by orchestrator; no retries or application revision rounds.

## 2026-11-06: spec-writer ADM-05 agreed scope and approved contract
- Done: revised FeatureList/UserStories for fixed roles, admin-created accounts/courses, disable/archive lifecycle and course access; wrote ADM-05 spec, API/UI plan and ordered tasks. Approved functional decisions and implementation instruction supplied by user in conversation; no redundant approval gate inferred.
- Next: orchestrator starts independent developer/test-designer from this commit, then merged read-only verifier; no application code written by spec-writer.
- Files touched: docs/FeatureList.md, docs/UserStories.md, workflow/specs/ADM-05/{spec,plan,tasks}.md, workflow/notes.md.
- Decisions: immutable role; shared CourseMembership interpreted by role; no compulsory password change; archived email retained; serialised admin writes and fresh actor checks. AI recheck covers actual authorised context; no invented course mapping for legacy fixtures.
- Blocking findings: none. speccheck ADM-05 PASS; git diff --check PASS. Parent validated test-only example password using shared validator.
- Invocation ID: adm05-spec-01; model/effort inherited and exact provider IDs/tokens/cost unavailable; elapsed about 10 minutes; tracker owned by orchestrator at workflow/usage/runs/2026-11-06-ADM05-01; no retries or correction rounds.

## 2026-11-06: spec-writer advisory review of ADM-05
- Done: compared ADM-05 stories with SHR-01/STU-01 contracts and teammate handoff. Course membership is only one of three ADM-05 stories; account disabling and role changes must affect existing sessions' subsequent requests. No ADM-05 spec folder found.
- Next: agree teacher course-access semantics, account/session lifecycle, last-admin protections and concurrency policy; write and approve ADM-05 spec/plan before implementation.
- Files touched: this handoff and logs/Adm05PreImplementationReview.md. No application changes or tests; remote PR/CI status not checked.
- Invocation/report: single advisory Codex session; no feature run or agents. Model/effort, tokens and cost unavailable; tracker not run; retries/revision rounds 0.

Newest entry first. Use `templates/handoff.md`. Older entries describe the state at the time; the newest entry supersedes their open/merged status. Keep the newest 10 entries here; older ones are in `notes-archive.md`. Feature state is in `STATUS.md`.
