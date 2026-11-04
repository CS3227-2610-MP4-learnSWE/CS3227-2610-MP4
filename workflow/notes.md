# Handoff notes

Newest entry first. Use `templates/handoff.md`. Older entries describe the state at the time; the newest entry supersedes their open/merged status. Keep the newest 10 entries here; older ones are in `notes-archive.md`. Feature state is in `STATUS.md`.

## 2026-11-04: Whole-batch publication scope preparation (orchestrator, single session)
- Clean masterdb82a18 confirms PR17 merged. Branchfeat/tea03-publish-content. User-approved change: all three questions in one reviewed batch become one practice set; no selection/mixing/assembly workflow. Actual publishing is not implemented by preparation.
- Docs/stories/shared contract aligned with implemented teacher auth/generation/editing/deletion and future publishing. UI builder/sidebar removed; /teacher/practice redirects to /teacher/generate?tab=questions. Studio states publishing unavailable. Current student runtime/backend unchanged; future set discovery/course checks/immutable version adapter explicitly required.
- Spec/test8350d2a RED before source614123a. Types/lint/format/build PASS; full247browser PASS (2.1m), strongest read-only review PASS plus38focusedpractice cases. One obsolete teacher-preview test adapted, retaining both explanation assertions. Small docs/preview cleanup uses AGENTS single-session exception; publishing implementation requires complete contract and VariantB.
- Next: preparation verified and committed locally; plan publishing API/schema/UI with student integration before application publishing code. No .env/devDB/liveLLM/push/PR/deployment. Log logs/BatchPublicationPreparation.md.
- Resource tracker attempted: no matching branch-attributed requests, actual tokens/cost unavailable. Existing PR17 completion handoff below is historical and its former publishing gate is superseded by the merge.

## 2026-11-04: Authenticated MCQ editing and unpublished deletion verified locally (orchestrator)
- Done on `feat/tea03-edit-mcqs-delete-drafts`: all teacher APIs use shared cookie/CSRF authentication and current course access; versioned three-question MCQ editing; confirmed permanent note/batch deletion; original-file deletion only without draft references. Source metadata and bytes delete atomically; quota/reference/version protections remain. Guides, stories, app help and shared contract updated. No publication/unpublishing or student-history changes.
- Workflow: clean master `da57eab` (PR16 after PR15); approved specification `0038b47`. Independent tests committed before source visibility; developer `d19bdf4`. Integration fixes `66ccbd8`; final regressions `94901d4` were RED before source `6c18dc9` and GREEN unchanged. Final integrated application/test tree `5df6934`.
- Verification: strongest read-only reviewer PASS at `5df6934`; fresh 728 backend / 245 browser tests, types/lint/format/build and extra expired-cookie/focus/logout probes passed. Two correction rounds used (cap2), no remaining findings. Isolated PostgreSQL14.24 checks passed; additional full Docker/PostgreSQL16 run also passed728backend (104.65s) after the user started Docker. Temporary native test cluster stopped; Docker development database untouched. No developer data, .env or live LLM touched.
- Try: from src/backend run `uv run --env-file .env alembic upgrade head`, restart the backend, refresh and sign in as a seeded teacher. Run auth.seed with existing SEED_* configuration if credentials have not been seeded. Existing data is preserved; no fresh database is needed for this additive migration.
- Next: human review/push/PR/merge gate. Implementation is committed locally; nothing pushed, published or deployed. See logs/TeacherMcqEditingDeletion.md and workflow/specs/TEA-03-mcqs-cleanup/retro.md.
- Resources: tracker attempted, no matching branch-attributed requests; actual tokens/cost unavailable (not zero). Inherited Codex roles plus gpt-6-astra high read-only verifier. Two application correction rounds; test-harness and sandbox retries documented in the session log.


## 2026-11-04: Authenticated MCQ editing/deletion build started (orchestrator)
- Approved user plan and spec0038b47; clean masterda57eab includes PR15 PostgreSQL storage and PR16 login. Branch feat/tea03-edit-mcqs-delete-drafts. Stories expanded for MCQ editing and unpublished note/batch/unused-source deletion.
- VariantB: spec-writer completed; developer mainfolder and independent designer work/mcq-cleanup-tests start from identical0038b47. Designer cannot see source until own tests committed. Strongest read-only verifier required after integration; max2 correction rounds; publishing human-gated.
- Baseline backend692PASS in isolated temporary PostgreSQL cluster localhost55439 (Docker executable unavailable); browser baseline pending. No .env/developer DB/liveLLM/deployment touched.
- Next: authenticated teacher transport/access, versioned MCQ editor and atomic confirmed deletions; integrate independent tests/review, then localcommit only. Details logs/TeacherMcqEditingDeletion.md.
- Resources: tracker pending; inherited Codex roles, tokens/cost not yet available; correction rounds0. One sandbox initdb retry with approval; no data workaround.



## 2026-11-03: Fix Alembic repeatable-read migration race (single session + verifier)
- Done: online Alembic engine explicitly uses READ COMMITTED before its first query, preventing stale version-table snapshots from bypassing locked empty-material guard. One-line source change; no new schema revision/API change.
- Evidence: independent reviewer confirmed prior defect; persistent regression6d8951e committed after RED and before source fix. Same regression GREEN, full505backendPASS. Strongest reviewer5migration casesPASS/no remaining findings. Docs/contract/plan updated; STATUS unblocked. Report logs/MigrationIsolationFix20261103.md.
- Next: human review/publishing gate; no current-database migration rerun needed solely for this engine setting. No developer DB/files/.env/live provider touched, nothing pushed. Frontend unchanged; prior160browser and frontendchecks not repeated.
- Resource use: tracker no (not measured), inherited Codex +gpt-6-astra high reviewer; tokens/cost unavailable; initial path/sandbox test launches corrected, verifier correction rounds0.




## 2026-11-03: Ponytail full PostgreSQL storage review (orchestrator)
- Review at63b02bf: one confirmed blocker, no other concrete correctness/conciseness findings. Under REPEATABLE READ database default, Alembic establishes a snapshot before material lock; a concurrent pre-lock legacy upload is missed and migration loses its old key.
- Next: set Alembic create_engine isolation_level="READ COMMITTED" and add pre-lock concurrent-writer regression with repeatable-read default. Temporary runtime fix probe preserved row/key/revision; no repository code fix applied.
- Evidence: fresh504backend/160browser/types/lint/format/build passed, but default-isolation tests miss this sequence. Isolated probe schemas cleaned; no developer data/.env/liveLLM/deployment. Report logs/PonytailDatabaseReview20261103.md.
- Resource use: tracker no (not measured), inherited Codex +gpt-6-astra high verifier, tokens/cost unavailable, application revision rounds0. Review only; no publishing.




## 2026-11-03: Fix Vite undefined backend port (single session)
- Done: proxy supports existing API_PROXY_TARGET, current API_PORT and default8000, in that precedence. Existing frontend env used old URL setting; master expected onlyport. README and four-case regression updated.
- Verification: pre-fix actual config assertion RED; focused regression GREEN; types/lint/format/build passed. Live backend health/proxied health/teacher courses all200. No actual.env edits or backend/data writes; full suites not repeated for config-only fix.
- Next: refresh frontend; restart npm run dev if old proxy persists. No publishing. Files: vite.config.ts, tests/vite-proxy.spec.ts, README, logs/ViteProxyFix20261103.md.
- Resource use: tracker no (unmeasured), inherited Codex, tokens/cost unavailable; wrong-workdir formatter cancelled then correct-dir checks passed; revision rounds0.




## 2026-11-03: Clean obsolete filesystem test scaffolding (single session)
- Done: removed unused session-wide upload-folder fixture, dead fixture/helper arguments and unused imports. Filename traversal assertions now use isolated tmp_path. Runtime storage.py still validates uploads; no unused runtime file was found for deletion.
- Verification:504backend passed; all213 assertions in four touched suites retained. No frontend/runtime/API changes; prior frontend checks not repeated. No user data/.env/old uploads/dependencies or migration/history files removed; legacy private-files ignore rule retained.
- Next: human publishing gate unchanged. Files: backend tests/conftest and four test suites, .gitignore comment, logs/DatabaseStorageCleanup20261103.md.
- Resource use: tracker no (not measured), inherited Codex model, tokens/cost unavailable, retries/revision rounds0. Small mechanical cleanup uses single-session workflow.




## 2026-11-03: Merge master into PostgreSQL storage branch (single session)
- Done: merged local master da389a5 (PR14 workflow/shared-helper refactors) into fix/teacher-postgres-file-storage. Retained PostgreSQL BYTEA/atomic uploads/quota/migration guards and master's teacher_access, timestamps, text normalisation, llm_errors and shared frontend transport.
- Conflict resolution: materials/notes/MCQ routers use shared teacher access; teacher_access drops obsolete storage_root requirement and retains READ COMMITTED for quota correctness. README/shared contract describe current BYTEA storage and shared helpers. Handoff history retained with older entries archived; STATUS updated.
- Verification:504backend tests passed in an isolated PostgreSQL schema;159mocked browser tests, types/lint/format/build and diff checks passed. Docker Desktop/test container restarted because stopped. No developer database/files/.env, live LLM, push or deployment.
- Next: human review/publishing gate; feature branch remains local. No open merge findings.
- Resource use: tracker run no (not measured); model inherited Codex; tokens/cost n/a (unavailable); one backend test launch retried after unavailable Docker, zero code-fix revision rounds.




## 2026-11-03: R4 and R5 duplication checks closed with no code change (single session)
- R4 (LLM error mapping): not duplicated across the teacher routers. `teacher_notes/generation._llm_error` is the one teacher mapping and `teacher_mcqs/generation.py` imports it. `companion_routes._map_error` is a second mapping with different codes (`rate_limited`, `companion_internal`) and student wording that tests assert, so merging would change error codes, which is out of scope. Optional follow-up: `teacher_mcqs` imports the private name `_llm_error` from `teacher_notes`; making it public or moving it to a small `llm_errors.py` would remove that.
- R5 (frontend requests): no service builds its own fetch, timeout or error handling. `companion.ts` and `practice.ts` call `request`; `teacherMaterials.ts`, `teacherMcqs.ts` and `teacherNotes.ts` call `requestTeacher`; `teacherGeneration.ts` only maps error codes to messages. The overlap is inside `client.ts`: `request` and `requestTeacher` each repeat the AbortController timeout and ApiError construction (they differ in headers and body parsing). `components/Shell.tsx` has one health-check `fetch`. Not changed; merging the two transports is a separate refactor that needs a decision.
- Follow-ups done on 2026-11-03 at the user's request, each on its own branch: `_llm_error` moved to `llm_errors.generation_error` (`refactor/r4-llm-errors`); `request` and `requestTeacher` share one private `send()` (`refactor/r5-client-transport`).
- Resource use: tracker run no; model Sonnet 5.5; total tokens and cost not measured yet; retries 0.




## 2026-11-02: Teacher PostgreSQL original-file storage complete locally (orchestrator)
- Done on fix/teacher-postgres-file-storage: originals in material_file BYTEA, metadata/content atomic, authorised original download and byte-based notes/MCQ extraction.10MiB/file and100MiB total raw-byte quota serialised with transaction advisory lock32272610 and READ COMMITTED. Missing content503; quota413 storage_quota_exceeded; UI limits/error/recovery and same endpoint/metadata contracts. No runtime FILE_STORAGE_DIR or permanent private-file writes.
- Migration:20261102_tea01_db_storage requires no material rows; ACCESS EXCLUSIVE table lock protects empty guard/DDL in both directions. Populated upgrade/downgrade refuses with data/schema/revision unchanged; no importer/delete/reset. Existing developer DB/files/.env untouched. Fresh setup documented: create learnswe_db_files, point DATABASE_URL there, migrate/seed; old uploads/drafts stay only in old DB/files. PostgreSQL backups include originals; monitor DB usage beyond100MiB file budget.
- Workflow: clean master6d65273/PR13; approved specstarta088945; sourcef80b086; independent tests6dff0a3 before app visibility, integratedabfd930. Historical storage spec banners and current guides/shared contract/env/CI/deployment/help updated. No new dependencies/shared LLM-client changes.
- Verification: strongest independent verifier PASS at1c7483370a02ccc6ae31c08e8416b81c5a7ba254, no blocking findings, one correction round. Fresh final499backend passed; verifier earlier159browser/types/lint/format/build remain applicable (only migration changed). Parent inspected390/1440 light/dark quota dialogs, readable/no overflow. Existing483backend test intent preserved plus16new cases;155browser plus4newquota/layout cases.
- Correction: verifier found concurrent legacy insert between empty guard and DDL could lose mapping. Independent8df7f8 regression RED before sourceccd808b lock fix, GREEN unchanged; full499backend passed. Contract clarificationd1b8de3 recorded. No other findings.
- Evidence: logs/TeacherDatabaseStorage.md and security/resource logs. Tests used isolated PostgreSQL schemas/tempfiles and fake LLM; no live provider, deployment, production auth or optional real-backend browser project checked.
- Next: human review/publishing gate. Local commits only; nothing pushed, no PR/master merge. Follow fresh-database README before starting this version; do not migrate the old populated database.
