# Feature status

One row per feature in `docs/FeatureList.md` (plus workflow tooling). The orchestrator updates the row when a feature changes stage. ADM-05 updated on 2026-11-06 on `feat/adm05-user-and-access-management`; other feature rows retain their recorded handoff state. Details and history: `notes.md`, `notes-archive.md`.

Stages: not started, spec, build, verified (local), merged.

| ID | Stage | Branch | PR | Open items |
|---|---|---|---|---|
| STU-01 | merged | `feat/stu01-spec` | 18 | Seeded and teacher-published lessons use the same student workflow. Course membership remains required; ADM-05 access management is verified locally on its feature branch. Known limits in `docs/DeveloperGuide.md`. |
| STU-02 | merged | `feat/stu02-practice-api-workflow-b`, `feat/stu02-frontend-run-b` | 1–5 (numbers per `checklist.md`) | Session authentication merged in PR16; practice records still use server memory. |
| STU-03 | merged | `feat/stu03-run-b` | 8 | Live provider quality unchecked; no authenticated persistence of chat history. |
| STU-04 | verified (local) | `claude/stu04-spec-4c7d06` | | Persistent practice attempts (PostgreSQL), `GET /api/progress`, Progress page, Overview with real figures. Verifier PASS in round 3 (user-authorised beyond the 2-round cap). Known limits: no cap on attempts per student, question reuse undecided, practice not course-scoped, a mounted page stays on the loading text after logout then an immediate Back. |
| STU-02-published-sets | verified (local); PR open | `claude/stu02-published-sets` | 28 | Student practice runs on teacher-published sets through one shared `set_provider` (course membership, uniform 404, 422 for malformed ids), picker page `/student/practice`, set page `/student/practice/<set id>`, dev seed, companion set lookup moved to the provider (nothing else in the companion). Verifier PASS in round 2 of 2. Edits to the teacher's TEA-03 files (two student routes, `seed.py`, one rewritten test): brief the teacher before merge. Open: `parse_uuid` accepts a space or underscore inside an id; unlimited retakes and question reuse undecided; two picker/progress Playwright tests have a click-then-Back race (`stu02ps-picker.spec.ts:410`, `stu04-progress.spec.ts:571`); real-backend Playwright and GitHub CI not run locally. |
| STU-05 | not started | | | |
| STU-06 | not started | | | |
| TEA-01 | merged | `feat/tea01-materials`, `fix/teacher-postgres-file-storage`, `feat/tea03-edit-mcqs-delete-drafts` | 10, 15, 17 | Upload/organisation/deletion and session auth merged. |
| TEA-02 | merged (notes and MCQs) | `feat/tea02-generate-notes`, `feat/tea02-generate-mcqs` | 11, 13 | Live provider quality checked only by user report. |
| TEA-03 | partly merged; publication verified (local) | `feat/tea03-publish-content` | 12, 17 | Notes/MCQ editing/deletion merged; immutable publication verified at380749e, strongest review PASS. Human push/PR/merge gate retained. |
| TEA-04 | verified (local; whole-batch publication) | `feat/tea03-publish-content` | | One batch of three questions = one immutable practice set; no assembly. Publishing verified at380749e; student attempt integration remains future. |
| TEA-05 | not started | | | |
| TEA-06 | not started | | | |
| ADM-01 | not started | | | |
| ADM-02 | build | `feat/adm02-targeted-feedback-forms` | | Revised spec/plan approved 2026-11-07 at 629f708; independent developer/test-designer started. Includes persistent private respondent autosave/resume and Completed state. Verification pending. |
| ADM-03 | not started | | | |
| ADM-04 | verified (local) | `feat/adm04-feedback-follow-up` | [31](https://github.com/CS3227-2610-MP4-learnSWE/CS3227-2610-MP4/pull/31) | Core strongest PASS; UI redesign/nav badge follow-up121backend/622browserPASS. Prior count-label finding fixed. [UI usage](usage/runs/2026-11-07-ADM04-UI-01/report.md); logs/Adm04UiRedesign.md. Remote CI/team review pending. |
| ADM-05 | verified (local) | `feat/adm05-user-and-access-management` | | Fixed-role account creation/lifecycle, courses with General topic, teacher/student assignments. Source `07deb57`; strongest verifier PASS; 391 browser tests, 968 backend cases covered across full/focused runs. Local commits only; apply migration before use. Evidence: `logs/Adm05Verification.md`. |
| ADM-06 | verified (local) | `feat/adm06-ai-usage-monitoring` | | Source c4df076; strongest verifier PASS at e85279e. Backend1169 PASS; all513 browser cases covered across full+focused recovery. Migration/restart/activation required; local only, human PR pending. [Retro](specs/ADM-06/retro.md), logs/Adm06Implementation.md. |
| SHR-01 | merged | `feat/shr01-auth-spec`, `feat/tea03-edit-mcqs-delete-drafts` | 16, 17 | Teacher session integration merged; deployment settings remain separate. |
| SHR-02 to SHR-05 | in progress per feature | | | Enforced and tested inside each feature so far; no cross-feature check yet. |
| OPT-01 to OPT-03 | not started | | | Outside the MVP. |
| CI-01 | merged | `chore/ci` | 4 | Deployment jobs blocked on hosting; see `deployment.md`. |
| TRK-01 | merged | `feat/token-tracker` | 2 | Prices must be checked against provider pricing. |
| TRK-02 | merged | `feat/token-tracker-invocation-report` | 20 | Invocation-level Markdown reports; team adoption requires each teammate to add local log IDs to the run manifest. |
| CHK-01 | merged | `claude/spec-check-455c55` | 19 | Spec checker for the spec-writer rules; 289 tests pass; verifier NOT PASS in rounds 1 and 2, then a narrow round 3 passed after a user-approved final fix; Local merge checks enforce STU-01 and publication-preparation specs; GitHub CI for this branch not run. |
