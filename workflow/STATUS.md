# Feature status

One row per feature in `docs/FeatureList.md` (plus workflow tooling). The orchestrator updates the row when a feature changes stage. State as of 2026-11-04 on `feat/tea03-edit-mcqs-delete-drafts`, from `master` at `da57eab` (PR16, after PR15). Details and history: `notes.md`, `notes-archive.md`.

Stages: not started, spec, build, verified (local), merged.

| ID | Stage | Branch | PR | Open items |
|---|---|---|---|---|
| STU-01 | not started | | | |
| STU-02 | merged | `feat/stu02-practice-api-workflow-b`, `feat/stu02-frontend-run-b` | 1–5 (numbers per `checklist.md`) | Session authentication merged in PR16; practice records still use server memory. |
| STU-03 | merged | `feat/stu03-run-b` | 8 | Live provider quality unchecked; no authenticated persistence of chat history. |
| STU-04 | not started | | | |
| STU-05 | not started | | | |
| STU-06 | not started | | | |
| TEA-01 | merged; cleanup/auth verified (local) | `feat/tea03-edit-mcqs-delete-drafts` | 10, 15 | PostgreSQL originals merged. Auth integration and unused-source deletion verified locally; human publishing gate. |
| TEA-02 | merged (notes and MCQs) | `feat/tea02-generate-notes`, `feat/tea02-generate-mcqs` | 11, 13 | Live provider quality checked only by user report. |
| TEA-03 | partly merged; editing/deletion verified (local) | `feat/tea03-edit-mcqs-delete-drafts` | 12 | MCQ editing and unpublished deletion verified; [retro](specs/TEA-03-mcqs-cleanup/retro.md). Publication remains future; human publishing gate. |
| TEA-04 | not started | | | |
| TEA-05 | not started | | | |
| TEA-06 | not started | | | |
| ADM-01 | not started | | | |
| ADM-02 | not started | | | |
| ADM-03 | not started | | | |
| ADM-04 | not started | | | |
| ADM-05 | not started | | | |
| ADM-06 | not started | | | |
| SHR-01 | merged; teacher integration verified (local) | `feat/shr01-auth-spec`, `feat/tea03-edit-mcqs-delete-drafts` | 16 | Login/student integration merged; teacher cookie/CSRF integration verified locally. |
| SHR-02 to SHR-05 | in progress per feature | | | Enforced and tested inside each feature so far; no cross-feature check yet. |
| OPT-01 to OPT-03 | not started | | | Outside the MVP. |
| CI-01 | merged | `chore/ci` | 4 | Deployment jobs blocked on hosting; see `deployment.md`. |
| TRK-01 | merged | `feat/token-tracker` | 2 | Prices must be checked against provider pricing. |
| CHK-01 | verified (local), not merged | `claude/spec-check-455c55` | | Spec checker for the spec-writer rules; 289 tests pass; verifier NOT PASS in rounds 1 and 2, then a narrow round 3 passed after a user-approved final fix; CI job not yet run on GitHub; STU-01 specs enforced after merge. |
