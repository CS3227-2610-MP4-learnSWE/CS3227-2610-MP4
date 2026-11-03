# Feature status

One row per feature in `docs/FeatureList.md` (plus workflow tooling). The orchestrator updates the row when a feature changes stage. State as of 2026-11-03 on `fix/teacher-postgres-file-storage`, with `master` at `da389a5` (PR 14) merged in. Details and history: `notes.md`, `notes-archive.md`.

Stages: not started, spec, build, verified (local), merged.

| ID | Stage | Branch | PR | Open items |
|---|---|---|---|---|
| STU-01 | not started | | | |
| STU-02 | merged | `feat/stu02-practice-api-workflow-b`, `feat/stu02-frontend-run-b` | 1–5 (numbers per `checklist.md`) | Placeholder identity and server-memory storage; no persistence or real login. |
| STU-03 | merged | `feat/stu03-run-b` | 8 | Live provider quality unchecked; no authenticated persistence of chat history. |
| STU-04 | not started | | | |
| STU-05 | not started | | | |
| STU-06 | not started | | | |
| TEA-01 | merged; database storage verified (local) | `feat/tea01-materials`, `fix/teacher-postgres-file-storage` | 10 | Migration-isolation review finding resolved; BYTEA branch awaits publishing approval. Placeholder identity header. |
| TEA-02 | merged (notes and MCQs) | `feat/tea02-generate-notes`, `feat/tea02-generate-mcqs` | 11, 13 | Live provider quality checked only by user report. |
| TEA-03 | partly merged (notes editing) | `feat/tea03-edit-notes` | 12 | MCQ editing, publishing and full revision history not built. |
| TEA-04 | not started | | | |
| TEA-05 | not started | | | |
| TEA-06 | not started | | | |
| ADM-01 | not started | | | |
| ADM-02 | not started | | | |
| ADM-03 | not started | | | |
| ADM-04 | not started | | | |
| ADM-05 | not started | | | |
| ADM-06 | not started | | | |
| SHR-01 | not started | | | Only the placeholder identity headers exist. |
| SHR-02 to SHR-05 | in progress per feature | | | Enforced and tested inside each feature so far; no cross-feature check yet. |
| OPT-01 to OPT-03 | not started | | | Outside the MVP. |
| CI-01 | merged | `chore/ci` | 4 | Deployment jobs blocked on hosting; see `deployment.md`. |
| TRK-01 | merged | `feat/token-tracker` | 2 | Prices must be checked against provider pricing. |
