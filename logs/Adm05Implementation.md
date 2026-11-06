# ADM-05 developer implementation — 2026-11-06

Role: developer generator, from approved ADM-05 spec/plan and synchronized fixed-role stories. Independent tests remain isolated and were not inspected or edited.

Implemented real admin Users/Courses screens and API; immutable-role account creation with shared validators/hashing; enabled/disabled/archived state; session revocation and fresh login; permanent archive preserving records/email; serialized admin mutations and fresh actor checks; self/last-admin protections; course creation and student/teacher memberships; filtering/search/pagination; exact error/confirmation/retry UI. Session issuance shares the lifecycle transaction lock to prevent login/disable races. Existing teacher generation rechecks membership; student companion now rechecks session/account before releasing generated text. Static fixture practice still has no course retrieval.

The additive migration extends existing users without deleting records. Seed commands use explicit historical core columns so old migration tests remain usable. Existing guides now explain setup, manual scenarios and the public test-only password example.

Checks: Python compilation and single Alembic head PASS. Frontend typecheck, lint, production build PASS. Existing Playwright suite: 376 passed, 1 failed in 4.7 minutes; the failure is the obsolete unauthenticated admin preview-route heading assertion at app.spec.ts:120. Historical SHR-01 seed migration regression: 22 passed; TEA-03 MCQ cleanup: 36 passed. A full backend run started before the seed compatibility fix was stopped past 89%; its setup errors are not a clean final result. Independent verification must rerun the entire suite from the committed source. No test was edited to hide a failure.

Two npm invocations were mistakenly issued from repository root and returned missing-package.json; corrected by running in src/frontend. Initial lint reported an unused removed-preview prop; it was removed and subsequent lint passed. No secrets, developer .env contents or live model calls were used. No remote Git/deployment actions performed. Automated tests used isolated PostgreSQL schemas on the documented local Docker service.

Resource use: inherited Codex model/effort and exact token/cost values unavailable; no subagents launched by developer. Orchestrator owns manifest/report. No implementation revision rounds yet.
