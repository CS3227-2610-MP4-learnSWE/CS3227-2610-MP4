# Feature status

One row per feature in `docs/FeatureList.md` (plus workflow tooling). The orchestrator updates the row when a feature changes stage. State as of 2026-11-05 on `feat/tea03-publish-content`, with master `5d2b23d` (PR18/19) merged into preparation from `db82a18` (PR17). Details and history: `notes.md`, `notes-archive.md`.

Stages: not started, spec, build, verified (local), merged.

| ID | Stage | Branch | PR | Open items |
|---|---|---|---|---|
| STU-01 | merged | `feat/stu01-spec` | 18 | Seeded and teacher-published lessons use the same student workflow. Course membership remains required; ADM-05 access management is future. Known limits in `docs/DeveloperGuide.md`. |
| STU-02 | merged | `feat/stu02-practice-api-workflow-b`, `feat/stu02-frontend-run-b` | 1–5 (numbers per `checklist.md`) | Session authentication merged in PR16; practice records still use server memory. |
| STU-03 | merged | `feat/stu03-run-b` | 8 | Live provider quality unchecked; no authenticated persistence of chat history. |
| STU-04 | not started | | | |
| STU-05 | not started | | | |
| STU-06 | not started | | | |
| TEA-01 | merged | `feat/tea01-materials`, `fix/teacher-postgres-file-storage`, `feat/tea03-edit-mcqs-delete-drafts` | 10, 15, 17 | Upload/organisation/deletion and session auth merged. |
| TEA-02 | merged (notes and MCQs) | `feat/tea02-generate-notes`, `feat/tea02-generate-mcqs` | 11, 13 | Live provider quality checked only by user report. |
| TEA-03 | partly merged; publication verified (local) | `feat/tea03-publish-content` | 12, 17 | Notes/MCQ editing/deletion merged; immutable publication verified at380749e, strongest review PASS. Human push/PR/merge gate retained. |
| TEA-04 | verified (local; whole-batch publication) | `feat/tea03-publish-content` | | One batch of three questions = one immutable practice set; no assembly. Publishing verified at380749e; student attempt integration remains future. |
| TEA-05 | not started | | | |
| TEA-06 | not started | | | |
| ADM-01 | not started | | | |
| ADM-02 | not started | | | |
| ADM-03 | not started | | | |
| ADM-04 | not started | | | |
| ADM-05 | not started | | | |
| ADM-06 | not started | | | |
| SHR-01 | merged | `feat/shr01-auth-spec`, `feat/tea03-edit-mcqs-delete-drafts` | 16, 17 | Teacher session integration merged; deployment settings remain separate. |
| SHR-02 to SHR-05 | in progress per feature | | | Enforced and tested inside each feature so far; no cross-feature check yet. |
| OPT-01 to OPT-03 | not started | | | Outside the MVP. |
| CI-01 | merged | `chore/ci` | 4 | Deployment jobs blocked on hosting; see `deployment.md`. |
| TRK-01 | merged | `feat/token-tracker` | 2 | Prices must be checked against provider pricing. |
| CHK-01 | merged | `claude/spec-check-455c55` | 19 | Spec checker for the spec-writer rules; 289 tests pass; verifier NOT PASS in rounds 1 and 2, then a narrow round 3 passed after a user-approved final fix; Local merge checks enforce STU-01 and publication-preparation specs; GitHub CI for this branch not run. |
