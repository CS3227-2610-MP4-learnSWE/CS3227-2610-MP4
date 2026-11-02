# TEA-02 draft notes increment — 2026-11-01

## Request and approved decisions

User requested implementation of the Teacher Increment 2 plan after merging TEA-01 and updating master. This increment generates, saves and displays concise unpublished notes from one authorised source. Editing is deferred to TEA-03; MCQs, publication, student access, OCR and chunking are excluded. Oversized sources are rejected, never silently truncated. The shared llm_client.py remains unchanged. No live model calls authorised.

## Workflow

- Clean master baseline 6ab27e4; created feat/tea02-generate-notes.
- Spec-writer recorded the approved user plan, concrete independent-testing contract and shared-data reference in 68d7577, followed by refinements; final start commit 97ae30b11e534376ef3d6bcc456c78815fa92107.
- Developer works in the feature checkout; independent test-designer in sibling work/tea02-tests on test/tea02-notes, same start commit. Tests must be committed before seeing implementation. Independent read-only verifier follows integration.
- Found historical migration hazard: TEA-01 iterated live Base.metadata; plan freezes the original five-table set so adding drafts does not break fresh installs.

## Verification evidence

- Before implementation: backend343 passed using isolated PostgreSQL schema/private temporary files; frontend typecheck and lint passed.
- Developer source de1cc1c: existing backend343, frontend types/lint/build and changed-source formatting passed. Existing browser101 passed; one stale preview-only assertion is intentionally replaced in the independent tests.
- Independent test branch committed before integration (da6ed03 through af9b127); baseline generation test failed404 as expected before endpoint existed. Includes40 backend cases and11 new browser scenarios, plus replacement of the obsolete teacher-preview assertion while retaining admin preview checks.
- Independent integration: full backend383 and browser113 passed, with frontend typecheck/lint/format/build. Four initial browser failures were selectors assuming standalone text or an unchanged pending button label; only selectors were corrected while preserving behavior assertions. Tests merged into feature at6945eb5.
- Parent inspected populated screenshots at390/1440 widths in both light/dark themes: readable, responsive and no page overflow. Changed Markdown links resolve.
- Independent verifier round1 on6945eb5 re-ran383backend/113browser and types/lint/format/build successfully. Found one blocking AC7 omission (creator absent from saved-list entries), plus two nonblocking items (missing45s timeout regression; historical shared-contract wording). Narrow correction round1 underway, with independent creator/timeout regressions and documentation correction. No other backend/security/concurrency defect identified. No production database, private development file storage or live SoC LLM used by tests.

## Resource record

Primary orchestrator plus spec-writer, developer, independent test-designer, later verifier. Inherited model configuration; exact tokens/cost not available. No live LLM calls, push, PR, deployment or master merge authorised by this implementation request.

Correction tracking: source/doc fix de9738c adds creator to saved-list entries and clarifies historical shared-contract scope. Independent regression designer reactivated with followup task (initial queued messages to completed agent did not trigger execution; orchestration delay only). New timeout cases use fake clocks; no live provider tests.

Independent correction integration at06311ac: creator assertion proven RED at41c5fd0 against old application, GREEN afterde9738c; two fake-clock tests confirm20-second success and45-second abort with selections/old drafts preserved and no automatic POST retry. Full browser115 passed, with types/lint/format/build. Backend unchanged from verifier's383-pass run. Correction source was committed before the regression commit while the completed test-designer was being reactivated; the regression was independently exercised on old code before seeing the fix. This is a narrow tests-first timing deviation in correction round1, not in initial feature test isolation.

## Final result

Independent strongest-model verifier PASS at06311acc29e0e52ce3115085a09744d5dfafc6ad after one correction round, no open findings. Fresh final browser115 passed (55.8s), types/lint/format/build/diff checks passed. Backend unchanged from independently rerun383-pass revision. Parent inspected all four initial populated mobile/desktop light/dark screenshots; verifier inspected corrected mobile-dark/desktop-light. Shared llm_client.py is byte-for-byte unchanged from baseline. Relative Markdown links checked. Human review/publishing gate remains: no push, PR or merge to master performed; live provider quality not exercised.

Before trying the feature against an existing development database, from src/backend run `uv run --env-file .env alembic upgrade head`, then restart the backend with its existing environment. Teacher -> AI content studio now uses real authorised source records and persists draft notes. A configured SoC LLM is needed for a manual real generation; missing configuration returns a clear error. Editing, MCQs and publishing remain future work. Tests did not migrate or use the developer database/files.
